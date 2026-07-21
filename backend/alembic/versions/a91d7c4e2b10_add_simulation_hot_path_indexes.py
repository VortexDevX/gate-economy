"""add simulation hot-path indexes

Revision ID: a91d7c4e2b10
Revises: 6f2b3df2a9f1
Create Date: 2026-07-18 05:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a91d7c4e2b10"
down_revision: str | None = "6f2b3df2a9f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Production tables already contain substantial history. PostgreSQL
    # concurrent builds avoid blocking the simulation's write transaction.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_orders_open_book",
            "orders",
            [
                "asset_type",
                "asset_id",
                "side",
                "price_limit_micro",
                "created_at_tick",
                "id",
            ],
            if_not_exists=True,
            postgresql_where=sa.text("status IN ('OPEN', 'PARTIAL')"),
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_orders_player_open_asset",
            "orders",
            ["player_id", "asset_type", "asset_id"],
            if_not_exists=True,
            postgresql_where=sa.text("status IN ('OPEN', 'PARTIAL')"),
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_orders_open_state",
            "orders",
            ["asset_type", "asset_id", "id"],
            if_not_exists=True,
            postgresql_where=sa.text("status IN ('OPEN', 'PARTIAL')"),
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_trades_asset_recent",
            "trades",
            ["asset_type", "asset_id", "created_at", "id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_trades_tick_asset",
            "trades",
            ["tick_id", "asset_type", "asset_id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_intents_queued_created",
            "intents",
            ["created_at", "id"],
            if_not_exists=True,
            postgresql_where=sa.text("status = 'QUEUED'"),
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_ledger_debit_recent",
            "ledger_entries",
            ["debit_type", "debit_id", "id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_ledger_credit_recent",
            "ledger_entries",
            ["credit_type", "credit_id", "id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_ledger_tick",
            "ledger_entries",
            ["tick_id", "id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_gates_status_id",
            "gates",
            ["status", "id"],
            if_not_exists=True,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for index_name, table_name in (
            ("ix_gates_status_id", "gates"),
            ("ix_ledger_tick", "ledger_entries"),
            ("ix_ledger_credit_recent", "ledger_entries"),
            ("ix_ledger_debit_recent", "ledger_entries"),
            ("ix_intents_queued_created", "intents"),
            ("ix_trades_tick_asset", "trades"),
            ("ix_trades_asset_recent", "trades"),
            ("ix_orders_open_state", "orders"),
            ("ix_orders_player_open_asset", "orders"),
            ("ix_orders_open_book", "orders"),
        ):
            op.drop_index(
                index_name,
                table_name=table_name,
                if_exists=True,
                postgresql_concurrently=True,
            )
