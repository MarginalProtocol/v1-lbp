import pytest

from eth_abi import encode


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


def test_supplier_create_and_initialize_pool__initializes_pool_and_receiver():
    pass


def test_supplier_create_and_initialize_pool__reverts_when_amount0_less_than_min():
    pass


def test_supplier_create_and_initialize_pool__reverts_when_amount1_less_than_min():
    pass
