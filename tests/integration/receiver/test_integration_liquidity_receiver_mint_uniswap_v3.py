import pytest

from ape.utils import ZERO_ADDRESS
from utils.constants import MAX_TICK
from utils.utils import calc_sqrt_price_x96_from_tick


# TODO: more param cases
# TODO: test event emitted
# TODO: check amount0, amount1 returned always less than amounts removed for uniswap


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_uniswap_v3__updates_reserves_when_pool_exists(
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

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    assert liquidity_receiver_params == margv1_receiver_params

    # cache reserves
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )

    amount0_univ3 = (reserve0 * liquidity_receiver_params.uniswapV3Ratio) // int(1e6)
    amount1_univ3 = (reserve1 * liquidity_receiver_params.uniswapV3Ratio) // int(1e6)

    # mint to univ3
    tx = liquidity_receiver.mintUniswapV3(sender=alice)
    events = tx.decode_logs(univ3_manager.IncreaseLiquidity)
    assert len(events) == 1

    event = events[0]
    (amount0, amount1) = (event.amount0, event.amount1)

    assert amount0 <= amount0_univ3
    assert amount1 <= amount1_univ3

    reserve0 -= amount0
    reserve1 -= amount1

    assert liquidity_receiver.reserve0() == reserve0
    assert liquidity_receiver.reserve1() == reserve1


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_uniswap_v3__creates_pool_when_pool_not_exists(
    another_margv1_liquidity_receiver_and_pool_finalized,
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
    another_margv1_ticks,
    another_margv1_receiver_params,
    another_margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
    accounts,
):
    factory.setFeeProtocol(fee_protocol, sender=admin)

    (tick_lower, tick_upper) = another_margv1_ticks
    tick_width_2x = tick_upper - tick_lower

    delta = int(tick_width_2x * percent_thru_range)
    tick = tick_lower + delta if init_with_sqrt_price_lower_x96 else tick_upper - delta
    sqrt_price_last_x96 = calc_sqrt_price_x96_from_tick(tick)

    (
        liquidity_receiver,
        pool_finalized_with_liquidity,
    ) = another_margv1_liquidity_receiver_and_pool_finalized(
        init_with_sqrt_price_lower_x96, sqrt_price_last_x96
    )
    assert (
        pool_finalized_with_liquidity.sqrtPriceInitializeX96() > 0
    )  # pool initialized

    state = pool_finalized_with_liquidity.state()
    assert state.feeProtocol == fee_protocol
    assert pytest.approx(state.sqrtPriceX96, rel=1e-3) == sqrt_price_last_x96

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    assert liquidity_receiver_params == another_margv1_receiver_params

    # check fee tier exists and no pool at fee tier
    assert (
        univ3_factory.getPool(
            another_margv1_token0.address,
            margv1_token1.address,
            liquidity_receiver_params.uniswapV3Fee,
        )
        == ZERO_ADDRESS
    )

    # mint to univ3
    tx = liquidity_receiver.mintUniswapV3(sender=alice)
    events = tx.decode_logs(univ3_factory.PoolCreated)
    assert len(events) == 1
    event = events[0]
    univ3_pool_address = event.pool

    # check pool created with initial price set to lbp pool price
    events = tx.decode_logs(univ3_pool.Initialize)
    assert len(events) == 1
    event = events[0]
    assert event.sqrtPriceX96 == state.sqrtPriceX96

    # check pool at fee tier now
    assert (
        univ3_factory.getPool(
            another_margv1_token0.address,
            margv1_token1.address,
            liquidity_receiver_params.uniswapV3Fee,
        )
        == univ3_pool_address
    )


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_uniswap_v3__stores_pool_info_when_pool_exists(
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

    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp == 0
    assert liquidity_receiver.uniswapV3PoolInfo().tokenId == 0

    # mint to univ3
    timestamp = chain.pending_timestamp
    liquidity_receiver.mintUniswapV3(sender=alice)

    info = liquidity_receiver.uniswapV3PoolInfo()
    assert info.blockTimestamp == timestamp
    assert info.poolAddress == univ3_pool.address
    assert info.tokenId > 0
    assert info.shares == 0


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_uniswap_v3__mints_uniswap_v3_liquidity_when_pool_exists(
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

    liquidity_receiver_params = liquidity_receiver.receiverParams()
    assert liquidity_receiver_params == margv1_receiver_params

    # cache reserves
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )

    amount0_univ3 = (reserve0 * liquidity_receiver_params.uniswapV3Ratio) // int(1e6)
    amount1_univ3 = (reserve1 * liquidity_receiver_params.uniswapV3Ratio) // int(1e6)

    zero_for_one = init_with_sqrt_price_lower_x96
    (amount0_desired, amount1_desired) = liquidity_receiver.getAmountsDesired(
        state.sqrtPriceX96, amount0_univ3, amount1_univ3, zero_for_one
    )
    assert amount0_desired <= amount0_univ3
    assert amount1_desired <= amount1_univ3

    univ3_tick_spacing = univ3_factory.feeAmountTickSpacing(
        liquidity_receiver_params.uniswapV3Fee
    )
    univ3_tick_upper = MAX_TICK - (MAX_TICK % univ3_tick_spacing)
    univ3_tick_lower = -univ3_tick_upper

    # mint to univ3
    liquidity_receiver.mintUniswapV3(sender=alice)

    info = liquidity_receiver.uniswapV3PoolInfo()
    assert info.tokenId > 0

    # calc liquidity expected using univ3 pool current price
    slot0 = univ3_pool.slot0()
    univ3_liquidity0 = (amount0_desired * slot0.sqrtPriceX96) // (1 << 96)
    univ3_liquidity1 = (amount1_desired * (1 << 96)) // slot0.sqrtPriceX96
    univ3_liquidity = (
        univ3_liquidity0 if univ3_liquidity0 < univ3_liquidity1 else univ3_liquidity1
    )

    # check univ3 manager position has correct tick range and liquidity
    univ3_position = univ3_manager.positions(info.tokenId)
    assert univ3_position.tickLower == univ3_tick_lower
    assert univ3_position.tickUpper == univ3_tick_upper
    assert pytest.approx(univ3_position.liquidity, rel=1e-6) == univ3_liquidity

    owner_address = univ3_manager.ownerOf(info.tokenId)
    assert owner_address == liquidity_receiver.address


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_uniswap_v3__transfers_funds_when_pool_exists(
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

    # cache balances before
    (balance0_receiver, balance1_receiver) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_univ3_pool, balance1_univ3_pool) = (
        margv1_token0.balanceOf(univ3_pool.address),
        margv1_token1.balanceOf(univ3_pool.address),
    )

    # mint to univ3
    tx = liquidity_receiver.mintUniswapV3(sender=alice)
    events = tx.decode_logs(liquidity_receiver.MintUniswapV3)
    assert len(events) == 1
    event = events[0]

    amount0 = event.amount0
    amount1 = event.amount1

    balance0_receiver -= amount0
    balance1_receiver -= amount1

    balance0_univ3_pool += amount0
    balance1_univ3_pool += amount1

    assert margv1_token0.balanceOf(liquidity_receiver.address) == balance0_receiver
    assert margv1_token1.balanceOf(liquidity_receiver.address) == balance1_receiver

    assert margv1_token0.balanceOf(univ3_pool.address) == balance0_univ3_pool
    assert margv1_token1.balanceOf(univ3_pool.address) == balance1_univ3_pool
