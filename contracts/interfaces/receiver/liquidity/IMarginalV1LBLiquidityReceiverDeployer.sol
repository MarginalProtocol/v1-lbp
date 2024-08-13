// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IMarginalV1LBReceiverDeployer} from "../IMarginalV1LBReceiverDeployer.sol";

/// @title The interface for a Marginal v1 liquidity boostrapping pool receiver deployer
/// @notice Deploys the receiver, receives funds forwarded from the supplier after liquidity bootstrapping pool is finalized
interface IMarginalV1LBLiquidityReceiverDeployer is
    IMarginalV1LBReceiverDeployer
{
    /// @notice Returns the address of the Uniswap v3 nonfungible position manager
    /// @return The address of the Uniswap v3 NFT manager
    function uniswapV3NonfungiblePositionManager()
        external
        view
        returns (address);

    /// @notice Returns the address of the Marginal v1 factory
    /// @return The address of the Marginal v1 factory
    function marginalV1Factory() external view returns (address);

    /// @notice Returns the address of the Marginal v1 periphery pool initializer
    /// @return The address of the Marginal v1 pool initializer
    function marginalV1PoolInitializer() external view returns (address);

    /// @notice Returns the address of the Marginal v1 periphery router
    /// @return The address of the Marginal v1 router
    function marginalV1Router() external view returns (address);

    /// @notice Returns the address of WETH9
    /// @return The address of WETH9
    function WETH9() external view returns (address);
}
