// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity boostrapping pool receiver
/// @notice Receives funds forwarded from the supplier after liquidity bootstrapping pool is finalized
interface IMarginalV1LBReceiver {
    /// @notice Returns the address of the liquidity bootstrapping pool that transferred funds to receiver
    /// @return The address of the liquidity bootstrapping pool
    function pool() external view returns (address);

    /// @notice Notifies receiver of funds transferred in from liquidity bootstrapping pool
    /// @dev Must transfer funds from supplier to receiver prior to calling IMarginalV1LBReceiver#notifyRewardAmounts
    /// @param amount0 The amount of token0 sent from `msg.sender` to receiver
    /// @param amount1 The amount of token1 sent from `msg.sender` to receiver
    function notifyRewardAmounts(uint256 amount0, uint256 amount1) external;
}
