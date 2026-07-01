from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageType(StrEnum):
    """Semantic categories for messages exchanged by enterprise agents.

    Message types describe the intent of a message independently from its
    sender, receiver, or priority. Using a string enum keeps serialized payloads
    stable and easy to transport through queues, HTTP APIs, logs, and databases.
    """

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


class Priority(StrEnum):
    """Urgency levels used to route, sort, and escalate agent messages."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentMessage(BaseModel):
    """Immutable-routed message envelope for agent-to-agent communication.

    ``AgentMessage`` is the canonical payload for collaboration inside a
    mission. It captures routing information, message intent, confidence,
    response expectations, thread lineage, and extensible metadata while
    preserving JSON-friendly serialization semantics.

    Message identifiers are generated once and frozen after model creation so
    downstream systems can safely use them for audit logs, parent-child
    threading, idempotency keys, and persistence references. Timestamps are
    always stored as timezone-aware UTC datetimes.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )

    id: UUID = Field(
        default_factory=uuid4,
        frozen=True,
        description="Stable unique identifier for this message.",
    )
    mission_id: UUID = Field(
        ...,
        description="Identifier of the mission that owns this message.",
    )
    sender: str = Field(
        ...,
        description="Name or system identifier of the agent sending the message.",
    )
    receiver: str = Field(
        ...,
        description="Name or system identifier of the intended recipient.",
    )
    message_type: MessageType = Field(
        ...,
        description="Semantic category describing the intent of the message.",
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Urgency level used for routing, sorting, and escalation.",
    )
    content: str = Field(
        ...,
        description="Primary natural-language payload delivered to the receiver.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the message content, from 0.0 to 1.0.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp for message creation.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-serializable extension data for transport or auditing.",
    )
    requires_response: bool = Field(
        default=False,
        description="Whether the sender expects a follow-up from the receiver.",
    )
    parent_message_id: UUID | None = Field(
        default=None,
        description="Optional identifier of the message this message replies to.",
    )

    @field_validator("sender", "receiver")
    @classmethod
    def _validate_non_empty_endpoint(cls, value: str) -> str:
        """Normalize and validate a routing endpoint.

        Empty senders and receivers make audit trails ambiguous and prevent
        reliable routing, so whitespace-only values are rejected.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("sender and receiver must be non-empty strings")
        return normalized

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        """Ensure confidence stays within the inclusive probability interval."""
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @field_validator("timestamp")
    @classmethod
    def _normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        """Return a timezone-aware UTC timestamp.

        Naive datetimes are rejected because their absolute point in time is
        ambiguous. Aware datetimes from other time zones are converted to UTC.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    def summary(self) -> str:
        """Return a compact human-readable summary for logs and dashboards.

        The summary includes timestamp, routing, message type, priority, and a
        short single-line content preview. Long content is truncated to keep log
        lines readable without mutating the original message.
        """
        preview = " ".join(self.content.strip().split())
        if len(preview) > 120:
            preview = f"{preview[:117]}..."

        return (
            f"{self.timestamp.isoformat()} | {self.sender} -> {self.receiver} | "
            f"{self.message_type.name} | priority={self.priority.name} | {preview}"
        )

    def is_high_priority(self) -> bool:
        """Return whether the message should receive expedited handling."""
        return self.priority in {Priority.HIGH, Priority.CRITICAL}

    def is_response(self) -> bool:
        """Return whether this message is a direct response payload."""
        return self.message_type is MessageType.RESPONSE

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation.

        UUIDs, datetimes, and enums are converted to JSON-compatible primitive
        values while preserving all public model fields.
        """
        return self.model_dump(mode="json")


if __name__ == "__main__":
    mission_id = uuid4()

    ceo_to_research = AgentMessage(
        mission_id=mission_id,
        sender="CEO",
        receiver="Research",
        message_type=MessageType.TASK,
        priority=Priority.HIGH,
        content="Assess the enterprise AI market and identify acquisition targets.",
        confidence=0.95,
        requires_response=True,
    )

    research_to_finance = AgentMessage(
        mission_id=mission_id,
        sender="Research",
        receiver="Finance",
        message_type=MessageType.QUESTION,
        priority=Priority.MEDIUM,
        content="Can you validate revenue quality and valuation ranges for the top targets?",
        confidence=0.88,
        requires_response=True,
        parent_message_id=ceo_to_research.id,
    )

    finance_to_research = AgentMessage(
        mission_id=mission_id,
        sender="Finance",
        receiver="Research",
        message_type=MessageType.RESPONSE,
        priority=Priority.MEDIUM,
        content="Initial checks show two targets with durable revenue and acceptable valuation ranges.",
        confidence=0.82,
        parent_message_id=research_to_finance.id,
        metadata={"targets_reviewed": 5, "targets_shortlisted": 2},
    )

    for message in (ceo_to_research, research_to_finance, finance_to_research):
        print(message.summary())
