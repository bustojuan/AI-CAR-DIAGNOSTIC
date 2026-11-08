from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from app.models.common import Schema, utcnow


class ConversationCreate(Schema):
    vehicle_id: UUID


class Message(Schema):
    message_id: UUID = Field(default_factory=uuid4)
    role: Literal["user", "assistant"]
    # JSON escaping may expand the bounded observation fields up to sixfold.
    content: str = Field(min_length=1, max_length=100000)
    created_at: datetime = Field(default_factory=utcnow)


class Conversation(Schema):
    conversation_id: UUID = Field(default_factory=uuid4)
    vehicle_id: UUID
    created_at: datetime = Field(default_factory=utcnow)
    messages: list[Message] = Field(default_factory=list)
    diagnostic_ids: list[UUID] = Field(default_factory=list)
    resolution_status: Literal["active", "resolved"] = "active"
    resolved_at: datetime | None = None
    resolution_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def consistent_resolution(self):
        if (self.resolution_status == "resolved") != (self.resolved_at is not None):
            raise ValueError("Only resolved cases must have a resolution date")
        if self.resolution_status == "active" and self.resolution_note is not None:
            raise ValueError("Active cases cannot have a current resolution note")
        return self
