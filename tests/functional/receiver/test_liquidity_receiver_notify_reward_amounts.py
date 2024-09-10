import pytest

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO
from utils.utils import calc_range_amounts_from_liquidity_sqrt_price_x96


# TODO: test exit, revert cases


@pytest.fixture
def liquidity_receiver_and_pool_finalized(
    liquidity_receiver_and_pool,
    callee,
    swap_math_lib,
    token0,
    token1,
    sender,
):
    def liquidity_receiver_and_pool_finalized(init_with_sqrt_price_lower_x96: bool):
        (
            liquidity_receiver,
            pool_initialized_with_liquidity,
        ) = liquidity_receiver_and_pool(init_with_sqrt_price_lower_x96)

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
            int(amount0 * 1.0001) if zero_for_one else int(amount1 * 1.0001)
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

        return (liquidity_receiver, pool_initialized_with_liquidity)

    yield liquidity_receiver_and_pool_finalized


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_notify_reward_amounts__updates_reserves_and_timestamp(
    factory,
    supplier,
    liquidity_receiver_and_pool_finalized,
    range_math_lib,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    (
        liquidity_receiver,
        pool_finalized_with_liquidity,
    ) = liquidity_receiver_and_pool_finalized(init_with_sqrt_price_lower_x96)
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    # amounts transferred from pool
    (sqrt_price_lower_x96, sqrt_price_upper_x96) = (
        pool_finalized_with_liquidity.sqrtPriceLowerX96(),
        pool_finalized_with_liquidity.sqrtPriceUpperX96(),
    )
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    (fees0, fees1) = range_math_lib.rangeFees(amount0, amount1, fee_protocol)
    amount0 -= fees0
    amount1 -= fees1

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0 if init_with_sqrt_price_lower_x96 else reserve1 > 0
    assert liquidity_receiver.blockTimestampNotified() == 0

    assert sender.address != finalizer.address
    pending_timestamp = chain.pending_timestamp
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
    )
    supplier.finalizePool(params, sender=sender)

    # factor in amount sent to treasury from amounts in
    amount0_treasury = int((amount0 * liquidity_receiver_params.treasuryRatio) / 1e6)
    amount1_treasury = int((amount1 * liquidity_receiver_params.treasuryRatio) / 1e6)

    reserve0 += amount0 - amount0_treasury
    reserve1 += amount1 - amount1_treasury

    (result_reserve0, result_reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert pytest.approx(result_reserve0, rel=1e-6) == reserve0
    assert pytest.approx(result_reserve1, rel=1e-6) == reserve1

    result_timestamp_notified = liquidity_receiver.blockTimestampNotified()
    assert result_timestamp_notified == pending_timestamp


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_notify_reward_amounts__transfers_funds(
    factory,
    supplier,
    liquidity_receiver_and_pool_finalized,
    range_math_lib,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    (
        liquidity_receiver,
        pool_finalized_with_liquidity,
    ) = liquidity_receiver_and_pool_finalized(init_with_sqrt_price_lower_x96)
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    # amounts transferred from pool
    (sqrt_price_lower_x96, sqrt_price_upper_x96) = (
        pool_finalized_with_liquidity.sqrtPriceLowerX96(),
        pool_finalized_with_liquidity.sqrtPriceUpperX96(),
    )
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    (fees0, fees1) = range_math_lib.rangeFees(amount0, amount1, fee_protocol)
    amount0 -= fees0
    amount1 -= fees1

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0 if init_with_sqrt_price_lower_x96 else reserve1 > 0
    assert liquidity_receiver_params.treasuryAddress == finalizer.address

    # cache balances prior
    (balance0_receiver, balance1_receiver) = (
        token0.balanceOf(liquidity_receiver.address),
        token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_treasury, balance1_treasury) = (
        token0.balanceOf(liquidity_receiver_params.treasuryAddress),
        token1.balanceOf(liquidity_receiver_params.treasuryAddress),
    )

    assert sender.address != finalizer.address
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
    )
    supplier.finalizePool(params, sender=sender)

    # factor in amount sent to treasury from amounts in
    amount0_treasury = int((amount0 * liquidity_receiver_params.treasuryRatio) / 1e6)
    amount1_treasury = int((amount1 * liquidity_receiver_params.treasuryRatio) / 1e6)

    balance0_receiver += amount0 - amount0_treasury
    balance1_receiver += amount1 - amount1_treasury

    balance0_treasury += amount0_treasury
    balance1_treasury += amount1_treasury

    (balance0_receiver_after, balance1_receiver_after) = (
        token0.balanceOf(liquidity_receiver.address),
        token1.balanceOf(liquidity_receiver.address),
    )
    assert pytest.approx(balance0_receiver_after, rel=1e-6) == balance0_receiver
    assert pytest.approx(balance1_receiver_after, rel=1e-6) == balance1_receiver

    assert balance0_receiver_after >= liquidity_receiver.reserve0()
    assert balance1_receiver_after >= liquidity_receiver.reserve1()

    (balance0_treasury_after, balance1_treasury_after) = (
        token0.balanceOf(liquidity_receiver_params.treasuryAddress),
        token1.balanceOf(liquidity_receiver_params.treasuryAddress),
    )
    assert pytest.approx(balance0_treasury_after, rel=1e-6) == balance0_treasury
    assert pytest.approx(balance1_treasury_after, rel=1e-6) == balance1_treasury


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_notify_reward_amounts__emits_rewards_added(
    factory,
    supplier,
    liquidity_receiver_and_pool_finalized,
    range_math_lib,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)
    (
        liquidity_receiver,
        pool_finalized_with_liquidity,
    ) = liquidity_receiver_and_pool_finalized(init_with_sqrt_price_lower_x96)
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    # amounts transferred from pool
    (sqrt_price_lower_x96, sqrt_price_upper_x96) = (
        pool_finalized_with_liquidity.sqrtPriceLowerX96(),
        pool_finalized_with_liquidity.sqrtPriceUpperX96(),
    )
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity, state.sqrtPriceX96, sqrt_price_lower_x96, sqrt_price_upper_x96
    )
    (fees0, fees1) = range_math_lib.rangeFees(amount0, amount1, fee_protocol)
    amount0 -= fees0
    amount1 -= fees1

    assert sender.address != finalizer.address
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
    )
    tx = supplier.finalizePool(params, sender=sender)
    events = tx.decode_logs(liquidity_receiver.RewardsAdded)
    assert len(events) == 1
    event = events[0]

    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )

    assert pytest.approx(event.amount0, rel=1e-6) == amount0
    assert pytest.approx(event.amount1, rel=1e-6) == amount1
    assert event.reserve0After == reserve0
    assert event.reserve1After == reserve1


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_notify_reward_amounts__updates_state_when_exit(
    factory,
    supplier,
    liquidity_receiver_and_pool_finalized,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    fee_protocol,
    init_with_sqrt_price_lower_x96,
):
    pass
