import pytest


@pytest.fixture(scope="session")
def admin(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def bob(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def sender(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def rando_token_a_address():
    return "0x000000000000000000000000000000000000000A"


@pytest.fixture(scope="session")
def rando_token_b_address():
    return "0x000000000000000000000000000000000000000b"


@pytest.fixture(scope="session")
def create_token(project, accounts):
    def create_token(name, decimals=18):
        return project.Token.deploy(name, decimals, sender=accounts[0])

    yield create_token


@pytest.fixture(scope="session")
def token_a(project, accounts, create_token):
    return create_token("A", decimals=6)


@pytest.fixture(scope="session")
def token_b(project, accounts, create_token):
    return create_token("B", decimals=18)


@pytest.fixture(scope="session")
def token_c(project, accounts, create_token):
    return create_token("C", decimals=18)


@pytest.fixture(scope="session")
def WETH9(project, accounts):
    return project.WETH9.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def rando_univ3_fee():
    return 500


@pytest.fixture(scope="session")
def univ3_factory_address():
    # https://docs.uniswap.org/contracts/v3/reference/deployments
    return "0x1F98431c8aD98523631AE4a59f267346ea31F984"


@pytest.fixture(scope="session")
def factory(project, accounts):
    deployer = project.MarginalV1LBPoolDeployer.deploy(sender=accounts[0])
    return project.MarginalV1LBFactory.deploy(deployer.address, sender=accounts[0])


@pytest.fixture(scope="session")
def create_pool(project, accounts, factory):
    def create_pool(
        _token_a, _token_b, _tick_lower, _tick_upper, _supplier, _timestamp_initial
    ):
        tx = factory.createPool(
            _token_a,
            _token_b,
            _tick_lower,
            _tick_upper,
            _supplier,
            _timestamp_initial,
            sender=accounts[0],
        )
        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        return project.MarginalV1LBPool.at(pool_address)

    yield create_pool


@pytest.fixture(scope="session")
def callee(project, accounts):
    return project.TestMarginalV1LBPoolCallee.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def ticks():
    tick_width = 2000  # ~50% in price from low to high
    tick_mid = 197682  # USDC/WETH tick on spot
    return (tick_mid - tick_width, tick_mid + tick_width)


@pytest.fixture(scope="session")
def pool(project, accounts, chain, token_a, token_b, ticks, callee, create_pool):
    (tick_lower, tick_upper) = ticks
    timestamp_initialize = chain.pending_timestamp
    return create_pool(
        token_a,
        token_b,
        tick_lower,
        tick_upper,
        callee,  # callee is supplier for core tests
        timestamp_initialize,
    )


@pytest.fixture(scope="session")
def another_pool(
    project, accounts, chain, token_a, token_b, ticks, callee, create_pool
):
    (tick_lower, tick_upper) = ticks
    tick_width = (tick_upper - tick_lower) // 2
    tick_mid = (tick_lower + tick_upper) // 2

    # wider tick range
    tick_width = int(1.25 * tick_width)
    tick_upper = tick_mid + tick_width
    tick_lower = tick_mid - tick_width

    timestamp_initialize = chain.pending_timestamp
    return create_pool(
        token_a,
        token_b,
        tick_lower,
        tick_upper,
        callee,  # callee is supplier for core tests
        timestamp_initialize,
    )


@pytest.fixture(scope="session")
def pool_two(project, accounts, chain, token_a, token_b, ticks, callee, create_pool):
    (tick_lower, tick_upper) = ticks
    tick_width = (tick_upper - tick_lower) // 2
    tick_mid = (tick_lower + tick_upper) // 2

    # narrower tick range
    tick_width = int(0.75 * tick_width)
    tick_upper = tick_mid + tick_width
    tick_lower = tick_mid - tick_width

    timestamp_initialize = chain.pending_timestamp
    return create_pool(
        token_a,
        token_b,
        tick_lower,
        tick_upper,
        callee,  # callee is supplier for core tests
        timestamp_initialize,
    )


@pytest.fixture(scope="session")
def pool_with_WETH9(
    project, accounts, chain, token_a, WETH9, ticks, callee, create_pool
):
    (tick_lower, tick_upper) = ticks
    timestamp_initialize = chain.pending_timestamp
    return create_pool(
        token_a,
        WETH9,
        tick_lower,
        tick_upper,
        callee,  # callee is supplier for core tests
        timestamp_initialize,
    )


@pytest.fixture(scope="session")
def sqrt_price_math_lib(project, accounts):
    return project.MockSqrtPriceMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def liquidity_math_lib(project, accounts):
    return project.MockLiquidityMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def swap_math_lib(project, accounts):
    return project.MockSwapMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def tick_math_lib(project, accounts):
    return project.MockTickMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def range_math_lib(project, accounts):
    return project.MockRangeMath.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def liquidity_amounts_lib(project, accounts):
    return project.MockLiquidityAmounts.deploy(sender=accounts[0])


@pytest.fixture(scope="session")
def callback_validation_lib(project, accounts):
    return project.MockCallbackValidation.deploy(sender=accounts[0])
