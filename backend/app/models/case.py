"""User-reported case status, separate from immutable diagnostic assessments."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.common import Schema, Text
from app.models.diagnostic import Urgency

URGENCY_RANK = {level: index for index, level in enumerate(Urgency, start=1)}


class CaseVersion(Schema):
    expected_latest_diagnostic_id: UUID


class ResolveCaseRequest(CaseVersion):
    resolution_note: str | None = Field(default=None, max_length=1000)


class CaseSummary(Schema):
    conversation_id: UUID
    vehicle_id: UUID
    created_at: datetime
    resolution_status: Literal["active", "resolved"]
    resolved_at: datetime | None
    resolution_note: str | None
    latest_diagnostic_id: UUID
    latest_assessment_at: datetime
    summary: Text
    assessment_count: int = Field(ge=1)
    historical_urgency: Urgency


class VehicleUrgency(Schema):
    vehicle_id: UUID
    urgency_level: Urgency | None
    active_case_count: int = Field(ge=0)
    resolved_case_count: int = Field(ge=0)
    explanation: Text


class CaseHistory(Schema):
    cases: list[CaseSummary]
    vehicle_urgency: VehicleUrgency


def aggregate_vehicle_urgency(vehicle_id: UUID, cases: list[CaseSummary]) -> VehicleUrgency:
    active = [case for case in cases if case.resolution_status == "active"]
    return VehicleUrgency(
        vehicle_id=vehicle_id,
        urgency_level=max((case.historical_urgency for case in active), key=URGENCY_RANK.get)
        if active
        else None,
        active_case_count=len(active),
        resolved_case_count=len(cases) - len(active),
        explanation=(
            "Highest recorded urgency among active cases. Resolution is user-reported, "
            "not independent verification of repair or driving safety."
            if active
            else "No active issues reported. This does not independently establish vehicle safety."
        ),
    )
