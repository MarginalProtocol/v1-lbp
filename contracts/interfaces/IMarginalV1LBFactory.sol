// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.5.0;

/// @title The interface for the Marginal v1 liquidity bootstrapping factory
/// @notice The Marginal v1 liquidity bootstrapping factory creates LB pools
interface IMarginalV1LBFactory {
    /// @notice Returns the Marginal v1 liquidity bootstrapping pool deployer to use when creating pools
    /// @return The address of the Marginal v1 liquidity bootstrapping pool deployer
    function marginalV1LBDeployer() external view returns (address);

    /// @notice Returns the current owner of the Marginal v1 liquidity bootstrapping factory contract
    /// @dev Changed via permissioned `setOwner` function on the factory
    /// @return The address of the current owner of the Marginal v1 liquidity factory
    function owner() external view returns (address);

    /// @notice Returns the pool address for the given unique Marginal v1 pool key
    /// @dev tokenA and tokenB may be passed in either token0/token1 or token1/token0 order
    /// @param tokenA The address of either token0/token1
    /// @param tokenB The address of the other token token1/token0
    /// @param tickLower The lower tick of liquidity range for bootstrapping pool
    /// @param tickUpper The upper tick of liquidity range for bootstrapping pool
    /// @param supplier The address of the supplier of funds for the liquidity bootstrapping pool
    /// @param blockTimestampInitialize The block timestamp at or after which pool can be initialized
    /// @return The address of the Marginal v1 liquidity bootstrapping pool
    function getPool(
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external view returns (address);

    /// @notice Returns whether given address is a Marginal v1 liquidity bootstrapping pool deployed by the factory
    /// @return Whether address is a pool
    function isPool(address pool) external view returns (bool);

    /// @notice Creates a new Marginal v1 pool for the given unique pool key
    /// @dev tokenA and tokenB may be passed in either token0/token1 or token1/token0 order
    /// @param tokenA The address of either token0/token1
    /// @param tokenB The address of the other token token1/token0
    /// @param tickLower The lower tick of liquidity range for bootstrapping pool
    /// @param tickUpper The upper tick of liquidity range for bootstrapping pool
    /// @param supplier The address of the supplier of funds for the liquidity bootstrapping pool
    /// @param blockTimestampInitialize The block timestamp at or after which pool can be initialized
    /// @return pool The address of the created Marginal v1 liquidity bootstrapping pool
    function createPool(
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external returns (address pool);

    /// @notice Sets the owner of the Marginal v1 liquidity bootstrapping factory contract
    /// @dev Can only be called by the current factory owner
    /// @param _owner The new owner of the factory
    function setOwner(address _owner) external;
}
