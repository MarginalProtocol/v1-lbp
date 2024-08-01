// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity >=0.7.5;

import {IMarginalV1Factory} from "@marginal/v1-core/contracts/interfaces/IMarginalV1Factory.sol";

import "../interfaces/IPeripheryImmutableState.sol";

/// @title Immutable state
/// @notice Immutable state used by liquidity bootstrapping periphery contracts
abstract contract PeripheryImmutableState is IPeripheryImmutableState {
    address public immutable factory;
    address public immutable marginalV1Factory;
    address public immutable uniswapV3Factory;
    address public immutable WETH9;

    constructor(address _factory, address _marginalV1Factory, address _WETH9) {
        factory = _factory;
        marginalV1Factory = _marginalV1Factory;
        uniswapV3Factory = IMarginalV1Factory(_marginalV1Factory)
            .uniswapV3Factory();
        WETH9 = _WETH9;
    }
}
