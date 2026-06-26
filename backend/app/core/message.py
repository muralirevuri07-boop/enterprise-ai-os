from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MessageType(Enum):
    """Enumerates standardized message categories exchanged by agents."""

    TASK = "task"
    RESPONSE = "response"
    QUESTION = "question"
    ANSWER = "answer"
    CHALLENGE = "challenge"
    EVIDENCE = "evidence"
    ALERT = "alert"
    APPROVAL = "approval"
    DECISION = "decision"
    SYSTEM = "system"


class Priority(Enum):
    """Defines the urgency level of an agent message."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentMessage(BaseModel):
    """Universal message envelope used by all agents in Enterprise AI OS.

    This model captures the essential routing, type, and content metadata for
    agent-to-agent communication within a mission-driven decision intelligence
    workflow.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique message identifier.")
    mission_id: UUID = Field(..., description="Identifier for the mission that owns this message.")
    sender: str = Field(..., description="Sender identity for this message.")
    receiver: str = Field(..., description="Receiver identity for this message.")
    message_type: MessageType = Field(..., description="Semantic type of the message.")
    priority: Priority = Field(default=Priority.MEDIUM, description="Urgency level of the message.")
    content: str = Field(..., description="Primary textual payload contained in the message.")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the message payload, between 0.0 and 1.0.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the message was generated.",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata for the message.")
    requires_response: bool = Field(
        default=False,
        description="Whether the sender expects a follow-up response.",
    )
    parent_message_id: Optional[UUID] = Field(
        default=None,
        description="Optional reference to a prior message in the conversation thread.",
    )

    model_config = {
        "extra": "forbid",
    }

    @field_validator("sender", "receiver")
    @classmethod
    def _validate_non_empty_address(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("sender and receiver must be non-empty strings")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    def summary(self) -> str:
        """Return a brief summary of the message for logs and monitoring."""
        preview = self.content.strip().replace("\n", " ")
        if len(preview) > 120:
            preview = f"{preview[:117]}..."
        return (
            f"{self.timestamp.isoformat()} | {self.sender} -> {self.receiver} | "
            f"{self.message_type.name} | priority={self.priority.name} | {preview}"
        )

    def is_high_priority(self) -> bool:
        """Return True when this message requires expedited handling."""
        return self.priority in {Priority.HIGH, Priority.CRITICAL}

    def is_response(self) -> bool:
        """Return True when this message is naturally a response from another agent."""
        return self.message_type == MessageType.RESPONSE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this message to a plain dictionary for transport or persistence."""
        return self.model_dump()


if __name__ == "__main__":
    example = AgentMessage(
        mission_id=uuid4(),
        sender="Research Agent",
        receiver="Finance Agent",
        message_type=MessageType.QUESTION,
        priority=Priority.HIGH,
        content="What financial assumptions should we use to validate the next-quarter revenue forecast?",
        confidence=0.92,
        requires_response=True,
    )

    print(example.summary())
    print(example.to_dict())
