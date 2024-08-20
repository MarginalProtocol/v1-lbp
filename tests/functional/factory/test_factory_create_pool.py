from ape import reverts

from utils.utils import calc_sqrt_price_x96_from_tick


def test_create_pool__deploys_pool_contract(
    project,
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    ticks,
    callee,
    chain,
):
    (tick_lower, tick_upper) = ticks
    timestamp_initial = chain.pending_timestamp + 3600

    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        tick_lower,
        tick_upper,
        callee.address,  # supplier
        timestamp_initial,
        sender=alice,
    )
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

    assert pool.factory() == factory.address
    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address
    assert pool.tickLower() == tick_lower
    assert pool.tickUpper() == tick_upper
    assert pool.sqrtPriceLowerX96() == calc_sqrt_price_x96_from_tick(tick_lower)
    assert pool.sqrtPriceUpperX96() == calc_sqrt_price_x96_from_tick(tick_upper)
    assert pool.supplier() == callee.address
    assert pool.blockTimestampInitialize() == timestamp_initial


def test_create_pool__stores_pool_address(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    ticks,
    callee,
    chain,
):
    (tick_lower, tick_upper) = ticks
    timestamp_initial = chain.pending_timestamp + 3600
    supplier = callee.address

    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        tick_lower,
        tick_upper,
        supplier,
        timestamp_initial,
        sender=alice,
    )
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool

    assert (
        factory.getPool(
            rando_token_a_address,
            rando_token_b_address,
            tick_lower,
            tick_upper,
            supplier,
            timestamp_initial,
        )
        == pool_address
    )
    assert (
        factory.getPool(
            rando_token_b_address,
            rando_token_a_address,
            tick_lower,
            tick_upper,
            supplier,
            timestamp_initial,
        )
        == pool_address
    )
    assert factory.isPool(pool_address) is True


def test_create_pool__orders_tokens(
    project,
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    ticks,
    callee,
    chain,
):
    (tick_lower, tick_upper) = ticks
    timestamp_initial = chain.pending_timestamp + 3600
    supplier = callee.address

    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        tick_lower,
        tick_upper,
        supplier,
        timestamp_initial,
        sender=alice,
    )
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1Pool.at(pool_address)

    assert pool.token0() == rando_token_a_address
    assert pool.token1() == rando_token_b_address


def test_create_pool__emits_pool_created(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    ticks,
    callee,
    chain,
):
    (tick_lower, tick_upper) = ticks
    timestamp_initial = chain.pending_timestamp + 3600
    supplier = callee.address

    tx = factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        tick_lower,
        tick_upper,
        supplier,
        timestamp_initial,
        sender=alice,
    )

    events = tx.decode_logs(factory.PoolCreated)
    assert len(events) == 1
    event = events[0]

    assert event.token0 == rando_token_a_address
    assert event.token1 == rando_token_b_address
    assert event.tickLower == tick_lower
    assert event.tickUpper == tick_upper
    assert event.supplier == supplier
    assert event.blockTimestampInitialize == timestamp_initial
    assert (
        event.pool.lower()
        == factory.getPool(
            rando_token_a_address,
            rando_token_b_address,
            tick_lower,
            tick_upper,
            supplier,
            timestamp_initial,
        ).lower()
    )


def test_create_pool__reverts_when_pool_active(
    factory,
    alice,
    rando_token_a_address,
    rando_token_b_address,
    ticks,
    callee,
    chain,
):
    (tick_lower, tick_upper) = ticks
    timestamp_initial = chain.pending_timestamp + 3600
    supplier = callee.address

    factory.createPool(
        rando_token_a_address,
        rando_token_b_address,
        tick_lower,
        tick_upper,
        supplier,
        timestamp_initial,
        sender=alice,
    )

    # should fail when try again with same params
    with reverts(factory.PoolActive):
        factory.createPool(
            rando_token_a_address,
            rando_token_b_address,
            tick_lower,
            tick_upper,
            supplier,
            timestamp_initial,
            sender=alice,
        )
