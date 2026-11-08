from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class Identity:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VehicleRow(Identity, Timestamps, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("model_year BETWEEN 1886 AND 2100", name="year_range"),
        CheckConstraint("mileage_km IS NULL OR mileage_km BETWEEN 0 AND 3000000", name="mileage"),
        CheckConstraint("vin IS NULL OR vin ~ '^[A-HJ-NPR-Z0-9]{17}$'", name="vin_format"),
    )
    manufacturer: Mapped[str] = mapped_column(String(200))
    model: Mapped[str] = mapped_column(String(200))
    model_year: Mapped[int] = mapped_column(Integer)
    engine: Mapped[str] = mapped_column(String(200))
    engine_code: Mapped[str | None] = mapped_column(String(200))
    fuel_type: Mapped[str] = mapped_column(String(200))
    transmission: Mapped[str] = mapped_column(String(200))
    power_output: Mapped[str | None] = mapped_column(String(200))
    mileage_km: Mapped[int | None] = mapped_column(Integer)
    vin: Mapped[str | None] = mapped_column(String(17))
    additional_information: Mapped[str | None] = mapped_column(Text)
    conversations: Mapped[list[ConversationRow]] = relationship(
        back_populates="vehicle", passive_deletes="all", lazy="raise"
    )


class ConversationRow(Identity, Timestamps, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('active','completed','cancelled')", name="status"),
        CheckConstraint("resolution_status IN ('active','resolved')", name="resolution_status"),
        CheckConstraint(
            "(resolution_status = 'resolved' AND resolved_at IS NOT NULL) OR "
            "(resolution_status = 'active' AND resolved_at IS NULL AND resolution_note IS NULL)",
            name="resolution_consistency",
        ),
        CheckConstraint(
            "resolution_note IS NULL OR length(resolution_note) <= 1000",
            name="resolution_note_length",
        ),
        UniqueConstraint("id", "vehicle_id", name="uq_conversations_id_vehicle"),
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    resolution_status: Mapped[str] = mapped_column(String(20), server_default="active")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vehicle: Mapped[VehicleRow] = relationship(back_populates="conversations", lazy="raise")
    messages: Mapped[list[MessageRow]] = relationship(
        back_populates="conversation",
        order_by="MessageRow.position",
        lazy="raise",
        passive_deletes="all",
    )
    diagnostics: Mapped[list[DiagnosticRow]] = relationship(
        back_populates="conversation",
        order_by="DiagnosticRow.turn_index",
        lazy="raise",
        passive_deletes="all",
    )


class MessageRow(Identity, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="role"),
        CheckConstraint("position >= 0", name="position"),
        CheckConstraint("length(content) BETWEEN 1 AND 100000", name="content_length"),
        UniqueConstraint("conversation_id", "position", name="uq_messages_conversation_position"),
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT")
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    conversation: Mapped[ConversationRow] = relationship(back_populates="messages", lazy="raise")


class DiagnosticRow(Identity, Timestamps, Base):
    __tablename__ = "diagnostics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "vehicle_id"],
            ["conversations.id", "conversations.vehicle_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("conversation_id", "turn_index", name="uq_diagnostics_conversation_turn"),
        CheckConstraint("turn_index >= 0", name="turn_index"),
        CheckConstraint("urgency_level IN ('low','moderate','high','critical')", name="urgency"),
        CheckConstraint(
            "driving_recommendation IN ('stop_safely_do_not_drive',"
            "'inspection_before_driving','caution_and_monitor')",
            name="driving",
        ),
        CheckConstraint(
            "generation_mode IN ('llm','deterministic_safety')", name="generation_mode"
        ),
        CheckConstraint(
            "urgency_level != 'critical' OR "
            "(driving_recommendation = 'stop_safely_do_not_drive' "
            "AND professional_assistance_recommended)",
            name="critical_safety",
        ),
        CheckConstraint(
            "urgency_level != 'high' OR "
            "(driving_recommendation != 'caution_and_monitor' "
            "AND professional_assistance_recommended)",
            name="high_safety",
        ),
        Index("ix_diagnostics_vehicle_id", "vehicle_id"),
    )
    conversation_id: Mapped[UUID] = mapped_column(Uuid)
    vehicle_id: Mapped[UUID] = mapped_column(Uuid)
    turn_index: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    urgency_level: Mapped[str] = mapped_column(String(20))
    urgency_assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    driving_recommendation: Mapped[str] = mapped_column(String(40))
    professional_assistance_recommended: Mapped[bool] = mapped_column(Boolean)
    extracted_symptoms: Mapped[list] = mapped_column(JSONB)
    recommended_checks: Mapped[list] = mapped_column(JSONB)
    follow_up_questions: Mapped[list] = mapped_column(JSONB)
    evidence_sources: Mapped[list] = mapped_column(JSONB)
    citations: Mapped[list] = mapped_column(JSONB, server_default="[]")
    tool_results: Mapped[list] = mapped_column(JSONB, server_default="[]")
    limitations: Mapped[list] = mapped_column(JSONB)
    next_steps: Mapped[list] = mapped_column(JSONB)
    model_name: Mapped[str | None] = mapped_column(String(200))
    rag_available: Mapped[bool] = mapped_column(Boolean, server_default="false")
    mcp_available: Mapped[bool] = mapped_column(Boolean, server_default="false")
    generation_mode: Mapped[str] = mapped_column(String(30))
    conversation: Mapped[ConversationRow] = relationship(back_populates="diagnostics", lazy="raise")
    hypotheses: Mapped[list[HypothesisRow]] = relationship(
        back_populates="diagnostic",
        order_by="HypothesisRow.display_order",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class HypothesisRow(Identity, Base):
    __tablename__ = "diagnostic_hypotheses"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="display_order"),
        CheckConstraint(
            "uncertainty IN ('possible','uncertain','insufficient_evidence')", name="uncertainty"
        ),
        UniqueConstraint("diagnostic_id", "display_order", name="uq_hypotheses_diagnostic_order"),
    )
    diagnostic_id: Mapped[UUID] = mapped_column(ForeignKey("diagnostics.id", ondelete="CASCADE"))
    component_or_system: Mapped[str] = mapped_column(String(200))
    possible_failure: Mapped[str] = mapped_column(Text)
    supporting_symptoms: Mapped[list] = mapped_column(JSONB)
    missing_or_contradictory_evidence: Mapped[list] = mapped_column(JSONB)
    recommended_verification: Mapped[str] = mapped_column(Text)
    professional_inspection_required: Mapped[bool] = mapped_column(Boolean)
    uncertainty: Mapped[str] = mapped_column(String(30))
    display_order: Mapped[int] = mapped_column(Integer)
    diagnostic: Mapped[DiagnosticRow] = relationship(back_populates="hypotheses", lazy="raise")


