#!/usr/bin/env python3
"""Print simulation timeline from events."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from glasshouse.simulation.engine import SimulationEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Show event timeline")
    parser.add_argument("--last", default="2h")
    parser.add_argument("--filter", default="")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    engine = SimulationEngine(seed=args.seed)
    engine.run(hours=2, ticks_per_hour=60)

    filters = [f.strip() for f in args.filter.split(",") if f.strip()]
    for event in engine.world.events_log:
        if filters:
            if not any(f in event.type.value for f in filters):
                payload_str = str(event.payload)
                if not any(f in payload_str for f in filters):
                    continue
        text = event.payload.get("exact_text", "")
        print(
            f"[tick {event.tick}] {event.type.value} @{event.location} actor={event.actor} {text}"
        )


if __name__ == "__main__":
    main()
