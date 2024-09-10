import pytest

from ape import reverts
from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO


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
def test_liquidity_receiver_free_reserves__updates_reserves(
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

    assert sender.address != finalizer.address
    pending_timestamp = chain.pending_timestamp
    deadline = pending_timestamp + 3600
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
        deadline,
    )
    supplier.finalizePool(params, sender=sender)

    # check receiver notified
    timestamp_notified = liquidity_receiver.blockTimestampNotified()
    assert timestamp_notified == pending_timestamp

    # check reserves added
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0
    assert reserve1 > 0

    # mine the chain forward past deadline
    receiver_params = liquidity_receiver.receiverParams()
    chain.mine(timestamp=timestamp_notified + receiver_params.lockDuration + 1)

    liquidity_receiver.freeReserves(sender=sender)

    assert liquidity_receiver.reserve0() == 0
    assert liquidity_receiver.reserve1() == 0


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_free_reserves__transfers_funds(
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

    assert sender.address != finalizer.address
    pending_timestamp = chain.pending_timestamp
    deadline = pending_timestamp + 3600
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
        deadline,
    )
    supplier.finalizePool(params, sender=sender)

    # check receiver notified
    timestamp_notified = liquidity_receiver.blockTimestampNotified()
    assert timestamp_notified == pending_timestamp

    # check reserves added
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0
    assert reserve1 > 0

    # mine the chain forward past deadline
    receiver_params = liquidity_receiver.receiverParams()
    chain.mine(timestamp=timestamp_notified + receiver_params.lockDuration + 1)

    # cache balances before
    (balance0_receiver, balance1_receiver) = (
        token0.balanceOf(liquidity_receiver.address),
        token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_sender, balance1_sender) = (
        token0.balanceOf(sender.address),
        token1.balanceOf(sender.address),
    )

    assert receiver_params.refundAddress == sender.address
    liquidity_receiver.freeReserves(sender=sender)

    (balance0_receiver_after, balance1_receiver_after) = (
        token0.balanceOf(liquidity_receiver.address),
        token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_sender_after, balance1_sender_after) = (
        token0.balanceOf(sender.address),
        token1.balanceOf(sender.address),
    )

    assert balance0_receiver_after == 0
    assert balance1_receiver_after == 0
    assert balance0_sender_after == balance0_sender + balance0_receiver
    assert balance1_sender_after == balance1_sender + balance1_receiver


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_liquidity_receiver_free_reserves__reverts_when_deadline_not_passed(
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

    assert sender.address != finalizer.address
    pending_timestamp = chain.pending_timestamp
    deadline = pending_timestamp + 3600
    params = (
        pool_finalized_with_liquidity.token0(),
        pool_finalized_with_liquidity.token1(),
        pool_finalized_with_liquidity.tickLower(),
        pool_finalized_with_liquidity.tickUpper(),
        pool_finalized_with_liquidity.blockTimestampInitialize(),
        deadline,
    )
    supplier.finalizePool(params, sender=sender)

    # check receiver notified
    timestamp_notified = liquidity_receiver.blockTimestampNotified()
    assert timestamp_notified == pending_timestamp

    # check reserves added
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0
    assert reserve1 > 0

    # mine the chain forward past deadline
    receiver_params = liquidity_receiver.receiverParams()
    chain.mine(timestamp=timestamp_notified + receiver_params.lockDuration - 2)

    with reverts(liquidity_receiver.DeadlineNotPassed):
        liquidity_receiver.freeReserves(sender=sender)
