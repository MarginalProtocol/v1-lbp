// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * @title V1LBRouter
 * @author Uniswap Labs
 *
 * @dev Fork of Uniswap V3 periphery SwapRouter for swaps on Marginal V1 liquidity bootstrapping pools.
 */
pragma solidity =0.8.15;
pragma abicoder v2;

import {SafeCast} from "@uniswap/v3-core/contracts/libraries/SafeCast.sol";
import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";

import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";
import {SelfPermit} from "@uniswap/v3-periphery/contracts/base/SelfPermit.sol";

import {IMarginalV1SwapCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SwapCallback.sol";

import {IV1LBRouter} from "./interfaces/IV1LBRouter.sol";
import {IMarginalV1LBPool} from "./interfaces/IMarginalV1LBPool.sol";

import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PeripheryPayments} from "./base/PeripheryPayments.sol";

import {CallbackValidation} from "./libraries/CallbackValidation.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";

/// @title Marginal v1 liquidity bootstrapping router
/// @notice Facilitates swaps on Marginal v1 liquidity bootstrapping pools
/// @dev Fork of the Uniswap v3 periphery SwapRouter
contract V1LBRouter is
    IV1LBRouter,
    IMarginalV1SwapCallback,
    PeripheryImmutableState,
    PeripheryPayments,
    PeripheryValidation,
    Multicall,
    SelfPermit
{
    using SafeCast for uint256;

    /// @dev Used as the placeholder value for amountInCached, because the computed amount in for an exact output swap
    /// can never actually be this value
    uint256 private constant DEFAULT_AMOUNT_IN_CACHED = type(uint256).max;

    /// @dev Transient storage variable used for returning the computed amount in for an exact output swap.
    uint256 private amountInCached = DEFAULT_AMOUNT_IN_CACHED;

    constructor(
        address _factory,
        address _marginalV1Factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _marginalV1Factory, _WETH9) {}

    /// @dev Returns the pool for the given token pair, and fee. The pool contract may or may not exist.
    function getPool(
        PoolAddress.PoolKey memory poolKey
    ) private view returns (IMarginalV1LBPool) {
        return IMarginalV1LBPool(PoolAddress.getAddress(factory, poolKey));
    }

    struct SwapCallbackData {
        PoolAddress.PoolKey poolKey;
        address tokenIn;
        address tokenOut;
        address payer;
    }

    /// @inheritdoc IMarginalV1SwapCallback
    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata _data
    ) external override {
        require(amount0Delta > 0 || amount1Delta > 0); // swaps entirely within 0-liquidity regions are not supported
        SwapCallbackData memory data = abi.decode(_data, (SwapCallbackData));
        CallbackValidation.verifyCallback(factory, data.poolKey);

        require(
            data.tokenIn == data.poolKey.token0 ||
                data.tokenIn == data.poolKey.token1,
            "tokenIn not in poolKey"
        );
        require(
            data.tokenOut == data.poolKey.token0 ||
                data.tokenOut == data.poolKey.token1,
            "tokenOut not in poolKey"
        );
        (address tokenIn, address tokenOut) = (data.tokenIn, data.tokenOut);

        (bool isExactInput, uint256 amountToPay) = amount0Delta > 0
            ? (tokenIn < tokenOut, uint256(amount0Delta))
            : (tokenOut < tokenIn, uint256(amount1Delta));
        if (isExactInput) {
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        } else {
            amountInCached = amountToPay;
            tokenIn = tokenOut; // swap in/out because exact output swaps are reversed
            pay(tokenIn, data.payer, msg.sender, amountToPay);
        }
    }

    /// @dev Performs a single exact input swap. Must have data tokenIn, tokenOut in poolKey tokens
    function exactInputInternal(
        uint256 amountIn,
        address recipient,
        uint160 sqrtPriceLimitX96,
        SwapCallbackData memory data
    ) private returns (uint256 amountOut) {
        // allow swapping to the router address with address 0
        if (recipient == address(0)) recipient = address(this);
        (address tokenIn, address tokenOut) = (data.tokenIn, data.tokenOut);

        bool zeroForOne = tokenIn < tokenOut;

        (int256 amount0, int256 amount1) = getPool(data.poolKey).swap(
            recipient,
            zeroForOne,
            amountIn.toInt256(),
            sqrtPriceLimitX96 == 0
                ? (
                    zeroForOne
                        ? TickMath.MIN_SQRT_RATIO + 1
                        : TickMath.MAX_SQRT_RATIO - 1
                )
                : sqrtPriceLimitX96,
            abi.encode(data)
        );

        return uint256(-(zeroForOne ? amount1 : amount0));
    }

    /// @inheritdoc IV1LBRouter
    function exactInputSingle(
        ExactInputSingleParams calldata params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountOut)
    {
        amountOut = exactInputInternal(
            params.amountIn,
            params.recipient,
            params.sqrtPriceLimitX96,
            SwapCallbackData({
                poolKey: PoolAddress.getPoolKey(
                    params.tokenIn,
                    params.tokenOut,
                    params.tickLower,
                    params.tickUpper,
                    params.supplier,
                    params.blockTimestampInitialize
                ),
                tokenIn: params.tokenIn,
                tokenOut: params.tokenOut,
                payer: msg.sender
            })
        );
        require(amountOut >= params.amountOutMinimum, "Too little received");
    }

    /// @dev Performs a single exact output swap. Must have data tokenIn, tokenOut in poolKey tokens
    function exactOutputInternal(
        uint256 amountOut,
        address recipient,
        uint160 sqrtPriceLimitX96,
        SwapCallbackData memory data
    ) private returns (uint256 amountIn) {
        // allow swapping to the router address with address 0
        if (recipient == address(0)) recipient = address(this);
        (address tokenIn, address tokenOut) = (data.tokenIn, data.tokenOut);

        bool zeroForOne = tokenIn < tokenOut;

        (int256 amount0Delta, int256 amount1Delta) = getPool(data.poolKey).swap(
            recipient,
            zeroForOne,
            -amountOut.toInt256(),
            sqrtPriceLimitX96 == 0
                ? (
                    zeroForOne
                        ? TickMath.MIN_SQRT_RATIO + 1
                        : TickMath.MAX_SQRT_RATIO - 1
                )
                : sqrtPriceLimitX96,
            abi.encode(data)
        );

        uint256 amountOutReceived;
        (amountIn, amountOutReceived) = zeroForOne
            ? (uint256(amount0Delta), uint256(-amount1Delta))
            : (uint256(amount1Delta), uint256(-amount0Delta));
        // it's technically possible to not receive the full output amount,
        // so if no price limit has been specified, require this possibility away
        if (sqrtPriceLimitX96 == 0) require(amountOutReceived == amountOut);

        // refund any unspent ETH sent in for swap given token exact output specified
        // @dev Ref jeiwan.net/posts/public-bug-report-uniswap-swaprouter
        refundETH();
    }

    /// @inheritdoc IV1LBRouter
    function exactOutputSingle(
        ExactOutputSingleParams calldata params
    )
        external
        payable
        override
        checkDeadline(params.deadline)
        returns (uint256 amountIn)
    {
        // avoid an SLOAD by using the swap return data
        amountIn = exactOutputInternal(
            params.amountOut,
            params.recipient,
            params.sqrtPriceLimitX96,
            SwapCallbackData({
                poolKey: PoolAddress.getPoolKey(
                    params.tokenIn,
                    params.tokenOut,
                    params.tickLower,
                    params.tickUpper,
                    params.supplier,
                    params.blockTimestampInitialize
                ),
                tokenIn: params.tokenIn,
                tokenOut: params.tokenOut,
                payer: msg.sender
            })
        );

        require(amountIn <= params.amountInMaximum, "Too much requested");
        // has to be reset even though we don't use it in the single hop case
        amountInCached = DEFAULT_AMOUNT_IN_CACHED;
    }
}
