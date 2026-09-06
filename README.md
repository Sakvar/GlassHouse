# GlassHouse

Headless Social Simulator (Stage 0 prototype).

## Quick start

```bash
# Start PostgreSQL + pgvector
docker compose up -d

# Install
pip install -e ".[dev]"

# Run tests (CI-safe, uses ScriptedStubLLM)
pytest tests/ -m "not evaluation"

# Run 48h accelerated simulation
python scripts/run_simulation.py --hours 48 --seed 42

# Inspect agent state
python scripts/inspect_agent.py --agent Max --show beliefs,claims,relationships

# Event timeline
python scripts/timeline.py --last 2h --filter gossip

# Debug API
uvicorn apps.api.main:app --reload
```

## Architecture

- **World Truth** → deterministic perception → **Knowledge** → structured **Claims** (with provenance) → **Beliefs**
- LLM returns typed intents/appraisals only; simulation core validates and applies mutations
- Event log is immutable; summaries and memories are derived data
- Cognition is sequential and event-driven in Stage 0

## Evaluation (optional, requires API key)

```bash
pytest tests/ -m evaluation
```
