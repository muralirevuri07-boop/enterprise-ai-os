from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MissionStatus(Enum):
    """Defines the lifecycle state of a mission."""

    CREATED = "created"
    PLANNING = "planning"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    GOVERNANCE_REVIEW = "governance_review"
    CEO_REVIEW = "ceo_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionPriority(Enum):
    """Defines the urgency of a mission."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Mission(BaseModel):
    """A mission captures a complete business objective and its execution state.

    Missions encapsulate structured collaboration needs, progress tracking, and
    governance metadata for the enterprise decision-making workflow.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique mission identifier.")
    title: str = Field(..., description="Short mission title.")
    objective: str = Field(..., description="Primary business objective for the mission.")
    created_by: str = Field(..., description="Identity of the user or agent that created the mission.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the mission was created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the mission was last updated.",
    )
    status: MissionStatus = Field(default=MissionStatus.CREATED, description="Current mission status.")
    priority: MissionPriority = Field(default=MissionPriority.MEDIUM, description="Mission urgency level.")
    assigned_agents: List[str] = Field(default_factory=list, description="Agents assigned to the mission.")
    conversation_id: UUID = Field(default_factory=uuid4, description="Identifier for the mission conversation.")
    final_decision: Optional[str] = Field(None, description="Final executive recommendation for the mission.")
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Final confidence score for the mission recommendation.",
    )
    governance_status: Optional[str] = Field(None, description="Governance review status.")
    evidence: List[str] = Field(default_factory=list, description="Collected evidence items supporting the mission.")
    approvals: List[str] = Field(default_factory=list, description="Approvals granted during mission execution.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata for mission extensions.")

    model_config = {
        "extra": "forbid",
    }

    @field_validator("title", "objective", "created_by")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("title, objective, and created_by must be non-empty strings")
        return cleaned_value

    @field_validator("assigned_agents", "evidence", "approvals", mode="before")
    @classmethod
    def _normalize_string_list(cls, value: List[str]) -> List[str]:
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def assign_agent(self, agent_name: str) -> None:
        """Assign a single agent to the mission."""
        normalized = agent_name.strip()
        if not normalized:
            raise ValueError("agent_name must be a non-empty string")
        if normalized not in self.assigned_agents:
            self.assigned_agents.append(normalized)
            self._touch()

    def assign_agents(self, agent_names: List[str]) -> None:
        """Assign multiple agents to the mission."""
        cleaned_agents = [name.strip() for name in agent_names if name and name.strip()]
        if not cleaned_agents:
            raise ValueError("agent_names must contain at least one non-empty string")

        for agent in cleaned_agents:
            if agent not in self.assigned_agents:
                self.assigned_agents.append(agent)
        self._touch()

    def update_status(self, status: MissionStatus) -> None:
        """Update the current mission status."""
        self.status = status
        self._touch()

    def add_evidence(self, evidence_item: str) -> None:
        """Add a new evidence item to the mission."""
        normalized = evidence_item.strip()
        if not normalized:
            raise ValueError("evidence_item must be a non-empty string")
        self.evidence.append(normalized)
        self._touch()

    def add_approval(self, approval: str) -> None:
        """Record an approval for the mission."""
        normalized = approval.strip()
        if not normalized:
            raise ValueError("approval must be a non-empty string")
        if normalized not in self.approvals:
            self.approvals.append(normalized)
            self._touch()

    def complete(self, final_decision: Optional[str] = None, confidence: Optional[float] = None) -> None:
        """Mark the mission as completed with an optional decision and confidence."""
        if final_decision is not None:
            self.final_decision = final_decision.strip() or self.final_decision
        if confidence is not None:
            self.confidence = self._validate_confidence(confidence)
        self.status = MissionStatus.COMPLETED
        self._touch()

    def fail(self, reason: Optional[str] = None) -> None:
        """Mark the mission as failed and optionally preserve the final decision reason."""
        if reason is not None:
            normalized = reason.strip()
            if normalized:
                self.final_decision = normalized
        self.status = MissionStatus.FAILED
        self._touch()

    def summary(self) -> Dict[str, Any]:
        """Return a compact summary of the mission state."""
        return {
            "id": str(self.id),
            "title": self.title,
            "objective": self.objective,
            "status": self.status.name,
            "priority": self.priority.name,
            "assigned_agents": self.assigned_agents.copy(),
            "total_evidence": len(self.evidence),
            "total_approvals": len(self.approvals),
            "final_decision": self.final_decision,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the mission."""
        return self.model_dump(mode="json")


if __name__ == "__main__":
    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Identify high-potential AI startups in Europe that align with our strategic capabilities and acquisition criteria.",
        created_by="CEO",
    )

    mission.assign_agents(["Research", "Finance", "Governance"])
    mission.add_evidence("Initial market sizing shows strong AI adoption in the Nordics.")
    mission.add_approval("Executive sponsorship received")
    mission.update_status(MissionStatus.IN_PROGRESS)
    mission.complete(
        final_decision="Recommend acquisition of two European AI startups with strong enterprise traction.",
        confidence=0.88,
    )

    print("Mission summary:", mission.summary())
    print("Mission payload:", mission.to_dict())
