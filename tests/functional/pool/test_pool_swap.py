import pytest

from ape import reverts
from datetime import timedelta
from hypothesis import given, settings, strategies as st

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import (
    calc_range_amounts_from_liquidity_sqrt_price_x96,
    calc_liquidity_sqrt_price_x96_from_reserves,
    calc_swap_amounts,
    calc_tick_from_sqrt_price_x96,
    calc_sqrt_price_x96_from_tick,
)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_input_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_input_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_input_zero_for_one_to_range_tick(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_finalize_x96 = pool_initialized_with_liquidity.sqrtPriceFinalizeX96()

    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_lower_x96
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount_specified = int(amount0 * 1.001)  # extra buffer

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    state.finalized = sqrt_price_x96_next == sqrt_price_finalize_x96

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_input_one_for_zero_to_range_tick(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    sqrt_price_finalize_x96 = pool_initialized_with_liquidity.sqrtPriceFinalizeX96()

    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_upper_x96
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount_specified = int(amount1 * 1.001)  # extra buffer

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)
    state.finalized = sqrt_price_x96_next == sqrt_price_finalize_x96

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_output_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__updates_state_with_exact_output_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__transfers_funds_with_exact_input_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice - amount1


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__transfers_funds_with_exact_input_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice - amount0


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__transfers_funds_with_exact_output_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    balance0_sender = token0.balanceOf(sender.address)
    balance1_alice = token1.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token0.balanceOf(sender.address) == balance0_sender - amount0
    assert token1.balanceOf(alice.address) == balance1_alice - amount1


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__transfers_funds_with_exact_output_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    balance1_sender = token1.balanceOf(sender.address)
    balance0_alice = token0.balanceOf(alice.address)

    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    assert (
        token0.balanceOf(pool_initialized_with_liquidity.address)
        == balance0_pool + amount0
    )
    assert (
        token1.balanceOf(pool_initialized_with_liquidity.address)
        == balance1_pool + amount1
    )

    assert token1.balanceOf(sender.address) == balance1_sender - amount1
    assert token0.balanceOf(alice.address) == balance0_alice - amount0


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__calls_swap_callback_with_exact_input_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__calls_swap_callback_with_exact_input_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__calls_swap_callback_with_exact_output_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__calls_swap_callback_with_exact_output_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    events = tx.decode_logs(callee.SwapCallback)
    assert len(events) == 1
    event = events[0]

    assert event.amount0Delta == amount0
    assert event.amount1Delta == amount1
    assert event.sender == sender.address


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__emits_swap_with_exact_input_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve0 // 100  # 1 % of reserves in
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]

    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick
    assert event.finalized == state.finalized


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__emits_swap_with_exact_input_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__emits_swap_with_exact_output_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount1 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__emits_swap_with_exact_output_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )

    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount0 = amount_specified

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    state = pool_initialized_with_liquidity.state()
    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__when_sqrt_price_x96_next_less_than_sqrt_price_lower_with_exact_input(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    ticks,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    (tick_lower, tick_upper) = ticks
    tick_next = tick_lower - 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)

    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token0.mint(sender.address, amount0, sender=sender)

    amount_specified = amount0  # amount in
    assert amount_specified > 0
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    # cache balances before
    (balance0_sender, balance1_sender) = (
        token0.balanceOf(sender.address),
        token1.balanceOf(sender.address),
    )
    (balance0_alice, balance1_alice) = (
        token0.balanceOf(alice.address),
        token1.balanceOf(alice.address),
    )
    (balance0_pool, balance1_pool) = (
        token0.balanceOf(pool_initialized_with_liquidity.address),
        token1.balanceOf(pool_initialized_with_liquidity.address),
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    # recalculate amounts based off upper price attained
    (amount0_clamped, amount1_clamped) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96
    )

    # update state price, should clamp to lower
    state.sqrtPriceX96 = sqrt_price_lower_x96
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_lower_x96)
    state.finalized = not init_with_sqrt_price_lower_x96

    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert pytest.approx(return_log.amount0, rel=1e-6) == amount0_clamped
    assert pytest.approx(return_log.amount1, rel=1e-6) == amount1_clamped

    state_after = pool_initialized_with_liquidity.state()
    assert state_after == state

    # check balances updated
    balance0_sender -= return_log.amount0
    balance1_alice += -return_log.amount1
    balance0_pool += return_log.amount0
    balance1_pool += return_log.amount1

    assert balance0_sender == token0.balanceOf(sender.address)
    assert balance1_sender == token1.balanceOf(sender.address)

    assert balance0_alice == token0.balanceOf(alice.address)
    assert balance1_alice == token1.balanceOf(alice.address)

    assert balance0_pool == token0.balanceOf(pool_initialized_with_liquidity.address)
    assert balance1_pool == token1.balanceOf(pool_initialized_with_liquidity.address)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__when_sqrt_price_x96_next_greater_than_sqrt_price_upper_with_exact_input(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    ticks,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    (tick_lower, tick_upper) = ticks
    tick_next = tick_upper + 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)

    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token1.mint(sender.address, amount1, sender=sender)

    amount_specified = amount1  # amount in
    assert amount_specified > 0
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # cache balances before
    (balance0_sender, balance1_sender) = (
        token0.balanceOf(sender.address),
        token1.balanceOf(sender.address),
    )
    (balance0_alice, balance1_alice) = (
        token0.balanceOf(alice.address),
        token1.balanceOf(alice.address),
    )
    (balance0_pool, balance1_pool) = (
        token0.balanceOf(pool_initialized_with_liquidity.address),
        token1.balanceOf(pool_initialized_with_liquidity.address),
    )

    # update the oracle
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    tx = callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )

    # recalculate amounts based off upper price attained
    (amount0_clamped, amount1_clamped) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_upper_x96
    )

    # update state price, should clamp to upper
    state.sqrtPriceX96 = sqrt_price_upper_x96
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_upper_x96)
    state.finalized = init_with_sqrt_price_lower_x96

    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert pytest.approx(return_log.amount0, rel=1e-6) == amount0_clamped
    assert pytest.approx(return_log.amount1, rel=1e-6) == amount1_clamped

    state_after = pool_initialized_with_liquidity.state()
    assert state_after == state

    # check balances updated
    balance1_sender -= return_log.amount1
    balance0_alice += -return_log.amount0
    balance0_pool += return_log.amount0
    balance1_pool += return_log.amount1

    assert balance0_sender == token0.balanceOf(sender.address)
    assert balance1_sender == token1.balanceOf(sender.address)

    assert balance0_alice == token0.balanceOf(alice.address)
    assert balance1_alice == token1.balanceOf(alice.address)

    assert balance0_pool == token0.balanceOf(pool_initialized_with_liquidity.address)
    assert balance1_pool == token1.balanceOf(pool_initialized_with_liquidity.address)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_amount_specified_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    zero_for_one = True
    amount_specified = 0
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    with reverts(pool_initialized_with_liquidity.InvalidAmountSpecified):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_limit_x96_greater_than_sqrt_price_x96_with_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    zero_for_one = True
    amount_specified = 1000000

    state = pool_initialized_with_liquidity.state()
    sqrt_price_limit_x96 = state.sqrtPriceX96 + 1

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_limit_x96_less_than_min_sqrt_ratio_with_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    zero_for_one = True
    amount_specified = 1000000
    sqrt_price_limit_x96 = MIN_SQRT_RATIO

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_limit_x96_less_than_sqrt_price_x96_with_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    zero_for_one = False
    amount_specified = 1000000

    state = pool_initialized_with_liquidity.state()
    sqrt_price_limit_x96 = state.sqrtPriceX96 - 1

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_limit_x96_greater_than_max_sqrt_ratio_with_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    zero_for_one = False
    amount_specified = 1000000
    sqrt_price_limit_x96 = MAX_SQRT_RATIO

    with reverts(pool_initialized_with_liquidity.InvalidSqrtPriceLimitX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_x96_next_less_than_sqrt_price_limit_with_zero_for_one(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next + 1

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_x96_next_greater_than_sqrt_price_limit_with_one_for_zero(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )
    sqrt_price_limit_x96 = sqrt_price_x96_next - 1

    with reverts(pool_initialized_with_liquidity.SqrtPriceX96ExceedsLimit):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_x96_next_less_than_sqrt_price_lower_with_exact_output(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    range_math_lib,
    sender,
    alice,
    token0,
    token1,
    ticks,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    (tick_lower, tick_upper) = ticks
    tick_next = tick_lower - 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)

    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token0.mint(sender.address, amount0, sender=sender)

    amount_specified = amount1  # amount out
    assert amount_specified < 0
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    with reverts(range_math_lib.InvalidSqrtPriceX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_sqrt_price_x96_next_greater_than_sqrt_price_upper_with_exact_output(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    range_math_lib,
    sender,
    alice,
    token0,
    token1,
    ticks,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    (tick_lower, tick_upper) = ticks
    tick_next = tick_upper + 100
    sqrt_price_x96_next = calc_sqrt_price_x96_from_tick(tick_next)

    # swap the pool to initial sqrt price
    (amount0, amount1) = calc_swap_amounts(
        state.liquidity, state.sqrtPriceX96, sqrt_price_x96_next
    )
    token1.mint(sender.address, amount1, sender=sender)

    amount_specified = amount0  # amount out
    assert amount_specified < 0
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    with reverts(range_math_lib.InvalidSqrtPriceX96):
        callee.swap(
            pool_initialized_with_liquidity.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


def test_pool_swap__reverts_when_pool_finalized(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    liquidity_math_lib,
    sender,
    alice,
    token0,
    token1,
    chain,
):
    init_with_sqrt_price_lower_x96 = True
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()

    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_upper_x96
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )
    amount_specified = int(amount1 * 1.001)  # extra buffer

    callee.swap(
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
        sender=sender,
    )
    state = pool_initialized_with_liquidity.state()
    assert state.finalized is True

    # try again with smaller amount specified
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_specified = 1 * reserve1 // 100  # 1 % of reserves in

    with reverts(pool_initialized_with_liquidity.Finalized):
        callee.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_amount0_transferred_less_than_min_with_zero_for_one(
    pool_initialized,
    callee_below_min0,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_specified = -1 * reserve1 // 100  # 1 % of reserves out
    zero_for_one = True
    sqrt_price_limit_x96 = MIN_SQRT_RATIO + 1

    with reverts(pool_initialized_with_liquidity.Amount0LessThanMin):
        callee_below_min0.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_swap__reverts_when_amount1_transferred_less_than_min_with_one_for_zero(
    pool_initialized,
    callee_below_min1,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    amount_specified = -1 * reserve0 // 100  # 1 % of reserves out
    zero_for_one = False
    sqrt_price_limit_x96 = MAX_SQRT_RATIO - 1

    with reverts(pool_initialized_with_liquidity.Amount1LessThanMin):
        callee_below_min1.swap(
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=500))
@given(
    amount_specified_pc=st.integers(
        min_value=-(1000000000 - 1), max_value=1000000000000000
    ),
    zero_for_one=st.booleans(),
    init_with_sqrt_price_lower_x96=st.booleans(),
)
def test_pool_swap__with_fuzz(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    amount_specified_pc,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**128-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**128-1
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    amount_specified = 0
    if amount_specified_pc == 0:
        return
    elif amount_specified_pc > 0:
        amount_specified = (
            (balance0_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance1_pool * amount_specified_pc) // 1000000000
        )
    else:
        amount_specified = (
            (balance1_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance0_pool * amount_specified_pc) // 1000000000
        )

    # set up fuzz test of swap
    state = pool_initialized_with_liquidity.state()

    exact_input = amount_specified > 0
    sqrt_price_limit_x96 = (
        MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
    )

    # cache for later sanity checks
    _liquidity = state.liquidity
    _sqrt_price_x96 = state.sqrtPriceX96

    # oracle updates
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )

    # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
    sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
        state.liquidity,
        state.sqrtPriceX96,
        zero_for_one,
        amount_specified,
    )
    (amount0, amount1) = swap_math_lib.swapAmounts(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_x96_next,
    )

    # set amount out to amount specified as exact output
    if not exact_input:
        amount0 = amount0 if zero_for_one else amount_specified
        amount1 = amount_specified if zero_for_one else amount1

    params = (
        pool_initialized_with_liquidity.address,
        alice.address,
        zero_for_one,
        amount_specified,
        sqrt_price_limit_x96,
    )
    tx = callee.swap(*params, sender=sender)
    return_log = tx.decode_logs(callee.SwapReturn)[0]
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1

    # check pool state transition
    # TODO: also test with protocol fee
    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()
    (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )

    # update state price
    state.sqrtPriceX96 = sqrt_price_x96_next
    state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

    state.blockTimestamp = block_timestamp_next
    state.tickCumulative = tick_cumulative

    result_state = pool_initialized_with_liquidity.state()
    assert pytest.approx(result_state.liquidity, rel=1e-14) == state.liquidity
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-14) == state.sqrtPriceX96
    assert result_state.tick == state.tick
    assert result_state.blockTimestamp == state.blockTimestamp
    assert result_state.tickCumulative == state.tickCumulative
    assert result_state.totalPositions == state.totalPositions

    # sanity check pool state
    # excluding fees should have after swap
    #  L = L
    #  sqrt(P') = sqrt(P) * (1 + dy / y) = sqrt(P) / (1 + dx / x); dx, dy can be > 0 or < 0
    calc_liquidity_next = _liquidity

    # del x, del y without fees
    _del_x = amount0 if amount0 < 0 else amount0
    _del_y = amount1 if amount1 < 0 else amount1

    _del_sqrt_price_y = 1 + _del_y / reserve1
    _del_sqrt_price_x = 1 / (1 + _del_x / reserve0)

    # L invariant on swap requires
    #  1 + dy / y = 1 / (1 + dx / x)
    assert pytest.approx(_del_sqrt_price_y, rel=1e-6) == _del_sqrt_price_x
    calc_sqrt_price_x96_next = int(_sqrt_price_x96 * _del_sqrt_price_y)

    # add in the fees
    (_reserve0_next, _reserve1_next) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        calc_liquidity_next,
        calc_sqrt_price_x96_next,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )
    (
        _liquidity_after,
        _sqrt_price_x96_after,
    ) = calc_liquidity_sqrt_price_x96_from_reserves(_reserve0_next, _reserve1_next)
    assert pytest.approx(result_state.liquidity, rel=1e-6) == _liquidity_after
    assert pytest.approx(result_state.sqrtPriceX96, rel=1e-6) == _sqrt_price_x96_after

    state = result_state  # for event checks below

    # check balances
    amount0_sender = -amount0 if zero_for_one else 0
    amount1_sender = 0 if zero_for_one else -amount1

    amount0_alice = 0 if zero_for_one else -amount0
    amount1_alice = -amount1 if zero_for_one else 0

    balance0_pool += amount0
    balance1_pool += amount1
    balance0_sender += amount0_sender
    balance1_sender += amount1_sender
    balance0_alice += amount0_alice
    balance1_alice += amount1_alice

    result_balance0_sender = token0.balanceOf(sender.address)
    result_balance1_sender = token1.balanceOf(sender.address)
    result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    result_balance0_alice = token0.balanceOf(alice.address)
    result_balance1_alice = token1.balanceOf(alice.address)

    assert result_balance0_sender == balance0_sender
    assert result_balance1_sender == balance1_sender
    assert result_balance0_pool == balance0_pool
    assert result_balance1_pool == balance1_pool
    assert result_balance0_alice == balance0_alice
    assert result_balance1_alice == balance1_alice

    # check events
    events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
    assert len(events) == 1
    event = events[0]

    assert event.sender == callee.address
    assert event.recipient == alice.address
    assert event.amount0 == amount0
    assert event.amount1 == amount1
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.liquidity == state.liquidity
    assert event.tick == state.tick

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)


@pytest.mark.fuzzing
@settings(deadline=timedelta(milliseconds=10000))
@given(
    amount_specified_pc=st.integers(
        min_value=-(1000000000 - 1), max_value=1000000000000000
    ),
    zero_for_one=st.booleans(),
    init_with_sqrt_price_lower_x96=st.booleans(),
    num_swaps=st.integers(min_value=2, max_value=4),
)
def test_pool_swap__multiple_with_fuzz(
    pool_initialized,
    callee,
    sqrt_price_math_lib,
    swap_math_lib,
    sender,
    alice,
    token0,
    token1,
    amount_specified_pc,
    zero_for_one,
    init_with_sqrt_price_lower_x96,
    num_swaps,
    chain,
):
    # @dev needed to reset chain state at end of function for each fuzz run
    snapshot = chain.snapshot()
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)

    # mint large number of tokens to sender to avoid balance issues
    balance0_sender = token0.balanceOf(sender.address)
    balance1_sender = token1.balanceOf(sender.address)
    token0.mint(sender.address, 2**128 - 1 - balance0_sender, sender=sender)
    token1.mint(sender.address, 2**128 - 1 - balance1_sender, sender=sender)

    # balances prior
    balance0_sender = token0.balanceOf(sender.address)  # 2**128-1
    balance1_sender = token1.balanceOf(sender.address)  # 2**128-1
    balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    amount_specified = 0
    if amount_specified_pc == 0:
        return
    elif amount_specified_pc > 0:
        amount_specified = (
            (balance0_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance1_pool * amount_specified_pc) // 1000000000
        )
    else:
        amount_specified = (
            (balance1_pool * amount_specified_pc) // 1000000000
            if zero_for_one
            else (balance0_pool * amount_specified_pc) // 1000000000
        )

    amount_specified = amount_specified // num_swaps

    sqrt_price_lower_x96 = pool_initialized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_initialized_with_liquidity.sqrtPriceUpperX96()

    # loop over num swaps
    for _ in range(num_swaps):
        # set up fuzz test of swap
        state = pool_initialized_with_liquidity.state()

        exact_input = amount_specified > 0
        sqrt_price_limit_x96 = (
            MAX_SQRT_RATIO - 1 if not zero_for_one else MIN_SQRT_RATIO + 1
        )

        # cache for later sanity checks
        _liquidity = state.liquidity
        _sqrt_price_x96 = state.sqrtPriceX96

        # oracle updates
        block_timestamp_next = chain.pending_timestamp
        tick_cumulative = state.tickCumulative + state.tick * (
            block_timestamp_next - state.blockTimestamp
        )

        # calc amounts in/out for the swap with first pass on price thru sqrt price math lib
        sqrt_price_x96_next = sqrt_price_math_lib.sqrtPriceX96NextSwap(
            state.liquidity,
            state.sqrtPriceX96,
            zero_for_one,
            amount_specified,
        )
        (amount0, amount1) = swap_math_lib.swapAmounts(
            state.liquidity,
            state.sqrtPriceX96,
            sqrt_price_x96_next,
        )

        # set amount out to amount specified as exact output
        if not exact_input:
            amount0 = amount0 if zero_for_one else amount_specified
            amount1 = amount_specified if zero_for_one else amount1

        params = (
            pool_initialized_with_liquidity.address,
            alice.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
        )
        tx = callee.swap(*params, sender=sender)
        return_log = tx.decode_logs(callee.SwapReturn)[0]
        assert return_log.amount0 == amount0
        assert return_log.amount1 == amount1

        # check pool state transition
        # TODO: also test with protocol fee
        (reserve0, reserve1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
            state.liquidity,
            state.sqrtPriceX96,
            sqrt_price_lower_x96,
            sqrt_price_upper_x96,
        )

        # update state price
        state.sqrtPriceX96 = sqrt_price_x96_next
        state.tick = calc_tick_from_sqrt_price_x96(sqrt_price_x96_next)

        state.blockTimestamp = block_timestamp_next
        state.tickCumulative = tick_cumulative

        result_state = pool_initialized_with_liquidity.state()

        assert pytest.approx(result_state.liquidity, rel=1e-14) == state.liquidity
        assert pytest.approx(result_state.sqrtPriceX96, rel=1e-14) == state.sqrtPriceX96
        assert result_state.tick == state.tick
        assert result_state.blockTimestamp == state.blockTimestamp
        assert result_state.tickCumulative == state.tickCumulative
        assert result_state.totalPositions == state.totalPositions

        # sanity check pool state
        # excluding fees should have after swap
        #  L = L
        #  sqrt(P') = sqrt(P) * (1 + dy / y) = sqrt(P) / (1 + dx / x); dx, dy can be > 0 or < 0
        calc_liquidity_next = _liquidity

        # del x, del y without fees
        _del_x = amount0 if amount0 < 0 else amount0
        _del_y = amount1 if amount1 < 0 else amount1

        _del_sqrt_price_y = 1 + _del_y / reserve1
        _del_sqrt_price_x = 1 / (1 + _del_x / reserve0)

        # L invariant on swap requires
        #  1 + dy / y = 1 / (1 + dx / x)
        assert pytest.approx(_del_sqrt_price_y, rel=1e-6) == _del_sqrt_price_x
        calc_sqrt_price_x96_next = int(_sqrt_price_x96 * _del_sqrt_price_y)

        # add in the fees
        (
            _reserve0_next,
            _reserve1_next,
        ) = calc_range_amounts_from_liquidity_sqrt_price_x96(
            calc_liquidity_next,
            calc_sqrt_price_x96_next,
            sqrt_price_lower_x96,
            sqrt_price_upper_x96,
        )
        (
            _liquidity_after,
            _sqrt_price_x96_after,
        ) = calc_liquidity_sqrt_price_x96_from_reserves(_reserve0_next, _reserve1_next)
        assert pytest.approx(result_state.liquidity, rel=1e-6) == _liquidity_after
        assert (
            pytest.approx(result_state.sqrtPriceX96, rel=1e-6) == _sqrt_price_x96_after
        )

        state = result_state  # for event checks below

        # check balances
        amount0_sender = -amount0 if zero_for_one else 0
        amount1_sender = 0 if zero_for_one else -amount1

        amount0_alice = 0 if zero_for_one else -amount0
        amount1_alice = -amount1 if zero_for_one else 0

        balance0_pool += amount0
        balance1_pool += amount1
        balance0_sender += amount0_sender
        balance1_sender += amount1_sender
        balance0_alice += amount0_alice
        balance1_alice += amount1_alice

        result_balance0_sender = token0.balanceOf(sender.address)
        result_balance1_sender = token1.balanceOf(sender.address)
        result_balance0_pool = token0.balanceOf(pool_initialized_with_liquidity.address)
        result_balance1_pool = token1.balanceOf(pool_initialized_with_liquidity.address)
        result_balance0_alice = token0.balanceOf(alice.address)
        result_balance1_alice = token1.balanceOf(alice.address)

        assert result_balance0_sender == balance0_sender
        assert result_balance1_sender == balance1_sender
        assert result_balance0_pool == balance0_pool
        assert result_balance1_pool == balance1_pool
        assert result_balance0_alice == balance0_alice
        assert result_balance1_alice == balance1_alice

        # TODO: check protocol fees (add fuzz param)

        # check events
        events = tx.decode_logs(pool_initialized_with_liquidity.Swap)
        assert len(events) == 1
        event = events[0]

        assert event.sender == callee.address
        assert event.recipient == alice.address
        assert event.amount0 == amount0
        assert event.amount1 == amount1
        assert event.sqrtPriceX96 == state.sqrtPriceX96
        assert event.liquidity == state.liquidity
        assert event.tick == state.tick

    # revert to chain state prior to fuzz run
    chain.restore(snapshot)
