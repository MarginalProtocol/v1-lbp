// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {LiquidityAmounts} from "@uniswap/v3-periphery/contracts/libraries/LiquidityAmounts.sol";

import {RangeMath} from "../libraries/RangeMath.sol";
import {PoolConstants} from "../libraries/PoolConstants.sol";

import {IMarginalV1LBSupplier} from "../interfaces/IMarginalV1LBSupplier.sol";
import {IV1LBReceiverQuoter} from "../interfaces/receiver/IV1LBReceiverQuoter.sol";
import {IV1LBQuoter} from "../interfaces/IV1LBQuoter.sol";

contract V1LBQuoter is IV1LBQuoter {
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

    constructor() {
        owner = msg.sender;
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
}
