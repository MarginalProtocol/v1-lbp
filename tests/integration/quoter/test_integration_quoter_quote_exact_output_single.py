import pytest


@pytest.mark.integration
@pytest.mark.parametrize("init_with_sqrt_price_lower_x96", [True, False])
def test_integration_quoter_quote_exact_output_single__quotes_swap(
    init_with_sqrt_price_lower_x96,
):
    pass
