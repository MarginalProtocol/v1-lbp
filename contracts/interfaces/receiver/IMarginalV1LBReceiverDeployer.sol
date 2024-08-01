// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity boostrapping pool receiver deployer
/// @notice Deploys the receiver, receives funds forwarded from the supplier after liquidity bootstrapping pool is finalized
interface IMarginalV1LBReceiverDeployer {
    /// @notice Deploys a new receiver for pool
    /// @param pool The address of the Marginal v1 liquidity bootstrapping pool
    /// @param data Any data passed through by the caller to initialize receiver
    function deploy(
        address pool,
        bytes calldata data
    ) external returns (address receiver);
}
