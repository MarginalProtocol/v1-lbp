// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

/// @title The interface of the receiver quoter for Marginal v1 liquidity bootstrapping receivers
/// @notice Quotes the result of initializing receivers for Marginal v1 liquidity bootstrapping pools
interface IV1LBReceiverQuoter {
    /// @notice Quotes the seed funds required to initialize this type of receiver
    /// @param liquidity The liquidity bootstrapping pool liquidity
    /// @param sqrtPriceX96 The initial price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @param sqrtPriceLowerX96 The lower price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @param sqrtPriceUpperX96 The upper price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @return amount0 The amount of token0 needed to initialize receiver
    /// @return amount1 The amount of token1 needed to initialize receiver
    function seeds(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) external view returns (uint256 amount0, uint256 amount1);
}
