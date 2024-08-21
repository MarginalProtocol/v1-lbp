import pytest

from math import sqrt
from utils.utils import calc_sqrt_price_x96_from_tick, calc_swap_amounts


@pytest.fixture
def reserve0():
    return int(4.22468e12)  # e.g. USDC reserves on spot


@pytest.fixture
def reserve1():
    return int(1.62406e21)  # e.g. WETH reserves on spot


@pytest.fixture
def liquidity(reserve0, reserve1):
    return int(sqrt(reserve0 * reserve1))


@pytest.mark.parametrize("skew", [-1.0, -0.5, 0, 0.5, 1.0])
@pytest.mark.parametrize("fee", [10, 50, 100])
def test_range_math_range_fees__returns_fees(
    range_math_lib,
    liquidity_amounts_lib,
    ticks,
    skew,
    fee,
    liquidity,
):
    (tick_lower, tick_upper) = ticks
    (sqrt_price_lower_x96, sqrt_price_upper_x96) = (
        calc_sqrt_price_x96_from_tick(tick_lower),
        calc_sqrt_price_x96_from_tick(tick_upper),
    )

    tick_width = (tick_upper - tick_lower) // 2
    tick_mid = (tick_lower + tick_upper) // 2

    delta = int(tick_width * skew)
    tick = tick_mid + delta
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    # Ref: @Uniswap/v3-core/contracts/UniswapV3Pool.sol#L350
    (amount0, _) = calc_swap_amounts(
        liquidity,
        sqrt_price_upper_x96,
        sqrt_price_x96,
    )
    (_, amount1) = calc_swap_amounts(
        liquidity,
        sqrt_price_lower_x96,
        sqrt_price_x96,
    )

    liquidity_after = liquidity_amounts_lib.getLiquidityForAmounts(
        sqrt_price_x96, sqrt_price_lower_x96, sqrt_price_upper_x96, amount0, amount1
    )
    assert pytest.approx(liquidity_after, rel=1e-6) == liquidity

    result = range_math_lib.rangeFees(
        amount0,
        amount1,
        fee,
    )
    (result0, result1) = result

    fees0 = int((amount0 * fee) // 1e4)
    fees1 = int((amount1 * fee) // 1e4)

    assert pytest.approx(result0, rel=1e-6) == fees0
    assert pytest.approx(result1, rel=1e-6) == fees1
