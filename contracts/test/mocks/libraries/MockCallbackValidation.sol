// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {CallbackValidation} from "../../../libraries/CallbackValidation.sol";
import {PoolAddress} from "../../../libraries/PoolAddress.sol";

import {IMarginalV1LBPool} from "../../../interfaces/IMarginalV1LBPool.sol";

contract MockCallbackValidation {
    function verifyCallback(
        address factory,
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external view returns (IMarginalV1LBPool pool) {
        return
            CallbackValidation.verifyCallback(
                factory,
                tokenA,
                tokenB,
                tickLower,
                tickUpper,
                supplier,
                blockTimestampInitialize
            );
    }

    function verifyCallback(
        address factory,
        PoolAddress.PoolKey memory poolKey
    ) external view returns (IMarginalV1LBPool pool) {
        return CallbackValidation.verifyCallback(factory, poolKey);
    }
}
