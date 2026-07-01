from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

try:
    from .message import AgentMessage, MessageType, Priority
    from .mission import Mission
except ImportError:
    from message import AgentMessage, MessageType, Priority
    from mission import Mission


class MissionConversation(BaseModel):
    """Thread-safe chronological conversation for a single mission.

    ``MissionConversation`` owns the immutable history of messages exchanged
    during a mission. Messages are copied on insert and copied again on
    retrieval, which prevents callers from mutating the internal timeline after
    messages have been accepted. All mutations are protected by a lock so the
    conversation can be safely shared by multiple workers in the same process.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        validate_assignment=True,
    )

    mission_id: UUID = Field(
        ...,
        description="Identifier of the mission this conversation belongs to.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp when the conversation started.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp for the latest conversation change.",
    )
    participants: set[str] = Field(
        default_factory=set,
        description="Agents that have sent or received at least one message.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-serializable extension data for integrations and auditing.",
    )

    _messages: list[AgentMessage] = PrivateAttr(default_factory=list)
    _message_ids: set[UUID] = PrivateAttr(default_factory=set)
    _lock: Lock = PrivateAttr(default_factory=Lock)

    @field_validator("started_at", "updated_at")
    @classmethod
    def _normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        """Return a timezone-aware UTC timestamp.

        Naive datetimes are rejected because their absolute point in time is
        ambiguous. Aware datetimes from any time zone are converted to UTC.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("conversation timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("participants")
    @classmethod
    def _normalize_participants(cls, value: set[str]) -> set[str]:
        """Normalize participant names and reject empty participant entries."""
        normalized_participants: set[str] = set()
        for participant in value:
            normalized = participant.strip()
            if not normalized:
                raise ValueError("participants must be non-empty strings")
            normalized_participants.add(normalized)
        return normalized_participants

    @property
    def messages(self) -> list[AgentMessage]:
        """Return a deep-copied snapshot of the conversation messages.

        The returned list and its ``AgentMessage`` instances are detached from
        internal storage. Mutating them cannot affect the stored conversation.
        """
        return self.history()

    @classmethod
    def from_mission(cls, mission: Mission, metadata: dict[str, Any] | None = None) -> MissionConversation:
        """Create a conversation for an existing mission.

        The mission identifier is copied from ``mission.id`` and the optional
        metadata is defensively copied so later caller mutations do not leak
        into the conversation.
        """
        return cls(mission_id=mission.id, metadata=deepcopy(metadata or {}))

    def _touch(self) -> None:
        """Refresh ``updated_at`` after an intentional state change."""
        self.updated_at = datetime.now(timezone.utc)

    def _add_message_unlocked(self, message: AgentMessage | None) -> None:
        """Validate and insert one message while the caller holds ``_lock``."""
        if message is None:
            return
        if message.mission_id != self.mission_id:
            raise ValueError(
                f"message mission_id {message.mission_id} does not match conversation mission_id {self.mission_id}"
            )
        if message.id in self._message_ids:
            raise ValueError(f"duplicate message id rejected: {message.id}")

        copied_message = deepcopy(message)
        self._messages.append(copied_message)
        self._message_ids.add(copied_message.id)
        self.participants = {
            *self.participants,
            copied_message.sender,
            copied_message.receiver,
        }
        self._touch()

    def start(self) -> None:
        """Mark the conversation as started and refresh its timestamp.

        ``start`` is useful when a conversation object is constructed before
        execution begins. It resets ``started_at`` and ``updated_at`` to the
        current UTC time without altering existing messages.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            self.started_at = now
            self.updated_at = now

    def add_message(self, message: AgentMessage) -> None:
        """Append one message to the conversation in insertion order.

        ``None`` messages are ignored, duplicate message IDs are rejected, and
        messages for a different mission are rejected. Accepted messages are
        deep-copied before storage, participants are updated automatically, and
        ``updated_at`` is refreshed.
        """
        with self._lock:
            self._add_message_unlocked(message)

    def broadcast(self, messages: list[AgentMessage]) -> None:
        """Append multiple messages atomically in the provided order.

        The method preserves the caller's message order, ignores ``None``
        entries, and rejects the entire broadcast if any non-``None`` message is
        invalid or has a duplicate ID. On success, all messages are inserted
        under a single lock and ``updated_at`` reflects the final insert.
        """
        with self._lock:
            pending_messages = [message for message in messages if message is not None]
            pending_ids: set[UUID] = set()

            for message in pending_messages:
                if message.mission_id != self.mission_id:
                    raise ValueError(
                        f"message mission_id {message.mission_id} does not match conversation mission_id {self.mission_id}"
                    )
                if message.id in self._message_ids or message.id in pending_ids:
                    raise ValueError(f"duplicate message id rejected: {message.id}")
                pending_ids.add(message.id)

            for message in pending_messages:
                self._add_message_unlocked(message)

    def history(self) -> list[AgentMessage]:
        """Return the full conversation history as a deep-copied list."""
        with self._lock:
            return deepcopy(self._messages)

    def latest(self) -> AgentMessage | None:
        """Return the latest inserted message, or ``None`` when history is empty."""
        with self._lock:
            if not self._messages:
                return None
            return deepcopy(self._messages[-1])

    def timeline(self) -> list[AgentMessage]:
        """Return messages in preserved chronological insertion order."""
        return self.history()

    def between(self, sender: str, receiver: str) -> list[AgentMessage]:
        """Return messages sent from ``sender`` to ``receiver``.

        Sender and receiver inputs are whitespace-normalized before matching.
        The result is a deep-copied snapshot in insertion order.
        """
        normalized_sender = sender.strip()
        normalized_receiver = receiver.strip()
        if not normalized_sender or not normalized_receiver:
            raise ValueError("sender and receiver must be non-empty strings")

        with self._lock:
            return deepcopy(
                [
                    message
                    for message in self._messages
                    if message.sender == normalized_sender and message.receiver == normalized_receiver
                ]
            )

    def participant_messages(self, agent: str) -> list[AgentMessage]:
        """Return all messages sent or received by ``agent`` in insertion order."""
        normalized_agent = agent.strip()
        if not normalized_agent:
            raise ValueError("agent must be a non-empty string")

        with self._lock:
            return deepcopy(
                [
                    message
                    for message in self._messages
                    if message.sender == normalized_agent or message.receiver == normalized_agent
                ]
            )

    def participants_list(self) -> list[str]:
        """Return conversation participants as a sorted list."""
        with self._lock:
            return sorted(self.participants)

    def total_messages(self) -> int:
        """Return the number of stored messages."""
        with self._lock:
            return len(self._messages)

    def summary(self) -> dict[str, Any]:
        """Return a compact JSON-serializable summary of the conversation."""
        with self._lock:
            first_timestamp = self._messages[0].timestamp.isoformat() if self._messages else None
            latest_timestamp = self._messages[-1].timestamp.isoformat() if self._messages else None

            return {
                "mission_id": str(self.mission_id),
                "started_at": self.started_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "participants": sorted(self.participants),
                "total_messages": len(self._messages),
                "first_message_at": first_timestamp,
                "latest_message_at": latest_timestamp,
            }

    def export_json(self) -> dict[str, Any]:
        """Return a JSON-serializable export of metadata and message history."""
        with self._lock:
            return {
                "mission_id": str(self.mission_id),
                "started_at": self.started_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "participants": sorted(self.participants),
                "messages": [message.to_dict() for message in self._messages],
                "metadata": deepcopy(self.metadata),
            }

    def clear(self) -> None:
        """Remove all messages and participants from the conversation.

        Metadata and mission identity are preserved. ``updated_at`` is refreshed
        so downstream consumers can observe the state reset.
        """
        with self._lock:
            self._messages.clear()
            self._message_ids.clear()
            self.participants = set()
            self._touch()


if __name__ == "__main__":
    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Identify acquisition-ready European AI startups with strong enterprise traction.",
    )

    conversation = MissionConversation.from_mission(mission)
    conversation.start()

    ceo_to_research = AgentMessage(
        mission_id=mission.id,
        sender="CEO",
        receiver="Research",
        message_type=MessageType.TASK,
        priority=Priority.HIGH,
        content="Identify promising AI startups in Europe for acquisition.",
        requires_response=True,
    )
    research_to_finance = AgentMessage(
        mission_id=mission.id,
        sender="Research",
        receiver="Finance",
        message_type=MessageType.QUESTION,
        priority=Priority.MEDIUM,
        content="Can you assess revenue quality and likely valuation ranges?",
        parent_message_id=ceo_to_research.id,
        requires_response=True,
    )
    finance_to_research = AgentMessage(
        mission_id=mission.id,
        sender="Finance",
        receiver="Research",
        message_type=MessageType.RESPONSE,
        priority=Priority.MEDIUM,
        content="Two targets show durable revenue and valuation ranges worth deeper diligence.",
        parent_message_id=research_to_finance.id,
        confidence=0.84,
    )
    research_to_ceo = AgentMessage(
        mission_id=mission.id,
        sender="Research",
        receiver="CEO",
        message_type=MessageType.RESPONSE,
        priority=Priority.HIGH,
        content="We recommend deeper diligence on two European AI infrastructure startups.",
        parent_message_id=ceo_to_research.id,
        confidence=0.88,
    )

    conversation.broadcast(
        [
            ceo_to_research,
            research_to_finance,
            finance_to_research,
            research_to_ceo,
        ]
    )

    print("Conversation summary:", conversation.summary())
    print("Conversation export:", conversation.export_json())
