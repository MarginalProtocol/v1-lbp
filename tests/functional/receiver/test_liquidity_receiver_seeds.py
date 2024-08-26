import pytest

from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_amounts_from_liquidity_sqrt_price_x96,
)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_seeds__returns_amounts(
    liquidity_receiver_and_pool,
    init_with_sqrt_price_lower_x96,
):
    (liquidity_receiver, pool) = liquidity_receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )

    state = pool.state()
    assert state.sqrtPriceX96 == pool.sqrtPriceInitializeX96()

    sqrt_price_lower_x96 = pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool.sqrtPriceUpperX96()
    sqrt_price_finalize_x96 = pool.sqrtPriceFinalizeX96()
    (amount0_pool, amount1_pool) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        sqrt_price_finalize_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    # calculate liquidity associated with raised side of pool
    zero_for_one = sqrt_price_finalize_x96 == sqrt_price_upper_x96
    liquidity = (
        (amount1_pool * (1 << 96)) // sqrt_price_finalize_x96
        if zero_for_one
        else (amount0_pool * sqrt_price_finalize_x96) // (1 << 96)
    )

    (amount0_desired, amount1_desired) = calc_amounts_from_liquidity_sqrt_price_x96(
        liquidity, sqrt_price_finalize_x96
    )
    if not zero_for_one:
        assert amount1_pool == 0
        assert amount0_pool >= amount0_desired
    else:
        assert amount0_pool == 0
        assert amount1_pool >= amount1_desired

    amount0 = amount0_desired if zero_for_one else 0
    amount1 = 0 if zero_for_one else amount1_desired

    (result_amount0, result_amount1) = liquidity_receiver.seeds(
        state.liquidity,
        state.sqrtPriceX96,
        pool.sqrtPriceLowerX96(),
        pool.sqrtPriceUpperX96(),
    )
    assert pytest.approx(result_amount0, rel=1e-6) == amount0
    assert pytest.approx(result_amount1, rel=1e-6) == amount1
