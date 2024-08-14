// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;
pragma abicoder v2;

/// @title The interface for the Marginal v1 liquidity bootstrapping router
/// @notice Facilitates swaps on Marginal v1 liquidity bootstrapping pools
interface IV1LBRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        int24 tickLower;
        int24 tickUpper;
        address supplier;
        uint256 blockTimestampInitialize;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    /// @notice Swaps `amountIn` of one token for as much as possible of another token
    /// @param params The parameters necessary for the swap, encoded as `ExactInputSingleParams` in calldata
    /// @return amountOut The amount of the received token
    function exactInputSingle(
        ExactInputSingleParams calldata params
    ) external payable returns (uint256 amountOut);

    struct ExactOutputSingleParams {
        address tokenIn;
        address tokenOut;
        int24 tickLower;
        int24 tickUpper;
        address supplier;
        uint256 blockTimestampInitialize;
        address recipient;
        uint256 deadline;
        uint256 amountOut;
        uint256 amountInMaximum;
        uint160 sqrtPriceLimitX96;
    }

    /// @notice Swaps as little as possible of one token for `amountOut` of another token
    /// @dev If a contract sending in native (gas) token, `msg.sender` must implement a `receive()` function to receive any refunded unspent amount in.
    /// @param params The parameters necessary for the swap, encoded as `ExactOutputSingleParams` in calldata
    /// @return amountIn The amount of the input token
    function exactOutputSingle(
        ExactOutputSingleParams calldata params
    ) external payable returns (uint256 amountIn);
}
