import pytest


# TODO: test emit, revert cases with non initialized receiver prior to test


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_initialize__updates_reserves(
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

    balance0 = token0.balanceOf(liquidity_receiver.address)
    balance1 = token1.balanceOf(liquidity_receiver.address)

    (amount0, amount1) = liquidity_receiver.seeds(
        pool.state().liquidity,
        pool.sqrtPriceInitializeX96(),
        pool.sqrtPriceLowerX96(),
        pool.sqrtPriceUpperX96(),
    )
    assert balance0 >= amount0
    assert balance1 >= amount1
    assert pytest.approx(balance0, rel=1e-6) == amount0
    assert pytest.approx(balance1, rel=1e-6) == amount1

    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 == amount0
    assert reserve1 == amount1
