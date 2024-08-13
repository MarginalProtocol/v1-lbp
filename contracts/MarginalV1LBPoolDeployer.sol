// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IMarginalV1LBPoolDeployer} from "./interfaces/IMarginalV1LBPoolDeployer.sol";
import {MarginalV1LBPool} from "./MarginalV1LBPool.sol";

contract MarginalV1LBPoolDeployer is IMarginalV1LBPoolDeployer {
    /// @inheritdoc IMarginalV1LBPoolDeployer
    function deploy(
        address token0,
        address token1,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external returns (address pool) {
        pool = address(
            new MarginalV1LBPool{
                salt: keccak256(
                    abi.encode(
                        msg.sender,
                        token0,
                        token1,
                        tickLower,
                        tickUpper,
                        supplier,
                        blockTimestampInitialize
                    )
                )
            }(
                msg.sender,
                token0,
                token1,
                tickLower,
                tickUpper,
                supplier,
                blockTimestampInitialize
            )
        );
    }
}
