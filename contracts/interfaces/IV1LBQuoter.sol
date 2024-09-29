// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.7.5;

import {IMarginalV1LBSupplier} from "./IMarginalV1LBSupplier.sol";
import {IV1LBRouter} from "./IV1LBRouter.sol";

/// @title The interface of the quoter for Marginal v1 liquidity bootstrapping pools
/// @notice Quotes the result of supplying and swaps on Marginal v1 liquidity bootstrapping pools
interface IV1LBQuoter {
    /// @notice Returns the current owner of the Marginal v1 liquidity bootstrapping quoter contract
    /// @dev Changed via permissioned `setOwner` function on the quoter
    /// @return The address of the current owner of the Marginal v1 liquidity bootstrapping quoter
    function owner() external view returns (address);

    /// @notice Returns the current receiver quoter associated with the Marginal v1 liquidity bootstrapping receiver deployer
    /// @dev Changed via permissioned `setReceiverQuoter` function on the quoter
    /// @return The address of the current receiver quoter for the Marginal v1 liquidity bootstrapping receiver deployer
    function receiverQuoters(
        address receiverDeployer
    ) external view returns (address);

    /// @notice Sets the owner of the Marginal v1 liquidity bootstrapping quoter contract
    /// @dev Can only be called by the current quoter owner
    /// @param _owner The new owner of the quoter
    function setOwner(address _owner) external;

    /// @notice Sets the current receiver quoter for the Marginal v1 liquidity bootstrapping receiver deployer
    /// @dev Can only be called by the current quoter owner
    /// @param receiverDeployer The address of the Marginal v1 receiver deployer
    /// @param receiverQuoter The address of the Marginal v1 receiver quoter for receivers deployed by the deployer
    function setReceiverQuoter(
        address receiverDeployer,
        address receiverQuoter
    ) external;

    /// @notice Quotes the result of MarginalV1LBSupplier::createAndInitializePool
    /// @param params Param inputs to MarginalV1LBSupplier::createAndInitializePool
    /// @dev Reverts if createAndInitializePool would revert
    /// @return shares The amount of shares minted after initializing pool with liquidity
    /// @return amount0 The amount of the input token0 to create and initialize pool and receiver
    /// @return amount1 The amount of the input token1 to create and initialize pool and receiver
    /// @return liquidity The amount of liquidity minted after initializing the pool
    /// @return sqrtPriceX96 The starting price of the pool as a sqrt(token1/token0) Q64.96 value
    /// @return sqrtPriceLowerX96 The lower price of the range position as a sqrt(token1/token0) Q64.96 value
    /// @return sqrtPriceUpperX96 The upper price of the range position as a sqrt(token1/token0) Q64.96 value
    function quoteCreateAndInitializePool(
        IMarginalV1LBSupplier.CreateAndInitializeParams calldata params
    )
        external
        view
        returns (
            uint256 shares,
            uint256 amount0,
            uint256 amount1,
            uint128 liquidity,
            uint160 sqrtPriceX96,
            uint160 sqrtPriceLowerX96,
            uint160 sqrtPriceUpperX96
        );

    /// @notice Quotes the amountOut result of V1LBRouter::exactInputSingle
    /// @param params Param inputs to V1LBRouter::exactInputSingle
    /// @dev Reverts if exactInputSingle would revert
    /// @return amountIn Amount of token sent to pool for swap
    /// @return amountOut Amount of token received from pool after swap
    /// @return liquidityAfter Pool liquidity after swap
    /// @return sqrtPriceX96After Pool sqrt price after swap
    /// @return finalizedAfter Whether the pool is finalized after swap
    function quoteExactInputSingle(
        IV1LBRouter.ExactInputSingleParams memory params
    )
        external
        view
        returns (
            uint256 amountIn,
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            bool finalizedAfter
        );

    /// @notice Quotes the amountIn result of V1LBRouter::exactOutputSingle
    /// @param params Param inputs to V1LBRouter::exactOutputSingle
    /// @dev Reverts if exactOutputSingle would revert
    /// @return amountIn Amount of token sent to pool for swap
    /// @return amountOut Amount of token received from pool after swap
    /// @return liquidityAfter Pool liquidity after swap
    /// @return sqrtPriceX96After Pool sqrt price after swap
    /// @return finalizedAfter Whether the pool is finalized after swap
    function quoteExactOutputSingle(
        IV1LBRouter.ExactOutputSingleParams calldata params
    )
        external
        view
        returns (
            uint256 amountIn,
            uint256 amountOut,
            uint128 liquidityAfter,
            uint160 sqrtPriceX96After,
            bool finalizedAfter
        );
}
