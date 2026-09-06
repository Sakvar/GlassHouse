from __future__ import annotations

from dataclasses import dataclass, field

from glasshouse.cognition.triggers import CognitionTrigger
from glasshouse.world.models import WorldEvent


@dataclass(order=True)
class QueueItem:
    sort_key: tuple[int, int, int] = field(compare=True)
    event: WorldEvent | None = field(compare=False, default=None)
    cognition: CognitionTrigger | None = field(compare=False, default=None)
    enqueue_order: int = field(compare=False, default=0)


class EventQueue:
    def __init__(self) -> None:
        self._items: list[QueueItem] = []
        self._counter = 0

    def enqueue_world(self, event: WorldEvent, tick: int, priority: int = 10) -> None:
        self._counter += 1
        self._items.append(
            QueueItem(
                sort_key=(tick, priority, self._counter),
                event=event,
                enqueue_order=self._counter,
            )
        )
        self._items.sort()

    def enqueue_cognition(self, trigger: CognitionTrigger) -> None:
        self._counter += 1
        self._items.append(
            QueueItem(
                sort_key=(trigger.tick, trigger.priority, self._counter),
                cognition=trigger,
                enqueue_order=self._counter,
            )
        )
        self._items.sort()

    def drain_world_events(self, tick: int) -> list[WorldEvent]:
        result: list[WorldEvent] = []
        remaining: list[QueueItem] = []
        for item in self._items:
            if item.event and item.sort_key[0] <= tick:
                result.append(item.event)
            else:
                remaining.append(item)
        self._items = remaining
        return result

    def pop_cognition(self) -> CognitionTrigger | None:
        for i, item in enumerate(self._items):
            if item.cognition:
                trigger = item.cognition
                self._items.pop(i)
                return trigger
        return None

    def pending_cognition_count(self) -> int:
        return sum(1 for item in self._items if item.cognition)
