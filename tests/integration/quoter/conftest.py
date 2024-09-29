import pytest


@pytest.fixture(scope="module")
def finalizer(accounts):
    yield accounts[4]


@pytest.fixture(scope="module")
def treasury(accounts):
    yield accounts[5]


@pytest.fixture(scope="module")
def margv1_liquidity_receiver_deployer(
    assert_mainnet_fork,
    project,
    accounts,
    univ3_manager,
    margv1_factory,
    margv1_initializer,
    margv1_router,
    margv1_supplier,
    WETH9,
):
    return project.MarginalV1LBLiquidityReceiverDeployer.deploy(
        margv1_supplier.address,
        univ3_manager.address,
        margv1_factory.address,
        margv1_initializer.address,
        margv1_router.address,
        WETH9.address,
        sender=accounts[0],
    )


@pytest.fixture(scope="module")
def margv1_receiver_quoter(assert_mainnet_fork, project, accounts):
    return project.V1LBLiquidityReceiverQuoter.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def margv1_quoter_initialized(
    assert_mainnet_fork,
    margv1_quoter,
    margv1_receiver_quoter,
    margv1_liquidity_receiver_deployer,
    admin,
):
    margv1_quoter.setReceiverQuoter(
        margv1_liquidity_receiver_deployer.address,
        margv1_receiver_quoter.address,
        sender=admin,
    )
    return margv1_quoter


@pytest.fixture(scope="module")
def margv1_receiver_params(finalizer, treasury, sender):
    return (
        treasury.address,  # treasuryAddress
        int(0.1e6),  # treasuryRatio: 10% to treasury
        int(
            0.5e6
        ),  # uniswapV3Ratio: 50% to univ3 pool and 50% to margv1 pool less treasury
        3000,  # uniswapV3Fee
        250000,  # marginalV1Maintenance
        finalizer.address,  # lockOwner
        int(86400 * 30),  # lockDuration: 30 days
        sender.address,  # refundAddress
    )
