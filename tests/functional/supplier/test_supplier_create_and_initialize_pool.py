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
    alice,
    ticks,
    chain,
    init_with_sqrt_price_lower_x96,
):
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

    amount_desired = (
        (spot_reserve0 * 100) // 10000
        if init_with_sqrt_price_lower_x96
        else (spot_reserve1 * 100) // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600
    timestamp_initialize = chain.pending_timestamp
    finalizer = alice.address

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
        finalizer,
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

    # receiver and finalizer stored on supplier
    assert supplier.receivers(pool_address) == receiver_address
    assert supplier.finalizers(pool_address) == alice.address


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
    alice,
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
        (spot_reserve0 * 100) // 10000
        if init_with_sqrt_price_lower_x96
        else (spot_reserve1 * 100) // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600
    finalizer = alice.address

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
        finalizer,
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

    # TODO: fix interface, project issues to check state changes on receiver, pool for initialize calls


def test_supplier_create_and_initialize_pool__refunds_ETH_with_WETH9(
    supplier,
    receiver_deployer,
    factory,
    WETH9,
    token0_with_WETH9,
    token1_with_WETH9,
    spot_reserve0,
    spot_reserve1,
    sender,
    alice,
    ticks,
    chain,
):
    init_with_sqrt_price_lower_x96 = token0_with_WETH9.address == WETH9.address
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    balance0_sender = (
        sender.balance
        if init_with_sqrt_price_lower_x96
        else token0_with_WETH9.balanceOf(sender.address)
    )
    balance1_sender = (
        token1_with_WETH9.balanceOf(sender.address)
        if init_with_sqrt_price_lower_x96
        else sender.balance
    )

    amount_desired = (
        (spot_reserve0 * 100) // 10000
        if init_with_sqrt_price_lower_x96
        else (spot_reserve1 * 100) // 10000
    )
    receiver_data = encode(["address"], [sender.address])
    deadline = chain.pending_timestamp + 3600
    finalizer = alice.address

    sqrt_price_lower_x96 = calc_sqrt_price_x96_from_tick(tick_lower)
    sqrt_price_upper_x96 = calc_sqrt_price_x96_from_tick(tick_upper)

    tick_final = tick_upper if init_with_sqrt_price_lower_x96 else tick_lower
    sqrt_price_finalize_x96 = calc_sqrt_price_x96_from_tick(tick_final)

    amount0_pool = amount_desired if init_with_sqrt_price_lower_x96 else 0
    amount1_pool = 0 if init_with_sqrt_price_lower_x96 else amount_desired
    amount0_pool += 1  # mint does a rough round up when adding liquidity
    amount1_pool += 1

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
    amount0_total = amount0_pool + amount0_receiver
    amount1_total = amount1_pool + amount1_receiver

    # add a bit extra to amount0 total as buffer to check for refund
    value = (
        int(1.10 * amount0_total)
        if init_with_sqrt_price_lower_x96
        else int(1.10 * amount1_total)
    )

    params = (
        token0_with_WETH9.address,
        token1_with_WETH9.address,
        tick_lower,
        tick_upper,
        tick,
        amount_desired,
        0,  # amount0Min
        0,  # amount1Min
        receiver_deployer.address,
        receiver_data,
        finalizer,
        deadline,
    )
    tx = supplier.createAndInitializePool(params, sender=sender, value=value)

    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    receiver_address = tx.decode_logs(receiver_deployer.ReceiverDeployed)[0].receiver

    gas0_total = tx.gas_used * tx.gas_price if init_with_sqrt_price_lower_x96 else 0
    gas1_total = 0 if init_with_sqrt_price_lower_x96 else tx.gas_used * tx.gas_price

    balance0_sender -= amount0_total + gas0_total
    balance1_sender -= amount1_total + gas1_total

    balance0_sender_after = (
        sender.balance
        if init_with_sqrt_price_lower_x96
        else token0_with_WETH9.balanceOf(sender.address)
    )
    balance1_sender_after = (
        token1_with_WETH9.balanceOf(sender.address)
        if init_with_sqrt_price_lower_x96
        else sender.balance
    )

    assert pytest.approx(balance0_sender_after, rel=1e-4) == balance0_sender
    assert pytest.approx(balance1_sender_after, rel=1e-4) == balance1_sender

    balance0_pool_after = token0_with_WETH9.balanceOf(pool_address)
    balance1_pool_after = token1_with_WETH9.balanceOf(pool_address)

    assert pytest.approx(balance0_pool_after, rel=1e-4) == amount0_pool
    assert pytest.approx(balance1_pool_after, rel=1e-4) == amount1_pool

    balance0_receiver_after = token0_with_WETH9.balanceOf(receiver_address)
    balance1_receiver_after = token1_with_WETH9.balanceOf(receiver_address)

    assert pytest.approx(balance0_receiver_after, rel=1e-4) == amount0_receiver
    assert pytest.approx(balance1_receiver_after, rel=1e-4) == amount1_receiver


def test_supplier_create_and_initialize_pool__reverts_when_amount0_less_than_min(
    supplier,
    receiver_deployer,
    factory,
    token0,
    token1,
    spot_reserve0,
    spot_reserve1,
    sender,
    alice,
    ticks,
    chain,
):
    init_with_sqrt_price_lower_x96 = True
    (tick_lower, tick_upper) = ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    amount_desired = (
        (spot_reserve0 * 100) // 10000
        if init_with_sqrt_price_lower_x96
        else (spot_reserve1 * 100) // 10000
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
        alice.address,  # finalizer
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
    alice,
    ticks,
    chain,
):
    init_with_sqrt_price_lower_x96 = False
    (tick_lower, tick_upper) = ticks
    tick = tick_upper
    sqrt_price_x96 = calc_sqrt_price_x96_from_tick(tick)

    amount_desired = (spot_reserve1 * 100) // 10000
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
        alice.address,  # finalizer
        deadline,
    )
    with reverts(supplier.Amount1LessThanMin):
        supplier.createAndInitializePool(params, sender=sender)
