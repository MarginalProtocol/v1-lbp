import pytest

from eth_abi import encode
from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_DURATION


@pytest.fixture(scope="module")
def finalizer(accounts):
    yield accounts[4]


@pytest.fixture(scope="module")
def treasury(accounts):
    yield accounts[5]


@pytest.fixture(scope="module")
def margv1_liquidity_receiver_deployer(
    assert_mainnet_fork,
    project,
    accounts,
    univ3_manager,
    margv1_factory,
    margv1_initializer,
    margv1_router,
    WETH9,
):
    return project.MarginalV1LBLiquidityReceiverDeployer.deploy(
        univ3_manager.address,
        margv1_factory.address,
        margv1_initializer.address,
        margv1_router.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def margv1_receiver_params(finalizer, treasury):
    return (
        treasury.address,  # treasuryAddress
        int(0.1e6),  # treasuryRatio: 10% to treasury
        int(
            0.5e6
        ),  # uniswapV3Ratio: 50% to univ3 pool and 50% to margv1 pool less treasury
        3000,  # uniswapV3Fee
        250000,  # marginalV1Maintenance
        finalizer.address,  # lockOwner
        int(86400 * 30),  # lockDuration: 30 days
    )


@pytest.fixture(scope="module")
def margv1_liquidity_receiver_and_pool(
    assert_mainnet_fork,
    project,
    accounts,
    factory,
    margv1_supplier,
    margv1_liquidity_receiver_deployer,
    margv1_receiver_params,
    sender,
    finalizer,
    margv1_token0,
    margv1_token1,
    margv1_ticks,
    chain,
):
    def margv1_liquidity_receiver_and_pool(init_with_sqrt_price_lower_x96: bool):
        (tick_lower, tick_upper) = margv1_ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

        amount_desired = (
            margv1_token0.balanceOf(sender.address) // 10
            if init_with_sqrt_price_lower_x96
            else margv1_token1.balanceOf(sender.address) // 10
        )
        receiver_data = encode(
            ["address", "uint24", "uint24", "uint24", "uint24", "address", "uint96"],
            margv1_receiver_params,
        )
        deadline = chain.pending_timestamp
        params = (
            margv1_token0.address,
            margv1_token1.address,
            tick_lower,
            tick_upper,
            tick,
            amount_desired,
            0,  # amount0Min
            0,  # amount1Min
            margv1_liquidity_receiver_deployer.address,
            receiver_data,
            finalizer.address,
            deadline,
        )
        tx = margv1_supplier.createAndInitializePool(params, sender=sender)

        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        receiver_address = tx.decode_logs(
            margv1_liquidity_receiver_deployer.ReceiverDeployed
        )[0].receiver
        receiver = project.MarginalV1LBLiquidityReceiver.at(receiver_address)
        return (receiver, pool)

    yield margv1_liquidity_receiver_and_pool


@pytest.fixture(scope="module")
def margv1_liquidity_receiver_and_pool_finalized(
    assert_mainnet_fork,
    margv1_liquidity_receiver_and_pool,
    sender,
    finalizer,
    margv1_token0,
    margv1_token1,
    margv1_supplier,
    callee,
    swap_math_lib,
    chain,
):
    def margv1_liquidity_receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96: bool,
        sqrt_price_last_x96: int,
    ):
        (
            liquidity_receiver,
            pool_initialized_with_liquidity,
        ) = margv1_liquidity_receiver_and_pool(init_with_sqrt_price_lower_x96)

        state = pool_initialized_with_liquidity.state()
        sqrt_price_finalize_x96 = pool_initialized_with_liquidity.sqrtPriceFinalizeX96()

        zero_for_one = state.sqrtPriceX96 > sqrt_price_finalize_x96
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        (amount0, amount1) = swap_math_lib.swapAmounts(
            state.liquidity,
            state.sqrtPriceX96,
            sqrt_price_last_x96,
        )
        amount_specified = (
            int(amount0 * 1.0001) if zero_for_one else int(amount1 * 1.0001)
        )

        callee.swap(
            pool_initialized_with_liquidity.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )

        timestamp_initialize = (
            pool_initialized_with_liquidity.blockTimestampInitialize()
        )
        chain.mine(timestamp=timestamp_initialize + MINIMUM_DURATION + 1)

        deadline = chain.pending_timestamp + 3600
        params = (
            pool_initialized_with_liquidity.token0(),
            pool_initialized_with_liquidity.token1(),
            pool_initialized_with_liquidity.tickLower(),
            pool_initialized_with_liquidity.tickUpper(),
            pool_initialized_with_liquidity.blockTimestampInitialize(),
            deadline,
        )
        margv1_supplier.finalizePool(params, sender=finalizer)

        return (liquidity_receiver, pool_initialized_with_liquidity)

    yield margv1_liquidity_receiver_and_pool_finalized


