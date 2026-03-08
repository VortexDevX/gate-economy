"""phase_8_10_canonical_alignment

Revision ID: 6f2b3df2a9f1
Revises: 2e9f2d2c75d9
Create Date: 2026-03-08 23:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6f2b3df2a9f1"
down_revision: Union[str, None] = "2e9f2d2c75d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_enum_value(enum_name: str, value: str) -> None:
    escaped = value.replace("'", "''")
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{escaped}'")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── Phase 8 alignment: taxonomy and canonical table name ──
    _add_enum_value("newscategory", "EVENT")
    _add_enum_value("newscategory", "LEADERBOARD")

    tables = set(inspector.get_table_names())
    if "news" in tables and "news_items" not in tables:
        op.rename_table("news", "news_items")

    for value in (
        "MANA_SURGE",
        "INSTABILITY_WAVE",
        "ECONOMIC_BOOM",
        "REGULATION_CRACKDOWN",
        "GATE_RESONANCE",
        "MARKET_PANIC",
        "TREASURE_DISCOVERY",
        "MANA_DROUGHT",
    ):
        _add_enum_value("eventtype", value)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'eventseverity') THEN
                CREATE TYPE eventseverity AS ENUM ('MINOR','MODERATE','MAJOR','CATASTROPHIC');
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'eventtargettype') THEN
                CREATE TYPE eventtargettype AS ENUM ('GLOBAL','GATE','GUILD','MARKET');
            END IF;
        END$$;
        """
    )

    event_cols = {c["name"] for c in inspector.get_columns("events")}
    if "severity" not in event_cols:
        op.add_column(
            "events",
            sa.Column(
                "severity",
                postgresql.ENUM(
                    "MINOR",
                    "MODERATE",
                    "MAJOR",
                    "CATASTROPHIC",
                    name="eventseverity",
                    create_type=False,
                ),
                nullable=False,
                server_default="MINOR",
            ),
        )
    if "target_type" not in event_cols:
        op.add_column(
            "events",
            sa.Column(
                "target_type",
                postgresql.ENUM(
                    "GLOBAL",
                    "GATE",
                    "GUILD",
                    "MARKET",
                    name="eventtargettype",
                    create_type=False,
                ),
                nullable=True,
            ),
        )
    if "effects" not in event_cols:
        op.add_column(
            "events",
            sa.Column("effects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if "duration_ticks" not in event_cols:
        op.add_column("events", sa.Column("duration_ticks", sa.Integer(), nullable=True))
    if "expires_at_tick" not in event_cols:
        op.add_column(
            "events", sa.Column("expires_at_tick", sa.Integer(), nullable=True)
        )

    op.execute(text("ALTER TABLE events ALTER COLUMN severity DROP DEFAULT"))

    # ── Phase 10 alignment: canonical leaderboard table name ──
    tables = set(inspector.get_table_names())
    if "player_net_worth" in tables and "leaderboard_entries" not in tables:
        op.rename_table("player_net_worth", "leaderboard_entries")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "leaderboard_entries" in tables and "player_net_worth" not in tables:
        op.rename_table("leaderboard_entries", "player_net_worth")

    if "news_items" in tables and "news" not in tables:
        op.rename_table("news_items", "news")
