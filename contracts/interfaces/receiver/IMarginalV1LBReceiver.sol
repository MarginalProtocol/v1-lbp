// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity boostrapping pool receiver
/// @notice Receives funds forwarded from the supplier after liquidity bootstrapping pool is finalized
interface IMarginalV1LBReceiver {
    /// @notice Returns the address of the liquidity bootstrapping pool that transferred funds to receiver
    /// @return The address of the liquidity bootstrapping pool
    function pool() external view returns (address);

    /// @notice The first of the two tokens of the pool, sorted by address
    /// @return The address of the token0 contract
    function token0() external view returns (address);

    /// @notice The second of the two tokens of the pool, sorted by address
    /// @return The address of the token1 contract
    function token1() external view returns (address);

    /// @notice Returns the seed amounts required to initialize receiver
    /// @param liquidity The liquidity bootstrapping pool liquidity
    /// @param sqrtPriceX96 The initial price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @param sqrtPriceLowerX96 The lower price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @param sqrtPriceUpperX96 The upper price of the liquidity bootstrapping pool as a sqrt(token1/token0) Q64.96 value
    /// @return amount0 The amount of token0 needed to initialize receiver
    /// @return amount1 The amount of token1 needed to initialize receiver
    function seeds(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        uint160 sqrtPriceLowerX96,
        uint160 sqrtPriceUpperX96
    ) external view returns (uint256 amount0, uint256 amount1);

    /// @notice Initializes receiver with additional reserve funds to couple with those eventually received via IMarginalV1Receiver#notifyRewardAmounts
    function initialize() external;

    /// @notice Notifies receiver of funds transferred in from liquidity bootstrapping pool
    /// @dev Must transfer funds from supplier to receiver prior to calling IMarginalV1LBReceiver#notifyRewardAmounts
    /// @param amount0 The amount of token0 sent from `msg.sender` to receiver
    /// @param amount1 The amount of token1 sent from `msg.sender` to receiver
    function notifyRewardAmounts(
        uint256 amount0,
        uint256 amount1
    ) external virtual;
}
