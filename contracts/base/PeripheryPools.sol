// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IUniswapV3Factory} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Factory.sol";
import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import {PeripheryImmutableState} from "./PeripheryImmutableState.sol";
import {IPeripheryPools} from "../interfaces/IPeripheryPools.sol";

/// @title Pool addresses for Uniswap v3 and Marginal v1 pools
abstract contract PeripheryPools is IPeripheryPools, PeripheryImmutableState {
    /// @inheritdoc IPeripheryPools
    function getUniswapV3Pool(
        address token0,
        address token1,
        uint24 fee
    ) public view returns (address) {
        return IUniswapV3Factory(uniswapV3Factory).getPool(token0, token1, fee);
    }

    /// @inheritdoc IPeripheryPools
    function getMarginalV1Pool(
        address token0,
        address token1,
        uint24 maintenance,
        address oracle
    ) public view returns (address) {
        return
            IMarginalV1Factory(marginalV1Factory).getPool(
                token0,
                token1,
                maintenance,
                oracle
            );
    }
}
