import pytest

from utils.utils import (
    calc_sqrt_price_x96_from_tick,
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_amounts_from_liquidity_sqrt_price_x96,
)


# TODO: fuzzing for sqrtPriceX96 initial


@pytest.mark.parametrize("percent_thru_range", [0, 0.25, 0.5, 0.75, 1.0])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_get_amounts_desired__returns_amounts(
    liquidity_receiver_and_pool,
    percent_thru_range,
    ticks,
    init_with_sqrt_price_lower_x96,
):
    (liquidity_receiver, pool) = liquidity_receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )
    state = pool.state()

    (tick_lower, tick_upper) = ticks
    tick_width_2x = tick_upper - tick_lower

    delta = int(tick_width_2x * percent_thru_range)
    tick = tick_lower + delta
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    sqrt_price_lower_x96 = pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool.sqrtPriceUpperX96()

    if sqrt_price_x96 < sqrt_price_lower_x96:
        sqrt_price_x96 = sqrt_price_lower_x96
    elif sqrt_price_x96 > sqrt_price_upper_x96:
        sqrt_price_x96 = sqrt_price_upper_x96

    (amount0_pool, amount1_pool) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    zero_for_one = init_with_sqrt_price_lower_x96
    liquidity = (
        (amount1_pool * (1 << 96)) // sqrt_price_x96
        if zero_for_one
        else (amount0_pool * sqrt_price_x96) // (1 << 96)
    )

    (amount0, amount1) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_x96
    )
    (result_amount0, result_amount1) = liquidity_receiver.getAmountsDesired(
        sqrt_price_x96,
        amount0_pool,
        amount1_pool,
        zero_for_one,
    )
