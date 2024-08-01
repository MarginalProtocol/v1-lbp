// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {SwapMath} from "@marginal/v1-core/contracts/libraries/SwapMath.sol";

/// @title Math library for range liquidity provision
/// @notice Determines physical amounts needed in range position
library RangeMath {
    error InvalidSqrtPriceX96();

    /// @notice Transforms (L, sqrtP) values into (x, y) reserve amounts adjusting for range limits of (sqrtPriceLowerX96, sqrtPriceUpperX96)
    /// @param liquidity Pool liquidity in (L, sqrtP) space
    /// @param sqrtPriceX96 Pool price in (L, sqrtP) space
    /// @param sqrtPriceLowerX96 Lower price limit of pool range position
    /// @param sqrtPriceUpperX96 Upper price limit of pool range position
    /// @return amount0 The amount of token0 associated with the given (L, sqrtP, sqrtP_lower, sqrtP_upper) values
    /// @return amount1 The amount of token1 associated with the given (L, sqrtP, sqrtP_lower, sqrtP_upper) values
    function toAmounts(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) internal pure returns (uint256 amount0, uint256 amount1) {
        if (
            sqrtPriceLowerX96 >= sqrtPriceUpperX96 ||
            sqrtPriceX96 < sqrtPriceLowerX96 ||
            sqrtPriceX96 > sqrtPriceUpperX96
        ) revert InvalidSqrtPriceX96();

        // TODO: check both amount{0,1}Delta values are negative
        // TODO: check -int(0) case below ok when at end of ranges
        (int256 amount0Delta, ) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceUpperX96
        );
        (, int256 amount1Delta) = SwapMath.swapAmounts(
            liquidity,
            sqrtPriceX96,
            sqrtPriceLowerX96
        );

        amount0 = uint256(-amount0Delta);
        amount1 = uint256(-amount1Delta);
    }

    /// @notice Computes range fees on amounts on after burning position
    /// @dev Can revert when amount > type(uint248).max, but irrelevant for SwapMath.sol::swapAmounts output and pool fee rate constant
    /// @param amount0 Amount of token0 to calculate range fees off of
    /// @param amount1 Amount of token1 to calculate range fees off of
    /// @param fee Fee rate applied on amounts removed from pool in units of 1 bips
    /// @return fees0 Total range fees taken on token0 amount removed from pool
    /// @return fees1 Total range fees token on token1 amount removed from pool
    function rangeFees(
        uint256 amount0,
        uint256 amount1,
        uint8 fee
    ) internal pure returns (uint256 fees0, uint256 fees1) {
        fees0 = (amount0 * fee) / 1e4;
        fees1 = (amount1 * fee) / 1e4;
    }
}