class TechnicalDocumentRow(Identity, Timestamps, Base):
    __tablename__ = "technical_documents"
    __table_args__ = (
        CheckConstraint("document_type IN ('pdf','markdown','txt','html')", name="document_type"),
        CheckConstraint(
            "evidence_type IN ('official_manufacturer','third_party_technical',"
            "'generic_reference','internal_demo')",
            name="evidence_type",
        ),
        CheckConstraint("license_status IN ('unknown','authorized','restricted')", name="license"),
        CheckConstraint(
            "verification_status IN ('unverified','verified','rejected')", name="verification"
        ),
        CheckConstraint("ingestion_status IN ('pending','processed','failed')", name="ingestion"),
        CheckConstraint(
            "model_year_start IS NULL OR model_year_start BETWEEN 1886 AND 2100", name="start_year"
        ),
        CheckConstraint(
            "model_year_end IS NULL OR model_year_end BETWEEN 1886 AND 2100", name="end_year"
        ),
        CheckConstraint(
            "model_year_start IS NULL OR model_year_end IS NULL "
            "OR model_year_start <= model_year_end",
            name="year_range",
        ),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash_format"),
        CheckConstraint(
            "evidence_type NOT IN ('generic_reference','internal_demo') OR "
            "(manufacturer IS NULL AND model IS NULL AND engine IS NULL "
            "AND engine_code IS NULL AND model_year_start IS NULL "
            "AND model_year_end IS NULL AND transmission IS NULL)",
            name="generic_scope",
        ),
    )
    title: Mapped[str] = mapped_column(String(500))
    source_name: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(300))
    document_type: Mapped[str] = mapped_column(String(20))
    evidence_type: Mapped[str] = mapped_column(String(40))
    manufacturer: Mapped[str | None] = mapped_column(String(200), index=True)
    model: Mapped[str | None] = mapped_column(String(200))
    model_year_start: Mapped[int | None] = mapped_column(Integer)
    model_year_end: Mapped[int | None] = mapped_column(Integer)
    engine: Mapped[str | None] = mapped_column(String(200))
    engine_code: Mapped[str | None] = mapped_column(String(200))
    transmission: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10))
    license_status: Mapped[str] = mapped_column(String(20), server_default="unknown")
    verification_status: Mapped[str] = mapped_column(String(20), server_default="unverified")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    storage_path: Mapped[str | None] = mapped_column(Text)
    ingestion_status: Mapped[str] = mapped_column(String(20), server_default="pending")
    public_source_url: Mapped[bool] = mapped_column(Boolean, server_default="false")
    extraction_error: Mapped[str | None] = mapped_column(String(100))
    chunks: Mapped[list[DocumentChunkRow]] = relationship(
        back_populates="document",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# Initial Alembic revision takes EMBEDDING_DIMENSIONS (default 1536) at migration time.
# ORM vector has no typmod so an intentional alternative dimension can be mapped;
# the migrated PostgreSQL vector(N) column and checks remain authoritative.
class DocumentChunkRow(Identity, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
        CheckConstraint("chunk_index >= 0", name="chunk_index"),
        CheckConstraint("page_number IS NULL OR page_number >= 1", name="page_number"),
        CheckConstraint("length(content) > 0", name="nonempty_content"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash_format"),
        CheckConstraint(
            "(embedding IS NULL AND embedding_model IS NULL AND embedding_dimensions IS NULL)"
            " OR (embedding IS NOT NULL AND embedding_model IS NOT NULL "
            "AND length(embedding_model) > 0 AND embedding_dimensions IS NOT NULL "
            "AND embedding_dimensions > 0 "
            "AND vector_dims(embedding) = embedding_dimensions)",
            name="embedding_metadata",
        ),
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("technical_documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(String(500))
    page_number: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    document: Mapped[TechnicalDocumentRow] = relationship(back_populates="chunks", lazy="raise")
