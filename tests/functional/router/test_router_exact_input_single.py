import pytest

from ape import reverts
from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_tick_from_sqrt_price_x96,
    calc_sqrt_price_x96_from_tick,
    calc_swap_amounts,
)


@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__updates_state(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in,
    )  # price change
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    result = pool_initialized_with_liquidity.state()
    assert result == state


@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__transfers_funds(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
    token0,
    token1,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

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
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # cache balances before swap
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    # calculate amount out
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    balance0_sender_after = (
        balance0_sender - amount_in if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in
    )

    assert token0.balanceOf(sender.address) == balance0_sender_after
    assert token1.balanceOf(sender.address) == balance1_sender_after

    balance0_alice_after = (
        balance0_alice if zero_for_one else balance0_alice + amount_out
    )
    balance1_alice_after = (
        balance1_alice + amount_out if zero_for_one else balance1_alice
    )

    assert token0.balanceOf(alice.address) == balance0_alice_after
    assert token1.balanceOf(alice.address) == balance1_alice_after

    balance0_pool_after = (
        balance0_pool + amount_in if zero_for_one else balance0_pool - amount_out
    )
    balance1_pool_after = (
        balance1_pool - amount_out if zero_for_one else balance1_pool + amount_in
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address) == balance0_pool_after
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address) == balance1_pool_after
    )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__when_sqrt_price_x96_next_less_than_sqrt_price_lower(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    init_with_sqrt_price_lower_x96,
    token0,
    token1,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

    state = pool_initialized_with_liquidity.state()
    assert state.sqrtPriceX96 > 0

    tick_lower = pool_initialized_with_liquidity.tickLower()
    tick_upper = pool_initialized_with_liquidity.tickUpper()
    supplier_address = pool_initialized_with_liquidity.supplier()
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()

    token_in = pool_initialized_with_liquidity.token0()
    token_out = pool_initialized_with_liquidity.token1()

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    tick_next = tick_lower - 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)
    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token0.mint(sender.address, amount0, sender=sender)

    zero_for_one = True
    amount_in = amount0
    assert amount_in > 0

    # cache balances before swap
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    assert state_after.sqrtPriceX96 == sqrt_price_lower_x96
    assert state_after.finalized == (not init_with_sqrt_price_lower_x96)

    (amount0_clamped, amount1_clamped) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96
    )
    amount_in_clamped = amount0_clamped
    amount_out_clamped = -amount1_clamped

    balance0_sender_after = (
        balance0_sender - amount_in_clamped if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in_clamped
    )

    assert (
        pytest.approx(token0.balanceOf(sender.address), rel=1e-6)
        == balance0_sender_after
    )
    assert (
        pytest.approx(token1.balanceOf(sender.address), rel=1e-6)
        == balance1_sender_after
    )

    balance0_alice_after = (
        balance0_alice if zero_for_one else balance0_alice + amount_out_clamped
    )
    balance1_alice_after = (
        balance1_alice + amount_out_clamped if zero_for_one else balance1_alice
    )

    assert (
        pytest.approx(token0.balanceOf(alice.address), rel=1e-6) == balance0_alice_after
    )
    assert (
        pytest.approx(token1.balanceOf(alice.address), rel=1e-6) == balance1_alice_after
    )

    balance0_pool_after = (
        balance0_pool + amount_in_clamped
        if zero_for_one
        else balance0_pool - amount_out_clamped
    )
    balance1_pool_after = (
        balance1_pool - amount_out_clamped
        if zero_for_one
        else balance1_pool + amount_in_clamped
    )

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-6, abs=1
        )
        == balance0_pool_after
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-6, abs=1
        )
        == balance1_pool_after
    )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__when_sqrt_price_x96_next_greater_than_sqrt_price_upper(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    init_with_sqrt_price_lower_x96,
    token0,
    token1,
    sqrt_price_math_lib,
    liquidity_math_lib,
    swap_math_lib,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

    state = pool_initialized_with_liquidity.state()
    assert state.sqrtPriceX96 > 0

    tick_lower = pool_initialized_with_liquidity.tickLower()
    tick_upper = pool_initialized_with_liquidity.tickUpper()
    supplier_address = pool_initialized_with_liquidity.supplier()
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()

    token_in = pool_initialized_with_liquidity.token1()
    token_out = pool_initialized_with_liquidity.token0()

    deadline = chain.pending_timestamp + 3600
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    tick_next = tick_upper + 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)
    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token1.mint(sender.address, amount1, sender=sender)

    zero_for_one = False
    amount_in = amount1
    assert amount_in > 0

    # cache balances before swap
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )
    router.exactInputSingle(params, sender=sender)

    state_after = pool_initialized_with_liquidity.state()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    assert state_after.sqrtPriceX96 == sqrt_price_upper_x96
    assert state_after.finalized == init_with_sqrt_price_lower_x96

    (amount0_clamped, amount1_clamped) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_upper_x96
    )
    amount_in_clamped = amount1_clamped
    amount_out_clamped = -amount0_clamped

    balance0_sender_after = (
        balance0_sender - amount_in_clamped if zero_for_one else balance0_sender
    )
    balance1_sender_after = (
        balance1_sender if zero_for_one else balance1_sender - amount_in_clamped
    )

    assert (
        pytest.approx(token0.balanceOf(sender.address), rel=1e-6)
        == balance0_sender_after
    )
    assert (
        pytest.approx(token1.balanceOf(sender.address), rel=1e-6)
        == balance1_sender_after
    )

    balance0_alice_after = (
        balance0_alice if zero_for_one else balance0_alice + amount_out_clamped
    )
    balance1_alice_after = (
        balance1_alice + amount_out_clamped if zero_for_one else balance1_alice
    )

    assert (
        pytest.approx(token0.balanceOf(alice.address), rel=1e-6) == balance0_alice_after
    )
    assert (
        pytest.approx(token1.balanceOf(alice.address), rel=1e-6) == balance1_alice_after
    )

    balance0_pool_after = (
        balance0_pool + amount_in_clamped
        if zero_for_one
        else balance0_pool - amount_out_clamped
    )
    balance1_pool_after = (
        balance1_pool - amount_out_clamped
        if zero_for_one
        else balance1_pool + amount_in_clamped
    )

    assert (
        pytest.approx(
            token0.balanceOf(pool_initialized_with_liquidity.address), rel=1e-6, abs=1
        )
        == balance0_pool_after
    )
    assert (
        pytest.approx(
            token1.balanceOf(pool_initialized_with_liquidity.address), rel=1e-6, abs=1
        )
        == balance1_pool_after
    )


@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__reverts_when_past_deadline(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

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

    deadline = chain.pending_timestamp - 1
    amount_out_min = 0
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )

    with reverts("Transaction too old"):
        router.exactInputSingle(params, sender=sender)


@pytest.mark.parametrize("zero_for_one", [True, False])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_router_exact_input_single__reverts_when_amount_out_less_than_min(
    pool_initialized,
    router,
    sender,
    alice,
    chain,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
    sqrt_price_math_lib,
    swap_math_lib,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    assert pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    assert pool_initialized_with_liquidity.totalSupply() > 0

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
    sqrt_price_limit_x96 = 0

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_in = 1 * reserve0 // 100 if zero_for_one else 1 * reserve1 // 100

    # calculate amount out
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_in,
    )  # price change before fees added

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    amount_out = -amount1 if zero_for_one else -amount0

    amount_out_min = amount_out + 1
    params = (
        token_in,
        token_out,
        tick_lower,
        tick_upper,
        supplier_address,
        timestamp_initialize,
        alice.address,  # recipient
        deadline,
        amount_in,
        amount_out_min,
        sqrt_price_limit_x96,
    )

    with reverts("Too little received"):
        router.exactInputSingle(params, sender=sender)
