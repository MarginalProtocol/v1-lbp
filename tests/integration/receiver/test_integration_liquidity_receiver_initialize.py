import pytest

from ape import reverts
from utils.utils import calc_sqrt_price_x96_from_tick


# TODO: more param cases


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_initialize__reverts_when_initialized(
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

    with reverts(liquidity_receiver.Initialized):
        liquidity_receiver.initialize(sender=sender)
