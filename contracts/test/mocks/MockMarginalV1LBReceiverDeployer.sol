// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IMarginalV1LBPool} from "../../interfaces/IMarginalV1LBPool.sol";
import {IMarginalV1LBReceiverDeployer} from "../../interfaces/receiver/IMarginalV1LBReceiverDeployer.sol";
import {MockMarginalV1LBReceiver} from "./MockMarginalV1LBReceiver.sol";

contract MockMarginalV1LBReceiverDeployer is IMarginalV1LBReceiverDeployer {
    mapping(address => address) public receivers;

    event ReceiverDeployed(address indexed pool, bytes data, address receiver);

    function deploy(
        address pool,
        bytes calldata data
    ) external returns (address receiver) {
        require(receivers[pool] == address(0));
        address token0 = IMarginalV1LBPool(pool).token0();
        address token1 = IMarginalV1LBPool(pool).token1();

        receiver = address(
            new MockMarginalV1LBReceiver(pool, token0, token1, data)
        );
        receivers[pool] = receiver;
        emit ReceiverDeployed(pool, data, receiver);
    }
}
