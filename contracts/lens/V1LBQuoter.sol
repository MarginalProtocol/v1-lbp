// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {LiquidityAmounts} from "@uniswap/v3-periphery/contracts/libraries/LiquidityAmounts.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";

import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";
import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";

import {PeripheryImmutableState} from "../base/PeripheryImmutableState.sol";

import {RangeMath} from "../libraries/RangeMath.sol";
import {PoolAddress} from "../libraries/PoolAddress.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

import {IMarginalV1LBSupplier} from "../interfaces/IMarginalV1LBSupplier.sol";
import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";
import {IV1LBReceiverQuoter} from "../interfaces/receiver/IV1LBReceiverQuoter.sol";
import {IV1LBRouter} from "../interfaces/IV1LBRouter.sol";
import {IV1LBQuoter} from "../interfaces/IV1LBQuoter.sol";

contract V1LBQuoter is
    IV1LBQuoter,
    PeripheryImmutableState,
    PeripheryValidation
{
    /// @inheritdoc IV1LBQuoter
    address public owner;

    /// @inheritdoc IV1LBQuoter
    mapping(address => address) public receiverQuoters;

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    event OwnerChanged(address indexed oldOwner, address indexed newOwner);
    event ReceiverQuoterChanged(
        address indexed oldReceiverQuoter,
        address indexed newReceiverQuoter
    );

    error Unauthorized();

    constructor(
        address _factory,
        address _marginalV1Factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _marginalV1Factory, _WETH9) {
        owner = msg.sender;
    }

    /// @dev Returns the pool for the given token pair, and fee. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) private view returns (IMarginalV1LBPool) {
        return IMarginalV1LBPool(PoolAddress.getAddress(factory, poolKey));
    }

    /// @inheritdoc IV1LBQuoter
    function setOwner(address _owner) external onlyOwner {
        emit OwnerChanged(owner, _owner);
        owner = _owner;
    }

    /// @inheritdoc IV1LBQuoter
    function setReceiverQuoter(
        address receiverDeployer,
        address receiverQuoter
    ) external onlyOwner {
        emit ReceiverQuoterChanged(
            receiverQuoters[receiverDeployer],
            receiverQuoter
        );
        receiverQuoters[receiverDeployer] = receiverQuoter;
    }

    /// @inheritdoc IV1LBQuoter
    function quoteCreateAndInitializePool(
        IMarginalV1LBSupplier.CreateAndInitializeParams calldata params
    )
        external
        view
        returns (
            uint256 shares,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidity,
            uint160 sqrtPriceX96,
            uint160 sqrtPriceLowerX96,
            uint160 sqrtPriceUpperX96
        )
    {
        // check create pool errors
        if (params.tokenA == params.tokenB) revert("Invalid tokens");

        // check finalizer and receiver errors
        if (params.finalizer == address(0)) revert("Invalid finalizer");
        if (params.receiverDeployer == address(0)) revert("Invalid receiver");

        // sqrtPriceX96 from param ticks
        if (params.tickLower >= params.tickUpper) revert("Invalid ticks");
        sqrtPriceX96 = TickMath.getSqrtRatioAtTick(params.tick);
        sqrtPriceLowerX96 = TickMath.getSqrtRatioAtTick(params.tickLower);
        sqrtPriceUpperX96 = TickMath.getSqrtRatioAtTick(params.tickUpper);

        // calculate liquidity using range math
        liquidity = LiquidityAmounts.getLiquidityForAmounts(
            sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96,
            sqrtPriceX96 == sqrtPriceLowerX96 ? params.amountDesired : 0, // reserve0
            sqrtPriceX96 == sqrtPriceLowerX96 ? 0 : params.amountDesired // reserve1
        );

        // calculate shares minted and amounts in on pool initialize
        if (
            sqrtPriceX96 != sqrtPriceLowerX96 &&
            sqrtPriceX96 != sqrtPriceUpperX96
        ) revert("Invalid sqrtPriceX96");
        if (liquidity <= PoolConstants.MINIMUM_LIQUIDITY)
            revert("Invalid liquidityDelta");

        // amounts in adjusted for concentrated range position price limits
        (amount0, amount1) = RangeMath.toAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
        if (sqrtPriceX96 != sqrtPriceUpperX96) amount0 += 1; // rough round up on amounts in when add liquidity
        if (sqrtPriceX96 != sqrtPriceLowerX96) amount1 += 1;

        shares = liquidity;

        address receiverQuoter = receiverQuoters[params.receiverDeployer];
        if (receiverQuoter == address(0)) revert("Receiver quoter not set");

        (
            uint256 amount0Receiver,
            uint256 amount1Receiver
        ) = IV1LBReceiverQuoter(receiverQuoter).seeds(
                liquidity,
                sqrtPriceX96,
                sqrtPriceLowerX96,
                sqrtPriceUpperX96
            );

        amount0 += amount0Receiver;
        amount1 += amount1Receiver;

        if (amount0 < params.amount0Min) revert("Amount0 less than min");
        if (amount1 < params.amount1Min) revert("Amount1 less than min");
    }

    /// @inheritdoc IV1LBQuoter
    function quoteExactInputSingle(
        IV1LBRouter.ExactInputSingleParams memory params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            bool finalizedAfter
        )
    {
        bool zeroForOne = params.tokenIn < params.tokenOut;
        IMarginalV1LBPool pool = getPool(
            PoolAddress.PoolKey({
                token0: zeroForOne ? params.tokenIn : params.tokenOut,
                token1: zeroForOne ? params.tokenOut : params.tokenIn,
                tickLower: params.tickLower,
                tickUpper: params.tickUpper,
                supplier: params.supplier,
                blockTimestampInitialize: params.blockTimestampInitialize
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            ,
            bool finalized
        ) = pool.state();
        if (finalized) revert("Finalized");

        uint160 sqrtPriceLimitX96 = params.sqrtPriceLimitX96 == 0
            ? (
                zeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
            : params.sqrtPriceLimitX96;

        if (
            params.amountIn == 0 ||
            params.amountIn >= uint256(type(uint256).max)
        ) revert("Invalid amountIn");
        int256 amountSpecified = int256(params.amountIn);

        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceLimitX96");

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            liquidity,
            sqrtPriceX96,
            zeroForOne,
            amountSpecified
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert("sqrtPriceX96Next exceeds limit");

        // clamp if exceeds lower or upper range limits
        (uint160 sqrtPriceLowerX96, uint160 sqrtPriceUpperX96) = (
            pool.sqrtPriceLowerX96(),
            pool.sqrtPriceUpperX96()
        );
        bool clamped;
        if (sqrtPriceX96Next < sqrtPriceLowerX96) {
            sqrtPriceX96Next = sqrtPriceLowerX96;
            clamped = true;
        } else if (sqrtPriceX96Next > sqrtPriceUpperX96) {
            sqrtPriceX96Next = sqrtPriceUpperX96;
            clamped = true;
        }

        // amounts without fees
        (int256 amount0, int256 amount1) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next
        );
        amountOut = uint256(-(zeroForOne ? amount1 : amount0));
        if (amountOut < params.amountOutMinimum) revert("Too little received");

        // account for clamping
        amountIn = !clamped
            ? params.amountIn
            : uint256(zeroForOne ? amount0 : amount1);

        // calculate liquidity, sqrtP, finalized after
        liquidityAfter = liquidity;
        sqrtPriceX96After = sqrtPriceX96Next;
        finalizedAfter = (sqrtPriceX96Next == pool.sqrtPriceFinalizeX96());
    }

    /// @inheritdoc IV1LBQuoter
    function quoteExactOutputSingle(
        IV1LBRouter.ExactOutputSingleParams memory params
    )
        external
        view
        checkDeadline(params.deadline)
        returns (
            uint256 amountIn,
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            bool finalizedAfter
        )
    {
        bool zeroForOne = params.tokenIn < params.tokenOut;
        IMarginalV1LBPool pool = getPool(
            PoolAddress.PoolKey({
                token0: zeroForOne ? params.tokenIn : params.tokenOut,
                token1: zeroForOne ? params.tokenOut : params.tokenIn,
                tickLower: params.tickLower,
                tickUpper: params.tickUpper,
                supplier: params.supplier,
                blockTimestampInitialize: params.blockTimestampInitialize
            })
        );

        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            ,
            bool finalized
        ) = pool.state();
        if (finalized) revert("Finalized");

        uint160 sqrtPriceLimitX96 = params.sqrtPriceLimitX96 == 0
            ? (
                zeroForOne
                    ? TickMath.MIN_SQRT_RATIO + 1
                    : TickMath.MAX_SQRT_RATIO - 1
            )
            : params.sqrtPriceLimitX96;

        if (
            params.amountOut == 0 ||
            params.amountOut >= uint256(type(uint256).max)
        ) revert("Invalid amountOut");
        int256 amountSpecified = -int256(params.amountOut);

        if (
            zeroForOne
                ? !(sqrtPriceLimitX96 < sqrtPriceX96 &&
                    sqrtPriceLimitX96 > SqrtPriceMath.MIN_SQRT_RATIO)
                : !(sqrtPriceLimitX96 > sqrtPriceX96 &&
                    sqrtPriceLimitX96 < SqrtPriceMath.MAX_SQRT_RATIO)
        ) revert("Invalid sqrtPriceLimitX96");

        uint160 sqrtPriceX96Next = SqrtPriceMath.sqrtPriceX96NextSwap(
            liquidity,
            sqrtPriceX96,
            zeroForOne,
            amountSpecified
        );
        if (
            zeroForOne
                ? sqrtPriceX96Next < sqrtPriceLimitX96
                : sqrtPriceX96Next > sqrtPriceLimitX96
        ) revert("sqrtPriceX96Next exceeds limit");

        // error if exceeds lower or upper range limits
        (uint160 sqrtPriceLowerX96, uint160 sqrtPriceUpperX96) = (
            pool.sqrtPriceLowerX96(),
            pool.sqrtPriceUpperX96()
        );
        if (
            sqrtPriceX96Next < sqrtPriceLowerX96 ||
            sqrtPriceX96Next > sqrtPriceUpperX96
        ) revert("Invalid sqrtPriceX96Next");

        // amounts without fees
        (int256 amount0, int256 amount1) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceX96Next
        );
        amountOut = uint256(-amountSpecified);
        amountIn = uint256(zeroForOne ? amount0 : amount1);
        if (amountIn > params.amountInMaximum) revert("Too much requested");

        // calculate liquidity, sqrtP, finalized after
        liquidityAfter = liquidity;
        sqrtPriceX96After = sqrtPriceX96Next;
        finalizedAfter = (sqrtPriceX96Next == pool.sqrtPriceFinalizeX96());
    }
}
