// SPDX-License-Identifier: AGPL-3.0
pragma solidity =0.8.15;

import {TickMath} from "@uniswap/v3-core/contracts/libraries/TickMath.sol";
import {LiquidityAmounts} from "@uniswap/v3-periphery/contracts/libraries/LiquidityAmounts.sol";
import {PeripheryValidation} from "@uniswap/v3-periphery/contracts/base/PeripheryValidation.sol";
import {Multicall} from "@uniswap/v3-periphery/contracts/base/Multicall.sol";

import {IMarginalV1MintCallback} from "@marginal/v1-core/contracts/interfaces/callback/IMarginalV1MintCallback.sol";

import {CallbackValidation} from "./libraries/CallbackValidation.sol";
import {PoolAddress} from "./libraries/PoolAddress.sol";
import {RangeMath} from "./libraries/RangeMath.sol";
import {PeripheryImmutableState} from "./base/PeripheryImmutableState.sol";
import {PeripheryPayments} from "./base/PeripheryPayments.sol";

import {IMarginalV1LBFinalizeCallback} from "./interfaces/callback/IMarginalV1LBFinalizeCallback.sol";
import {IMarginalV1LBReceiverDeployer} from "./interfaces/receiver/IMarginalV1LBReceiverDeployer.sol";

import {IMarginalV1LBReceiver} from "./interfaces/receiver/IMarginalV1LBReceiver.sol";
import {IMarginalV1LBPool} from "./interfaces/IMarginalV1LBPool.sol";
import {IMarginalV1LBFactory} from "./interfaces/IMarginalV1LBFactory.sol";
import {IMarginalV1LBSupplier} from "./interfaces/IMarginalV1LBSupplier.sol";

