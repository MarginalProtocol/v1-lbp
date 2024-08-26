import pytest


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_constructor__sets_params(
    liquidity_receiver_and_pool,
    liquidity_receiver_deployer,
    token0,
    token1,
    receiver_params,
    init_with_sqrt_price_lower_x96,
):
    (liquidity_receiver, pool) = liquidity_receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )
    assert liquidity_receiver.pool() == pool.address
    assert liquidity_receiver.token0() == token0.address
    assert liquidity_receiver.token1() == token1.address
    assert liquidity_receiver.deployer() == liquidity_receiver_deployer.address
    assert liquidity_receiver.receiverParams() == receiver_params
