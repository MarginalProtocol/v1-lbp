import pytest

from utils.constants import SECONDS_AGO
from utils.utils import calc_sqrt_price_x96_from_tick


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__mints_marginal_v1_liquidity_when_pool_not_exists(
    margv1_liquidity_receiver_and_pool_finalized,
    factory,
    sender,
    alice,
    admin,
    finalizer,
    treasury,
    chain,
    univ3_factory,
    univ3_pool,
    univ3_manager,
    margv1_ticks,
    margv1_factory,
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

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().tokenId > 0

    # check oracle initialized
    slot0 = univ3_pool.slot0()
    assert (
        slot0.observationCardinality >= margv1_factory.observationCardinalityMinimum()
    )
    chain.mine(deltatime=SECONDS_AGO + 1)

    # TODO: cache remaining reserves before

    # mint margv1 liquidity
    liquidity_receiver.mintMarginalV1(sender=alice)
