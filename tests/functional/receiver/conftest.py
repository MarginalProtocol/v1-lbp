import pytest

from ape.utils import ZERO_ADDRESS
from eth_abi import encode
from math import sqrt


@pytest.fixture(scope="module")
def mock_univ3_factory(project, accounts):
    return project.MockUniswapV3Factory.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def mock_margv1_factory(project, accounts, mock_univ3_factory):
    return project.MockMarginalV1Factory.deploy(
        mock_univ3_factory.address, sender=accounts[0]
    )


@pytest.fixture(scope="module")
def supplier(project, accounts, factory, mock_margv1_factory, WETH9):
    return project.MarginalV1LBSupplier.deploy(
        factory.address,
        mock_margv1_factory.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def liquidity_receiver_deployer(project, accounts, mock_margv1_factory, WETH9):
    # TODO: replace zero addresses with mocks
    return project.MarginalV1LBLiquidityReceiverDeployer.deploy(
        ZERO_ADDRESS,  # univ3 manager
        mock_margv1_factory.address,
        ZERO_ADDRESS,  # margv1 initializer
        ZERO_ADDRESS,  # margv1 router
        WETH9.address,
        sender=accounts[0],
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
def receiver_params(finalizer, sender):
    return (
        finalizer.address,  # treasuryAddress
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
def liquidity_receiver_and_pool(
    project,
    accounts,
    factory,
    supplier,
    liquidity_receiver_deployer,
    receiver_params,
    sender,
    finalizer,
    token0,
    token1,
    ticks,
    spot_reserve0,
    spot_reserve1,
    chain,
):
    def liquidity_receiver_and_pool(init_with_sqrt_price_lower_x96: bool):
        (tick_lower, tick_upper) = ticks
        tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
        amount_desired = (
            (spot_reserve0 * 100) // 10000
            if init_with_sqrt_price_lower_x96
            else (spot_reserve1 * 100) // 10000
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
            receiver_params,
        )
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
            liquidity_receiver_deployer.address,
            receiver_data,
            finalizer.address,
            deadline,
        )
        tx = supplier.createAndInitializePool(params, sender=sender)

        pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
        pool = project.MarginalV1LBPool.at(pool_address)

        receiver_address = tx.decode_logs(liquidity_receiver_deployer.ReceiverDeployed)[
            0
        ].receiver
        receiver = project.MarginalV1LBLiquidityReceiver.at(receiver_address)
        return (receiver, pool)

    yield liquidity_receiver_and_pool
