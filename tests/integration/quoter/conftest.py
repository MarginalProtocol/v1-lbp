import pytest

from eth_abi import encode

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_swap_amounts, calc_sqrt_price_x96_from_tick


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
    margv1_supplier,
    WETH9,
):
    return project.MarginalV1LBLiquidityReceiverDeployer.deploy(
        margv1_supplier.address,
        univ3_manager.address,
        margv1_factory.address,
        margv1_initializer.address,
        margv1_router.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def margv1_receiver_quoter(assert_mainnet_fork, project, accounts):
    return project.V1LBLiquidityReceiverQuoter.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def margv1_quoter_initialized(
    assert_mainnet_fork,
    margv1_quoter,
    margv1_receiver_quoter,
    margv1_liquidity_receiver_deployer,
    admin,
):
    margv1_quoter.setReceiverQuoter(
        margv1_liquidity_receiver_deployer.address,
        margv1_receiver_quoter.address,
        sender=admin,
    )
    return margv1_quoter


@pytest.fixture(scope="module")
def margv1_receiver_params(finalizer, treasury, sender):
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
        sender.address,  # refundAddress
    )


@pytest.fixture(scope="module")
def margv1_pool_initialized(
    assert_mainnet_fork,
    project,
    margv1_liquidity_receiver_deployer,
    margv1_supplier,
    margv1_token0,
    margv1_token1,
    margv1_ticks,
    margv1_receiver_params,
    callee,
    finalizer,
    factory,
    sender,
    whale,
):
    def margv1_pool_initialized(init_with_sqrt_price_lower_x96: bool):
        (tick_lower, tick_upper) = margv1_ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

        amount_desired = (
            margv1_token0.balanceOf(sender.address) // 10
            if init_with_sqrt_price_lower_x96
            else margv1_token1.balanceOf(sender.address) // 10
        )
        receiver_data = encode(
            [
                "address",
                "uint24",
                "uint24",
                "uint24",
                "uint24",
                "address",
                "uint96",
                "address",
            ],
            margv1_receiver_params,
        )
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
        )

        tx = margv1_supplier.createAndInitializePool(params, sender=sender)
        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        # swap the pool to mid sqrt price
        tick_mid = (tick_lower + tick_upper) // 2
        sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick_mid)

        liquidity = pool.state().liquidity
        sqrt_price_initialize_x96 = pool.sqrtPriceInitializeX96()
        (amount0, amount1) = calc_swap_amounts(
            liquidity, sqrt_price_initialize_x96, sqrt_price_x96
        )

        zero_for_one = amount0 > 0
        amount_in = amount0 if zero_for_one else amount1
        token_in = margv1_token0 if zero_for_one else margv1_token1
        token_in.transfer(sender.address, amount_in, sender=whale)

        amount_specified = amount_in
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        callee.swap(
            pool.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )
        return pool

    yield margv1_pool_initialized
