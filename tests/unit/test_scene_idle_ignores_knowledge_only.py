from glasshouse.scenes.manager import SceneManager
from glasshouse.scenes.models import SemanticChange


def test_knowledge_only_does_not_reset_idle():
    mgr = SceneManager()
    scene = mgr.start_scene("living_room", ["lea", "eva"], [], "2026-01-01T10:00:00")
    change = SemanticChange()
    mgr.advance_turn(scene.id, change, knowledge_only=True)
    assert scene.idle_turns == 1


def test_semantic_change_resets_idle():
    mgr = SceneManager()
    scene = mgr.start_scene("living_room", ["lea", "eva"], [], "2026-01-01T10:00:00")
    mgr.advance_turn(scene.id, SemanticChange(), knowledge_only=True)
    mgr.advance_turn(scene.id, SemanticChange(claims_changed=True), knowledge_only=False)
    assert scene.idle_turns == 0
