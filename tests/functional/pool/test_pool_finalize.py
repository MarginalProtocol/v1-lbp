import pytest

from hexbytes import HexBytes
from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_DURATION
from utils.utils import calc_range_amounts_from_liquidity_sqrt_price_x96


@pytest.fixture
def pool_finalized(pool_initialized, callee, swap_math_lib, token0, token1, sender):
    def pool_finalized(init_with_sqrt_price_lower: bool):
        pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower)

        state = pool_initialized_with_liquidity.state()
        sqrt_price_finalize_x96 = pool_initialized_with_liquidity.sqrtPriceFinalizeX96()

        zero_for_one = state.sqrtPriceX96 > sqrt_price_finalize_x96
        sqrt_price_limit_x96 = (
            MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1
        )

        (amount0, amount1) = swap_math_lib.swapAmounts(
            state.liquidity,
            state.sqrtPriceX96,
            sqrt_price_finalize_x96,
        )
        amount_specified = (
            int(amount0 * 1.000001) if zero_for_one else int(amount1 * 1.000001)
        )
        token_in = token0 if zero_for_one else token1
        token_in.mint(sender.address, amount_specified, sender=sender)

        callee.swap(
            pool_initialized_with_liquidity.address,
            sender.address,
            zero_for_one,
            amount_specified,
            sqrt_price_limit_x96,
            sender=sender,
        )

        return pool_initialized_with_liquidity

    yield pool_finalized


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__updates_state(
    factory,
    pool_finalized,
    callee,
    sender,
    admin,
    alice,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    # update liquidity for burn
    state.liquidity = 0

    # update oracle write
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )

    assert pool_finalized_with_liquidity.state() == state


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__burns_lp_shares(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )

    assert (
        pool_finalized_with_liquidity.balanceOf(pool_finalized_with_liquidity.address)
        == 0
    )
    assert pool_finalized_with_liquidity.totalSupply() == 0


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__transfers_funds(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    token0,
    token1,
    range_math_lib,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    sqrt_price_finalize_x96 = pool_finalized_with_liquidity.sqrtPriceFinalizeX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    amount_left_in_token = (
        amount0 if sqrt_price_finalize_x96 == sqrt_price_upper_x96 else amount1
    )
    assert amount_left_in_token == 0

    # take protocol fees out
    (fees0, fees1) = range_math_lib.rangeFees(amount0, amount1, state.feeProtocol)

    balance0_pool = token0.balanceOf(pool_finalized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_finalized_with_liquidity.address)

    balance0_factory = token0.balanceOf(factory.address)
    balance1_factory = token1.balanceOf(factory.address)

    balance0_alice = token0.balanceOf(alice.address)
    balance1_alice = token1.balanceOf(alice.address)

    callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )

    balance0_pool -= amount0
    balance1_pool -= amount1

    balance0_factory += fees0
    balance1_factory += fees1

    balance0_alice += amount0 - fees0
    balance1_alice += amount1 - fees1

    assert token0.balanceOf(pool_finalized_with_liquidity.address) == balance0_pool
    assert token1.balanceOf(pool_finalized_with_liquidity.address) == balance1_pool

    assert token0.balanceOf(factory.address) == balance0_factory
    assert token1.balanceOf(factory.address) == balance1_factory

    assert token0.balanceOf(alice.address) == balance0_alice
    assert token1.balanceOf(alice.address) == balance1_alice


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__returns_amounts(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    token0,
    token1,
    range_math_lib,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    tx = callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )
    return_log = tx.decode_logs(callee.FinalizeReturn)[0]
    assert return_log.liquidityDelta == state.liquidity
    assert return_log.sqrtPriceX96 == state.sqrtPriceX96
    assert return_log.amount0 == amount0
    assert return_log.amount1 == amount1


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__emits_finalize(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    token0,
    token1,
    range_math_lib,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    tx = callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )
    events = tx.decode_logs(pool_finalized_with_liquidity.Finalize)
    assert len(events) == 1
    event = events[0]

    assert event.liquidityDelta == state.liquidity
    assert event.sqrtPriceX96 == state.sqrtPriceX96
    assert event.amount0 == amount0
    assert event.amount1 == amount1


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__updates_state_when_exit(
    factory,
    pool_initialized,
    callee,
    sender,
    admin,
    alice,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert state.finalized is False

    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()
    chain.mine(timestamp=timestamp_initialize + MINIMUM_DURATION + 1)

    # update liquidity for burn
    state.liquidity = 0

    # state should toggle to finalized
    state.finalized = True

    # update oracle write
    block_timestamp_next = chain.pending_timestamp
    tick_cumulative_next = state.tickCumulative + state.tick * (
        block_timestamp_next - state.blockTimestamp
    )
    state.tickCumulative = tick_cumulative_next
    state.blockTimestamp = block_timestamp_next

    callee.finalize(
        pool_initialized_with_liquidity.address, alice.address, sender=sender
    )

    assert pool_initialized_with_liquidity.state() == state


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__reverts_when_not_supplier(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    token0,
    token1,
    range_math_lib,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert pool_finalized_with_liquidity.supplier() != sender.address

    with reverts(pool_finalized_with_liquidity.Unauthorized):
        data = HexBytes("")
        pool_finalized_with_liquidity.finalize(data, sender=sender)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__reverts_when_not_finalized(
    pool_initialized,
    callee,
    sender,
    admin,
    alice,
    chain,
    init_with_sqrt_price_lower_x96,
):
    pool_initialized_with_liquidity = pool_initialized(init_with_sqrt_price_lower_x96)
    state = pool_initialized_with_liquidity.state()
    assert state.finalized is False

    with reverts(pool_initialized_with_liquidity.NotFinalized):
        callee.finalize(
            pool_initialized_with_liquidity.address, alice.address, sender=sender
        )


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_pool_finalize__reverts_when_no_supply(
    pool_finalized,
    factory,
    callee,
    sender,
    admin,
    alice,
    token0,
    token1,
    range_math_lib,
    chain,
    init_with_sqrt_price_lower_x96,
):
    # finalize first then try again
    pool_finalized_with_liquidity = pool_finalized(init_with_sqrt_price_lower_x96)
    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True

    shares = pool_finalized_with_liquidity.balanceOf(
        pool_finalized_with_liquidity.address
    )
    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert shares > 0
    assert total_supply > 0

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    callee.finalize(
        pool_finalized_with_liquidity.address,
        alice.address,
        sender=sender,
    )
    assert pool_finalized_with_liquidity.totalSupply() == 0

    with reverts(pool_finalized_with_liquidity.SupplyLessThanMin):
        callee.finalize(
            pool_finalized_with_liquidity.address, alice.address, sender=sender
        )
