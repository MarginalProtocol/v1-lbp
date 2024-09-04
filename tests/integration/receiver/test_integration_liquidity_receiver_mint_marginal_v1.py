import pytest
from ape.utils import ZERO_ADDRESS

from utils.constants import MINIMUM_LIQUIDITY, SECONDS_AGO
from utils.utils import calc_sqrt_price_x96_from_tick


# TODO: more param cases
# TODO: revert cases, when pool created cases, event emitted
# TODO: check amount0, amount1 returned always less than amounts removed for marginal


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__updates_reserves_when_pool_not_exists(
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
    margv1_initializer,
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
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp == 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # check oracle initialized
    slot0 = univ3_pool.slot0()
    assert (
        slot0.observationCardinality >= margv1_factory.observationCardinalityMinimum()
    )
    chain.mine(deltatime=SECONDS_AGO + 1)

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_initializer.PoolInitialize)
    assert len(events) == 1

    # check reserves set to zero
    assert liquidity_receiver.reserve0() == 0
    assert liquidity_receiver.reserve1() == 0


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__updates_reserves_when_pool_exists(
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
    margv1_initializer,
    margv1_router,
    margv1_receiver_params,
    margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
    project,
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

    # create margv1 pool
    liquidity_receiver_params = liquidity_receiver.receiverParams()
    slot0 = univ3_pool.slot0()
    amount1_init = int(1.0e18)  # 1 ETH
    amount0_init = (amount1_init * (1 << 192)) // (slot0.sqrtPriceX96**2)
    init_params = (
        univ3_pool.token0(),
        univ3_pool.token1(),
        liquidity_receiver_params.marginalV1Maintenance,
        liquidity_receiver_params.uniswapV3Fee,
        sender.address,
        slot0.sqrtPriceX96,
        0,
        MINIMUM_LIQUIDITY**2,
        2**255 - 1,
        2**255 - 1,
        amount0_init,
        amount1_init,
        0,
        0,
        chain.pending_timestamp + 3600,
    )
    tx = margv1_initializer.createAndInitializePoolIfNecessary(
        init_params, sender=sender
    )

    event = tx.decode_logs(margv1_initializer.PoolInitialize)[0]
    pool_token = project.Token.at(event.pool)
    total_supply = pool_token.totalSupply()
    assert total_supply > 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # check oracle initialized
    slot0 = univ3_pool.slot0()
    assert (
        slot0.observationCardinality >= margv1_factory.observationCardinalityMinimum()
    )
    chain.mine(deltatime=SECONDS_AGO + 1)

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_router.IncreaseLiquidity)
    assert len(events) == 1

    info = liquidity_receiver.marginalV1PoolInfo()
    total_supply += info.shares
    assert pool_token.totalSupply() == total_supply

    # check reserves set to zero
    assert liquidity_receiver.reserve0() == 0
    assert liquidity_receiver.reserve1() == 0


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__stores_pool_info_when_pool_not_exists(
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
    margv1_initializer,
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
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp == 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # check oracle initialized
    slot0 = univ3_pool.slot0()
    assert (
        slot0.observationCardinality >= margv1_factory.observationCardinalityMinimum()
    )
    chain.mine(deltatime=SECONDS_AGO + 1)

    # mint margv1 liquidity
    timestamp = chain.pending_timestamp
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_initializer.PoolInitialize)
    assert len(events) == 1

    info = liquidity_receiver.marginalV1PoolInfo()
    assert info.blockTimestamp == timestamp
    assert info.poolAddress != ZERO_ADDRESS
    assert info.tokenId == 0
    assert info.shares > 0


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__stores_pool_info_when_pool_exists(
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
    margv1_initializer,
    margv1_router,
    margv1_receiver_params,
    margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
    project,
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

    # create margv1 pool
    liquidity_receiver_params = liquidity_receiver.receiverParams()
    slot0 = univ3_pool.slot0()
    amount1_init = int(1.0e18)  # 1 ETH
    amount0_init = (amount1_init * (1 << 192)) // (slot0.sqrtPriceX96**2)
    init_params = (
        univ3_pool.token0(),
        univ3_pool.token1(),
        liquidity_receiver_params.marginalV1Maintenance,
        liquidity_receiver_params.uniswapV3Fee,
        sender.address,
        slot0.sqrtPriceX96,
        0,
        MINIMUM_LIQUIDITY**2,
        2**255 - 1,
        2**255 - 1,
        amount0_init,
        amount1_init,
        0,
        0,
        chain.pending_timestamp + 3600,
    )
    tx = margv1_initializer.createAndInitializePoolIfNecessary(
        init_params, sender=sender
    )

    event = tx.decode_logs(margv1_initializer.PoolInitialize)[0]
    pool_token = project.Token.at(event.pool)
    total_supply = pool_token.totalSupply()
    assert total_supply > 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # mint margv1 liquidity
    timestamp = chain.pending_timestamp
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_router.IncreaseLiquidity)
    assert len(events) == 1

    info = liquidity_receiver.marginalV1PoolInfo()
    assert info.blockTimestamp == timestamp
    assert info.poolAddress != ZERO_ADDRESS
    assert info.tokenId == 0
    assert info.shares > 0


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
    margv1_initializer,
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

    # cache remaining reserves
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )

    zero_for_one = init_with_sqrt_price_lower_x96
    (amount0_desired, amount1_desired) = liquidity_receiver.getAmountsDesired(
        state.sqrtPriceX96, reserve0, reserve1, zero_for_one
    )
    assert amount0_desired <= reserve0
    assert amount1_desired <= reserve1

    # calculate estimated liquidity to be minted to receiver
    slot0 = univ3_pool.slot0()
    margv1_liquidity0 = (amount0_desired * slot0.sqrtPriceX96) // (1 << 96)
    margv1_liquidity1 = (amount1_desired * (1 << 96)) // slot0.sqrtPriceX96
    margv1_liquidity = (
        margv1_liquidity0
        if margv1_liquidity0 < margv1_liquidity1
        else margv1_liquidity1
    )

    # account for liquidity burned taken off desired
    margv1_liquidity -= 2 * (MINIMUM_LIQUIDITY**2)

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_initializer.PoolInitialize)
    assert len(events) == 1

    info = liquidity_receiver.marginalV1PoolInfo()
    assert pytest.approx(info.shares, rel=1e-4) == margv1_liquidity


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__mints_marginal_v1_liquidity_when_pool_exists(
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
    margv1_initializer,
    margv1_router,
    margv1_receiver_params,
    margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
    project,
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

    # create margv1 pool
    liquidity_receiver_params = liquidity_receiver.receiverParams()
    slot0 = univ3_pool.slot0()
    amount1_init = int(1.0e18)  # 1 ETH
    amount0_init = (amount1_init * (1 << 192)) // (slot0.sqrtPriceX96**2)
    init_params = (
        univ3_pool.token0(),
        univ3_pool.token1(),
        liquidity_receiver_params.marginalV1Maintenance,
        liquidity_receiver_params.uniswapV3Fee,
        sender.address,
        slot0.sqrtPriceX96,
        0,
        MINIMUM_LIQUIDITY**2,
        2**255 - 1,
        2**255 - 1,
        amount0_init,
        amount1_init,
        0,
        0,
        chain.pending_timestamp + 3600,
    )
    tx = margv1_initializer.createAndInitializePoolIfNecessary(
        init_params, sender=sender
    )

    event = tx.decode_logs(margv1_initializer.PoolInitialize)[0]
    pool_token = project.Token.at(event.pool)
    total_supply = pool_token.totalSupply()
    assert total_supply > 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # cache remaining reserves
    (reserve0, reserve1) = (
        liquidity_receiver.reserve0(),
        liquidity_receiver.reserve1(),
    )

    zero_for_one = init_with_sqrt_price_lower_x96
    (amount0_desired, amount1_desired) = liquidity_receiver.getAmountsDesired(
        state.sqrtPriceX96, reserve0, reserve1, zero_for_one
    )
    assert amount0_desired <= reserve0
    assert amount1_desired <= reserve1

    # calculate estimated liquidity to be minted to receiver
    margv1_liquidity0 = (amount0_desired * slot0.sqrtPriceX96) // (1 << 96)
    margv1_liquidity1 = (amount1_desired * (1 << 96)) // slot0.sqrtPriceX96
    margv1_liquidity = (
        margv1_liquidity0
        if margv1_liquidity0 < margv1_liquidity1
        else margv1_liquidity1
    )

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    events = tx.decode_logs(margv1_router.IncreaseLiquidity)
    assert len(events) == 1

    info = liquidity_receiver.marginalV1PoolInfo()
    assert pytest.approx(info.shares, rel=1e-3) == margv1_liquidity
    assert (
        pytest.approx(pool_token.balanceOf(liquidity_receiver.address), rel=1e-3)
        == margv1_liquidity
    )


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__transfer_funds_when_pool_not_exists(
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
    margv1_initializer,
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

    # cache balances before
    (balance0_receiver, balance1_receiver) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_sender, balance1_sender) = (
        margv1_token0.balanceOf(sender.address),
        margv1_token1.balanceOf(sender.address),
    )

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    assert len(tx.decode_logs(margv1_initializer.PoolInitialize)) == 1

    events = tx.decode_logs(liquidity_receiver.MintMarginalV1)
    assert len(events) == 1
    event = events[0]

    amount0 = event.amount0
    amount1 = event.amount1

    # check token balance differences sent to refund address
    balance0_receiver -= amount0
    balance1_receiver -= amount1

    (balance0_receiver_after, balance1_receiver_after) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )
    assert balance0_receiver_after == 0
    assert balance1_receiver_after == 0

    # add balances to refund address
    balance0_sender += balance0_receiver
    balance1_sender += balance1_receiver

    (balance0_sender_after, balance1_sender_after) = (
        margv1_token0.balanceOf(sender.address),
        margv1_token1.balanceOf(sender.address),
    )
    assert balance0_sender_after == balance0_sender
    assert balance1_sender_after == balance1_sender


