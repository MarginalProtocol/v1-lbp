// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {IPeripheryPayments} from "../interfaces/IPeripheryPayments.sol";
import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";

abstract contract PeripheryPayments is
    IPeripheryPayments,
    PeripheryImmutableState
{
    /// @dev Should override for periphery contracts used
    receive() external payable virtual {}

    /// @inheritdoc IPeripheryPayments
    function refundETH() public payable override {
        if (address(this).balance > 0)
            TransferHelper.safeTransferETH(msg.sender, address(this).balance);
    }

    /// @inheritdoc IPeripheryPayments
    function sweepETH(uint256 amountMinimum, address recipient) public payable {
        uint256 balanceETH = address(this).balance;
        require(balanceETH >= amountMinimum, "Insufficient ETH");

        if (balanceETH > 0)
            TransferHelper.safeTransferETH(recipient, balanceETH);
    }

    /// @notice Pay ERC20 token to recipient
    /// @param token The token to pay
    /// @param payer The entity that must pay
    /// @param recipient The entity that will receive payment
    /// @param value The amount to pay
    function pay(
        address token,
        address payer,
        address recipient,
        uint256 value
    ) internal {
        if (token == WETH9 && address(this).balance >= value) {
            // pay with WETH9
            IWETH9(WETH9).deposit{value: value}(); // wrap only what is needed to pay
            IWETH9(WETH9).transfer(recipient, value);
        } else if (payer == address(this)) {
            // pay with tokens already in the contract (for the exact input multihop case)
            TransferHelper.safeTransfer(token, recipient, value);
        } else {
            // pull payment
            TransferHelper.safeTransferFrom(token, payer, recipient, value);
        }
    }

    /// @notice Balance of ERC20 token held by this contract
    /// @param token The token to check
    /// @return value The balance amount
    function balance(address token) internal view returns (uint256 value) {
        return IERC20(token).balanceOf(address(this));
    }
}
