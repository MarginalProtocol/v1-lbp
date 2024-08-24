// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

contract MockMarginalV1Factory {
    address public immutable uniswapV3Factory;
    mapping(address => mapping(address => mapping(uint24 => mapping(address => address))))
        public getPool;

    constructor(address _uniswapV3Factory) {
        uniswapV3Factory = _uniswapV3Factory;
    }

    function setPool(
        address tokenA,
        address tokenB,
        uint24 maintenance,
        address oracle,
        address pool
    ) external {
        getPool[tokenA][tokenB][maintenance][oracle] = pool;
        getPool[tokenB][tokenA][maintenance][oracle] = pool;
    }
}
