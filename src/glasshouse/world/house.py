from glasshouse.world.models import Location, WorldState

ROOMS = ["kitchen", "living_room", "bedroom_a", "bedroom_b", "garden"]

ADJACENCY: dict[str, list[str]] = {
    "kitchen": ["living_room"],
    "living_room": ["kitchen", "bedroom_a", "bedroom_b", "garden"],
    "bedroom_a": ["living_room"],
    "bedroom_b": ["living_room"],
    "garden": ["living_room"],
}


def create_house() -> dict[str, Location]:
    return {
        room_id: Location(
            id=room_id,
            name=room_id.replace("_", " ").title(),
            connected_to=ADJACENCY[room_id],
        )
        for room_id in ROOMS
    }


def create_initial_world() -> WorldState:
    return WorldState(locations=create_house())


def are_adjacent(loc_a: str, loc_b: str) -> bool:
    if loc_a == loc_b:
        return False
    return loc_b in ADJACENCY.get(loc_a, [])


def distance_level(observer_loc: str, event_loc: str) -> str:
    if observer_loc == event_loc:
        return "same_room"
    if are_adjacent(observer_loc, event_loc):
        return "adjacent"
    return "far"
