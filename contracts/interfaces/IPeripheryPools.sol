// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

/// @title Periphery Pools
/// @notice Functions to ease retrieving Uniswap v3 and Marginal v1 pools
interface IPeripheryPools {
    /// @notice Gets a Uniswap v3 pool
    /// @dev Returns zero address if Uniswap v3 pool does not exist yet
    /// @param token0 The address of token0 for pool
    /// @param token1 The address of token1 for pool
    /// @param fee The fee tier of the pool
    /// @return The address of the uniswap v3 pool
    function getUniswapV3Pool(
        address token0,
        address token1,
        uint24 fee
    ) external view returns (address);

    /// @notice Gets a Marginal v1 pool
    /// @dev Returns zero address if Marginal v1 pool does not exist yet
    /// @param token0 The address of token0 for pool
    /// @param token1 The address of token1 for pool
    /// @param maintenance The minimum maintenance requirement for pool
    /// @param oracle The address of the Uniswap v3 oracle pool
    function getMarginalV1Pool(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) external view returns (address);
}
