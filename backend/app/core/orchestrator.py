from __future__ import annotations

import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

try:
    from app.agents.base import BaseAgent
    from app.core.agent_bus import AgentBus
    from app.core.conversation import MissionConversation
    from app.core.message import AgentMessage, MessageType, Priority
    from app.core.mission import Mission, MissionPriority, MissionStatus
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from agents.base import BaseAgent
    from core.agent_bus import AgentBus
    from core.conversation import MissionConversation
    from core.message import AgentMessage, MessageType, Priority
    from core.mission import Mission, MissionPriority, MissionStatus


class Orchestrator:
    """Coordinate mission execution across registered specialist agents.

    The orchestrator acts as the CEO coordinator only: it creates missions,
    selects eligible agents, dispatches task messages through ``AgentBus``,
    observes responses addressed to ``CEO``, runs a governance review, and
    publishes a final CEO decision. Specialist work remains inside registered
    ``BaseAgent`` instances.
    """

    CEO_NAME = "CEO"

    def __init__(self) -> None:
        """Create an orchestrator with an initial control conversation.

        ``create_mission`` replaces the control conversation with a mission
        conversation before execution. Keeping an initial bus allows agents to
        be registered before the first mission is created; they are rebound to
        the active mission bus whenever a new mission is created.
        """
        control_mission = Mission(
            title="Orchestrator control mission",
            objective="Coordinate mission setup before a business mission is created.",
        )
        self._conversation: MissionConversation = MissionConversation.from_mission(control_mission)
        self._bus: AgentBus = AgentBus(self._conversation)
        self._agents: dict[str, BaseAgent] = {}
        self._active_missions: dict[UUID, Mission] = {}
        self._ceo_inbox: list[AgentMessage] = []
        self._lock: Lock = Lock()
        self._register_ceo_listener()

    @property
    def bus(self) -> AgentBus:
        """Return the currently active mission bus."""
        return self._bus

    @property
    def conversation(self) -> MissionConversation:
        """Return the currently active mission conversation."""
        return self._conversation

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialist agent with the active bus.

        Registration is keyed by ``agent.name``. The agent is also bound to the
        active bus so its ``receive`` and ``send`` methods validate against the
        current mission context.
        """
        if not self._is_agent_like(agent):
            raise TypeError("agent must provide the BaseAgent interface")
        name = self._normalize_name(agent.name)
        if name == self.CEO_NAME:
            raise ValueError("CEO is reserved for the orchestrator coordinator")

        with self._lock:
            if name in self._agents:
                raise ValueError(f"agent already registered: {name}")
            self._agents[name] = agent
            self._bind_agent_to_active_bus(agent)

    def unregister_agent(self, name: str) -> None:
        """Unregister an agent by name.

        Removing an unknown agent is treated as an idempotent no-op so shutdown
        and test cleanup code can call this method safely.
        """
        normalized_name = self._normalize_name(name)
        with self._lock:
            self._agents.pop(normalized_name, None)
            self._bus.unregister(normalized_name)

    def available_agents(self) -> list[str]:
        """Return registered specialist agent names in deterministic order."""
        with self._lock:
            return sorted(self._agents)

    def create_mission(
        self,
        title: str,
        objective: str,
        priority: MissionPriority | str = MissionPriority.MEDIUM,
    ) -> Mission:
        """Create and activate a new mission.

        A fresh ``MissionConversation`` and ``AgentBus`` are created for the
        mission, the CEO listener is registered, and all existing agents are
        rebound to the new bus.
        """
        normalized_priority = self._coerce_priority(priority)
        mission = Mission(title=title, objective=objective, priority=normalized_priority)

        with self._lock:
            self._active_missions[mission.id] = mission
            self._conversation = MissionConversation.from_mission(mission)
            self._conversation.start()
            self._bus = AgentBus(self._conversation)
            self._ceo_inbox.clear()
            self._register_ceo_listener()
            for agent in self._agents.values():
                self._bind_agent_to_active_bus(agent)

        return mission

    def assign_agents(self, mission: Mission) -> None:
        """Select eligible agents for a mission using ``can_handle``.

        Eligible agents are added to ``mission.assigned_agents`` and the mission
        moves to ``PLANNING``. At least one eligible specialist is required.
        """
        self._ensure_active_mission(mission)

        eligible_agents: list[str] = []
        with self._lock:
            agents = list(self._agents.values())

        for agent in agents:
            if agent.can_handle(mission):
                eligible_agents.append(agent.name)

        if not eligible_agents:
            raise RuntimeError("no registered agents can handle this mission")

        mission.assign_agents(eligible_agents)
        mission.update_status(MissionStatus.PLANNING)

    def execute(self, mission: Mission) -> dict[str, Any]:
        """Run the full CEO-coordinated mission workflow.

        The flow assigns eligible agents, sends task messages, collects
        responses, detects conflicts, completes governance review, finalizes a
        CEO decision, and marks the mission completed.
        """
        self._ensure_active_mission(mission)
        if not mission.assigned_agents:
            self.assign_agents(mission)

        mission.update_status(MissionStatus.RUNNING)

        for agent_name in mission.assigned_agents:
            self.dispatch(
                AgentMessage(
                    mission_id=mission.id,
                    sender=self.CEO_NAME,
                    receiver=agent_name,
                    message_type=MessageType.TASK,
                    priority=Priority.HIGH,
                    content=self._task_content_for(mission, agent_name),
                    requires_response=True,
                )
            )

        responses = self.collect_responses(mission)
        conflicts = self.detect_conflicts(mission)
        governance = self.governance_review(mission)
        decision = self.finalize(mission)
        self.complete(mission)

        return {
            "mission": mission.to_dict(),
            "responses": [message.to_dict() for message in responses],
            "conflicts": conflicts,
            "governance_review": governance.to_dict() if governance is not None else None,
            "decision": decision.to_dict(),
            "conversation": self._conversation.export_json(),
        }

    def dispatch(self, message: AgentMessage) -> AgentMessage | None:
        """Send a message through the active bus."""
        if message.mission_id != self._conversation.mission_id:
            raise ValueError("message mission_id does not match the active conversation")
        return self._bus.send(message)

    def collect_responses(self, mission: Mission) -> list[AgentMessage]:
        """Collect all responses addressed to CEO for a mission."""
        self._ensure_active_mission(mission)
        with self._lock:
            return deepcopy(
                [
                    message
                    for message in self._ceo_inbox
                    if message.mission_id == mission.id
                    and getattr(message.message_type, "value", message.message_type)
                    in {
                        MessageType.RESPONSE.value,
                        MessageType.ANSWER.value,
                        MessageType.EVIDENCE.value,
                        MessageType.APPROVAL.value,
                    }
                ]
            )

    def detect_conflicts(self, mission: Mission) -> list[dict[str, Any]]:
        """Detect high-level disagreements in collected agent responses.

        The detector compares simple decision signals across responses. It is
        intentionally conservative: it reports clear approve/reject,
        proceed/do-not-proceed, and low-risk/high-risk disagreements without
        inventing domain conclusions.
        """
        responses = self.collect_responses(mission)
        conflicts: list[dict[str, Any]] = []
        signal_pairs = (
            ("approve", "reject"),
            ("proceed", "do not proceed"),
            ("recommend", "do not recommend"),
            ("low risk", "high risk"),
            ("viable", "not viable"),
        )

        for index, first in enumerate(responses):
            first_text = first.content.lower()
            for second in responses[index + 1 :]:
                second_text = second.content.lower()
                for positive, negative in signal_pairs:
                    opposing = (
                        positive in first_text
                        and negative in second_text
                        or negative in first_text
                        and positive in second_text
                    )
                    if opposing:
                        conflicts.append(
                            {
                                "agents": [first.sender, second.sender],
                                "signal_pair": [positive, negative],
                                "severity": "high",
                                "first_message_id": str(first.id),
                                "second_message_id": str(second.id),
                            }
                        )
                        break

        return conflicts

    def governance_review(self, mission: Mission) -> AgentMessage | None:
        """Run governance review before CEO finalization.

        A governance-capable agent is selected by capability metadata rather
        than by a hardcoded agent name. If no such agent exists, execution fails
        because the mission contract requires governance review before a final
        decision.
        """
        self._ensure_active_mission(mission)
        governance_agent = self._select_governance_agent(mission)
        if governance_agent is None:
            raise RuntimeError("no governance-capable agent is registered")

        mission.update_status(MissionStatus.REVIEW)
        before_ids = {message.id for message in self.collect_responses(mission)}
        self.dispatch(
            AgentMessage(
                mission_id=mission.id,
                sender=self.CEO_NAME,
                receiver=governance_agent.name,
                message_type=MessageType.TASK,
                priority=Priority.CRITICAL,
                content=self._governance_task_content(mission),
                requires_response=True,
            )
        )

        after_responses = self.collect_responses(mission)
        for message in reversed(after_responses):
            if message.id not in before_ids and message.sender == governance_agent.name:
                return message
        return None

    def finalize(self, mission: Mission) -> AgentMessage:
        """Produce and store the CEO final decision message."""
        self._ensure_active_mission(mission)
        responses = self.collect_responses(mission)
        conflicts = self.detect_conflicts(mission)

        response_lines = [
            f"{message.sender}: {message.content}" for message in responses
        ]
        conflict_text = (
            f"{len(conflicts)} conflict(s) detected and considered."
            if conflicts
            else "No material response conflicts detected."
        )
        content = (
            f"CEO Decision for mission '{mission.title}': proceed to deeper diligence. "
            f"{conflict_text} Inputs reviewed: {' | '.join(response_lines)}"
        )

        decision = AgentMessage(
            mission_id=mission.id,
            sender=self.CEO_NAME,
            receiver=self.CEO_NAME,
            message_type=MessageType.DECISION,
            priority=Priority.CRITICAL,
            content=content,
            confidence=0.9 if not conflicts else 0.75,
        )
        self.dispatch(decision)
        return decision

    def complete(self, mission: Mission) -> None:
        """Mark a mission completed after final decision publication."""
        self._ensure_active_mission(mission)
        for agent_name in mission.assigned_agents:
            mission.complete_agent(agent_name)
        mission.update_status(MissionStatus.COMPLETED)

    def mission_status(self, mission_id: UUID) -> dict[str, Any] | None:
        """Return JSON-safe status for a known mission."""
        with self._lock:
            mission = self._active_missions.get(mission_id)
            if mission is None:
                return None
            conversation_summary = (
                self._conversation.summary()
                if self._conversation.mission_id == mission_id
                else None
            )
            return {
                "mission": mission.to_dict(),
                "conversation": conversation_summary,
                "available_agents": sorted(self._agents),
                "reported_at": datetime.now(timezone.utc).isoformat(),
            }

    def reset(self) -> None:
        """Clear active missions, conversation history, and agent state."""
        with self._lock:
            self._active_missions.clear()
            self._ceo_inbox.clear()
            self._conversation.clear()
            self._bus.clear()
            for agent in self._agents.values():
                agent.reset()

    def _register_ceo_listener(self) -> None:
        """Register the CEO coordinator listener on the active bus."""
        self._bus.register(self.CEO_NAME, self._receive_as_ceo)

    def _receive_as_ceo(self, message: AgentMessage) -> AgentMessage | None:
        """Store messages addressed to CEO without creating more work."""
        with self._lock:
            self._ceo_inbox.append(deepcopy(message))
        return None

    def _bind_agent_to_active_bus(self, agent: BaseAgent) -> None:
        """Bind an agent callback to the active bus."""
        setattr(agent, "_bus", self._bus)
        self._bus.register(agent.name, agent.receive)

    def _ensure_active_mission(self, mission: Mission) -> None:
        """Validate that ``mission`` is known and backed by the active bus."""
        with self._lock:
            if mission.id not in self._active_missions:
                self._active_missions[mission.id] = mission
            if self._conversation.mission_id != mission.id:
                self._conversation = MissionConversation.from_mission(mission)
                self._conversation.start()
                self._bus = AgentBus(self._conversation)
                self._ceo_inbox.clear()
                self._register_ceo_listener()
                for agent in self._agents.values():
                    self._bind_agent_to_active_bus(agent)

    def _select_governance_agent(self, mission: Mission) -> BaseAgent | None:
        """Return the first registered governance-capable agent."""
        with self._lock:
            agents = list(self._agents.values())
        for agent in agents:
            capability_text = f"{agent.name} {agent.role} {agent.description}".lower()
            if "governance" in capability_text and agent.can_handle(mission):
                return agent
        for agent in agents:
            capability_text = f"{agent.name} {agent.role} {agent.description}".lower()
            if "governance" in capability_text:
                return agent
        return None

    def _task_content_for(self, mission: Mission, agent_name: str) -> str:
        """Build a CEO task for an assigned agent."""
        return (
            f"Mission: {mission.title}\n"
            f"Objective: {mission.objective}\n"
            f"Assigned specialist: {agent_name}\n"
            "Provide a concise response with recommendation, risks, and confidence."
        )

    def _governance_task_content(self, mission: Mission) -> str:
        """Build the governance review task from collected mission context."""
        responses = self.collect_responses(mission)
        conflicts = self.detect_conflicts(mission)
        response_summary = " | ".join(f"{message.sender}: {message.content}" for message in responses)
        return (
            f"Review mission governance readiness for: {mission.objective}. "
            f"Responses: {response_summary or 'No prior specialist responses.'} "
            f"Detected conflicts: {conflicts or 'none'}."
        )

    @staticmethod
    def _coerce_priority(priority: MissionPriority | str) -> MissionPriority:
        """Normalize a mission priority value."""
        if isinstance(priority, MissionPriority):
            return priority
        normalized = priority.strip().lower()
        for candidate in MissionPriority:
            if normalized in {candidate.value, candidate.name.lower()}:
                return candidate
        raise ValueError(f"unknown mission priority: {priority}")

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Return a stripped non-empty name."""
        normalized = name.strip()
        if not normalized:
            raise ValueError("name must be a non-empty string")
        return normalized

    @staticmethod
    def _is_agent_like(agent: object) -> bool:
        """Return whether an object provides the required agent interface."""
        return all(
            hasattr(agent, attribute)
            for attribute in ("name", "role", "description", "can_handle", "receive", "reset")
        )


