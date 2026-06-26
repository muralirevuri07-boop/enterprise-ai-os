from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Protocol, TypedDict
from uuid import UUID

from .agent_bus import AgentBus
from .conversation import MissionConversation
from .message import AgentMessage, MessageType, Priority
from .mission import Mission, MissionStatus


class AgentProtocol(Protocol):
    """Minimal agent interface required by the orchestrator."""

    name: str

    def execute(self, task: str) -> str:
        ...


class AgentResponse(TypedDict):
    agent: str
    task: str
    output: str
    message: AgentMessage
    confidence: float


@dataclass(frozen=True)
class OrchestratorReport:
    mission_id: UUID
    final_decision: str
    conflicts: List[Dict[str, Any]]
    governance_feedback: Optional[str]
    mission_summary: Dict[str, Any]


class Orchestrator:
    """Coordinate specialist agents to deliver executive mission recommendations."""

    def __init__(self, agent_bus: AgentBus, registered_agents: Optional[Dict[str, AgentProtocol]] = None) -> None:
        self.agent_bus = agent_bus
        self._registered_agents: Dict[str, AgentProtocol] = {}
        # observed messages for monitoring (not used to relay messages)
        self._observed_messages: List[AgentMessage] = []
        # register as an observer to the bus so the orchestrator can watch activity
        try:
            self.agent_bus.register_observer(self._on_message)
        except Exception:
            pass
        if registered_agents:
            for agent in registered_agents.values():
                self.register_agent(agent)

    def register_agent(self, agent: AgentProtocol) -> None:
        """Register an agent instance by name for future mission coordination."""
        name = agent.name.strip()
        if not name:
            raise ValueError("agent.name must be a non-empty string")
        if name in self._registered_agents:
            raise ValueError(f"agent '{name}' is already registered")
        self._registered_agents[name] = agent
        # If the agent supports attaching to the AgentBus, attach it so it can receive messages
        try:
            attach = getattr(agent, "attach_to_bus", None)
            if callable(attach):
                attach(self.agent_bus)
        except Exception:
            # attachment failure should not block registration
            pass

    def unregister_agent(self, name: str) -> None:
        """Unregister a previously registered agent."""
        normalized = name.strip()
        if normalized not in self._registered_agents:
            raise KeyError(f"agent '{normalized}' is not registered")
        self._registered_agents.pop(normalized)

    def available_agents(self) -> List[str]:
        """Return the list of currently registered agent names."""
        return sorted(self._registered_agents.keys())

    def create_execution_plan(self, mission: Mission) -> Dict[str, str]:
        """Create a mission execution plan that assigns tasks to specialist agents."""
        if not self._registered_agents:
            raise RuntimeError("No agents are registered with the orchestrator")

        if mission.assigned_agents:
            agent_candidates = [agent for agent in mission.assigned_agents if agent in self._registered_agents]
        else:
            agent_candidates = [
                name
                for name in ("Research", "Finance", "Governance")
                if name in self._registered_agents
            ]
            if not agent_candidates:
                agent_candidates = list(self._registered_agents.keys())

        if mission.priority in {"HIGH", "CRITICAL"} and "Governance" in self._registered_agents:
            if "Governance" not in agent_candidates:
                agent_candidates.append("Governance")

        plan: Dict[str, str] = {}
        for agent_name in agent_candidates:
            if agent_name == "Research":
                plan[agent_name] = (
                    f"Research the mission objective and collect evidence relevant to: {mission.objective}"
                )
            elif agent_name == "Finance":
                plan[agent_name] = (
                    f"Analyze the financial implications of the mission objective: {mission.objective}"
                )
            elif agent_name == "Governance":
                plan[agent_name] = (
                    "Review the mission objective, specialist outputs, and any detected conflicts for governance compliance "
                    "and executive readiness."
                )
            else:
                plan[agent_name] = f"Support the mission objective with a specialist response for: {mission.objective}"

        return plan

    def assign_tasks(self, mission: Mission) -> Dict[str, str]:
        """Assign task messages to the agents selected for the mission."""
        plan = self.create_execution_plan(mission)
        conversation = MissionConversation(mission.conversation_id, self.agent_bus)

        if not conversation.history():
            conversation.start()

        for agent_name, task in plan.items():
            conversation.send(
                sender="CEO",
                receiver=agent_name,
                message_type=MessageType.TASK,
                content=task,
                priority=Priority.HIGH,
            )

        mission.assign_agents(list(plan.keys()))
        mission.update_status(MissionStatus.ASSIGNED)
        mission.metadata["execution_plan"] = plan
        return plan

    def execute_mission(self, mission: Mission) -> OrchestratorReport:
        """Execute the full orchestrator flow for a mission."""
        mission.update_status(MissionStatus.PLANNING)
        conversation = MissionConversation(mission.conversation_id, self.agent_bus)
        if not conversation.history():
            conversation.start()

        self.assign_tasks(mission)
        mission.update_status(MissionStatus.IN_PROGRESS)

        responses = self.collect_responses(mission)
        conflicts = self.detect_conflicts(responses)

        governance_feedback: Optional[str] = None
        if conflicts:
            governance_feedback = self.request_governance_review(mission)

        final_decision = self.make_final_decision(mission, responses, conflicts, governance_feedback)
        summary = self.complete_mission(mission, final_decision=final_decision)

        return OrchestratorReport(
            mission_id=mission.id,
            final_decision=final_decision,
            conflicts=conflicts,
            governance_feedback=governance_feedback,
            mission_summary=summary,
        )

    def collect_responses(self, mission: Mission) -> List[AgentResponse]:
        """Collect specialist agent responses and publish them to the mission conversation."""
        plan = mission.metadata.get("execution_plan")
        if not plan or not isinstance(plan, dict):
            plan = self.create_execution_plan(mission)

        conversation = MissionConversation(mission.conversation_id, self.agent_bus)
        responses: List[AgentResponse] = []

        for agent_name, task in plan.items():
            agent = self._registered_agents.get(agent_name)
            if agent is None:
                continue

            output = agent.execute(task)
            response_message = conversation.send(
                sender=agent_name,
                receiver="CEO",
                message_type=MessageType.RESPONSE,
                content=output,
                priority=Priority.MEDIUM,
                confidence=1.0,
            )
            responses.append(
                AgentResponse(
                    agent=agent_name,
                    task=task,
                    output=output,
                    message=response_message,
                    confidence=response_message.confidence,
                )
            )

        return responses

    def detect_conflicts(self, responses: List[AgentResponse]) -> List[Dict[str, Any]]:
        """Detect potential conflicts between specialist responses."""
        conflicts: List[Dict[str, Any]] = []
        patterns = [
            ("recommend", "do not recommend"),
            ("approve", "reject"),
            ("low risk", "high risk"),
            ("strong opportunity", "significant risk"),
        ]

        normalized: Dict[str, str] = {
            response["agent"]: response["output"].strip().lower() for response in responses
        }

        for i, first in enumerate(responses):
            for second in responses[i + 1 :]:
                first_text = normalized[first["agent"]]
                second_text = normalized[second["agent"]]
                for positive, negative in patterns:
                    if positive in first_text and negative in second_text:
                        conflicts.append(
                            {
                                "agents": [first["agent"], second["agent"]],
                                "topic": "recommendation disagreement",
                                "positions": {first["agent"]: first["output"], second["agent"]: second["output"]},
                                "severity": "HIGH",
                            }
                        )
                        break
                    if negative in first_text and positive in second_text:
                        conflicts.append(
                            {
                                "agents": [first["agent"], second["agent"]],
                                "topic": "recommendation disagreement",
                                "positions": {first["agent"]: first["output"], second["agent"]: second["output"]},
                                "severity": "HIGH",
                            }
                        )
                        break

        return conflicts

    def request_governance_review(self, mission: Mission) -> Optional[str]:
        """Request a governance review when specialist responses conflict."""
        governance_agent = self._registered_agents.get("Governance")
        if governance_agent is None:
            mission.update_status(MissionStatus.CEO_REVIEW)
            return None

        conversation = MissionConversation(mission.conversation_id, self.agent_bus)
        mission.update_status(MissionStatus.GOVERNANCE_REVIEW)

        task = (
            "Review the mission objective and the specialist responses. Identify governance risks, "
            "compliance issues, and whether the mission is ready for executive recommendation."
        )
        conversation.send(
            sender="CEO",
            receiver="Governance",
            message_type=MessageType.TASK,
            content=task,
            priority=Priority.CRITICAL,
        )

        output = governance_agent.execute(task)
        conversation.send(
            sender="Governance",
            receiver="CEO",
            message_type=MessageType.RESPONSE,
            content=output,
            priority=Priority.MEDIUM,
        )

        mission.governance_status = "reviewed"
        mission.add_evidence(f"Governance review completed by Governance agent.")
        return output

    def make_final_decision(
        self,
        mission: Mission,
        responses: List[AgentResponse],
        conflicts: List[Dict[str, Any]],
        governance_feedback: Optional[str] = None,
    ) -> str:
        """Produce an executive recommendation without performing specialist work."""
        lines: List[str] = [
            "The orchestrator has coordinated specialist agents and produced an executive recommendation.",
            f"Mission objective: {mission.objective}",
        ]

        if conflicts:
            lines.append(
                "Conflicts were detected between specialist agents and escalated for governance review."
            )
        else:
            lines.append("Specialist inputs are aligned and do not require additional conflict resolution.")

        if governance_feedback:
            lines.append(f"Governance review conclusion: {governance_feedback}")
            mission.update_status(MissionStatus.CEO_REVIEW)
        else:
            mission.update_status(MissionStatus.CEO_REVIEW)
            lines.append("Executive recommendation is based on available specialist responses.")

        lines.append("Proceed with the mission under CEO oversight and update governance controls as required.")
        return " ".join(lines)

    def complete_mission(
        self,
        mission: Mission,
        final_decision: str,
        confidence: float = 0.85,
    ) -> Dict[str, Any]:
        """Mark the mission complete and publish the final executive recommendation."""
        conversation = MissionConversation(mission.conversation_id, self.agent_bus)
        conversation.send(
            sender="CEO",
            receiver="Mission",
            message_type=MessageType.DECISION,
            content=final_decision,
            priority=Priority.CRITICAL,
            confidence=confidence,
        )

        mission.complete(final_decision=final_decision, confidence=confidence)
        return mission.summary()

    def _on_message(self, message: AgentMessage) -> None:
        """Observer callback invoked for every message on the AgentBus.

        The orchestrator should not relay or intercept messages; it only observes.
        """
        try:
            self._observed_messages.append(message)
        except Exception:
            pass


