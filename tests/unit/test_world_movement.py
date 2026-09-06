from glasshouse.world.actions import move_agent
from glasshouse.world.house import create_initial_world
from glasshouse.world.models import Activity, AgentRef


def test_move_between_connected_rooms():
    world = create_initial_world()
    world.tick = 1
    world.agents["max"] = AgentRef(agent_id="max", location_id="bedroom_a")
    event, updated = move_agent(world, "max", "living_room")
    assert updated.location_id == "living_room"
    assert event.type.value == "move"


def test_move_rejects_disconnected():
    world = create_initial_world()
    world.agents["max"] = AgentRef(agent_id="max", location_id="bedroom_a")
    import pytest
    with pytest.raises(ValueError):
        move_agent(world, "max", "garden")
