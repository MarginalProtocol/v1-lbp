// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IMarginalV1MintCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1MintCallback.sol";
import {IMarginalV1SwapCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1SwapCallback.sol";

import {IMarginalV1LBFinalizeCallback} from "../interfaces/callback/IMarginalV1LBFinalizeCallback.sol";
import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";

contract TestMarginalV1LBPoolCallee is
    IMarginalV1MintCallback,
    IMarginalV1SwapCallback,
    IMarginalV1LBFinalizeCallback
{
    using SafeERC20 for IERC20;

    event MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        address sender
    );
    event SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        address sender
    );
    event FinalizeCallback(
        uint256 amount0Transferred,
        uint256 amount1Transferred,
        address sender
    );
    event InitializeReturn(uint256 shares, uint256 amount0, uint256 amount1);
    event MintReturn(uint256 shares, uint256 amount0, uint256 amount1);
    event SwapReturn(int256 amount0, int256 amount1);
    event FinalizeReturn(
        uint128 liquidityDelta,
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1
    );
    event BurnReturn(uint128 liquidityDelta, uint256 amount0, uint256 amount1);

    function initialize(
        address pool,
        uint128 liquidityDelta,
        uint160 sqrtPriceX96
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1) {
        (shares, amount0, amount1) = IMarginalV1LBPool(pool).initialize(
            liquidityDelta,
            sqrtPriceX96,
            abi.encode(msg.sender)
        );
        emit InitializeReturn(shares, amount0, amount1);
    }

    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit MintCallback(amount0Owed, amount1Owed, sender);

        if (amount0Owed > 0)
            IERC20(IMarginalV1LBPool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                amount0Owed
            );
        if (amount1Owed > 0)
            IERC20(IMarginalV1LBPool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                amount1Owed
            );
    }

    function swap(
        address pool,
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96
    ) external returns (int256 amount0, int256 amount1) {
        (amount0, amount1) = IMarginalV1LBPool(pool).swap(
            recipient,
            zeroForOne,
            amountSpecified,
            sqrtPriceLimitX96,
            abi.encode(msg.sender)
        );
        emit SwapReturn(amount0, amount1);
    }

    function marginalV1SwapCallback(
        int256 amount0Delta,
        int256 amount1Delta,
        bytes calldata data
    ) external {
        address sender = abi.decode(data, (address));

        emit SwapCallback(amount0Delta, amount1Delta, sender);

        if (amount0Delta > 0) {
            IERC20(IMarginalV1LBPool(msg.sender).token0()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount0Delta)
            );
        } else if (amount1Delta > 0) {
            IERC20(IMarginalV1LBPool(msg.sender).token1()).safeTransferFrom(
                sender,
                msg.sender,
                uint256(amount1Delta)
            );
        } else {
            assert(amount0Delta == 0 && amount1Delta == 0);
        }
    }

    function finalize(
        address pool,
        address recipient
    )
        external
        returns (
            uint128 liquidityDelta,
            uint160 sqrtPriceX96,
            uint256 amount0,
            uint256 amount1
        )
    {
        (liquidityDelta, sqrtPriceX96, amount0, amount1) = IMarginalV1LBPool(
            pool
        ).finalize(abi.encode(recipient));
        emit FinalizeReturn(liquidityDelta, sqrtPriceX96, amount0, amount1);
    }

    function marginalV1LBFinalizeCallback(
        uint256 amount0Transferred,
        uint256 amount1Transferred,
        bytes calldata data
    ) external {
        address recipient = abi.decode(data, (address));

        if (amount0Transferred > 0) {
            address token0 = IMarginalV1LBPool(msg.sender).token0();
            IERC20(token0).safeTransfer(
                recipient,
                IERC20(token0).balanceOf(address(this))
            );
        }
        if (amount1Transferred > 0) {
            address token1 = IMarginalV1LBPool(msg.sender).token1();
            IERC20(token1).safeTransfer(
                recipient,
                IERC20(token1).balanceOf(address(this))
            );
        }
    }
}
