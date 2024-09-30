import pytest

from ape import reverts
from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_swap_amounts,
)


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_integration_quoter_quote_exact_output_single__quotes_swap(
    margv1lb_router,
    margv1_pool_initialized,
    margv1_quoter,
    margv1_token0,
    margv1_token1,
    chain,
    sender,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = margv1_pool_initialized(
        init_with_sqrt_price_lower_x96
    )
    state = pool_initialized_with_liquidity.state()
    assert state.sqrtPriceX96 > 0

    tick_lower = pool_initialized_with_liquidity.tickLower()
    tick_upper = pool_initialized_with_liquidity.tickUpper()
    supplier_address = pool_initialized_with_liquidity.supplier()
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_specified = (
        -(1 * reserve1) // 100 if zero_for_one else -(1 * reserve0) // 100
    )

    # cache balances before
    balance0_sender = margv1_token0.balanceOf(sender.address)
    balance1_sender = margv1_token1.balanceOf(sender.address)

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        sender.address,  # recipient
        deadline,
        -amount_specified,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    result = margv1_quoter.quoteExactOutputSingle(params)
    margv1lb_router.exactOutputSingle(params, sender=sender)

    amount0 = margv1_token0.balanceOf(sender.address) - balance0_sender
    amount1 = margv1_token1.balanceOf(sender.address) - balance1_sender

    amount_in = -amount0 if zero_for_one else -amount1
    amount_out = amount1 if zero_for_one else amount0

    state_after = pool_initialized_with_liquidity.state()
    (liquidity_after, sqrt_price_x96_after, finalized_after) = (
        state_after.liquidity,
        state_after.sqrtPriceX96,
        state_after.finalized,
    )
    assert result == (
        amount_in,
        amount_out,
        liquidity_after,
        sqrt_price_x96_after,
        finalized_after,
    )


@pytest.mark.integration
@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_integration_quoter_quote_exact_output_single__reverts_when_exceeds_tick_range(
    margv1lb_router,
    margv1_pool_initialized,
    margv1_quoter,
    margv1_token0,
    margv1_token1,
    chain,
    sender,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = margv1_pool_initialized(
        init_with_sqrt_price_lower_x96
    )
    state = pool_initialized_with_liquidity.state()
    assert state.sqrtPriceX96 > 0

    tick_lower = pool_initialized_with_liquidity.tickLower()
    tick_upper = pool_initialized_with_liquidity.tickUpper()
    supplier_address = pool_initialized_with_liquidity.supplier()
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()

    token_in = (
        pool_initialized_with_liquidity.token0()
        if zero_for_one
        else pool_initialized_with_liquidity.token1()
    )
    token_out = (
        pool_initialized_with_liquidity.token1()
        if zero_for_one
        else pool_initialized_with_liquidity.token0()
    )

    deadline = chain.pending_timestamp + 3600
    amount_in_max = 2**256 - 1
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()

    sqrt_price_x96 = sqrt_price_lower_x96 if zero_for_one else sqrt_price_upper_x96
    (amount0_swap, amount1_swap) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96
    )
    amount_specified = -amount1_swap if zero_for_one else -amount0_swap
    amount_specified = int(1.01 * amount_specified)  # extra buffer to overshoot

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        sender.address,  # recipient
        deadline,
        amount_specified,
        amount_in_max,
        sqrt_price_limit_x96,
    )
    with reverts("revert: Invalid sqrtPriceX96Next"):
        margv1_quoter.quoteExactOutputSingle(params)
