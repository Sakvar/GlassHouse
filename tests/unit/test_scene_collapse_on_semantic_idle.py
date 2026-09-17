from glasshouse.scenes.manager import SceneManager
from glasshouse.scenes.models import SemanticChange


def test_scene_collapses_after_three_idle_turns():
    mgr = SceneManager()
    scene = mgr.start_scene("living_room", ["lea", "eva"], [], "2026-01-01T10:00:00")
    for _ in range(3):
        should = mgr.advance_turn(scene.id, SemanticChange(), knowledge_only=True)
    assert should is True
