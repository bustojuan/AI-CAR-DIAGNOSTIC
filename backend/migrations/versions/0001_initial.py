"""Initial operational and future RAG storage schema.

Revision ID: 0001_initial
Revises: None
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.core.config import Settings

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    settings = op.get_context().config.attributes.get("settings") or Settings()
    dimensions = settings.embedding_dimensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")

    op.create_table(
        "technical_documents",
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_name", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("manufacturer", sa.String(length=200), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("model_year_start", sa.Integer(), nullable=True),
        sa.Column("model_year_end", sa.Integer(), nullable=True),
        sa.Column("engine", sa.String(length=200), nullable=True),
        sa.Column("engine_code", sa.String(length=200), nullable=True),
        sa.Column("transmission", sa.String(length=200), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("license_status", sa.String(length=20), server_default="unknown", nullable=False),
        sa.Column(
            "verification_status", sa.String(length=20), server_default="unverified", nullable=False
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column(
            "ingestion_status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_technical_documents_hash_format")
        ),
        sa.CheckConstraint(
            "document_type IN ('pdf','markdown','txt','html')",
            name=op.f("ck_technical_documents_document_type"),
        ),
        sa.CheckConstraint(
            "evidence_type IN ('official_manufacturer','third_party_technical','generic_reference','internal_demo')",
            name=op.f("ck_technical_documents_evidence_type"),
        ),
        sa.CheckConstraint(
            "evidence_type NOT IN ('generic_reference','internal_demo') OR (manufacturer IS NULL AND model IS NULL AND engine IS NULL AND engine_code IS NULL AND model_year_start IS NULL AND model_year_end IS NULL AND transmission IS NULL)",
            name=op.f("ck_technical_documents_generic_scope"),
        ),
        sa.CheckConstraint(
            "ingestion_status IN ('pending','processed','failed')",
            name=op.f("ck_technical_documents_ingestion"),
        ),
        sa.CheckConstraint(
            "license_status IN ('unknown','authorized','restricted')",
            name=op.f("ck_technical_documents_license"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('unverified','verified','rejected')",
            name=op.f("ck_technical_documents_verification"),
        ),
        sa.CheckConstraint(
            "model_year_end IS NULL OR model_year_end BETWEEN 1886 AND 2100",
            name=op.f("ck_technical_documents_end_year"),
        ),
        sa.CheckConstraint(
            "model_year_start IS NULL OR model_year_end IS NULL OR model_year_start <= model_year_end",
            name=op.f("ck_technical_documents_year_range"),
        ),
        sa.CheckConstraint(
            "model_year_start IS NULL OR model_year_start BETWEEN 1886 AND 2100",
            name=op.f("ck_technical_documents_start_year"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_technical_documents")),
        sa.UniqueConstraint("content_hash", name=op.f("uq_technical_documents_content_hash")),
    )
    op.create_index(
        op.f("ix_technical_documents_manufacturer"),
        "technical_documents",
        ["manufacturer"],
        unique=False,
    )
    op.create_table(
        "vehicles",
        sa.Column("manufacturer", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("model_year", sa.Integer(), nullable=False),
        sa.Column("engine", sa.String(length=200), nullable=False),
        sa.Column("engine_code", sa.String(length=200), nullable=True),
        sa.Column("fuel_type", sa.String(length=200), nullable=False),
        sa.Column("transmission", sa.String(length=200), nullable=False),
        sa.Column("power_output", sa.String(length=200), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(length=17), nullable=True),
        sa.Column("additional_information", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "vin IS NULL OR vin ~ '^[A-HJ-NPR-Z0-9]{17}$'", name=op.f("ck_vehicles_vin_format")
        ),
        sa.CheckConstraint(
            "mileage_km IS NULL OR mileage_km BETWEEN 0 AND 3000000",
            name=op.f("ck_vehicles_mileage"),
        ),
        sa.CheckConstraint("model_year BETWEEN 1886 AND 2100", name=op.f("ck_vehicles_year_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
    )
    op.create_table(
        "conversations",
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active','completed','cancelled')", name=op.f("ck_conversations_status")
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name=op.f("fk_conversations_vehicle_id_vehicles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
        sa.UniqueConstraint("id", "vehicle_id", name="uq_conversations_id_vehicle"),
    )
    op.create_index(
        op.f("ix_conversations_vehicle_id"), "conversations", ["vehicle_id"], unique=False
    )
    op.create_table(
        "document_chunks",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("section", sa.String(length=500), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(dimensions), nullable=True),
        sa.Column("embedding_model", sa.String(length=200), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_document_chunks_hash_format")
        ),
        sa.CheckConstraint(
            "(embedding IS NULL AND embedding_model IS NULL AND embedding_dimensions IS NULL) OR (embedding IS NOT NULL AND embedding_model IS NOT NULL AND length(embedding_model) > 0 AND embedding_dimensions IS NOT NULL AND embedding_dimensions > 0 AND vector_dims(embedding) = embedding_dimensions)",
            name=op.f("ck_document_chunks_embedding_metadata"),
        ),
        sa.CheckConstraint("chunk_index >= 0", name=op.f("ck_document_chunks_chunk_index")),
        sa.CheckConstraint("length(content) > 0", name=op.f("ck_document_chunks_nonempty_content")),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 1", name=op.f("ck_document_chunks_page_number")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["technical_documents.id"],
            name=op.f("fk_document_chunks_document_id_technical_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
    )
    op.create_table(
        "diagnostics",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("urgency_level", sa.String(length=20), nullable=False),
        sa.Column("driving_recommendation", sa.String(length=40), nullable=False),
        sa.Column("professional_assistance_recommended", sa.Boolean(), nullable=False),
        sa.Column("extracted_symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("follow_up_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("next_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("rag_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("mcp_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("generation_mode", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "driving_recommendation IN ('stop_safely_do_not_drive','inspection_before_driving','caution_and_monitor')",
            name=op.f("ck_diagnostics_driving"),
        ),
        sa.CheckConstraint(
            "generation_mode IN ('llm','deterministic_safety')",
            name=op.f("ck_diagnostics_generation_mode"),
        ),
        sa.CheckConstraint(
            "urgency_level != 'critical' OR (driving_recommendation = 'stop_safely_do_not_drive' AND professional_assistance_recommended)",
            name=op.f("ck_diagnostics_critical_safety"),
        ),
        sa.CheckConstraint(
            "urgency_level != 'high' OR (driving_recommendation != 'caution_and_monitor' AND professional_assistance_recommended)",
            name=op.f("ck_diagnostics_high_safety"),
        ),
        sa.CheckConstraint(
            "urgency_level IN ('low','moderate','high','critical')",
            name=op.f("ck_diagnostics_urgency"),
        ),
        sa.CheckConstraint("turn_index >= 0", name=op.f("ck_diagnostics_turn_index")),
        sa.ForeignKeyConstraint(
            ["conversation_id", "vehicle_id"],
            ["conversations.id", "conversations.vehicle_id"],
            name=op.f("fk_diagnostics_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostics")),
        sa.UniqueConstraint(
            "conversation_id", "turn_index", name="uq_diagnostics_conversation_turn"
        ),
    )
    op.create_index("ix_diagnostics_vehicle_id", "diagnostics", ["vehicle_id"], unique=False)
    op.create_table(
        "messages",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant')", name=op.f("ck_messages_role")),
        sa.CheckConstraint(
            "length(content) BETWEEN 1 AND 100000", name=op.f("ck_messages_content_length")
        ),
        sa.CheckConstraint("position >= 0", name=op.f("ck_messages_position")),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_messages_conversation_id_conversations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
        sa.UniqueConstraint(
            "conversation_id", "position", name="uq_messages_conversation_position"
        ),
    )
    op.create_table(
        "diagnostic_hypotheses",
        sa.Column("diagnostic_id", sa.Uuid(), nullable=False),
        sa.Column("component_or_system", sa.String(length=200), nullable=False),
        sa.Column("possible_failure", sa.Text(), nullable=False),
        sa.Column("supporting_symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "missing_or_contradictory_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("recommended_verification", sa.Text(), nullable=False),
        sa.Column("professional_inspection_required", sa.Boolean(), nullable=False),
        sa.Column("uncertainty", sa.String(length=30), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "uncertainty IN ('possible','uncertain','insufficient_evidence')",
            name=op.f("ck_diagnostic_hypotheses_uncertainty"),
        ),
        sa.CheckConstraint(
            "display_order >= 0", name=op.f("ck_diagnostic_hypotheses_display_order")
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_id"],
            ["diagnostics.id"],
            name=op.f("fk_diagnostic_hypotheses_diagnostic_id_diagnostics"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_hypotheses")),
        sa.UniqueConstraint(
            "diagnostic_id", "display_order", name="uq_hypotheses_diagnostic_order"
        ),
    )

    op.execute("""
        CREATE FUNCTION enforce_conversation_status() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status IS DISTINCT FROM NEW.status AND
               (OLD.status <> 'active' OR NEW.status NOT IN ('completed','cancelled')) THEN
                RAISE EXCEPTION 'Invalid conversation status transition' USING ERRCODE='23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER conversation_status_transition BEFORE UPDATE OF status ON conversations "
        "FOR EACH ROW EXECUTE FUNCTION enforce_conversation_status()"
    )


def downgrade():
    # Destructive: explicit downgrade removes application tables. Keeps shared extension.

    op.drop_table("diagnostic_hypotheses")
    op.drop_table("messages")
    op.drop_table("diagnostics")
    op.drop_table("document_chunks")
    op.drop_table("conversations")
    op.execute("DROP FUNCTION enforce_conversation_status()")
    op.drop_table("vehicles")
    op.drop_table("technical_documents")
