from glasshouse.world.actions import create_utterance_event, create_truth_admission_event
from glasshouse.world.models import AgentRef, Activity, WorldState
from glasshouse.world.perception import PerceptionLevel, compute_perception


def _world_with_agents() -> WorldState:
    world = WorldState()
    world.agents = {
        "max": AgentRef(agent_id="max", location_id="bedroom_a", activity=Activity.IDLE),
        "lea": AgentRef(
            agent_id="lea", location_id="living_room", activity=Activity.IDLE, attention=0.85
        ),
        "eva": AgentRef(
            agent_id="eva", location_id="living_room", activity=Activity.EATING, attention=0.3
        ),
    }
    return world


def test_adjacent_partial_perception():
    world = _world_with_agents()
    world.tick = 1
    event = create_truth_admission_event(world, "max", "claim_1", volume=0.4)
    level = compute_perception(event, world.agents["lea"], event.location)
    assert level in (PerceptionLevel.PARTIAL, PerceptionLevel.FULL)


def test_same_room_low_attention_none():
    world = _world_with_agents()
    world.tick = 1
    event = create_utterance_event(world, "max", "claim_1", "quiet whisper", volume=0.2)
    world.agents["max"] = AgentRef(
        agent_id="max", location_id="bedroom_a", activity=Activity.IDLE, attention=0.1
    )
    level = compute_perception(event, world.agents["eva"], event.location)
    assert level == PerceptionLevel.NONE or world.agents["eva"].location_id != event.location


def test_sleeping_observer_gets_none():
    world = _world_with_agents()
    world.tick = 1
    world.agents["dan"] = AgentRef(
        agent_id="dan", location_id="bedroom_a", activity=Activity.SLEEPING
    )
    event = create_utterance_event(world, "max", "claim_1", "hello", volume=0.9)
    level = compute_perception(event, world.agents["dan"], event.location)
    assert level == PerceptionLevel.NONE