if __name__ == "__main__":
    class DemoAgent(BaseAgent):
        """Small deterministic agent used by the orchestrator example."""

        def __init__(
            self,
            name: str,
            role: str,
            description: str,
            bus: AgentBus,
            response: str,
        ) -> None:
            super().__init__(name=name, role=role, description=description, bus=bus)
            self._response = response
            self._started = False

        def initialize(self) -> None:
            self._started = True

        def can_handle(self, mission: Mission) -> bool:
            return self.name in mission.assigned_agents or self.role.lower().split()[0] in mission.objective.lower()

        def handle_task(self, message: AgentMessage) -> AgentMessage | None:
            return AgentMessage(
                mission_id=message.mission_id,
                sender=self.name,
                receiver=Orchestrator.CEO_NAME,
                message_type=MessageType.RESPONSE,
                priority=Priority.MEDIUM,
                content=self._response,
                confidence=0.86,
                parent_message_id=message.id,
            )

        def review(self, message: AgentMessage) -> AgentMessage | None:
            return None

        def health(self) -> dict[str, Any]:
            return {"name": self.name, "status": "healthy" if self._started else "initializing"}

        def shutdown(self) -> None:
            self._started = False

    orchestrator = Orchestrator()
    mission = orchestrator.create_mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Research AI startups in Europe for acquisition with finance and governance review.",
        priority=MissionPriority.HIGH,
    )

    research = DemoAgent(
        name="Research",
        role="Research Specialist",
        description="Researches markets and acquisition targets.",
        bus=orchestrator.bus,
        response="Recommend proceeding: several European AI startups match strategic acquisition criteria.",
    )
    finance = DemoAgent(
        name="Finance",
        role="Finance Specialist",
        description="Reviews financial viability and acquisition economics.",
        bus=orchestrator.bus,
        response="Proceed with caution: valuation ranges are acceptable if diligence confirms revenue durability.",
    )
    governance = DemoAgent(
        name="Governance",
        role="Governance Reviewer",
        description="Reviews governance, compliance, and executive decision readiness.",
        bus=orchestrator.bus,
        response="Governance approves deeper diligence with documented risk controls and board reporting.",
    )

    for demo_agent in (research, finance, governance):
        demo_agent.initialize()
        orchestrator.register_agent(demo_agent)

    report = orchestrator.execute(mission)

    print("Mission status:", orchestrator.mission_status(mission.id))
    print("Decision:", report["decision"]["content"])
    print("Flow:")
    for message in orchestrator.conversation.history():
        print(message.summary())
