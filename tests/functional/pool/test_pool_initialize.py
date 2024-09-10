import pytest
from math import sqrt

from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
)


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_initialize__updates_state(
    another_pool,
    factory,
    callee,
    sender,
    admin,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 1 // 10000  # 0.01% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.sqrtPriceX96 == 0

    # update factory to set global protocol fee
    factory.setFeeProtocol(fee_protocol, sender=admin)
    assert factory.feeProtocol() == fee_protocol

    sqrt_price_lower_x96 = another_pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = another_pool.sqrtPriceUpperX96()
    sqrt_price_x96 = (
        sqrt_price_lower_x96 if init_with_sqrt_price_lower_x96 else sqrt_price_upper_x96
    )
    tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96)

    # mint more to sender in case
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    if init_with_sqrt_price_lower_x96:
        amount0 += 1
    else:
        amount1 += 1  # mint does a rough round up when adding liquidity

    token0.mint(sender.address, amount0, sender=sender)
    token1.mint(sender.address, amount1, sender=sender)

    callee.initialize(
        another_pool.address,
        liquidity_delta,
        sqrt_price_x96,
        sender=sender,
    )

    sqrt_price_initialize_x96 = sqrt_price_x96
    sqrt_price_finalize_x96 = (
        sqrt_price_upper_x96 if init_with_sqrt_price_lower_x96 else sqrt_price_lower_x96
    )
    assert another_pool.sqrtPriceInitializeX96() == sqrt_price_initialize_x96
    assert another_pool.sqrtPriceFinalizeX96() == sqrt_price_finalize_x96

    state.sqrtPriceX96 = sqrt_price_x96
    state.liquidity = liquidity_delta
    state.tick = tick
    state.blockTimestamp = chain.blocks.head.timestamp
    state.tickCumulative = 0
    state.feeProtocol = fee_protocol
    state.finalized = False

    result = another_pool.state()

    assert pytest.approx(result.sqrtPriceX96, rel=1e-4) == state.sqrtPriceX96
    assert result.totalPositions == state.totalPositions
    assert result.liquidity == state.liquidity
    assert pytest.approx(result.tick, abs=1) == state.tick
    assert result.tickCumulative == state.tickCumulative
    assert result.feeProtocol == state.feeProtocol
    assert result.finalized == state.finalized


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_initialize__mints_lp_shares(
    another_pool,
    callee,
    sender,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 1 // 10000  # 0.01% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.sqrtPriceX96 == 0

    sqrt_price_lower_x96 = another_pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = another_pool.sqrtPriceUpperX96()
    sqrt_price_x96 = (
        sqrt_price_lower_x96 if init_with_sqrt_price_lower_x96 else sqrt_price_upper_x96
    )

    # mint more to sender in case
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    if init_with_sqrt_price_lower_x96:
        amount0 += 1
    else:
        amount1 += 1  # mint does a rough round up when adding liquidity

    token0.mint(sender.address, amount0, sender=sender)
    token1.mint(sender.address, amount1, sender=sender)

    callee.initialize(
        another_pool.address,
        liquidity_delta,
        sqrt_price_x96,
        sender=sender,
    )

    total_supply += liquidity_delta
    assert another_pool.totalSupply() == total_supply
    assert another_pool.balanceOf(another_pool.address) == liquidity_delta


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_initialize__transfers_funds(
    another_pool,
    callee,
    sender,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    ticks,
    init_with_sqrt_price_lower_x96,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 1 // 10000  # 0.01% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.sqrtPriceX96 == 0

    sqrt_price_lower_x96 = another_pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = another_pool.sqrtPriceUpperX96()
    sqrt_price_x96 = (
        sqrt_price_lower_x96 if init_with_sqrt_price_lower_x96 else sqrt_price_upper_x96
    )

    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    if init_with_sqrt_price_lower_x96:
        amount0 += 1
    else:
        amount1 += 1  # mint does a rough round up when adding liquidity

    token0.mint(sender.address, amount0, sender=sender)
    token1.mint(sender.address, amount1, sender=sender)

    shares_before = another_pool.balanceOf(another_pool.address)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(another_pool.address)
    balance1_pool = token1.balanceOf(another_pool.address)

    tx = callee.initialize(
        another_pool.address,
        liquidity_delta,
        sqrt_price_x96,
        sender=sender,
    )
    shares = another_pool.balanceOf(another_pool.address) - shares_before

    balance0_pool += amount0
    balance1_pool += amount1

    assert token0.balanceOf(another_pool.address) == balance0_pool
    assert token1.balanceOf(another_pool.address) == balance1_pool

    return_log = tx.decode_logs(callee.InitializeReturn)[0]
    assert (return_log.shares, return_log.amount0, return_log.amount1) == (
        shares,
        amount0,
        amount1,
    )

    balance0_sender -= amount0
    balance1_sender -= amount1

    assert token0.balanceOf(sender.address) == balance0_sender
    assert token1.balanceOf(sender.address) == balance1_sender


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_initialize__emits_initialize(
    another_pool,
    callee,
    sender,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    liquidity_spot = int(sqrt(spot_reserve0 * spot_reserve1))
    liquidity_delta = liquidity_spot * 1 // 10000  # 0.01% of spot reserves
    total_supply = another_pool.totalSupply()
    assert total_supply == 0

    state = another_pool.state()
    assert state.sqrtPriceX96 == 0

    sqrt_price_lower_x96 = another_pool.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = another_pool.sqrtPriceUpperX96()
    sqrt_price_x96 = (
        sqrt_price_lower_x96 if init_with_sqrt_price_lower_x96 else sqrt_price_upper_x96
    )

    # mint more to sender in case
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity_delta,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    if init_with_sqrt_price_lower_x96:
        amount0 += 1
    else:
        amount1 += 1  # mint does a rough round up when adding liquidity

    token0.mint(sender.address, amount0, sender=sender)
    token1.mint(sender.address, amount1, sender=sender)

    tx = callee.initialize(
        another_pool.address,
        liquidity_delta,
        sqrt_price_x96,
        sender=sender,
    )
    state = another_pool.state()

    events = tx.decode_logs(another_pool.Initialize)
    assert len(events) == 1
    event = events[0]

    assert event.liquidity == state.liquidity
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.tick == state.tick
