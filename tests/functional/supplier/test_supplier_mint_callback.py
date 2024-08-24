from ape import reverts
from eth_abi import encode


def test_supplier_mint_callback__reverts_when_pool_not_sender(
    supplier, sender, another_pool, callback_validation_lib, chain
):
    amount0 = 1  # 1 wei
    amount1 = 1
    data = encode(
        ["(address,address,int24,int24,address,uint256)", "address"],
        [
            (
                another_pool.token0(),
                another_pool.token1(),
                another_pool.tickLower(),
                another_pool.tickUpper(),
                another_pool.supplier(),
                another_pool.blockTimestampInitialize(),
            ),
            sender.address,
        ],
    )

    with reverts(callback_validation_lib.PoolNotSender):
        supplier.marginalV1MintCallback(amount0, amount1, data, sender=sender)
