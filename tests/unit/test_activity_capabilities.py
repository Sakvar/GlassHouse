from glasshouse.world.models import Activity, capabilities_for


def test_sleeping_cannot_perceive():
    caps = capabilities_for(Activity.SLEEPING)
    assert caps.can_perceive is False
    assert caps.can_speak is False


def test_walking_can_perceive_not_speak():
    caps = capabilities_for(Activity.WALKING)
    assert caps.can_perceive is True
    assert caps.can_speak is False


def test_conversing_full_capabilities():
    caps = capabilities_for(Activity.CONVERSING)
    assert caps.can_perceive is True
    assert caps.can_speak is True
