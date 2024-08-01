// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 liquidity bootstrapping pool deployer
/// @notice The Marginal v1 liquidity bootstrapping pool deployer deploys new pools
interface IMarginalV1LBPoolDeployer {
    /// @notice Deploys a new Marginal v1 liquidity bootstrapping pool for the given unique pool key
    /// @dev `msg.sender` treated as factory address for the pool
    /// @param token0 The address of token0 for the liquidity bootstrapping pool
    /// @param token1 The address of token1 for the liquidity bootstrapping pool
    /// @param tickLower The lower tick of liquidity range for bootstrapping pool
    /// @param tickUpper The upper tick of liquidity range for bootstrapping pool
    /// @param supplier The address of the supplier of funds for the liquidity bootstrapping pool
    /// @param blockTimestampInitialize The block timestamp at or after which pool can be initialized
    /// @return pool The address of the deployed Marginal v1 liquidity bootstrapping pool
    function deploy(
        address token0,
        address token1,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external returns (address pool);
}
