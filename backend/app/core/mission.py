from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MissionStatus(StrEnum):
    """Lifecycle states for a mission.

    A mission begins in ``CREATED``, can move through planning and execution
    states, and ends in either ``COMPLETED`` or ``FAILED``. The enum values are
    strings so serialized payloads remain stable across APIs, queues, logs, and
    persistence layers.
    """

    CREATED = "created"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING = "waiting"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class MissionPriority(StrEnum):
    """Urgency levels used to rank mission execution and escalation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Mission(BaseModel):
    """Structured mission record for coordinating enterprise agent work.

    ``Mission`` models a business objective from creation through completion.
    It tracks assigned agents, completed agents, workflow status, optional links
    to conversation and final-report records, and extension metadata. The model
    is designed for reliable transport and persistence: identifiers are UUIDs,
    datetimes are timezone-aware UTC values, enums serialize cleanly, and the
    mission ID is immutable after creation.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )

    id: UUID = Field(
        default_factory=uuid4,
        frozen=True,
        description="Stable unique identifier for this mission.",
    )
    title: str = Field(
        ...,
        description="Short human-readable mission title.",
    )
    objective: str = Field(
        ...,
        description="Detailed business objective the mission is expected to satisfy.",
    )
    status: MissionStatus = Field(
        default=MissionStatus.CREATED,
        description="Current lifecycle status of the mission.",
    )
    priority: MissionPriority = Field(
        default=MissionPriority.MEDIUM,
        description="Execution priority used for scheduling and escalation.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp for mission creation.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timezone-aware UTC timestamp for the latest state change.",
    )
    assigned_agents: list[str] = Field(
        default_factory=list,
        description="Unique list of agents assigned to execute the mission.",
    )
    completed_agents: list[str] = Field(
        default_factory=list,
        description="Assigned agents that have completed their mission work.",
    )
    conversation_id: UUID | None = Field(
        default=None,
        description="Optional identifier of the conversation associated with the mission.",
    )
    final_report_id: UUID | None = Field(
        default=None,
        description="Optional identifier of the final report produced for the mission.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON-serializable extension data for integrations and auditing.",
    )

    @field_validator("title", "objective")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        """Normalize and validate required descriptive text fields."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("title and objective must be non-empty strings")
        return normalized

    @field_validator("assigned_agents", "completed_agents")
    @classmethod
    def _validate_unique_agents(cls, value: list[str]) -> list[str]:
        """Normalize agent names and ensure each list contains unique entries."""
        normalized_agents: list[str] = []
        seen_agents: set[str] = set()

        for agent in value:
            normalized = agent.strip()
            if not normalized:
                raise ValueError("agent names must be non-empty strings")
            if normalized in seen_agents:
                raise ValueError("agent lists must contain unique agent names")
            seen_agents.add(normalized)
            normalized_agents.append(normalized)

        return normalized_agents

    @field_validator("created_at", "updated_at")
    @classmethod
    def _normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        """Return a timezone-aware UTC timestamp.

        Naive datetimes are rejected because their absolute point in time is
        ambiguous. Aware datetimes from any time zone are converted to UTC.
        """
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("mission timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_completed_agents_are_assigned(self) -> Mission:
        """Ensure completion can only be recorded for assigned agents."""
        assigned = set(self.assigned_agents)
        completed = set(self.completed_agents)
        if not completed.issubset(assigned):
            unknown_agents = ", ".join(sorted(completed - assigned))
            raise ValueError(f"completed_agents must be a subset of assigned_agents: {unknown_agents}")
        return self

    def _touch(self) -> None:
        """Refresh ``updated_at`` after an intentional state change."""
        self.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _normalize_agent(agent: str) -> str:
        """Return a validated agent name suitable for mission lists."""
        normalized = agent.strip()
        if not normalized:
            raise ValueError("agent must be a non-empty string")
        return normalized

    def assign_agent(self, agent: str) -> None:
        """Assign one agent to the mission.

        Duplicate assignments are treated as idempotent no-ops. When a new
        agent is added, ``updated_at`` is refreshed automatically.
        """
        normalized = self._normalize_agent(agent)
        if normalized not in self.assigned_agents:
            self.assigned_agents = [*self.assigned_agents, normalized]
            self._touch()

    def assign_agents(self, agents: list[str]) -> None:
        """Assign multiple agents to the mission.

        The input must contain at least one non-empty agent name. Existing
        assignments are preserved, duplicate names are collapsed, and
        ``updated_at`` is refreshed only when the assignment set changes.
        """
        normalized_agents = [self._normalize_agent(agent) for agent in agents]
        if not normalized_agents:
            raise ValueError("agents must contain at least one agent")

        updated_agents = list(self.assigned_agents)
        for agent in normalized_agents:
            if agent not in updated_agents:
                updated_agents.append(agent)

        if updated_agents != self.assigned_agents:
            self.assigned_agents = updated_agents
            self._touch()

    def complete_agent(self, agent: str) -> None:
        """Mark an assigned agent as complete.

        Completion is only valid for agents already assigned to the mission.
        Re-completing the same agent is idempotent and does not change
        ``updated_at``.
        """
        normalized = self._normalize_agent(agent)
        if normalized not in self.assigned_agents:
            raise ValueError(f"cannot complete unassigned agent: {normalized}")

        if normalized not in self.completed_agents:
            self.completed_agents = [*self.completed_agents, normalized]
            self._touch()

    def update_status(self, status: MissionStatus) -> None:
        """Set the mission lifecycle status and refresh ``updated_at``.

        Assigning the current status is idempotent and leaves ``updated_at``
        unchanged.
        """
        if self.status != status:
            self.status = status
            self._touch()

    def is_completed(self) -> bool:
        """Return whether the mission has reached the completed terminal state."""
        return self.status is MissionStatus.COMPLETED

    def is_failed(self) -> bool:
        """Return whether the mission has reached the failed terminal state."""
        return self.status is MissionStatus.FAILED

    def progress(self) -> float:
        """Return completion progress as a float from ``0.0`` to ``1.0``.

        Progress is calculated from completed agents divided by assigned agents.
        A mission with no assigned agents reports ``0.0`` because no executable
        work has been allocated yet.
        """
        if not self.assigned_agents:
            return 0.0
        return len(self.completed_agents) / len(self.assigned_agents)

    def summary(self) -> str:
        """Return a compact human-readable mission summary.

        The summary is intended for logs, dashboards, and CLI output. It keeps
        the mission objective out of the line to avoid verbose log entries while
        still exposing status, priority, assignment progress, and identifiers.
        """
        percent = self.progress() * 100
        return (
            f"{self.title} | status={self.status.name} | priority={self.priority.name} | "
            f"progress={percent:.0f}% ({len(self.completed_agents)}/{len(self.assigned_agents)}) | "
            f"id={self.id}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation of the mission."""
        return self.model_dump(mode="json")


if __name__ == "__main__":
    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective=(
            "Identify high-potential AI startups in Europe that align with acquisition "
            "criteria, strategic product gaps, and enterprise revenue goals."
        ),
        priority=MissionPriority.HIGH,
    )

    mission.assign_agents(["Research", "Finance", "Governance"])
    mission.update_status(MissionStatus.RUNNING)
    mission.complete_agent("Research")
    mission.complete_agent("Finance")
    mission.update_status(MissionStatus.REVIEW)

    print(mission.summary())
    print(mission.to_dict())
