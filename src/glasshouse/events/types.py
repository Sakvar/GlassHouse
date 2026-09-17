from __future__ import annotations

from enum import Enum, StrEnum


class QueuedEventType(StrEnum):
    WORLD = "world"
    COGNITION = "cognition"


class EventPriority(int, Enum):
    HIGH = 0
    NORMAL = 10
    LOW = 20
