import logging
from contextlib import asynccontextmanager

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.exceptions import AppError
from app.database.models import (
    ConversationRow,
    DiagnosticRow,
    HypothesisRow,
    MessageRow,
    VehicleRow,
)
from app.database.session import inspect_database, make_engine, make_sessions
from app.mcp.retention import require_persistable_report
from app.models.case import URGENCY_RANK, CaseSummary
from app.models.common import utcnow
from app.models.conversation import Conversation, Message
from app.models.diagnostic import Diagnostic
from app.models.vehicle import Vehicle, seed_vehicle
from app.repositories.interfaces import Transaction

logger = logging.getLogger(__name__)


class PostgresVehicleRepository:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def public(row):
        return Vehicle(
            vehicle_id=row.id,
            **{key: getattr(row, key) for key in Vehicle.model_fields if key != "vehicle_id"},
        )

    async def list_vehicles(self):
        return [
            self.public(row)
            for row in await self.session.scalars(select(VehicleRow).order_by(VehicleRow.id))
        ]

    async def get_vehicle(self, vehicle_id, *, lock=False):
        query = select(VehicleRow).where(VehicleRow.id == vehicle_id)
        row = await self.session.scalar(query.with_for_update() if lock else query)
        return self.public(row) if row else None

    async def save_vehicle(self, vehicle):
        data = vehicle.model_dump(exclude={"vehicle_id"})
        statement = insert(VehicleRow).values(id=vehicle.vehicle_id, **data)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[VehicleRow.id], set_={**data, "updated_at": utcnow()}
            )
        )


class PostgresMessageRepository:
    def __init__(self, session):
        self.session = session

    async def append_messages(self, conversation_id, messages):
        existing = set(
            await self.session.scalars(
                select(MessageRow.id).where(MessageRow.conversation_id == conversation_id)
            )
        )
        for position, message in enumerate(messages):
            if message.message_id not in existing:
                self.session.add(
                    MessageRow(
                        id=message.message_id,
                        conversation_id=conversation_id,
                        position=position,
                        role=message.role,
                        content=message.content,
                        created_at=message.created_at,
                    )
                )
        await self.session.flush()


class PostgresConversationRepository:
    def __init__(self, session):
        self.session = session
        self.messages = PostgresMessageRepository(session)

    async def get_conversation(self, conversation_id, *, lock=False, allow_closed=False):
        query = (
            select(ConversationRow)
            .where(ConversationRow.id == conversation_id)
            .options(selectinload(ConversationRow.messages))
        )
        row = await self.session.scalar(query.with_for_update() if lock else query)
        if not row:
            return None
        if lock and not allow_closed and row.status != "active":
            raise AppError(409, "conversation_closed", "This conversation is no longer active.")
        report_ids = list(
            await self.session.scalars(
                select(DiagnosticRow.id)
                .where(DiagnosticRow.conversation_id == conversation_id)
                .order_by(DiagnosticRow.turn_index)
            )
        )
        return Conversation(
            conversation_id=row.id,
            vehicle_id=row.vehicle_id,
            created_at=row.created_at,
            resolution_status=row.resolution_status,
            resolved_at=row.resolved_at,
            resolution_note=row.resolution_note,
            messages=[
                Message(message_id=m.id, role=m.role, content=m.content, created_at=m.created_at)
                for m in row.messages
            ],
            diagnostic_ids=report_ids,
        )

    async def list_cases(self, vehicle_id):
        # One statement, no messages/evidence fetched and no per-case queries.
        partition = DiagnosticRow.conversation_id
        rank = case(
            *[
                (DiagnosticRow.urgency_level == level.value, value)
                for level, value in URGENCY_RANK.items()
            ],
            else_=0,
        )
        reports = (
            select(
                DiagnosticRow.conversation_id,
                DiagnosticRow.id.label("latest_diagnostic_id"),
                DiagnosticRow.created_at.label("latest_assessment_at"),
                DiagnosticRow.summary,
                func.max(rank).over(partition_by=partition).label("urgency_rank"),
                func.count().over(partition_by=partition).label("assessment_count"),
                func.row_number()
                .over(partition_by=partition, order_by=DiagnosticRow.turn_index.desc())
                .label("position"),
            )
            .where(DiagnosticRow.vehicle_id == vehicle_id)
            .subquery()
        )
        query = (
            select(ConversationRow, reports)
            .join(reports, reports.c.conversation_id == ConversationRow.id)
            .where(ConversationRow.vehicle_id == vehicle_id, reports.c.position == 1)
            .order_by(ConversationRow.created_at.desc(), ConversationRow.id.desc())
        )
        result = []
        for item in await self.session.execute(query):
            row = item[0]
            result.append(
                CaseSummary(
                    conversation_id=row.id,
                    vehicle_id=row.vehicle_id,
                    created_at=row.created_at,
                    resolution_status=row.resolution_status,
                    resolved_at=row.resolved_at,
                    resolution_note=row.resolution_note,
                    latest_diagnostic_id=item.latest_diagnostic_id,
                    latest_assessment_at=item.latest_assessment_at,
                    summary=item.summary,
                    assessment_count=item.assessment_count,
                    historical_urgency=next(
                        level for level, value in URGENCY_RANK.items() if value == item.urgency_rank
                    ),
                )
            )
        return result

    async def save_conversation(self, conversation):
        await self.session.execute(
            insert(ConversationRow)
            .values(
                id=conversation.conversation_id,
                vehicle_id=conversation.vehicle_id,
                created_at=conversation.created_at,
            )
            .on_conflict_do_nothing(index_elements=[ConversationRow.id])
        )
        await self.messages.append_messages(conversation.conversation_id, conversation.messages)
        row = await self.session.get(ConversationRow, conversation.conversation_id)
        row.last_message_at = (
            conversation.messages[-1].created_at if conversation.messages else None
        )
        row.resolution_status = conversation.resolution_status
        row.resolved_at = conversation.resolved_at
        row.resolution_note = conversation.resolution_note
        row.updated_at = utcnow()
        await self.session.flush()


