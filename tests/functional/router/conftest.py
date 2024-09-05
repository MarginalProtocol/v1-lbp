import pytest

from math import sqrt

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_swap_amounts, calc_sqrt_price_x96_from_tick


@pytest.fixture(scope="module")
def receiver_deployer(project, accounts):
    return project.MockMarginalV1LBReceiverDeployer.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def mock_univ3_factory(project, accounts):
    return project.MockUniswapV3Factory.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def mock_margv1_factory(project, accounts, mock_univ3_factory):
    return project.MockMarginalV1Factory.deploy(
        mock_univ3_factory.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def router(project, accounts, factory, mock_margv1_factory, WETH9):
    return project.V1LBRouter.deploy(
        factory.address, mock_margv1_factory.address, WETH9.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def spot_reserve0(pool, token_a, token_b):
    x = int(4.22468e14)  # e.g. USDC reserves on spot
    return x


@pytest.fixture(scope="module")
def spot_reserve1(pool, token_a, token_b):
    y = int(1.62406e23)  # e.g. WETH reserves on spot
    return y


@pytest.fixture(scope="module")
def spot_liquidity(spot_reserve0, spot_reserve1):
    return int(sqrt(spot_reserve0 * spot_reserve1))


@pytest.fixture(scope="module")
def sqrt_price_x96_initial(spot_reserve0, spot_reserve1):
    sqrt_price = sqrt(spot_reserve1 / spot_reserve0)
    return int(sqrt_price * (1 << 96))


@pytest.fixture(scope="module")
def token0(pool, token_a, token_b, sender, callee, router, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(router.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, callee, router, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(router.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1


@pytest.fixture(scope="module")
def finalizer(accounts):
    yield accounts[4]


@pytest.fixture(scope="module")
def pool_initialized(
    pool, callee, token0, token1, sender, spot_liquidity, sqrt_price_x96_initial, ticks
):
    def pool_initialized(init_with_sqrt_price_lower_x96: bool):
        liquidity_delta = (spot_liquidity * 100) // 10000  # 1% of spot reserves
        sqrt_price_initialize_x96 = (
            pool.sqrtPriceLowerX96()
            if init_with_sqrt_price_lower_x96
            else pool.sqrtPriceUpperX96()
        )

        callee.initialize(
            pool.address,
            liquidity_delta,
            sqrt_price_initialize_x96,
            sender=sender,
        )

        # swap the pool to mid sqrt price
        (tick_lower, tick_upper) = ticks
        tick_mid = (tick_lower + tick_upper) // 2
        sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick_mid)

        sqrt_price_initialize_x96 = pool.sqrtPriceInitializeX96()
        (amount0, amount1) = calc_swap_amounts(
            liquidity_delta, sqrt_price_initialize_x96, sqrt_price_x96
        )

        zero_for_one = amount0 > 0
        amount_in = amount0 if zero_for_one else amount1
        token_in = token0 if zero_for_one else token1
        token_in.mint(sender.address, amount_in, sender=sender)

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

    yield pool_initialized


@pytest.fixture(scope="module")
def token0_with_WETH9(
    pool_with_WETH9,
    token_a,
    WETH9,
    sender,
    callee,
    supplier,
    router,
    spot_reserve0,
    chain,
):
    _token0 = token_a if pool_with_WETH9.token0() == token_a.address else WETH9
    _token0.approve(callee.address, 2**256 - 1, sender=sender)
    _token0.approve(supplier.address, 2**256 - 1, sender=sender)
    _token0.approve(router.address, 2**256 - 1, sender=sender)

    if _token0.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve0 + sender.balance)
        WETH9.deposit(value=spot_reserve0, sender=sender)
    else:
        _token0.mint(sender.address, spot_reserve0, sender=sender)
    return _token0


@pytest.fixture(scope="module")
def token1_with_WETH9(
    pool_with_WETH9,
    token_a,
    WETH9,
    sender,
    callee,
    supplier,
    router,
    spot_reserve1,
    chain,
):
    _token1 = WETH9 if pool_with_WETH9.token1() == WETH9.address else token_a
    _token1.approve(callee.address, 2**256 - 1, sender=sender)
    _token1.approve(supplier.address, 2**256 - 1, sender=sender)
    _token1.approve(router.address, 2**256 - 1, sender=sender)

    if _token1.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve1 + sender.balance)
        WETH9.deposit(value=spot_reserve1, sender=sender)
    else:
        _token1.mint(sender.address, spot_reserve1, sender=sender)
    return _token1


@pytest.fixture(scope="module")
def pool_initialized_with_WETH9(
    pool,
    callee,
    token0_with_WETH9,
    token1_with_WETH9,
    sender,
    spot_liquidity,
    sqrt_price_x96_initial,
    ticks,
):
    def pool_initialized_with_WETH9(init_with_sqrt_price_lower_x96: bool):
        liquidity_delta = (spot_liquidity * 100) // 10000  # 1% of spot reserves
        sqrt_price_initialize_x96 = (
            pool.sqrtPriceLowerX96()
            if init_with_sqrt_price_lower_x96
            else pool.sqrtPriceUpperX96()
        )

        callee.initialize(
            pool.address,
            liquidity_delta,
            sqrt_price_initialize_x96,
            sender=sender,
        )

        # swap the pool to mid sqrt price
        (tick_lower, tick_upper) = ticks
        tick_mid = (tick_lower + tick_upper) // 2
        sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick_mid)

        sqrt_price_initialize_x96 = pool.sqrtPriceInitializeX96()
        (amount0, amount1) = calc_swap_amounts(
            liquidity_delta, sqrt_price_initialize_x96, sqrt_price_x96
        )

        zero_for_one = amount0 > 0
        amount_in = amount0 if zero_for_one else amount1
        token_in = token0_with_WETH9 if zero_for_one else token1_with_WETH9
        token_in.mint(sender.address, amount_in, sender=sender)

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

    yield pool_initialized_with_WETH9
