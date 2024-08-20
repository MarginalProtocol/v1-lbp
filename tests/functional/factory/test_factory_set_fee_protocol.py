from ape import reverts


def test_set_fee_protocol__updates_fee_protocol(factory, admin):
    assert factory.feeProtocol() == 0
    fee_protocol = 10
    factory.setFeeProtocol(fee_protocol, sender=admin)
    assert factory.feeProtocol() == fee_protocol


def test_set_fee_protocol__emits_set_fee_protocol(factory, admin):
    assert factory.feeProtocol() == 0
    fee_protocol = 10
    tx = factory.setFeeProtocol(fee_protocol, sender=admin)
    events = tx.decode_logs(factory.SetFeeProtocol)
    assert len(events) == 1

    event = events[0]
    assert event.oldFeeProtocol == 0
    assert event.newFeeProtocol == fee_protocol


def test_set_fee_protocol__reverts_when_not_owner(factory, alice):
    fee_protocol = 10
    with reverts(factory.Unauthorized):
        factory.setFeeProtocol(fee_protocol, sender=alice)
