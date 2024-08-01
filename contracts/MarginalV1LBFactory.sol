// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {IMarginalV1LBFactory} from "./interfaces/IMarginalV1LBFactory.sol";
import {IMarginalV1LBPoolDeployer} from "./interfaces/IMarginalV1LBPoolDeployer.sol";

contract MarginalV1LBFactory is IMarginalV1LBFactory {
    /// @inheritdoc IMarginalV1LBFactory
    address public immutable marginalV1LBDeployer;

    /// @inheritdoc IMarginalV1LBFactory
    address public owner;

    /// @inheritdoc IMarginalV1LBFactory
    mapping(address => mapping(address => mapping(int24 => mapping(int24 => mapping(address => mapping(uint256 => address))))))
        public getPool;
    /// @inheritdoc IMarginalV1LBFactory
    mapping(address => bool) public isPool;

    /// @inheritdoc IMarginalV1LBFactory
    uint8 public feeProtocol;

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    event PoolCreated(
        address indexed token0,
        address indexed token1,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize,
        address pool
    );
    event OwnerChanged(address indexed oldOwner, address indexed newOwner);
    event SetFeeProtocol(uint8 oldFeeProtocol, uint8 newFeeProtocol);
    event CollectProtocol(
        address sender,
        address indexed token,
        address indexed recipient,
        uint256 amount
    );

    error Unauthorized();
    error PoolActive();

    constructor(address _marginalV1LBDeployer) {
        owner = msg.sender;
        emit OwnerChanged(address(0), msg.sender);

        marginalV1LBDeployer = _marginalV1LBDeployer;
    }

    /// @inheritdoc IMarginalV1LBFactory
    function createPool(
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        address supplier,
        uint256 blockTimestampInitialize
    ) external returns (address pool) {
        (address token0, address token1) = tokenA < tokenB
            ? (tokenA, tokenB)
            : (tokenB, tokenA);

        if (
            getPool[token0][token1][tickLower][tickUpper][supplier][
                blockTimestampInitialize
            ] != address(0)
        ) revert PoolActive();

        pool = IMarginalV1LBPoolDeployer(marginalV1LBDeployer).deploy(
            token0,
            token1,
            tickLower,
            tickUpper,
            supplier,
            blockTimestampInitialize
        );

        // populate in reverse for key (token0, token1, tickLower, tickUpper, supplier, blockTimestampInitialize)
        getPool[token0][token1][tickLower][tickUpper][supplier][
            blockTimestampInitialize
        ] = pool;
        getPool[token1][token0][tickLower][tickUpper][supplier][
            blockTimestampInitialize
        ] = pool;
        isPool[pool] = true;

        emit PoolCreated(
            token0,
            token1,
            tickLower,
            tickUpper,
            supplier,
            blockTimestampInitialize,
            pool
        );
    }

    /// @inheritdoc IMarginalV1LBFactory
    function setOwner(address _owner) external onlyOwner {
        emit OwnerChanged(owner, _owner);
        owner = _owner;
    }

    /// @inheritdoc IMarginalV1LBFactory
    function setFeeProtocol(uint8 _feeProtocol) external onlyOwner {
        emit SetFeeProtocol(feeProtocol, _feeProtocol);
        feeProtocol = _feeProtocol;
    }

    /// @inheritdoc IMarginalV1LBFactory
    function collectProtocol(
        address token,
        address recipient
    ) external onlyOwner returns (uint256 amount) {
        amount = IERC20(token).balanceOf(address(this));
        if (amount > 0) TransferHelper.safeTransfer(token, recipient, amount);
        emit CollectProtocol(msg.sender, token, recipient, amount);
    }
}
