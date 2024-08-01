// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

/// @title Pool addresses for Uniswap v3 and Marginal v1 pools
abstract contract PeripheryPools is IPeripheryPools, PeripheryImmutableState {
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
    ) internal view returns (address) {
        return IUniswapV3Factory(uniswapV3Factory).getPool(token0, token1, fee);
    }

    /// @notice Gets a Marginal v1 pool
    /// @dev Returns zero address if Marginal v1 pool does not exist yet
    /// @param token0 The address of token0 for pool
    /// @param token1 The address of token1 for pool
    /// @param maintenance The minimum maintenance requirement for pool
    /// @param uniswapV3Fee The fee tier of the Uniswap v3 oracle pool
    function getMarginalV1Pool(
        address token0,
        address token1,
        uint24 maintenance,
        uint24 uniswapV3Fee
    ) internal view returns (address) {
        address oracle = getUniswapV3Pool(token0, token1, uniswapV3Fee);
        if (oracle == address(0)) return address(0);
        return
            IMarginalV1Factory(marginalV1Factory).getPool(
                token0,
                token1,
                maintenance,
                oracle
            );
    }
}
