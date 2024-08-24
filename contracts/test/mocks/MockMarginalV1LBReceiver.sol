// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

import {FixedPoint96} from "@marginal/v1-core/contracts/libraries/FixedPoint96.sol";
import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";

import {RangeMath} from "../../libraries/RangeMath.sol";
import {IMarginalV1LBPool} from "../../interfaces/IMarginalV1LBPool.sol";
import {IMarginalV1LBReceiver} from "../../interfaces/receiver/IMarginalV1LBReceiver.sol";

contract MockMarginalV1LBReceiver is IMarginalV1LBReceiver {
    address public immutable pool;
    address public immutable token0;
    address public immutable token1;
    address public immutable sender;

    uint256 public reserve0;
    uint256 public reserve1;

    constructor(
        address _pool,
        address _token0,
        address _token1,
        bytes memory _data
    ) {
        pool = _pool;
        token0 = _token0;
        token1 = _token1;
        sender = abi.decode(_data, (address));
    }

    function seeds(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) public view returns (uint256 amount0, uint256 amount1) {
        // @dev oversimplified calculation of other token
        bool _zeroForOne = (sqrtPriceX96 == sqrtPriceLowerX96);
        uint160 sqrtPriceFinalizeX96 = _zeroForOne
            ? sqrtPriceUpperX96
            : sqrtPriceLowerX96;
        (uint256 amount0Pool, uint256 amount1Pool) = RangeMath.toAmounts(
            liquidity,
            sqrtPriceFinalizeX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
        if (_zeroForOne) {
            require(amount0Pool == 0);
            amount0 = Math.mulDiv(
                Math.mulDiv(
                    amount1Pool,
                    FixedPoint96.Q96,
                    sqrtPriceFinalizeX96
                ),
                FixedPoint96.Q96,
                sqrtPriceFinalizeX96
            );
        } else {
            require(amount1Pool == 0);
            amount1 = Math.mulDiv(
                Math.mulDiv(
                    amount0Pool,
                    sqrtPriceFinalizeX96,
                    FixedPoint96.Q96
                ),
                sqrtPriceFinalizeX96,
                FixedPoint96.Q96
            );
        }
    }

    function initialize() external {
        (
            uint160 sqrtPriceX96,
            ,
            uint128 liquidity,
            ,
            ,
            ,
            ,

        ) = IMarginalV1LBPool(pool).state();
        uint160 sqrtPriceLowerX96 = IMarginalV1LBPool(pool).sqrtPriceLowerX96();
        uint160 sqrtPriceUpperX96 = IMarginalV1LBPool(pool).sqrtPriceUpperX96();

        (uint256 amount0, uint256 amount1) = seeds(
            liquidity,
            sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
        require(
            IERC20(token0).balanceOf(address(this)) >= amount0,
            "balance0 < amount0"
        );
        require(
            IERC20(token1).balanceOf(address(this)) >= amount1,
            "balance1 < amount1"
        );

        reserve0 = amount0;
        reserve1 = amount1;
    }

    function notifyRewardAmounts(
        uint256 amount0,
        uint256 amount1
    ) external virtual override {
        require(
            IERC20(token0).balanceOf(address(this)) >= reserve0 + amount0,
            "balance0 < reserve0 + amount0"
        );
        require(
            IERC20(token1).balanceOf(address(this)) >= reserve1 + amount1,
            "balance1 < reserve1 + amount1"
        );
        reserve0 += amount0;
        reserve1 += amount1;
    }
}
