// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {MarginalV1LBLiquidityReceiver} from "./MarginalV1LBLiquidityReceiver.sol";

import {IMarginalV1LBPool} from "../interfaces/IMarginalV1LBPool.sol";
import {IMarginalV1LBReceiverDeployer} from "../interfaces/receiver/IMarginalV1LBReceiverDeployer.sol";
import {IMarginalV1LBLiquidityReceiverDeployer} from "../interfaces/receiver/liquidity/IMarginalV1LBLiquidityReceiverDeployer.sol";

contract MarginalV1LBLiquidityReceiverDeployer is
    IMarginalV1LBLiquidityReceiverDeployer
{
    /// @inheritdoc IMarginalV1LBLiquidityReceiverDeployer
    address public immutable uniswapV3NonfungiblePositionManager;
    /// @inheritdoc IMarginalV1LBLiquidityReceiverDeployer
    address public immutable marginalV1Factory;
    /// @inheritdoc IMarginalV1LBLiquidityReceiverDeployer
    address public immutable marginalV1PoolInitializer;
    /// @inheritdoc IMarginalV1LBLiquidityReceiverDeployer
    address public immutable marginalV1Router;
    /// @inheritdoc IMarginalV1LBLiquidityReceiverDeployer
    address public immutable WETH9;

    modifier onlyPoolSupplier(address pool) {
        if (msg.sender != IMarginalV1LBPool(pool).supplier())
            revert Unauthorized();
        _;
    }

    event ReceiverDeployed(address indexed pool, bytes data, address receiver);

    error Unauthorized();

    constructor(
        address _uniswapV3NonfungiblePositionManager,
        address _marginalV1Factory,
        address _marginalV1PoolInitializer,
        address _marginalV1Router,
        address _WETH9
    ) {
        uniswapV3NonfungiblePositionManager = _uniswapV3NonfungiblePositionManager;
        marginalV1Factory = _marginalV1Factory;
        marginalV1PoolInitializer = _marginalV1PoolInitializer;
        marginalV1Router = _marginalV1Router;
        WETH9 = _WETH9;
    }

    /// @inheritdoc IMarginalV1LBReceiverDeployer
    function deploy(
        address pool,
        bytes calldata data
    )
        external
        virtual
        override(IMarginalV1LBReceiverDeployer)
        onlyPoolSupplier(pool)
        returns (address receiver)
    {
        address factory = IMarginalV1LBPool(pool).factory();
        receiver = address(
            new MarginalV1LBLiquidityReceiver{
                salt: keccak256(abi.encode(msg.sender, pool))
            }(factory, marginalV1Factory, WETH9, pool, data)
        );
        emit ReceiverDeployed(pool, data, receiver);
    }
}
