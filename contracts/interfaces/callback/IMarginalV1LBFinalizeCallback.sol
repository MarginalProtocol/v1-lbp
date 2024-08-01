// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity bootstrapping finalize callback
/// @notice Callback for a Marginal v1 liquidity bootstrapping pools when finalizing the LBP
/// @dev Any contract that receives bootstrapped funds from IMarginalLBPool#finalize must implement this interface
interface IMarginalV1LBFinalizeCallback {
    /// @notice Callback through IMarginalV1LBPool#finalize after transferring funds to this contract
    /// @dev In the implementation you must use token balances for funds transferred by the liquidity bootstrapping pool.
    /// The caller of this method must be checked to be a MarginalV1LBPool deployed by the canonical MarginalV1LBFactory.
    /// @param amount0Transferred The amount of token0 transferred after finalizing the LBP
    /// @param amount1Transferred The amount of token1 transferred after finalizing the LBP
    /// @param data Any data passed through by the caller via the IMarginalV1LBPool#finalize call
    function marginalV1LBFinalizeCallback(
        uint256 amount0Transferred,
        uint256 amount1Transferred,
        bytes calldata data
    ) external;
}
