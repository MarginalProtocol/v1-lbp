import pytest

from eth_abi import encode
from math import sqrt


@pytest.fixture(scope="module")
def supplier(project, accounts, factory, univ3_factory_address, WETH9):
    # use mock margv1 factory
    _margv1_factory = project.MockMarginalV1Factory.deploy(
        univ3_factory_address, sender=accounts[0]
    )
    return project.MarginalV1LBSupplier.deploy(
        factory.address,
        _margv1_factory.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def receiver_deployer(project, accounts):
    return project.MockMarginalV1LBReceiverDeployer.deploy(sender=accounts[0])


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
def token0(pool, token_a, token_b, sender, callee, supplier, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(supplier.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, callee, supplier, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(supplier.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1


@pytest.fixture(scope="module")
def finalizer(accounts):
    yield accounts[4]


@pytest.fixture(scope="module")
def receiver_and_pool(
    project,
    accounts,
    factory,
    supplier,
    receiver_deployer,
    sender,
    finalizer,
    token0,
    token1,
    ticks,
    spot_reserve0,
    spot_reserve1,
    chain,
):
    def receiver_and_pool(init_with_sqrt_price_lower_x96: bool):
        (tick_lower, tick_upper) = ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
        amount_desired = (
            (spot_reserve0 * 100) // 10000
            if init_with_sqrt_price_lower_x96
            else (spot_reserve1 * 100) // 10000
        )
        receiver_data = encode(["address"], [sender.address])
        deadline = chain.pending_timestamp
        params = (
            token0.address,
            token1.address,
            tick_lower,
            tick_upper,
            tick,
            amount_desired,
            0,  # amount0Min
            0,  # amount1Min
            receiver_deployer.address,
            receiver_data,
            finalizer.address,
            deadline,
        )
        tx = supplier.createAndInitializePool(params, sender=sender)

        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        receiver_address = tx.decode_logs(receiver_deployer.ReceiverDeployed)[
            0
        ].receiver
        receiver = project.MockMarginalV1LBReceiver.at(receiver_address)
        return (receiver, pool)

    yield receiver_and_pool


@pytest.fixture(scope="module")
def token0_with_WETH9(
    pool_with_WETH9, token_a, WETH9, sender, callee, supplier, spot_reserve0, chain
):
    _token0 = token_a if pool_with_WETH9.token0() == token_a.address else WETH9
    _token0.approve(callee.address, 2**256 - 1, sender=sender)
    _token0.approve(supplier.address, 2**256 - 1, sender=sender)

    if _token0.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve0 + sender.balance)
        WETH9.deposit(value=spot_reserve0, sender=sender)
    else:
        _token0.mint(sender.address, spot_reserve0, sender=sender)
    return _token0


@pytest.fixture(scope="module")
def token1_with_WETH9(
    pool_with_WETH9, token_a, WETH9, sender, callee, supplier, spot_reserve1, chain
):
    _token1 = WETH9 if pool_with_WETH9.token1() == WETH9.address else token_a
    _token1.approve(callee.address, 2**256 - 1, sender=sender)
    _token1.approve(supplier.address, 2**256 - 1, sender=sender)

    if _token1.address == WETH9.address:
        chain.set_balance(sender.address, spot_reserve1 + sender.balance)
        WETH9.deposit(value=spot_reserve1, sender=sender)
    else:
        _token1.mint(sender.address, spot_reserve1, sender=sender)
    return _token1


@pytest.fixture(scope="module")
def receiver_and_pool_with_WETH9(
    project,
    accounts,
    factory,
    supplier,
    receiver_deployer,
    sender,
    finalizer,
    token0_with_WETH9,
    token1_with_WETH9,
    ticks,
    spot_reserve0,
    spot_reserve1,
    chain,
):
    def receiver_and_pool_with_WETH9(init_with_sqrt_price_lower_x96: bool):
        (tick_lower, tick_upper) = ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
        amount_desired = (
            (spot_reserve0 * 100) // 10000
            if init_with_sqrt_price_lower_x96
            else (spot_reserve1 * 100) // 10000
        )
        receiver_data = encode(["address"], [sender.address])
        deadline = chain.pending_timestamp
        params = (
            token0_with_WETH9.address,
            token1_with_WETH9.address,
            tick_lower,
            tick_upper,
            tick,
            amount_desired,
            0,  # amount0Min
            0,  # amount1Min
            receiver_deployer.address,
            receiver_data,
            finalizer.address,
            deadline,
        )
        tx = supplier.createAndInitializePool(params, sender=sender)

        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        receiver_address = tx.decode_logs(receiver_deployer.ReceiverDeployed)[
            0
        ].receiver
        receiver = project.MockMarginalV1LBReceiver.at(receiver_address)
        return (receiver, pool)

    yield receiver_and_pool
