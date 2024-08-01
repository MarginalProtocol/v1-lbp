// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity ^0.8.0;

import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";
import {PoolAddress} from "./PoolAddress.sol";

/// @notice Provides validation for callbacks from Marginal V1 Liquidity Bootstrapping Pools
/// @dev Fork of Uniswap V3 periphery CallbackValidation.sol
library CallbackValidation {
    error PoolNotSender();

    /// @notice Returns the address of a valid Marginal V1 Liquidity Bootstrapping Pool
    /// @param factory The contract address of the Marginal V1 liquidity bootstrapping factory
    /// @param tokenA The contract address of either token0 or token1
    /// @param tokenB The contract address of the other token
    /// @param tickLower The lower tick of liquidity range for bootstrapping pool
    /// @param tickUpper The upper tick of liquidity range for bootstrapping pool
    /// @param supplier The address of the supplier of funds for the liquidity bootstrapping pool
    /// @param blockTimestampInitialize The block timestamp at or after which pool can be initialized
    /// @return pool The V1 liquidity bootstrapping pool contract address
    function verifyCallback(
        address factory,
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) internal view returns (IMarginalV1LBPool pool) {
        return
            verifyCallback(
                factory,
                PoolAddress.getPoolKey(
                    tokenA,
                    tokenB,
                    tickLower,
                    tickUpper,
                    supplier,
                    blockTimestampInitialize
                )
            );
    }

    /// @notice Returns the address of a valid Marginal V1 Liquidity Bootstrapping Pool
    /// @param factory The contract address of the Marginal V1 liquidity bootstrapping factory
    /// @param poolKey The identifying key of the V1 liquidity bootstrapping pool
    /// @return pool The V1 liquidity bootstrapping pool contract address
    function verifyCallback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) internal view returns (IMarginalV1LBPool pool) {
        pool = IMarginalV1LBPool(PoolAddress.getAddress(factory, poolKey));
        if (msg.sender != address(pool)) revert PoolNotSender();
    }
}
