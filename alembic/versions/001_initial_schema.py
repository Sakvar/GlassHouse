"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "world_events",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(64), nullable=True),
        sa.Column("target", sa.String(64), nullable=True),
        sa.Column("location", sa.String(64), nullable=False),
        sa.Column(
            "payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.Column(
            "witnesses", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_events_run_id", "world_events", ["run_id"])
    op.create_index("ix_world_events_tick", "world_events", ["tick"])

    op.create_table(
        "claims",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("holder_id", sa.String(64), nullable=True),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("predicate", sa.String(64), nullable=False),
        sa.Column("object", sa.String(64), nullable=True),
        sa.Column("data", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("state", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "episodic_memories",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "event_ids", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.Column(
            "claim_ids", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.Column("subject", sa.String(64), nullable=True),
        sa.Column("predicate", sa.String(64), nullable=True),
        sa.Column("salience", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "semantic_memories",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("predicate", sa.String(64), nullable=False),
        sa.Column("generalization", sa.Text(), nullable=False),
        sa.Column(
            "claim_ids", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # The prototype stores float arrays; no vector extension is required.

    op.create_table(
        "semantic_memory_embeddings",
        sa.Column("memory_id", sa.String(64), nullable=False),
        sa.Column(
            "embedding",
            sa.JSON().with_variant(postgresql.ARRAY(sa.Float()), "postgresql"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("memory_id"),
    )

    op.create_table(
        "scenes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(64), nullable=False),
        sa.Column(
            "participants", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "drama_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("storyline_id", sa.String(128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("data", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("schema_name", sa.String(64), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column(
            "predicates", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True
        ),
        sa.Column("prompt_hash", sa.String(32), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("llm_call_log")
    op.drop_table("drama_scores")
    op.drop_table("scenes")
    op.drop_table("semantic_memory_embeddings")
    op.drop_table("semantic_memories")
    op.drop_table("episodic_memories")
    op.drop_table("agent_states")
    op.drop_table("claims")
    op.drop_table("world_events")
    op.drop_table("simulation_runs")
