"""Track user-reported resolution without changing historical assessments."""

import sqlalchemy as sa
from alembic import op

revision = "0005_resolution"
down_revision = "0004_urgency"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversations",
        sa.Column("resolution_status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "conversations", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("conversations", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.create_check_constraint(
        "resolution_status", "conversations", "resolution_status IN ('active','resolved')"
    )
    op.create_check_constraint(
        "resolution_consistency",
        "conversations",
        "(resolution_status = 'resolved' AND resolved_at IS NOT NULL) OR (resolution_status = 'active' AND resolved_at IS NULL AND resolution_note IS NULL)",
    )
    op.create_check_constraint(
        "resolution_note_length",
        "conversations",
        "resolution_note IS NULL OR length(resolution_note) <= 1000",
    )


def downgrade():
    for name in ("resolution_note_length", "resolution_consistency", "resolution_status"):
        op.drop_constraint(op.f("ck_conversations_" + name), "conversations", type_="check")
    for name in ("resolution_note", "resolved_at", "resolution_status"):
        op.drop_column("conversations", name)
