import pytest


@pytest.mark.integration
def test_integration_quoter_set_receiver_quoter__sets_receiver_quoter(
    margv1_quoter_initialized,
    margv1_liquidity_receiver_deployer,
    margv1_receiver_quoter,
):
    assert (
        margv1_quoter_initialized.receiverQuoters(
            margv1_liquidity_receiver_deployer.address
        )
        == margv1_receiver_quoter.address
    )