class PostgresDiagnosticRepository:
    def __init__(self, session, model_name):
        self.session, self.model_name = session, model_name

    async def get_diagnostic(self, diagnostic_id):
        row = await self.session.scalar(
            select(DiagnosticRow)
            .where(DiagnosticRow.id == diagnostic_id)
            .options(selectinload(DiagnosticRow.hypotheses))
        )
        if not row:
            return None
        values = {
            key: getattr(row, key)
            for key in Diagnostic.model_fields
            if key not in {"diagnostic_id", "possible_causes"}
        }
        values["possible_causes"] = [
            {
                "label": "hypothesis",
                **{
                    key: getattr(hypothesis, key)
                    for key in (
                        "component_or_system",
                        "possible_failure",
                        "supporting_symptoms",
                        "missing_or_contradictory_evidence",
                        "recommended_verification",
                        "professional_inspection_required",
                        "uncertainty",
                    )
                },
            }
            for hypothesis in row.hypotheses
        ]
        return Diagnostic(diagnostic_id=row.id, **values)

    async def save_diagnostic(self, diagnostic):
        require_persistable_report(diagnostic)
        turn_index = await self.session.scalar(
            select(func.coalesce(func.max(DiagnosticRow.turn_index), -1) + 1).where(
                DiagnosticRow.conversation_id == diagnostic.conversation_id
            )
        )
        data = diagnostic.model_dump(
            mode="json",
            exclude={
                "diagnostic_id",
                "conversation_id",
                "vehicle_id",
                "created_at",
                "possible_causes",
            },
        )
        self.session.add(
            DiagnosticRow(
                id=diagnostic.diagnostic_id,
                conversation_id=diagnostic.conversation_id,
                vehicle_id=diagnostic.vehicle_id,
                created_at=diagnostic.created_at,
                turn_index=turn_index,
                model_name=self.model_name if diagnostic.generation_mode == "llm" else None,
                **data,
                hypotheses=[
                    HypothesisRow(display_order=index, **cause.model_dump(exclude={"label"}))
                    for index, cause in enumerate(diagnostic.possible_causes)
                ],
            )
        )
        await self.session.flush()


class PostgresRepository:
    """Existing aggregate contract, composed from four shared-session repositories."""

    def __init__(self, session, model_name):
        vehicles = PostgresVehicleRepository(session)
        conversations = PostgresConversationRepository(session)
        diagnostics = PostgresDiagnosticRepository(session, model_name)
        self.list_vehicles = vehicles.list_vehicles
        self.get_vehicle = vehicles.get_vehicle
        self.save_vehicle = vehicles.save_vehicle
        self.get_conversation = conversations.get_conversation
        self.save_conversation = conversations.save_conversation
        self.list_cases = conversations.list_cases
        self.get_diagnostic = diagnostics.get_diagnostic
        self.save_diagnostic = diagnostics.save_diagnostic


class PostgresStore:
    persistence = "postgresql"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.sessions = None

    def connect(self):
        if self.engine is None:
            self.engine = make_engine(self.settings)
            self.sessions = make_sessions(self.engine)

    @asynccontextmanager
    async def transaction(self) -> Transaction:
        self.connect()
        try:
            async with self.sessions() as session, session.begin():
                yield PostgresRepository(session, self.settings.openai_model)
        except IntegrityError:
            logger.warning("database_integrity_conflict")
            raise AppError(
                409, "database_conflict", "Operation conflicts with stored data."
            ) from None
        except SQLAlchemyError:
            logger.warning("database_operation_failed")
            raise AppError(503, "database_unavailable", "PostgreSQL is unavailable.") from None

    async def initialize(self):
        self.connect()
        try:
            async with self.engine.connect() as connection:
                info = await inspect_database(connection)
                if not info["pgvector_version"] or info["revision"] != "0005_resolution":
                    raise AppError(503, "database_not_migrated", "Run alembic upgrade head.")
                if info["embedding_dimensions"] != self.settings.embedding_dimensions:
                    raise AppError(
                        503,
                        "embedding_dimension_mismatch",
                        "EMBEDDING_DIMENSIONS differs from the migrated database.",
                    )
            async with self.sessions() as session, session.begin():
                vehicle = seed_vehicle()
                await session.execute(
                    insert(VehicleRow)
                    .values(id=vehicle.vehicle_id, **vehicle.model_dump(exclude={"vehicle_id"}))
                    .on_conflict_do_nothing(index_elements=[VehicleRow.id])
                )
        except SQLAlchemyError:
            await self.close()
            raise AppError(
                503,
                "database_unavailable",
                "Check PostgreSQL connectivity and run alembic upgrade head.",
            ) from None
        except AppError:
            await self.close()
            raise

    async def ready(self):
        try:
            self.connect()
            async with self.engine.connect() as connection:
                info = await inspect_database(connection)
                return bool(info["pgvector_version"]) and info["revision"] == "0005_resolution"
        except (SQLAlchemyError, AppError):
            return False

    async def close(self):
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.sessions = None
