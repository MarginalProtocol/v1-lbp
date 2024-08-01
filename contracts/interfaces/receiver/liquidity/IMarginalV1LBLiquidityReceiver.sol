// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import {IMarginalV1LBReceiver} from "../IMarginalV1LBReceiver.sol";

/// @title The interface for a Marginal v1 liquidity boostrapping pool receiver for creating Uniswap v3 and Marginal v1 pools
/// @notice Receives funds forwarded from the supplier after liquidity bootstrapping pool is finalized and uses them to create Uniswap v3 and Marginal v1 pools
interface IMarginalV1LBLiquidityReceiver is IMarginalV1LBReceiver {
    /// @notice Returns the deployer of the receiver contract
    /// @return The address of the receiver deployer
    function deployer() external view returns (address);

    /// @notice Returns the amount of token0 left in the receiver for liquidity pools
    /// @return The amount of token0 left
    function reserve0() external view returns (uint256);

    /// @notice Returns the amount of token1 left in the receiver for liquidity pools
    /// @return The amount of token1 left
    function reserve1() external view returns (uint256);

    /// @notice Returns the receiver params set on deployment to use when creating Uniswap v3 and Marginal v1 pools
    /// @return treasuryAddress The address to send treasury ratio funds to
    /// @return treasuryRatio The fraction of lbp funds to send to treasury in units of hundredths of 1 bip
    /// @return uniswapV3Ratio The fraction of lbp funds less supplier to add to Uniswap v3 pool in units of hundredths of 1 bip
    /// @return uniswapV3Fee The fee tier of Uniswap v3 pool to add liquidity to
    /// @return marginalV1Maintenance The minimum maintenance requirement of Marginal v1 pool to add liquidity to
    /// @return lockOwner The address that can unlock liquidity after lock passes from this contract
    /// @return lockDuration The number of seconds after which can unlock liquidity receipt tokens from this contract
    function receiverParams()
        external
        view
        returns (
            address treasuryAddress,
            uint24 treasuryRatio,
            uint24 uniswapV3Ratio,
            uint24 uniswapV3Fee,
            uint24 marginalV1Maintenance,
            address lockOwner,
            uint96 lockDuration
        );

    /// @notice Returns the pool information for the created and initialized Uniswap v3 pool
    /// @dev Returned `shares` will always be zero for Uniswap v3
    /// @return blockTimestamp The block timestamp at which added liquidity to pool
    /// @return poolAddress The address of Uniswap v3 added liquidity to
    /// @return tokenId The tokenId (if any) of pool added liquidity for nonfungible liquidity
    /// @return shares The shares (if any) of pool added liquidity for fungible liquidity
    function uniswapV3PoolInfo()
        external
        view
        returns (
            uint96 blockTimestamp,
            address poolAddress,
            uint256 tokenId,
            uint256 shares
        );

    /// @notice Returns the pool information for the created and initialized Marginal v1 pool
    /// @dev Returned `tokenId` will always be zero for Marginal v1
    /// @return blockTimestamp The block timestamp at which added liquidity to pool
    /// @return poolAddress The address of Uniswap v3 added liquidity to
    /// @return tokenId The tokenId (if any) of pool added liquidity for nonfungible liquidity
    /// @return shares The shares (if any) of pool added liquidity for fungible liquidity
    function marginalV1PoolInfo()
        external
        view
        returns (
            uint96 blockTimestamp,
            address poolAddress,
            uint256 tokenId,
            uint256 shares
        );

    /// @notice Mints the Uniswap v3 full range liquidity position after creating the Uniswap v3 pool if necessary
    /// @dev Initializes to LBP final price if Uniswap v3 pool has not yet been initialized
    /// @return uniswapV3Pool The address of the Uniswap v3 pool providing liquidity to
    /// @return tokenId The token ID of the minted Uniswap v3 full range liquidity position
    /// @return liquidity The liquidity minted by providing full range liquidity on the Uniswap v3 pool
    /// @return amount0 The amount of token0 used to provide full range liquidity on the Uniswap v3 pool
    /// @return amount1 The amount of token1 used to provide full range liquidity on the Uniswap v3 pool
    function mintUniswapV3()
        external
        payable
        returns (
            address uniswapV3Pool,
            uint256 tokenId,
            uint128 liquidity,
            uint256 amount0,
            uint256 amount1
        );

    /// @notice Mints the Marginal v1 liquidity after creating the Marginal v1 pool if necessary
    /// @dev Initializes to the Uniswap v3 pool price if Marginal v1 pool has not yet been initialized
    /// @return marginalV1Pool The address of the Marginal v1 pool providing liquidity to
    /// @return shares The shares of liquidity minted to the Marginal v1 pool
    /// @return amount0 The amount of token0 used to provide liquidity to the Marginal v1 pool
    /// @return amount1 The amount of token1 used to provide liquidity to the Marginal v1 pool
    function mintMarginalV1()
        external
        payable
        returns (
            address marginalV1Pool,
            uint256 shares,
            uint256 amount0,
            uint256 amount1
        );

    /// @notice Frees the Uniswap v3 full range liquidity position locked in receiver if enough time has passed
    /// @dev Reverts if `msg.sender` is not lock owner or if not enough time has passed since Uniswap v3 pool liquidity minted
    /// @param recipient The address of the recipient of the unlocked Uniswap v3 full range liquidity position
    function freeUniswapV3(address recipient) external;

    /// @notice Frees the Marginal v1 liquidity shares locked in receiver if enough time has passed
    /// @dev Reverts if `msg.sender` is not lock owner or if not enough time has passed since Marginal v1 pool liquidity minted
    /// @param recipient The address of the recipient of the unlocked Marginal v1 liquidity shares
    function freeMarginalV1(address recipient) external;
}
