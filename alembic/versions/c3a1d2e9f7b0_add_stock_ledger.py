"""Add stock_on_hand to product_variants and inventory_ledger table

Adds `stock_on_hand` (INTEGER, NOT NULL DEFAULT 0) to `product_variants` so
the ORM catalogue can track trackable stock, and creates the
`inventory_ledger` audit-of-record style ledger: one row per applied stock
movement, keyed by a unique `source_key` (e.g. `ingestion:{id}:{line}`) for
idempotency.

Revision ID: c3a1d2e9f7b0
Revises: beed12e124c9
Create Date: 2026-11-15 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3a1d2e9f7b0"
down_revision: str | Sequence[str] | None = "beed12e124c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_variants",
        sa.Column("stock_on_hand", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "inventory_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "variant_id",
            sa.Integer(),
            sa.ForeignKey("product_variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_key", name="uq_inventory_ledger_source_key"),
    )
    op.create_index("ix_inventory_ledger_variant_id", "inventory_ledger", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_ledger_variant_id", table_name="inventory_ledger")
    op.drop_table("inventory_ledger")
    op.drop_column("product_variants", "stock_on_hand")
