from glasshouse.agents.seeds import create_seed_agents
from glasshouse.cognition.claims import Claim, ClaimPredicate
from glasshouse.cognition.validator import ValidationError, validate_intent
from glasshouse.llm.schemas import Intent, IntentType, UtteranceIntent
from glasshouse.world.house import create_house
from glasshouse.world.models import Activity


def test_cannot_speak_while_walking():
    agents = create_seed_agents()
    agent = agents["max"]
    agent.ref = agent.ref.model_copy(update={"activity": Activity.WALKING})
    intent = UtteranceIntent(
        claim=Claim(subject="max", predicate=ClaimPredicate.DISLIKES),
        exact_text="hi",
    )
    try:
        validate_intent(agent, intent, create_house())
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_cannot_act_while_sleeping():
    agents = create_seed_agents()
    agent = agents["max"]
    agent.ref = agent.ref.model_copy(update={"activity": Activity.SLEEPING})
    intent = Intent(intent_type=IntentType.MOVE, target="living_room")
    try:
        validate_intent(agent, intent, create_house())
        assert False
    except ValidationError:
        pass
