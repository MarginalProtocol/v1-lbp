// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IPeripheryImmutableState} from "./IPeripheryImmutableState.sol";

/// @title The interface for a Marginal v1 liquidity boostrapping pool supplier
/// @notice Creates and initializes Marginal v1 liquidity bootstrapping pool, supplier necessary liquidity for LBP
interface IMarginalV1LBSupplier is IPeripheryImmutableState {
    /// @notice Returns the address of receiver of transferred funds for a liquidity bootstrapping pool
    /// @param pool The liquidity bootstrapping pool
    /// @return The address of the receiver of the raised funds from the liquidity bootstrapping pool
    function receivers(address pool) external view returns (address);

    /// @notice Returns the address of finalizer of transferred funds for a liquidity bootstrapping pool
    /// @param pool The liquidity bootstrapping pool
    /// @return The address of the finalizer who can early exit from the liquidity bootstrapping pool if necessary after min duration
    function finalizers(address pool) external view returns (address);

    struct CreateAndInitializeParams {
        address tokenA;
        address tokenB;
        int24 tickLower;
        int24 tickUpper;
        int24 tick;
        uint256 amountDesired; // amount desired for pool only
        uint256 amount0Min; // minimum amount enforced on sum of pool and receiver amounts
        uint256 amount1Min; // minimum amount enforced on sum of pool and receiver amounts
        address receiverDeployer;
        bytes receiverData;
        address finalizer; // can early exit from pool after min duration
    }

    /// @notice Creates a new liquidity boostrapping pool then initializes
    /// @dev Also deploys a receiver that receives funds after the liquidity bootstrapping pool is finalized
    /// @param params The parameters necessary to create and initialize a pool, encoded as `CreateAndInitializeParams` in calldata
    /// @return pool Returns the pool address based on the pair of tokens, tick lower, and tick upper, will return the newly created pool address
    /// @return receiver Returns the receiver address that receives funds after the liquidity bootstrapping pool is finalized
    /// @return shares The amount of shares minted after initializing pool with liquidity
    /// @return amount0 The amount of the input token0 to create and initialize pool and receiver
    /// @return amount1 The amount of the input token1 to create and initialize pool and receiver
    function createAndInitializePool(
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
        uint256 blockTimestampInitialize;
    }

    /// @notice Finalizes an existing liquidity bootstrapping pool, then forwards received funds to recipient stored on initialization
    /// @param params The parameters necessary to finalize a pool, encoded as `FinalizeParams` in calldata
    /// @return liquidityDelta The amount of liquidity burned when finalizing pool
    /// @return sqrtPriceX96 The final price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @return amount0 The amount of token0 forwarded from pool reserves when finalizing
    /// @return amount1 The amount of token1 forwarded from pool reserves when finalizing
    /// @return fees0 The amount of token0 sent to factory for protocol fees from pool reserves when finalizing
    /// @return fees1 The amount of token1 sent to factory for protoocl fees from pool reserves when finalizing
    function finalizePool(
        FinalizeParams calldata params
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
}
