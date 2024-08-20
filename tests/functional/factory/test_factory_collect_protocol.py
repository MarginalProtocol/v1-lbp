import pytest

from ape import reverts


@pytest.fixture
def token0(pool, token_a, sender):
    token0 = token_a
    amount = int(1e6) * int(10 ** token0.decimals())
    token0.mint(sender.address, amount, sender=sender)
    return token0


def test_collect_protocol__transfers_funds(factory, token0, admin, sender, alice):
    amount = token0.balanceOf(sender) // 10000
    assert amount > 0
    token0.transfer(factory.address, amount, sender=sender)

    balance_alice_before = token0.balanceOf(alice.address)
    balance_factory_before = token0.balanceOf(factory.address)
    assert balance_factory_before == amount

    factory.collectProtocol(token0.address, alice.address, sender=admin)
    assert token0.balanceOf(factory.address) == 0
    assert token0.balanceOf(alice.address) == balance_alice_before + amount


def test_collect_protocol__emits_collect_protocol(
    factory, token0, admin, sender, alice
):
    amount = token0.balanceOf(sender) // 10000
    assert amount > 0
    token0.transfer(factory.address, amount, sender=sender)

    tx = factory.collectProtocol(token0.address, alice.address, sender=admin)
    events = tx.decode_logs(factory.CollectProtocol)
    assert len(events) == 1

    event = events[0]
    assert event.sender == admin.address
    assert event.token == token0.address
    assert event.recipient == alice.address
    assert event.amount == amount


def test_collect_protocol__reverts_when_not_owner(factory, token0, alice, sender):
    amount = token0.balanceOf(sender) // 10000
    assert amount > 0
    token0.transfer(factory.address, amount, sender=sender)

    with reverts(factory.Unauthorized):
        factory.collectProtocol(token0.address, alice.address, sender=alice)
