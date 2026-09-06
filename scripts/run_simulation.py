#!/usr/bin/env python3
"""Run accelerated simulation."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from glasshouse.simulation.engine import SimulationEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Glasshouse simulation")
    parser.add_argument("--hours", type=float, default=48)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--speed", type=float, default=1000, help="Acceleration factor (informational)")
    args = parser.parse_args()

    engine = SimulationEngine(seed=args.seed)
    ticks_per_hour = 60
    total_ticks = int(args.hours * ticks_per_hour)

    print(f"Running {args.hours}h simulation (seed={args.seed}, {total_ticks} ticks)...")
    for i in range(total_ticks):
        events = engine.tick()
        if events and i % 60 == 0:
            print(f"  tick {engine.world.tick}: {len(events)} events")

    print(f"Done. {len(engine.world.events_log)} total events, {len(engine.drama_scores)} drama scores.")
    for score in engine.drama_scores[:5]:
        print(f"  {score.storyline_id}: {score.score:.2f} [{', '.join(score.factors)}]")


if __name__ == "__main__":
    main()
