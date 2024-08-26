// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

contract MockUniswapV3Factory {
    mapping(uint24 => int24) public feeAmountTickSpacing;
    mapping(address => mapping(address => mapping(uint24 => address)))
        public getPool;

    constructor() {
        feeAmountTickSpacing[500] = 10;
        feeAmountTickSpacing[3000] = 60;
        feeAmountTickSpacing[10000] = 200;
    }

    function setPool(
        address tokenA,
        address tokenB,
        uint24 fee,
        address pool
    ) external {
        getPool[tokenA][tokenB][fee] = pool;
        getPool[tokenB][tokenA][fee] = pool;
    }
}
