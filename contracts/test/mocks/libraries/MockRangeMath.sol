// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {RangeMath} from "../../../libraries/RangeMath.sol";

contract MockRangeMath {
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) external pure returns (uint256 amount0, uint256 amount1) {
        (amount0, amount1) = RangeMath.toAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96
        );
    }

    function rangeFees(
        uint256 amount0,
        uint256 amount1,
        uint8 fee
    ) external pure returns (uint256 fees0, uint256 fees1) {
        (fees0, fees1) = RangeMath.rangeFees(amount0, amount1, fee);
    }
}
