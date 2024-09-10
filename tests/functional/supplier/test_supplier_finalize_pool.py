import pytest

from ape import reverts

from utils.constants import MIN_SQRT_RATIO, MAX_SQRT_RATIO, MINIMUM_DURATION
from utils.utils import calc_range_amounts_from_liquidity_sqrt_price_x96


# TODO: test remaining revert cases


@pytest.fixture
def receiver_and_pool_finalized(
    receiver_and_pool,
    callee,
    swap_math_lib,
    token0,
    token1,
    sender,
):
    def receiver_and_pool_finalized(init_with_sqrt_price_lower: bool):
        (receiver, pool_initialized_with_liquidity) = receiver_and_pool(
            init_with_sqrt_price_lower
        )

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

        return (receiver, pool_initialized_with_liquidity)

    yield receiver_and_pool_finalized


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__finalizes_pool(
    factory,
    supplier,
    receiver_and_pool_finalized,
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
    (receiver, pool_finalized_with_liquidity) = receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
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

    total_supply = pool_finalized_with_liquidity.totalSupply()
    assert total_supply == 0

    state = pool_finalized_with_liquidity.state()
    assert state.liquidity == 0


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__transfer_funds(
    supplier,
    receiver_and_pool_finalized,
    factory,
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
    # funds to receiver
    factory.setFeeProtocol(fee_protocol, sender=admin)
    (receiver, pool_finalized_with_liquidity) = receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
    )

    # cache balances prior
    balance0_pool = token0.balanceOf(pool_finalized_with_liquidity.address)
    balance1_pool = token1.balanceOf(pool_finalized_with_liquidity.address)

    balance0_factory = token0.balanceOf(factory.address)
    balance1_factory = token1.balanceOf(factory.address)

    balance0_receiver = token0.balanceOf(receiver.address)
    balance1_receiver = token1.balanceOf(receiver.address)

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    # factory in fees
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
    supplier.finalizePool(params, sender=sender)

    # update balances for funds transferred from pool to receiver
    balance0_pool -= amount0 + fees0
    balance1_pool -= amount1 + fees1

    balance0_factory += fees0
    balance1_factory += fees1

    balance0_receiver += amount0
    balance1_receiver += amount1

    # cache updated balances
    balance0_pool_after = token0.balanceOf(pool_finalized_with_liquidity.address)
    balance1_pool_after = token1.balanceOf(pool_finalized_with_liquidity.address)

    balance0_factory_after = token0.balanceOf(factory.address)
    balance1_factory_after = token1.balanceOf(factory.address)

    balance0_receiver_after = token0.balanceOf(receiver.address)
    balance1_receiver_after = token1.balanceOf(receiver.address)

    assert pytest.approx(balance0_pool_after, rel=1e-6) == balance0_pool
    assert pytest.approx(balance1_pool_after, rel=1e-6) == balance1_pool

    assert pytest.approx(balance0_factory_after, rel=1e-6) == balance0_factory
    assert pytest.approx(balance1_factory_after, rel=1e-6) == balance1_factory

    assert pytest.approx(balance0_receiver_after, rel=1e-6) == balance0_receiver_after
    assert pytest.approx(balance1_receiver_after, rel=1e-6) == balance1_receiver_after


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__notifies_reward_amounts(
    supplier,
    receiver_and_pool_finalized,
    range_math_lib,
    factory,
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
    (receiver, pool_finalized_with_liquidity) = receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_finalized_with_liquidity.totalSupply() > 0

    state = pool_finalized_with_liquidity.state()
    assert state.finalized is True
    assert state.feeProtocol == fee_protocol

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
    )

    # calc amounts in pool
    sqrt_price_lower_x96 = pool_finalized_with_liquidity.sqrtPriceLowerX96()
    sqrt_price_upper_x96 = pool_finalized_with_liquidity.sqrtPriceUpperX96()
    (amount0, amount1) = calc_range_amounts_from_liquidity_sqrt_price_x96(
        state.liquidity,
        state.sqrtPriceX96,
        sqrt_price_lower_x96,
        sqrt_price_upper_x96,
    )

    # factory in fees
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

    events = tx.decode_logs(pool_finalized_with_liquidity.Burn)
    assert len(events) == 1
    event = events[0]

    result_amount0 = event.amount0
    result_amount1 = event.amount1

    assert pytest.approx(result_amount0, rel=1e-6) == amount0
    assert pytest.approx(result_amount1, rel=1e-6) == amount1

    receiver_reserve0 += result_amount0
    receiver_reserve1 += result_amount1

    (result_reserve0, result_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert result_reserve0 == receiver_reserve0
    assert result_reserve1 == receiver_reserve1


@pytest.mark.parametrize("fee_protocol", [0, 10, 100])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__finalizes_pool_when_exit(
    factory,
    supplier,
    receiver_and_pool,
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
    (receiver, pool_initialized_with_liquidity) = receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_initialized_with_liquidity.totalSupply() > 0

    state = pool_initialized_with_liquidity.state()
    assert state.finalized is False
    assert state.feeProtocol == fee_protocol

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
    )

    # mine chain forward beyond min duration
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()
    chain.mine(timestamp=timestamp_initialize + MINIMUM_DURATION + 1)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.tickLower(),
        pool_initialized_with_liquidity.tickUpper(),
        pool_initialized_with_liquidity.blockTimestampInitialize(),
    )
    supplier.finalizePool(params, sender=finalizer)

    total_supply = pool_initialized_with_liquidity.totalSupply()
    assert total_supply == 0

    state = pool_initialized_with_liquidity.state()
    assert state.liquidity == 0


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__reverts_when_cannot_exit(
    factory,
    supplier,
    receiver_and_pool,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    init_with_sqrt_price_lower_x96,
):
    (receiver, pool_initialized_with_liquidity) = receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_initialized_with_liquidity.totalSupply() > 0

    state = pool_initialized_with_liquidity.state()
    assert state.finalized is False

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
    )

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.tickLower(),
        pool_initialized_with_liquidity.tickUpper(),
        pool_initialized_with_liquidity.blockTimestampInitialize(),
    )

    with reverts(pool_initialized_with_liquidity.NotFinalized):
        supplier.finalizePool(params, sender=finalizer)


@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_supplier_finalize_pool__reverts_on_exit_when_not_finalizer(
    factory,
    supplier,
    receiver_and_pool,
    token0,
    token1,
    sender,
    admin,
    finalizer,
    chain,
    init_with_sqrt_price_lower_x96,
):
    (receiver, pool_initialized_with_liquidity) = receiver_and_pool(
        init_with_sqrt_price_lower_x96
    )
    assert (
        pool_initialized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized
    assert pool_initialized_with_liquidity.totalSupply() > 0

    state = pool_initialized_with_liquidity.state()
    assert state.finalized is False

    (receiver_reserve0, receiver_reserve1) = (receiver.reserve0(), receiver.reserve1())
    assert (
        receiver_reserve0 > 0
        if init_with_sqrt_price_lower_x96
        else receiver_reserve1 > 0
    )

    # mine chain forward beyond min duration
    timestamp_initialize = pool_initialized_with_liquidity.blockTimestampInitialize()
    chain.mine(timestamp=timestamp_initialize + MINIMUM_DURATION + 1)

    params = (
        pool_initialized_with_liquidity.token0(),
        pool_initialized_with_liquidity.token1(),
        pool_initialized_with_liquidity.tickLower(),
        pool_initialized_with_liquidity.tickUpper(),
        pool_initialized_with_liquidity.blockTimestampInitialize(),
    )

    with reverts(supplier.Unauthorized):
        supplier.finalizePool(params, sender=sender)
