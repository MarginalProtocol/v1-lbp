import pytest

from eth_abi import encode


@pytest.mark.integration
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_integration_quoter_quote_create_and_initialize_pool__quotes_create(
    margv1_quoter_initialized,
    margv1_liquidity_receiver_deployer,
    margv1_supplier,
    margv1_token0,
    margv1_token1,
    margv1_ticks,
    margv1_receiver_params,
    factory,
    finalizer,
    treasury,
    project,
    sender,
    init_with_sqrt_price_lower_x96,
):
    (tick_lower, tick_upper) = margv1_ticks
    tick = tick_lower if init_with_sqrt_price_lower_x96 else tick_upper

    amount_desired = (
        margv1_token0.balanceOf(sender.address) // 10
        if init_with_sqrt_price_lower_x96
        else margv1_token1.balanceOf(sender.address) // 10
    )
    receiver_data = encode(
        [
            "address",
            "uint24",
            "uint24",
            "uint24",
            "uint24",
            "address",
            "uint96",
            "address",
        ],
        margv1_receiver_params,
    )
    params = (
        margv1_token0.address,
        margv1_token1.address,
        tick_lower,
        tick_upper,
        tick,
        amount_desired,
        0,  # amount0Min
        0,  # amount1Min
        margv1_liquidity_receiver_deployer.address,
        receiver_data,
        finalizer.address,
    )
    result = margv1_quoter_initialized.quoteCreateAndInitializePool(params)

    # cache balances before
    balance0_sender = margv1_token0.balanceOf(sender.address)
    balance1_sender = margv1_token1.balanceOf(sender.address)

    tx = margv1_supplier.createAndInitializePool(params, sender=sender)
    pool_address = tx.decode_logs(factory.PoolCreated)[0].pool
    pool = project.MarginalV1LBPool.at(pool_address)

    shares = pool.balanceOf(pool.address)
    amount0 = balance0_sender - margv1_token0.balanceOf(sender.address)
    amount1 = balance1_sender - margv1_token1.balanceOf(sender.address)

    state = pool.state()
    liquidity = state.liquidity
    sqrt_price_x96 = state.sqrtPriceX96

    (sqrt_price_lower_x96, sqrt_price_upper_x96) = (
        pool.sqrtPriceLowerX96(),
        pool.sqrtPriceUpperX96(),
    )
    assert result == (
        shares,
        amount0,
        amount1,
        liquidity,
        sqrt_price_x96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
