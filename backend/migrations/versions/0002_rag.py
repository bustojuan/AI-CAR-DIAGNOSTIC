"""Persist validated citations, extraction failures and explicit source-link permission."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_rag"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "diagnostics", sa.Column("citations", JSONB(), nullable=False, server_default="[]")
    )
    op.add_column(
        "technical_documents",
        sa.Column("public_source_url", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("technical_documents", sa.Column("extraction_error", sa.String(100)))


def downgrade():
    op.drop_column("technical_documents", "extraction_error")
    op.drop_column("technical_documents", "public_source_url")
    op.drop_column("diagnostics", "citations")
