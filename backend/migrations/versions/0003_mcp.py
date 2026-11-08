"""Persist application-validated MCP provenance and structured tool results."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_mcp"
down_revision = "0002_rag"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "diagnostics", sa.Column("tool_results", JSONB(), nullable=False, server_default="[]")
    )


def downgrade():
    op.drop_column("diagnostics", "tool_results")
