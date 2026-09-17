#!/usr/bin/env python3
"""Run accelerated simulation."""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from glasshouse.simulation.engine import SimulationEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Glasshouse simulation")
    parser.add_argument("--hours", type=float, default=48)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--speed", type=float, default=1000, help="Acceleration factor (informational)"
    )
    parser.add_argument("--tick-minutes", type=int, default=120)
    args = parser.parse_args()
    if not math.isfinite(args.hours) or args.hours < 0:
        parser.error("--hours must be finite and non-negative")

    engine = SimulationEngine(seed=args.seed, tick_minutes=args.tick_minutes)
    total_ticks = math.ceil(args.hours * 60 / args.tick_minutes)
    print(f"Вилла: {args.hours} ч., seed={args.seed}, тиков: {total_ticks}")
    for _ in range(total_ticks):
        engine.tick()
        recap = engine.show.recaps[-1]
        print(f"\n[{recap.sim_time}] Тик {recap.tick}")
        for text in recap.what_happened:
            print(f"  {text}")
        print(f"  {recap.why_it_matters}")
        for change in recap.relationship_changes:
            print(
                f"  {change.actor_id} → {change.target_id}: {change.dimension} "
                f"{change.before:g} → {change.after:g}"
            )
    print("\nСледующий выбор:")
    for goal in engine.show.active_goals():
        print(f"  {goal.id}: {goal.title} ({', '.join(goal.eligible_characters)})")


if __name__ == "__main__":
    main()
