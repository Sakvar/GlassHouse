from glasshouse.cognition.perception import perceive_event, write_knowledge
from glasshouse.world.actions import create_utterance_event
from glasshouse.world.models import AgentRef, WorldState


def test_knowledge_created_from_utterance():
    world = WorldState()
    world.tick = 1
    world.agents = {
        "lea": AgentRef(agent_id="lea", location_id="living_room", attention=0.8),
        "eva": AgentRef(agent_id="eva", location_id="living_room", attention=0.8),
    }
    event = create_utterance_event(world, "lea", "c1", "test speech", volume=0.8)
    entries = perceive_event(world, event)
    assert len(entries) >= 1
    eva_entries = [e for e in entries if e.agent_id == "eva"]
    assert len(eva_entries) == 1
    store = type("S", (), {"entries": {}})()
    from glasshouse.cognition.perception import KnowledgeStore
    store = KnowledgeStore()
    write_knowledge(store, eva_entries[0])
    assert eva_entries[0].id in store.entries
