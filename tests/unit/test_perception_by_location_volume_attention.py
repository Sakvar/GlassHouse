from glasshouse.world.actions import create_truth_admission_event
from glasshouse.world.models import AgentRef, WorldState
from glasshouse.world.perception import PerceptionLevel, compute_perception


def test_adjacent_high_attention_partial():
    world = WorldState()
    world.tick = 1
    world.agents = {
        "max": AgentRef(agent_id="max", location_id="bedroom_a"),
        "lea": AgentRef(agent_id="lea", location_id="living_room", attention=0.9),
    }
    event = create_truth_admission_event(world, "max", "c1", volume=0.4)
    level = compute_perception(event, world.agents["lea"], event.location)
    assert level == PerceptionLevel.PARTIAL


def test_far_distance_none():
    world = WorldState()
    world.tick = 1
    world.agents = {
        "max": AgentRef(agent_id="max", location_id="bedroom_a"),
        "lea": AgentRef(agent_id="lea", location_id="garden", attention=0.9),
    }
    event = create_truth_admission_event(world, "max", "c1", volume=0.9)
    level = compute_perception(event, world.agents["lea"], event.location)
    assert level == PerceptionLevel.NONE
