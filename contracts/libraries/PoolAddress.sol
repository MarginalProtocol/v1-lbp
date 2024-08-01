// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.5.0;

import {IMarginalV1LBFactory} from "../interfaces/IMarginalV1LBFactory.sol";

/// @dev Fork of Uniswap V3 periphery PoolAddress.sol
library PoolAddress {
    error PoolInactive();

    /// @notice The identifying key of the pool
    struct PoolKey {
        address token0;
        address token1;
        int24 tickLower;
        int24 tickUpper;
        address supplier;
        uint256 blockTimestampInitialize;
    }

    /// @notice Returns PoolKey: the ordered tokens with the matched fee levels
    /// @param tokenA The first token of a pool, unsorted
    /// @param tokenB The second token of a pool, unsorted
    /// @param tickLower The lower tick of liquidity range for bootstrapping pool
    /// @param tickUpper The upper tick of liquidity range for bootstrapping pool
    /// @param supplier The address of the supplier of funds for the liquidity bootstrapping pool
    /// @param blockTimestampInitialize The block timestamp at or after which pool can be initialized
    /// @return PoolKey The pool details with ordered token0 and token1 assignments
    function getPoolKey(
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) internal pure returns (PoolKey memory) {
        if (tokenA > tokenB) (tokenA, tokenB) = (tokenB, tokenA);
        return
            PoolKey({
                token0: tokenA,
                token1: tokenB,
                tickLower: tickLower,
                tickUpper: tickUpper,
                supplier: supplier,
                blockTimestampInitialize: blockTimestampInitialize
            });
    }

    /// @notice Gets the pool address from factory given pool key
    /// @dev Reverts if pool not created yet
    /// @param factory The liquidity bootstrapping factory contract address
    /// @param key The pool key
    /// @return pool The contract address of the pool
    function getAddress(
        address factory,
        PoolKey memory key
    ) internal view returns (address pool) {
        pool = IMarginalV1LBFactory(factory).getPool(
            key.token0,
            key.token1,
            key.tickLower,
            key.tickUpper,
            key.supplier,
            key.blockTimestampInitialize
        );
        if (pool == address(0)) revert PoolInactive();
    }

    /// @notice Checks factory for whether `pool` is a valid pool
    /// @param factory The factory contract address
    /// @param pool The contract address to check whether is a pool
    function isPool(
        address factory,
        address pool
    ) internal view returns (bool) {
        return IMarginalV1LBFactory(factory).isPool(pool);
    }
}
