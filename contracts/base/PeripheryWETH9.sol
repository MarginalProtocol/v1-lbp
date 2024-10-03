// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IWETH9} from "@uniswap/v3-periphery/contracts/interfaces/external/IWETH9.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";

import {IPeripheryWETH9} from "../interfaces/IPeripheryWETH9.sol";
import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";

/// @dev Not included in @marginal/v1-lbp/contracts/base/PeripheryPayments.sol because liquidity receiver
/// @dev also inherits v1-lbp PeripheryPayments while warehousing ERC20s (likely WETH9)
abstract contract PeripheryWETH9 is IPeripheryWETH9, PeripheryImmutableState {
    /// @inheritdoc IPeripheryWETH9
    function unwrapWETH9(
        uint256 amountMinimum,
        address recipient
    ) public payable override {
        uint256 balanceWETH9 = IWETH9(WETH9).balanceOf(address(this));
        require(balanceWETH9 >= amountMinimum, "Insufficient WETH9");

        if (balanceWETH9 > 0) {
            IWETH9(WETH9).withdraw(balanceWETH9);
            TransferHelper.safeTransferETH(recipient, balanceWETH9);
        }
    }
}
