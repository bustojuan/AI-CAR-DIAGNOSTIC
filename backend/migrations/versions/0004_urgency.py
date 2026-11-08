"""Preserve explainable urgency triage; historical assessments remain null."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_urgency"
down_revision = "0003_mcp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("diagnostics", sa.Column("urgency_assessment", JSONB(), nullable=True))


def downgrade():
    op.drop_column("diagnostics", "urgency_assessment")
