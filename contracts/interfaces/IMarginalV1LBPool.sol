// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity bootstrapping pool
/// @notice A Marginal v1 liquidity bootstrapping pool facilitates initial liquidity bootstrapping for an asset that strictly conforms
/// to the ERC20 specification
interface IMarginalV1LBPool {
    /// @notice The Marginal v1 factory that created the pool
    /// @return The address of the Marginal v1 factory
    function factory() external view returns (address);

    /// @notice The first of the two tokens of the pool, sorted by address
    /// @return The address of the token0 contract
    function token0() external view returns (address);

    /// @notice The second of the two tokens of the pool, sorted by address
    /// @return The address of the token1 contract
    function token1() external view returns (address);

    /// @notice The lower tick limit of the liquidity bootstrapping pool range position
    /// @return The lower tick limit of the range position
    function tickLower() external view returns (int24);

    /// @notice The upper tick limit of the liquidity bootstrapping pool range position
    /// @return The upper tick limit of the range position
    function tickUpper() external view returns (int24);

    /// @notice The lower price limit of the liquidity bootstrapping pool range position
    /// @return The lower price of the range position as a sqrt(token1/token0) Q64.96 value
    function sqrtPriceLowerX96() external view returns (uint160);

    /// @notice The upper price limit of the liquidity bootstrapping pool range position
    /// @return The upper price of the range position as a sqrt(token1/token0) Q64.96 value
    function sqrtPriceUpperX96() external view returns (uint160);

    /// @notice The supplier of initial token0 or token1 funds for liquidity bootstrapping pool
    /// @return The address of the supplier of initial token funds
    function supplier() external view returns (address);

    /// @notice Returns the block timestamp at or after which the liquidity bootstrapping can be initialized
    /// @return The block timestamp at or after which pool was initialized
    function blockTimestampInitialize() external view returns (uint256);

    /// @notice The initial price of the liquidity bootstrapping pool
    /// @return The initial price of pool as a sqrt(token1/token0) Q64.96 value
    function sqrtPriceInitializeX96() external view returns (uint160);

    /// @notice The targeted final price of the liquidity bootstrapping pool
    /// @return The targeted final price of pool as a sqrt(token1/token0) Q64.96 value
    function sqrtPriceFinalizeX96() external view returns (uint160);

    /// @notice The pool state represented in (L, sqrt(P)) space
    /// @return sqrtPriceX96 The current price of the pool as a sqrt(token1/token0) Q64.96 value
    /// totalPositions The total number of leverage positions that have ever been taken out on the pool
    /// liquidity The currently available liquidity offered by the pool for swaps and leverage positions
    /// tick The current tick of the pool, i.e. according to the last tick transition that was run.
    /// blockTimestamp The last `block.timestamp` at which state was synced
    /// tickCumulative The tick cumulative running sum of the pool, used in funding calculations
    /// feeProtocol The protocol fee for both tokens of the pool
    /// finalized Whether the pool has been finalized
    function state()
        external
        view
        returns (
            uint160 sqrtPriceX96,
            uint96 totalPositions,
            uint128 liquidity,
            int24 tick,
            uint32 blockTimestamp,
            int56 tickCumulative,
            uint8 feeProtocol,
            bool finalized
        );

    /// @notice Initializes the liquidity bootstrapping pool at a given start price adding liquidity to the pool range position
    /// @dev The caller of this method receives a callback in the form of IMarginalV1MintCallback#marginalV1MintCallback.
    /// @param liquidity The liquidity added to the pool
    /// @param sqrtPriceX96 The initial price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @param data Any data to be passed through to the mint callback
    /// @return shares The amount of LP token shares minted
    /// @return amount0 The amount of token0 added to the pool reserves
    /// @return amount1 The amount of token1 added to the pool reserves
    function initialize(
        uint128 liquidity,
        uint160 sqrtPriceX96,
        bytes calldata data
    ) external returns (uint256 shares, uint256 amount0, uint256 amount1);

    /// @notice Finalizes the liquidity bootstrapping removing liquidity from the pool
    /// @dev Can be called if pool sqrt price has reached final tick or if supplier manually exists after minimum bootstrapping duration.
    /// The `recipient_` of the pool receives a callback in the form of IMarginalV1LBFinalizeCallback#marginalV1LBFinalizeCallback.
    /// @param data Any data to be passed through to the finalize callback
    /// @return liquidityDelta The liquidity removed from the pool
    /// @return sqrtPriceX96 The final price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @return amount0 The amount of token0 removed from pool reserves less protocol fees
    /// @return amount1 The amount of token1 removed from pool reserves less protocol fees
    /// @return fees0 The amount of token0 taken as protocol fees from pool reserves
    /// @return fees1 The amount of token1 taken as protocol fees from pool reserves
    function finalize(
        bytes calldata data
    )
        external
        returns (
            uint128 liquidityDelta,
            uint160 sqrtPriceX96,
            uint256 amount0,
            uint256 amount1,
            uint256 fees0,
            uint256 fees1
        );

    /// @notice Swap token0 for token1, or token1 for token0
    /// @dev The caller of this method receives a callback in the form of IMarginalV1SwapCallback#marginalV1SwapCallback
    /// @param recipient The address to receive the output of the swap
    /// @param zeroForOne The direction of the swap, true for token0 to token1, false for token1 to token0
    /// @param amountSpecified The amount of the swap, which implicitly configures the swap as exact input (positive), or exact output (negative)
    /// @param sqrtPriceLimitX96 The Q64.96 sqrt price limit. If zero for one, the price cannot be less than this
    /// value after the swap otherwise the call reverts. If one for zero, the price cannot be greater than this value after the swap
    /// @param data Any data to be passed through to the callback
    /// @return amount0 The delta of the balance of token0 of the pool, exact when negative, minimum when positive
    /// @return amount1 The delta of the balance of token1 of the pool, exact when negative, minimum when positive
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1);
}
