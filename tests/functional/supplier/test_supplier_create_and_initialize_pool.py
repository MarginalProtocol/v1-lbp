import pytest

from ape import reverts
from eth_abi import encode

from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_range_liquidity_from_sqrt_price_x96_amounts,
    calc_sqrt_price_x96_from_tick,
)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_create_and_initialize_pool__creates_pool_and_receiver(
    supplier,
    receiver_deployer,
    factory,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    sender,
    ticks,
    chain,
    init_with_sqrt_price_lower_x96,
):
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

    amount_desired = (
        spot_reserve0 * 1 // 10000
        if init_with_sqrt_price_lower_x96
        else spot_reserve1 * 1 // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600
    timestamp_initialize = chain.pending_timestamp

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
        deadline,
    )
    tx = supplier.createAndInitializePool(params, sender=sender)

    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    assert (
        factory.getPool(
            token0.address,
            token1.address,
            tick_lower,
            tick_upper,
            supplier.address,
            timestamp_initialize,
        )
        == pool_address
    )

    receiver_address = tx.decode_logs(receiver_deployer.ReceiverDeployed)[0].receiver
    assert receiver_deployer.receivers(pool_address) == receiver_address

    # receiver stored on supplier
    assert supplier.receivers(pool_address) == receiver_address


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_create_and_initialize_pool__initializes_pool_and_receiver(
    supplier,
    receiver_deployer,
    factory,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    sender,
    ticks,
    chain,
    init_with_sqrt_price_lower_x96,
):
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    amount_desired = (
        spot_reserve0 * 1 // 10000
        if init_with_sqrt_price_lower_x96
        else spot_reserve1 * 1 // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600

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
        deadline,
    )
    tx = supplier.createAndInitializePool(params, sender=sender)

    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    receiver_address = tx.decode_logs(receiver_deployer.ReceiverDeployed)[0].receiver

    amount0_pool = amount_desired if init_with_sqrt_price_lower_x96 else 0
    amount1_pool = 0 if init_with_sqrt_price_lower_x96 else amount_desired
    amount0_pool += 1  # mint does a rough round up when adding liquidity
    amount1_pool += 1

    assert pytest.approx(token0.balanceOf(pool_address), rel=1e-4) == amount0_pool
    assert pytest.approx(token1.balanceOf(pool_address), rel=1e-4) == amount1_pool

    sqrt_price_lower_x96 = calc_sqrt_price_x96_from_tick(tick_lower)
    sqrt_price_upper_x96 = calc_sqrt_price_x96_from_tick(tick_upper)

    tick_final = tick_upper if init_with_sqrt_price_lower_x96 else tick_lower
    sqrt_price_finalize_x96 = calc_sqrt_price_x96_from_tick(tick_final)

    liquidity = calc_range_liquidity_from_sqrt_price_x96_amounts(
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
        (amount_desired if init_with_sqrt_price_lower_x96 else 0),
        (0 if init_with_sqrt_price_lower_x96 else amount_desired),
    )
    (amount0_final, amount1_final) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity,
        sqrt_price_finalize_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    amount0_receiver = (
        (amount1_final * (1 << 192)) // (sqrt_price_finalize_x96**2)
        if init_with_sqrt_price_lower_x96
        else 0
    )
    amount1_receiver = (
        0
        if init_with_sqrt_price_lower_x96
        else (amount0_final * (sqrt_price_finalize_x96**2)) // (1 << 192)
    )

    assert (
        pytest.approx(token0.balanceOf(receiver_address), rel=1e-4) == amount0_receiver
    )
    assert (
        pytest.approx(token1.balanceOf(receiver_address), rel=1e-4) == amount1_receiver
    )

    balance0_sender -= amount0_pool + amount0_receiver
    balance1_sender -= amount1_pool + amount1_receiver

    assert pytest.approx(token0.balanceOf(sender.address), rel=1e-4) == balance0_sender
    assert pytest.approx(token1.balanceOf(sender.address), rel=1e-4) == balance1_sender


def test_supplier_create_and_initialize_pool__reverts_when_amount0_less_than_min(
    supplier,
    receiver_deployer,
    factory,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    sender,
    ticks,
    chain,
):
    init_with_sqrt_price_lower_x96 = True
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    amount_desired = (
        spot_reserve0 * 1 // 10000
        if init_with_sqrt_price_lower_x96
        else spot_reserve1 * 1 // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600

    amount0_pool = amount_desired
    amount0_pool += 1  # mint does a rough round up when adding liquidity

    sqrt_price_lower_x96 = calc_sqrt_price_x96_from_tick(tick_lower)
    sqrt_price_upper_x96 = calc_sqrt_price_x96_from_tick(tick_upper)
    sqrt_price_finalize_x96 = calc_sqrt_price_x96_from_tick(tick_upper)

    liquidity = calc_range_liquidity_from_sqrt_price_x96_amounts(
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
        amount_desired,
        0,
    )
    (amount0_final, amount1_final) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity,
        sqrt_price_finalize_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    amount0_receiver = (amount1_final * (1 << 192)) // (sqrt_price_finalize_x96**2)

    amount0_min = amount0_pool + amount0_receiver
    amount0_min = int(amount0_min * 1.01)  # buffer

    params = (
        token0.address,
        token1.address,
        tick_lower,
        tick_upper,
        tick,
        amount_desired,
        amount0_min,  # amount0Min
        0,  # amount1Min
        receiver_deployer.address,
        receiver_data,
        deadline,
    )
    with reverts(supplier.Amount0LessThanMin):
        supplier.createAndInitializePool(params, sender=sender)


def test_supplier_create_and_initialize_pool__reverts_when_amount1_less_than_min(
    supplier,
    receiver_deployer,
    factory,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    sender,
    ticks,
    chain,
):
    init_with_sqrt_price_lower_x96 = False
    (tick_lower, tick_upper) = ticks
    tick = tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    amount_desired = spot_reserve1 * 1 // 10000
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600

    amount1_pool = amount_desired
    amount1_pool += 1  # mint does a rough round up when adding liquidity

    sqrt_price_lower_x96 = calc_sqrt_price_x96_from_tick(tick_lower)
    sqrt_price_upper_x96 = calc_sqrt_price_x96_from_tick(tick_upper)

    tick_final = tick_upper if init_with_sqrt_price_lower_x96 else tick_lower
    sqrt_price_finalize_x96 = calc_sqrt_price_x96_from_tick(tick_final)

    liquidity = calc_range_liquidity_from_sqrt_price_x96_amounts(
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
        (amount_desired if init_with_sqrt_price_lower_x96 else 0),
        (0 if init_with_sqrt_price_lower_x96 else amount_desired),
    )
    (amount0_final, amount1_final) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        liquidity,
        sqrt_price_finalize_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    amount1_receiver = (amount0_final * (sqrt_price_finalize_x96**2)) // (1 << 192)

    amount1_min = amount1_pool + amount1_receiver
    amount1_min = int(amount1_min * 1.01)  # buffer

    params = (
        token0.address,
        token1.address,
        tick_lower,
        tick_upper,
        tick,
        amount_desired,
        0,  # amount0Min
        amount1_min,  # amount1Min
        receiver_deployer.address,
        receiver_data,
        deadline,
    )
    with reverts(supplier.Amount1LessThanMin):
        supplier.createAndInitializePool(params, sender=sender)
