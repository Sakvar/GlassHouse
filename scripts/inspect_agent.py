#!/usr/bin/env python3
"""Inspect agent state."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from glasshouse.agents.seeds import create_seed_agents


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect agent state")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--show", default="beliefs,claims,memory,relationships")
    args = parser.parse_args()

    agents = create_seed_agents()
    agent_id = args.agent.lower()
    if agent_id not in agents:
        print(f"Unknown agent: {args.agent}")
        sys.exit(1)

    agent = agents[agent_id]
    sections = [s.strip() for s in args.show.split(",")]

    if "beliefs" in sections:
        print("=== Beliefs ===")
        for b in agent.beliefs.entries.values():
            print(f"  {b.subject}:{b.predicate.value} conf={b.confidence:.2f}")

    if "claims" in sections:
        print("=== Claims ===")
        for c in agent.claims.entries.values():
            prov = f" (from {c.provenance.source_claim_id})" if c.provenance else ""
            print(f"  {c.subject}:{c.predicate.value}{prov}")

    if "relationships" in sections:
        print("=== Relationships ===")
        for other_id, rel in agent.relationships.items():
            print(f"  {other_id}: trust={rel.trust:.0f} attraction={rel.attraction:.0f}")

    if "memory" in sections:
        print("=== Memory ===")
        print(f"  working: {len(agent.memory.working)} items")
        print(f"  episodic: {len(agent.memory.episodic)} items")


if __name__ == "__main__":
    main()