contract MarginalV1LBSupplier is
    IMarginalV1LBSupplier,
    IMarginalV1MintCallback,
    IMarginalV1LBFinalizeCallback,
    PeripheryImmutableState,
    PeripheryPayments,
    PeripheryValidation,
    Multicall
{
    uint256 private constant DEFAULT_BALANCE_CACHED = type(uint256).max;

    /// @dev Transient storage variables used for computing amounts received on finalize callback
    uint256 private balance0Cached = DEFAULT_BALANCE_CACHED;
    uint256 private balance1Cached = DEFAULT_BALANCE_CACHED;

    /// @inheritdoc IMarginalV1LBSupplier
    mapping(address => address) public receivers;

    error InvalidPool();
    error InvalidReceiver();
    error Amount0LessThanMin();
    error Amount1LessThanMin();

    constructor(
        address _factory,
        address _marginalV1Factory,
        address _WETH9
    ) PeripheryImmutableState(_factory, _marginalV1Factory, _WETH9) {}

    /// @dev Returns the pool key for the given unique (token0, token1, tickLower, tickUpper, supplier, blockTimestampInitialize) tuple.
    function getPoolKey(
        address tokenA,
        address tokenB,
        int24 tickLower,
        int24 tickUpper,
        uint256 blockTimestampInitialize
    ) private view returns (PoolAddress.PoolKey memory) {
        return
            PoolAddress.getPoolKey(
                tokenA,
                tokenB,
                tickLower,
                tickUpper,
                address(this),
                blockTimestampInitialize
            );
    }

    /// @dev Returns the pool for the given unique pool key. The pool contract may or may not exist.
    function getPoolAddress(
        PoolAddress.PoolKey memory poolKey
    ) private view returns (address) {
        return PoolAddress.getAddress(factory, poolKey);
    }

    /// @inheritdoc IMarginalV1LBSupplier
    function createAndInitializePool(
        CreateAndInitializeParams calldata params
    )
        external
        payable
        checkDeadline(params.deadline)
        returns (
            address pool,
            address receiver,
            uint256 shares,
            uint256 amount0,
            uint256 amount1
        )
    {
        PoolAddress.PoolKey memory poolKey = getPoolKey(
            params.tokenA,
            params.tokenB,
            params.tickLower,
            params.tickUpper,
            block.timestamp
        );
        pool = IMarginalV1LBFactory(factory).createPool(
            params.tokenA,
            params.tokenB,
            params.tickLower,
            params.tickUpper,
            address(this),
            block.timestamp // use current block timestamp
        );

        // deploy the receiver after creating liquidity bootstrapping pool
        if (params.receiverDeployer == address(0)) revert InvalidReceiver();
        // @dev should revert if data not valid
        receiver = IMarginalV1LBReceiverDeployer(params.receiverDeployer)
            .deploy(pool, params.receiverData);
        receivers[pool] = receiver;

        // initialize pool since not initialized yet
        uint160 sqrtPriceX96 = TickMath.getSqrtRatioAtTick(params.tick);
        uint160 sqrtPriceLowerX96 = IMarginalV1LBPool(pool).sqrtPriceLowerX96();
        uint160 sqrtPriceUpperX96 = IMarginalV1LBPool(pool).sqrtPriceUpperX96();

        // calculate liquidity using range math
        uint128 liquidity = LiquidityAmounts.getLiquidityForAmounts(
            sqrtPriceX96,
            sqrtPriceLowerX96,
            sqrtPriceUpperX96,
            sqrtPriceX96 == sqrtPriceLowerX96 ? params.amountDesired : 0, // reserve0
            sqrtPriceX96 == sqrtPriceLowerX96 ? 0 : params.amountDesired // reserve1
        );

        (shares, amount0, amount1) = IMarginalV1LBPool(pool).initialize(
            liquidity,
            sqrtPriceX96,
            abi.encode(MintCallbackData({poolKey: poolKey, payer: msg.sender}))
        );

        // transfer funds to receiver to cover any additional token needed once receive from lbp at finalize
        (
            uint256 amount0Receiver,
            uint256 amount1Receiver
        ) = IMarginalV1LBReceiver(receiver).seeds(
                liquidity,
                sqrtPriceX96,
                sqrtPriceLowerX96,
                sqrtPriceUpperX96
            );
        if (amount0Receiver > 0)
            pay(poolKey.token0, msg.sender, receiver, amount0Receiver);
        if (amount1Receiver > 0)
            pay(poolKey.token1, msg.sender, receiver, amount1Receiver);
        IMarginalV1LBReceiver(receiver).initialize();

        amount0 += amount0Receiver;
        amount1 += amount1Receiver;

        if (amount0 < params.amount0Min) revert Amount0LessThanMin();
        if (amount1 < params.amount1Min) revert Amount1LessThanMin();
    }

    struct MintCallbackData {
        PoolAddress.PoolKey poolKey;
        address payer;
    }

    /// @inheritdoc IMarginalV1MintCallback
    function marginalV1MintCallback(
        uint256 amount0Owed,
        uint256 amount1Owed,
        bytes calldata data
    ) external {
        MintCallbackData memory decoded = abi.decode(data, (MintCallbackData));
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        if (amount0Owed > 0)
            pay(decoded.poolKey.token0, decoded.payer, msg.sender, amount0Owed);
        if (amount1Owed > 0)
            pay(decoded.poolKey.token1, decoded.payer, msg.sender, amount1Owed);
    }

    /// @inheritdoc IMarginalV1LBSupplier
    function finalizePool(
        FinalizeParams calldata params
    )
        external
        returns (
            uint128 liquidityDelta,
            uint160 sqrtPriceX96,
            uint256 amount0,
            uint256 amount1
        )
    {
        PoolAddress.PoolKey memory poolKey = getPoolKey(
            params.tokenA,
            params.tokenB,
            params.tickLower,
            params.tickUpper,
            params.blockTimestampInitialize
        );
        address pool = getPoolAddress(poolKey);
        if (pool == address(0)) revert InvalidPool();

        address receiver = receivers[pool];
        if (receiver == address(0)) revert InvalidReceiver();

        // cache balances for check on finalize callback on amounts received
        balance0Cached = balance(poolKey.token0);
        balance1Cached = balance(poolKey.token1);

        (liquidityDelta, sqrtPriceX96, amount0, amount1) = IMarginalV1LBPool(
            pool
        ).finalize(
                abi.encode(
                    FinalizeCallbackData({poolKey: poolKey, receiver: receiver})
                )
            );
    }

    struct FinalizeCallbackData {
        PoolAddress.PoolKey poolKey;
        address receiver;
    }

    /// @inheritdoc IMarginalV1LBFinalizeCallback
    function marginalV1LBFinalizeCallback(
        uint256 amount0Transferred,
        uint256 amount1Transferred,
        bytes calldata data
    ) external {
        FinalizeCallbackData memory decoded = abi.decode(
            data,
            (FinalizeCallbackData)
        );
        CallbackValidation.verifyCallback(factory, decoded.poolKey);

        // only support tokens with standard ERC20 transfer
        if (
            balance0Cached + amount0Transferred >
            balance(decoded.poolKey.token0)
        ) revert Amount0LessThanMin();
        if (
            balance1Cached + amount1Transferred >
            balance(decoded.poolKey.token1)
        ) revert Amount1LessThanMin();

        if (amount0Transferred > 0)
            pay(
                decoded.poolKey.token0,
                address(this),
                decoded.receiver,
                amount0Transferred
            );
        if (amount1Transferred > 0)
            pay(
                decoded.poolKey.token1,
                address(this),
                decoded.receiver,
                amount1Transferred
            );

        IMarginalV1LBReceiver(decoded.receiver).notifyRewardAmounts(
            amount0Transferred,
            amount1Transferred
        );

        // reset balances cached
        balance0Cached = DEFAULT_BALANCE_CACHED;
        balance1Cached = DEFAULT_BALANCE_CACHED;
    }
}
