import pytest

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


# TODO: mock receiver deployment


@pytest.fixture(scope="module")
def spot_reserve0(pool, token_a, token_b):
    y = int(4.22468e14)  # e.g. USDC reserves on spot
    x = int(1.62406e23)  # e.g. WETH reserves on spot
    return x if pool.token0() == token_a.address else y


@pytest.fixture(scope="module")
def spot_reserve1(pool, token_a, token_b):
    y = int(4.22468e14)  # e.g. USDC reserves on spot
    x = int(1.62406e23)  # e.g. WETH reserves on spot
    return y if pool.token1() == token_b.address else x


@pytest.fixture(scope="module")
def spot_liquidity(spot_reserve0, spot_reserve1):
    return int(sqrt(spot_reserve0 * spot_reserve1))


@pytest.fixture(scope="module")
def sqrt_price_x96_initial(spot_reserve0, spot_reserve1):
    sqrt_price = sqrt(spot_reserve1 / spot_reserve0)
    return int(sqrt_price * (1 << 96))


@pytest.fixture(scope="module")
def token0(pool, token_a, token_b, sender, supplier, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(supplier.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, supplier, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(supplier.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1
