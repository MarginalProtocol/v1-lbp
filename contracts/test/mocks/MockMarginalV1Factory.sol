// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

contract MockMarginalV1Factory {
    address public immutable uniswapV3Factory;
    mapping(address => mapping(address => mapping(uint24 => mapping(address => address))))
        public getPool;
    mapping(uint24 => uint256) public getLeverage;

    constructor(address _uniswapV3Factory) {
        uniswapV3Factory = _uniswapV3Factory;

        getLeverage[250000] = 5000000;
        getLeverage[500000] = 3000000;
        getLeverage[1000000] = 2000000;
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
