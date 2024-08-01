// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

/// @title The interface for a Marginal v1 liquidity boostrapping pool supplier
/// @notice Creates and initializes Marginal v1 liquidity bootstrapping pool, supplier necessary liquidity for LBP
interface IMarginalV1LBSupplier {
    /// @notice Returns the address of receiver of transferred funds for a liquidity bootrapping pool
    /// @param pool The liquidity bootstrapping pool transferring the funds
    /// @return The address of the receiver of the raised funds from the liquidity bootstrapping pool
    function receivers(address pool) external view returns (address);

    struct CreateAndInitializeParams {
        address tokenA;
        address tokenB;
        int24 tickLower;
        int24 tickUpper;
        int24 tick;
        uint256 amountDesired;
        uint256 amountMin;
        address receiverDeployer;
        bytes receiverData;
        uint256 deadline;
    }

    /// @notice Creates a new liquidity boostrapping pool if it does not exist, then initializes if not initialized
    /// @param params The parameters necessary to create and initialize a pool, encoded as `CreateAndInitializeParams` in calldata
    /// @return pool Returns the pool address based on the pair of tokens, tick lower, and tick upper, will return the newly created pool address if necessary
    /// @return receiver Returns the receiver address that receives funds after the liquidity bootstrapping pool is finalized
    /// @return shares The amount of shares minted after initializing pool with liquidity
    /// @return amount0 The amount of the input token0 to create and initialize pool
    /// @return amount1 The amount of the input token1 to create and initialize pool
    function createAndInitializePoolIfNecessary(
        CreateAndInitializeParams calldata params
    )
        external
        payable
        returns (
            address pool,
            address receiver,
            uint256 shares,
            uint256 amount0,
            uint256 amount1
        );

    struct FinalizeParams {
        address tokenA;
        address tokenB;
        int24 tickLower;
        int24 tickUpper;
    }

    /// @notice Finalizes an existing liquidity bootstrapping pool, then forwards received funds to recipient stored on initialization
    /// @param params The parameters necessary to finalize a pool, encoded as `FinalizeParams` in calldata
    /// @return liquidityDelta The amount of liquidity burned when finalizing pool
    /// @return sqrtPriceX96 The final price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @return amount0 The amount of token0 removed from pool reserves when finalizing
    /// @return amount1 The amount of token1 removed from pool reserves when finalizing
    function finalizePool(
        FinalizeParams calldata params
    )
        external
        returns (
            uint128 liquidityDelta,
            uint160 sqrtPriceX96,
            uint256 amount0,
            uint256 amount1
        );
}
