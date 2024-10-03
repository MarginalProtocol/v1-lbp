// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

/// @title Periphery WETH9
/// @notice Functions to ease withdrawals of WETH9
/// @dev Do not include in contracts that hold WETH9
interface IPeripheryWETH9 {
    /// @notice Unwraps the contract's WETH9 balance and sends it to recipient as ETH.
    /// @dev The amountMinimum parameter prevents malicious contracts from stealing WETH9 from users.
    /// @param amountMinimum The minimum amount of WETH9 to unwrap
    /// @param recipient The address receiving ETH
    function unwrapWETH9(
        uint256 amountMinimum,
        address recipient
    ) external payable;
}
