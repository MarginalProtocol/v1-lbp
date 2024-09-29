import pytest


@pytest.fixture(scope="module")
def assert_mainnet_fork(networks):
    assert (
        networks.active_provider.network.name == "mainnet-fork"
    ), "network not set to mainnet-fork"


@pytest.fixture(scope="module")
def whale(assert_mainnet_fork, accounts):
    return accounts["0x8EB8a3b98659Cce290402893d0123abb75E3ab28"]  # avalanche bridge


@pytest.fixture(scope="module")
def WETH9(assert_mainnet_fork, Contract):
    return Contract("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")


@pytest.fixture(scope="module")
def USDC(assert_mainnet_fork, Contract):
    return Contract("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")


@pytest.fixture(scope="module")
def TTOKEN(assert_mainnet_fork, Contract):
    return Contract("0x2abA156fFb8BD5cCaD8C1b7DaaBC3Aa532dfC120")


@pytest.fixture(scope="module")
def univ3_factory(assert_mainnet_fork, univ3_factory_address, Contract):
    return Contract(univ3_factory_address)


@pytest.fixture(scope="module")
def univ3_pool(assert_mainnet_fork, Contract):
    return Contract("0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8")


@pytest.fixture(scope="module")
def univ3_manager(assert_mainnet_fork, Contract):
    return Contract("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")


@pytest.fixture(scope="module")
def margv1_factory(assert_mainnet_fork, Contract):
    return Contract("0x95D95C41436C15b50217Bf1C0f810536AD181C13")


@pytest.fixture(scope="module")
def margv1_initializer(assert_mainnet_fork, Contract):
    return Contract("0x9e7efb5f29C789dE8157cA1A19D6915012caE676")


@pytest.fixture(scope="module")
def margv1_router(assert_mainnet_fork, Contract):
    return Contract("0xD8FDd7357cBD8b88e690c9266608092eEFE7123b")


@pytest.fixture(scope="module")
def margv1_supplier(
    assert_mainnet_fork, project, accounts, factory, margv1_factory, WETH9
):
    return project.MarginalV1LBSupplier.deploy(
        factory.address,
        margv1_factory.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def margv1_quoter(
    assert_mainnet_fork, project, accounts, factory, margv1_factory, WETH9
):
    return project.V1LBQuoter.deploy(
        factory.address,
        margv1_factory.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def margv1_ticks(
    assert_mainnet_fork,
    univ3_pool,
):
    tick_width = 2000  # ~50% in price from low to high
    tick_mid = univ3_pool.slot0().tick
    return (tick_mid - tick_width, tick_mid + tick_width)


@pytest.fixture(scope="module")
def another_margv1_ticks(assert_mainnet_fork):
    tick_width = 2000
    tick_mid = -82944  # TEST/WETH tick on spot
    return (tick_mid - tick_width, tick_mid + tick_width)


@pytest.fixture(scope="module")
def margv1_token0(
    assert_mainnet_fork,
    univ3_pool,
    WETH9,
    USDC,
    sender,
    callee,
    margv1_supplier,
    margv1_initializer,
    whale,
):
    token0 = USDC
    amount0 = token0.balanceOf(whale.address) // 2  # 50% of balance
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(margv1_supplier.address, 2**256 - 1, sender=sender)
    token0.approve(margv1_initializer.address, 2**256 - 1, sender=sender)
    token0.transfer(sender.address, amount0, sender=whale)
    return token0


@pytest.fixture(scope="module")
def margv1_token1(
    assert_mainnet_fork,
    univ3_pool,
    WETH9,
    USDC,
    sender,
    callee,
    margv1_supplier,
    margv1_initializer,
    whale,
):
    token1 = WETH9
    amount1 = token1.balanceOf(whale.address) // 2  # 50% of balance
    token1.approve(callee.address, 2**256 - 1, sender=sender)
    token1.approve(margv1_supplier.address, 2**256 - 1, sender=sender)
    token1.approve(margv1_initializer.address, 2**256 - 1, sender=sender)
    token1.transfer(sender.address, amount1, sender=whale)
    return token1


@pytest.fixture(scope="module")
def another_margv1_token0(
    assert_mainnet_fork,
    univ3_pool,
    WETH9,
    USDC,
    TTOKEN,
    sender,
    callee,
    margv1_supplier,
    margv1_initializer,
    whale,
):
    token0 = TTOKEN
    amount0 = token0.balanceOf(whale.address) // 2  # 50% of balance
    token0.approve(callee.address, 2**256 - 1, sender=sender)
    token0.approve(margv1_supplier.address, 2**256 - 1, sender=sender)
    token0.approve(margv1_initializer.address, 2**256 - 1, sender=sender)
    token0.transfer(sender.address, amount0, sender=whale)
    return token0
