// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

/// @title Periphery Payments
/// @notice Functions to ease deposits and withdrawals of ETH
interface IPeripheryPayments {
    /// @notice Refunds any ETH balance held by this contract to the `msg.sender`
    /// @dev Useful for bundling with mint or increase liquidity that uses ether, or exact output swaps
    /// that use ether for the input amount
    function refundETH() external payable;

    /// @notice Transfers the full amount of ETH held by this contract to recipient
    /// @dev The amountMinimum parameter prevents malicious contracts from stealing the ETH from users
    /// @param amountMinimum The minimum amount of ETH required for a transfer
    /// @param recipient The destination address of the ETH
    function sweepETH(
        uint256 amountMinimum,
        address recipient
    ) external payable;
}
