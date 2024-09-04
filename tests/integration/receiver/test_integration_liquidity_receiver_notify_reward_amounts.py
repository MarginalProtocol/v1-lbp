import pytest

from utils.constants import MINIMUM_DURATION
from utils.utils import calc_sqrt_price_x96_from_tick


# TODO: more param cases


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_notify_reward_amounts__updates_reserves_timestamp_and_transfers_funds(
    margv1_liquidity_receiver_and_pool_finalized,
    factory,
    sender,
    admin,
    finalizer,
    treasury,
    chain,
    margv1_ticks,
    margv1_receiver_params,
    margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)

    (tick_lower, tick_upper) = margv1_ticks
    tick_width_2x = tick_upper - tick_lower

    delta = int(tick_width_2x * percent_thru_range)
    tick = tick_lower + delta if init_with_sqrt_price_lower_x96 else tick_upper - delta
    sqrt_price_last_x96 = calc_sqrt_price_x96_from_tick(tick)

    (
        liquidity_receiver,
        pool_finalized_with_liquidity,
    ) = margv1_liquidity_receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96, sqrt_price_last_x96
    )
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized

    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert pytest.approx(state.sqrtPriceX96, rel=1e-3) == sqrt_price_last_x96

    if percent_thru_range >= 1.0:
        assert state.finalized is True
    else:
        timestamp_initialize = pool_finalized_with_liquidity.blockTimestampInitialize()
        assert chain.pending_timestamp >= timestamp_initialize + MINIMUM_DURATION

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    assert liquidity_receiver_params == margv1_receiver_params

    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )
    assert reserve0 > 0
    assert reserve1 > 0

    (balance0_receiver, balance1_receiver) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )

    assert pytest.approx(balance0_receiver, rel=1e-6) == reserve0
    assert pytest.approx(balance1_receiver, rel=1e-6) == reserve1
    assert balance0_receiver >= reserve0
    assert balance1_receiver >= reserve1

    timestamp_notified = liquidity_receiver.blockTimestampNotified()
    assert timestamp_notified == chain.blocks.head.timestamp

    (balance0_treasury, balance1_treasury) = (
        margv1_token0.balanceOf(treasury),
        margv1_token1.balanceOf(treasury),
    )

    assert liquidity_receiver_params.treasuryRatio > 0
    if percent_thru_range >= 1.0:
        if init_with_sqrt_price_lower_x96:
            assert balance0_treasury == 0
            assert balance1_treasury > 0
        else:
            assert balance0_treasury > 0
            assert balance1_treasury == 0
    else:
        assert balance0_treasury > 0
        assert balance1_treasury > 0