if __name__ == "__main__":
    from uuid import uuid4

    class SimpleAgent:
        def __init__(self, name: str, executor: Any) -> None:
            self.name = name
            self._executor = executor

        def execute(self, task: str) -> str:
            return self._executor(task)

    def research_executor(task: str) -> str:
        return (
            "Research findings indicate that several European AI startups are strategically "
            "positioned for acquisition, with differentiated product roadmaps and strong domain expertise."
        )

    def finance_executor(task: str) -> str:
        return (
            "Finance analysis identifies moderate acquisition risk, recommends continued diligence, "
            "and highlights revenue multiple pressure in the current funding environment."
        )

    def governance_executor(task: str) -> str:
        return (
            "Governance review confirms the mission can proceed with executive oversight, "
            "but requires a formal risk mitigation plan before final approval."
        )

    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Identify high-potential AI startups in Europe that align with our strategic acquisition criteria.",
        created_by="CEO",
    )

    bus = AgentBus()
    orchestrator = Orchestrator(agent_bus=bus)
    orchestrator.register_agent(SimpleAgent("Research", research_executor))
    orchestrator.register_agent(SimpleAgent("Finance", finance_executor))
    orchestrator.register_agent(SimpleAgent("Governance", governance_executor))

    report = orchestrator.execute_mission(mission)
    print("Mission summary:", report.mission_summary)
    print("Final decision:\n", report.final_decision)
    print("Conflicts detected:", report.conflicts)
    print("Governance feedback:\n", report.governance_feedback)