@pytest.mark.integration
@pytest.mark.parametrize("fee_protocol", [10])
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
@pytest.mark.parametrize("percent_thru_range", [1.0])
def test_integration_liquidity_receiver_mint_marginal_v1__transfer_funds_when_pool_exists(
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
    margv1_initializer,
    margv1_router,
    margv1_receiver_params,
    margv1_token0,
    margv1_token1,
    fee_protocol,
    percent_thru_range,
    init_with_sqrt_price_lower_x96,
    project,
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

    # create margv1 pool
    liquidity_receiver_params = liquidity_receiver.receiverParams()
    slot0 = univ3_pool.slot0()
    amount1_init = int(1.0e18)  # 1 ETH
    amount0_init = (amount1_init * (1 << 192)) // (slot0.sqrtPriceX96**2)
    init_params = (
        univ3_pool.token0(),
        univ3_pool.token1(),
        liquidity_receiver_params.marginalV1Maintenance,
        liquidity_receiver_params.uniswapV3Fee,
        sender.address,
        slot0.sqrtPriceX96,
        0,
        MINIMUM_LIQUIDITY**2,
        2**255 - 1,
        2**255 - 1,
        amount0_init,
        amount1_init,
        0,
        0,
        chain.pending_timestamp + 3600,
    )
    tx = margv1_initializer.createAndInitializePoolIfNecessary(
        init_params, sender=sender
    )

    event = tx.decode_logs(margv1_initializer.PoolInitialize)[0]
    pool_token = project.Token.at(event.pool)
    total_supply = pool_token.totalSupply()
    assert total_supply > 0

    # mint univ3 liquidity first
    liquidity_receiver.mintUniswapV3(sender=alice)
    assert liquidity_receiver.uniswapV3PoolInfo().blockTimestamp > 0

    # check oracle initialized
    slot0 = univ3_pool.slot0()
    assert (
        slot0.observationCardinality >= margv1_factory.observationCardinalityMinimum()
    )
    chain.mine(deltatime=SECONDS_AGO + 1)

    # cache balances before
    (balance0_receiver, balance1_receiver) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )
    (balance0_sender, balance1_sender) = (
        margv1_token0.balanceOf(sender.address),
        margv1_token1.balanceOf(sender.address),
    )

    # mint margv1 liquidity
    tx = liquidity_receiver.mintMarginalV1(sender=alice)
    assert len(tx.decode_logs(margv1_router.IncreaseLiquidity)) == 1

    events = tx.decode_logs(liquidity_receiver.MintMarginalV1)
    assert len(events) == 1
    event = events[0]

    amount0 = event.amount0
    amount1 = event.amount1

    # check token balance differences sent to refund address
    balance0_receiver -= amount0
    balance1_receiver -= amount1

    (balance0_receiver_after, balance1_receiver_after) = (
        margv1_token0.balanceOf(liquidity_receiver.address),
        margv1_token1.balanceOf(liquidity_receiver.address),
    )
    assert balance0_receiver_after == 0
    assert balance1_receiver_after == 0

    # add balances to refund address
    balance0_sender += balance0_receiver
    balance1_sender += balance1_receiver

    (balance0_sender_after, balance1_sender_after) = (
        margv1_token0.balanceOf(sender.address),
        margv1_token1.balanceOf(sender.address),
    )
    assert balance0_sender_after == balance0_sender
    assert balance1_sender_after == balance1_sender
