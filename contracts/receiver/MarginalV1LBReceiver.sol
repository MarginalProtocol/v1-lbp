// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IMarginalV1LBReceiver} from "../interfaces/receiver/IMarginalV1LBReceiver.sol";
import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";

abstract contract MarginalV1LBReceiver is IMarginalV1LBReceiver {
    /// @inheritdoc IMarginalV1LBReceiver
    address public immutable pool;
    /// @inheritdoc IMarginalV1LBReceiver
    address public immutable token0;
    /// @inheritdoc IMarginalV1LBReceiver
    address public immutable token1;

    constructor(address _pool) {
        pool = _pool;
        token0 = IMarginalV1LBPool(_pool).token0();
        token1 = IMarginalV1LBPool(_pool).token1();
    }

    /// @inheritdoc IMarginalV1LBReceiver
    function notifyRewardAmounts(
        uint256 amount0,
        uint256 amount1
    ) external virtual;
}
