"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lei_records",
        sa.Column("lei", sa.String(20), primary_key=True),
        sa.Column("legal_name", sa.Text),
        sa.Column("jurisdiction", sa.String(10)),
        sa.Column("entity_status", sa.String(30)),
        sa.Column("entity_category", sa.String(30)),
        sa.Column("managing_lou", sa.String(20)),
        sa.Column("registration_status", sa.String(30)),
        sa.Column("initial_registration_date", sa.Date),
        sa.Column("last_update_date", sa.Date),
        sa.Column("next_renewal_date", sa.Date),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_lei_records_managing_lou", "lei_records", ["managing_lou"])
    op.create_index("ix_lei_records_jurisdiction", "lei_records", ["jurisdiction"])
    op.create_index("ix_lei_records_entity_status", "lei_records", ["entity_status"])
    op.create_index(
        "ix_lei_records_initial_registration_date",
        "lei_records",
        ["initial_registration_date"],
    )

    op.create_table(
        "lous",
        sa.Column("lou_lei", sa.String(20), primary_key=True),
        sa.Column("lou_name", sa.Text),
        sa.Column("country", sa.String(5)),
        sa.Column("website", sa.Text),
        sa.Column("status", sa.String(30)),
    )

    op.create_table(
        "pipeline_watermark",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("file_name", sa.Text, unique=True, nullable=False),
        sa.Column("applied_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("record_count", sa.Integer),
    )


def downgrade() -> None:
    op.drop_table("pipeline_watermark")
    op.drop_table("lous")
    op.drop_table("lei_records")
