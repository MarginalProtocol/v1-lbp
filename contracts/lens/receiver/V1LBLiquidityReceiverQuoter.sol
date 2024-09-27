// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {LiquidityMath} from "@marginal/v1-core/contracts/libraries/LiquidityMath.sol";
import {LiquidityAmounts} from "@marginal/v1-periphery/contracts/libraries/LiquidityAmounts.sol";

import {RangeMath} from "../../libraries/RangeMath.sol";
import {IV1LBReceiverQuoter} from "../../interfaces/receiver/IV1LBReceiverQuoter.sol";

contract V1LBLiquidityReceiverQuoter is IV1LBReceiverQuoter {
    /// @inheritdoc IV1LBReceiverQuoter
    function seeds(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) external view returns (uint256 amount0, uint256 amount1) {
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
        (uint256 amount0Desired, uint256 amount1Desired) = getAmountsDesired(
            sqrtPriceFinalizeX96,
            amount0Pool,
            amount1Pool,
            _zeroForOne
        );
        // @dev extra tokens to add to reserves of receiver is in the offered token as
        // notifyRewardAmounts provides acquired token side of full range liquidity mint
        amount0 = _zeroForOne ? amount0Desired : 0;
        amount1 = _zeroForOne ? 0 : amount1Desired;
    }

    /// @notice Returns the amounts desired to mint full range liquidity given reserves from lbp
    /// @dev Uses liquidity value calculated from reserve amount in token acquired
    /// @param sqrtPriceX96 The price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @param amount0 The amount of token0 to use from reserve
    /// @param amount1 The amount of token1 to use from reserve
    /// @param _zeroForOne Whether lbp offered up token0 for token1
    /// @return amount0Desired The maximum amount of token0 needed to mint full range liquidity
    /// @return amount1Desired The maximum amount of token1 needed to mint full range liquidity
    function getAmountsDesired(
        uint160 sqrtPriceX96,
        uint256 amount0,
        uint256 amount1,
        bool _zeroForOne
    ) public pure returns (uint256 amount0Desired, uint256 amount1Desired) {
        // calculate additional amount{0,1} needed to provide full range liquidity
        (uint128 liquidity0, uint128 liquidity1) = (
            LiquidityAmounts.getLiquidityForAmount0(sqrtPriceX96, amount0),
            LiquidityAmounts.getLiquidityForAmount1(sqrtPriceX96, amount1)
        );
        uint128 liquidity = _zeroForOne ? liquidity1 : liquidity0; // liquidity determined by lbp acquired token
        (amount0Desired, amount1Desired) = LiquidityMath.toAmounts(
            liquidity,
            sqrtPriceX96
        );
    }
}
