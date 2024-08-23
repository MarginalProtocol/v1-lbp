import pytest

from math import sqrt

from utils.constants import MAX_SQRT_RATIO
from utils.utils import calc_swap_amounts


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
def token0(pool, token_a, token_b, sender, callee, spot_reserve0):
    token0 = token_a if pool.token0() == token_a.address else token_b
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.mint(sender.address, spot_reserve0, sender=sender)
    return token0


@pytest.fixture(scope="module")
def token1(pool, token_a, token_b, sender, callee, spot_reserve1):
    token1 = token_b if pool.token1() == token_b.address else token_a
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.mint(sender.address, spot_reserve1, sender=sender)
    return token1


@pytest.fixture(scope="module")
def pool_initialized_with_liquidity(
    pool, callee, token0, token1, sender, spot_liquidity, sqrt_price_x96_initial, ticks
):
    liquidity_delta = spot_liquidity * 1 // 10000  # 0.01% of spot reserves
    sqrt_price_lower_x96 = pool.sqrtPriceLowerX96()

    callee.initialize(
        pool.address,
        liquidity_delta,
        sqrt_price_lower_x96,
        sender=sender,
    )

    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        liquidity_delta, sqrt_price_lower_x96, sqrt_price_x96_initial
    )
    token1.mint(sender.address, amount1, sender=sender)

    zero_for_one = False
    amount_specified = amount1
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    callee.swap(
        pool.address,
        sender.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return pool
