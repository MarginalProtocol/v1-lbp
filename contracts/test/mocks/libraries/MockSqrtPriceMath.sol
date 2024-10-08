// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.17;

import {SqrtPriceMath} from "@marginal/v1-core/contracts/libraries/SqrtPriceMath.sol";

contract MockSqrtPriceMath {
    function sqrtPriceX96NextOpen(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint128 liquidityDelta,
        bool zeroForOne,
        uint24 maintenance
    ) external view returns (uint160) {
        return
            SqrtPriceMath.sqrtPriceX96NextOpen(
                liquidity,
                sqrtPriceX96,
                liquidityDelta,
                zeroForOne,
                maintenance
            );
    }

    function sqrtPriceX96NextSwap(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        bool zeroForOne,
        int256 amountSpecified
    ) external pure returns (uint160) {
        return
            SqrtPriceMath.sqrtPriceX96NextSwap(
                liquidity,
                sqrtPriceX96,
                zeroForOne,
                amountSpecified
            );
    }
}