@pytest.fixture(scope="module")
def another_margv1_receiver_params(finalizer, treasury):
    return (
        treasury.address,  # treasuryAddress
        int(0.1e6),  # treasuryRatio: 10% to treasury
        int(
            0.5e6
        ),  # uniswapV3Ratio: 50% to univ3 pool and 50% to margv1 pool less treasury
        500,  # uniswapV3Fee
        250000,  # marginalV1Maintenance
        finalizer.address,  # lockOwner
        int(86400 * 30),  # lockDuration: 30 days
    )


@pytest.fixture(scope="module")
def another_margv1_liquidity_receiver_and_pool(
    assert_mainnet_fork,
    project,
    accounts,
    factory,
    margv1_supplier,
    margv1_liquidity_receiver_deployer,
    another_margv1_receiver_params,
    sender,
    finalizer,
    another_margv1_token0,
    margv1_token1,
    another_margv1_ticks,
    chain,
):
    def another_margv1_liquidity_receiver_and_pool(
        init_with_sqrt_price_lower_x96: bool,
    ):
        (tick_lower, tick_upper) = another_margv1_ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

        amount_desired = (
            another_margv1_token0.balanceOf(sender.address) // 100
            if init_with_sqrt_price_lower_x96
            else margv1_token1.balanceOf(sender.address) // 100
        )
        receiver_data = encode(
            ["address", "uint24", "uint24", "uint24", "uint24", "address", "uint96"],
            another_margv1_receiver_params,
        )
        deadline = chain.pending_timestamp
        params = (
            another_margv1_token0.address,
            margv1_token1.address,
            tick_lower,
            tick_upper,
            tick,
            amount_desired,
            0,  # amount0Min
            0,  # amount1Min
            margv1_liquidity_receiver_deployer.address,
            receiver_data,
            finalizer.address,
            deadline,
        )
        tx = margv1_supplier.createAndInitializePool(params, sender=sender)

        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        receiver_address = tx.decode_logs(
            margv1_liquidity_receiver_deployer.ReceiverDeployed
        )[0].receiver
        receiver = project.MarginalV1LBLiquidityReceiver.at(receiver_address)
        return (receiver, pool)

    yield another_margv1_liquidity_receiver_and_pool


@pytest.fixture(scope="module")
def another_margv1_liquidity_receiver_and_pool_finalized(
    assert_mainnet_fork,
    another_margv1_liquidity_receiver_and_pool,
    sender,
    finalizer,
    another_margv1_token0,
    margv1_token1,
    margv1_supplier,
    callee,
    swap_math_lib,
    chain,
):
    def another_margv1_liquidity_receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96: bool,
        sqrt_price_last_x96: int,
    ):
        (
            liquidity_receiver,
            pool_initialized_with_liquidity,
        ) = another_margv1_liquidity_receiver_and_pool(init_with_sqrt_price_lower_x96)

        state = pool_initialized_with_liquidity.state()
        sqrt_price_finalize_x96 = pool_initialized_with_liquidity.sqrtPriceFinalizeX96()

        zero_for_one = state.sqrtPriceX96 > sqrt_price_finalize_x96
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        (amount0, amount1) = swap_math_lib.swapAmounts(
            state.liquidity,
            state.sqrtPriceX96,
            sqrt_price_last_x96,
        )
        amount_specified = (
            int(amount0 * 1.0001) if zero_for_one else int(amount1 * 1.0001)
        )

        callee.swap(
            pool_initialized_with_liquidity.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )

        timestamp_initialize = (
            pool_initialized_with_liquidity.blockTimestampInitialize()
        )
        chain.mine(timestamp=timestamp_initialize + MINIMUM_DURATION + 1)

        deadline = chain.pending_timestamp + 3600
        params = (
            pool_initialized_with_liquidity.token0(),
            pool_initialized_with_liquidity.token1(),
            pool_initialized_with_liquidity.tickLower(),
            pool_initialized_with_liquidity.tickUpper(),
            pool_initialized_with_liquidity.blockTimestampInitialize(),
            deadline,
        )
        margv1_supplier.finalizePool(params, sender=finalizer)

        return (liquidity_receiver, pool_initialized_with_liquidity)

    yield another_margv1_liquidity_receiver_and_pool_finalized
