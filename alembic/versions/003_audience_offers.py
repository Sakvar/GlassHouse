"""Audience offers with shared influence budgets and idempotent submissions."""

import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "viewer_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("goal_id", sa.String(length=200), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("points >= 1 AND points <= 3"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "user_id", "request_id"),
    )
    op.create_index(
        "ix_offers_user_tick",
        "viewer_offers",
        ["season_id", "user_id", "tick"],
        unique=False,
    )
    op.create_index(
        "ix_offers_goal_tick",
        "viewer_offers",
        ["season_id", "goal_id", "tick"],
        unique=False,
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_viewer_offer_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'viewer_offers is append-only'; END; $$""")
        op.execute("""CREATE TRIGGER viewer_offers_immutable BEFORE UPDATE OR DELETE
        ON viewer_offers FOR EACH ROW EXECUTE FUNCTION reject_viewer_offer_mutation()""")
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER viewer_offers_no_{action.lower()} BEFORE {action}
            ON viewer_offers BEGIN SELECT RAISE(ABORT, 'viewer_offers is append-only'); END""")


def downgrade():
    op.drop_index("ix_offers_goal_tick", table_name="viewer_offers")
    op.drop_index("ix_offers_user_tick", table_name="viewer_offers")
    op.drop_table("viewer_offers")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_viewer_offer_mutation()")
