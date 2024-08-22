import pytest
from ape import reverts

from hexbytes import HexBytes
from utils.utils import calc_sqrt_price_x96_from_tick


def test_pool_constructor__sets_params(
    chain, factory, pool, token_a, token_b, ticks, callee
):
    _token0 = (
        token_a if HexBytes(token_a.address) < HexBytes(token_b.address) else token_b
    )
    _token1 = (
        token_b if HexBytes(token_a.address) < HexBytes(token_b.address) else token_a
    )

    assert pool.factory() == factory.address
    assert pool.token0() == _token0.address
    assert pool.token1() == _token1.address

    (tick_lower, tick_upper) = ticks
    assert pool.tickLower() == tick_lower
    assert pool.tickUpper() == tick_upper
    assert pytest.approx(
        pool.sqrtPriceLowerX96(), rel=1e-4
    ) == calc_sqrt_price_x96_from_tick(tick_lower)
    assert pytest.approx(
        pool.sqrtPriceUpperX96(), rel=1e-4
    ) == calc_sqrt_price_x96_from_tick(tick_upper)

    assert pool.supplier() == callee.address
    assert pool.blockTimestampInitialize() == chain.blocks.head.timestamp


def test_pool_constructor__reverts_when_tick_lower_greater_than_upper(
    chain, pool, create_pool, token_a, token_b, ticks, callee
):
    (_, tick_upper) = ticks
    timestamp_initialize = chain.pending_timestamp
    with reverts(pool.InvalidTicks):
        create_pool(
            token_a,
            token_b,
            tick_upper,
            tick_upper,
            callee,
            timestamp_initialize,
        )


def test_pool_constructor__reverts_when_timestamp_initialize_less_than_block_timestamp(
    chain, pool, create_pool, token_a, token_b, ticks, callee
):
    (tick_lower, tick_upper) = ticks
    timestamp_initialize = chain.pending_timestamp - 1
    with reverts(pool.InvalidBlockTimestamp):
        create_pool(
            token_a,
            token_b,
            tick_lower - 10,
            tick_upper + 10,
            callee,
            timestamp_initialize,
        )
