from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from app.core.message import AgentMessage
from app.core.mission import Mission
from app.core.agent_bus import AgentBus
from app.core.message import MessageType


class BaseAgent(ABC):
    """Abstract base class that defines the contract for Enterprise AI OS agents."""

    def __init__(self, name: str, role: str, description: str) -> None:
        self._name = name.strip()
        self._role = role.strip()
        self._description = description.strip()
        if not self._name:
            raise ValueError("Agent name must be a non-empty string")
        if not self._role:
            raise ValueError("Agent role must be a non-empty string")
        if not self._description:
            raise ValueError("Agent description must be a non-empty string")

        self._logger = logging.getLogger(f"enterprise_ai_os.agent.{self._name}")
        self._logger.addHandler(logging.NullHandler())
        self._processed_message_ids: set = set()
        self._requested_finance_missions: set = set()

    @property
    def name(self) -> str:
        """Return the canonical name of this agent."""
        return self._name

    @property
    def role(self) -> str:
        """Return the operational role of this agent."""
        return self._role

    @property
    def description(self) -> str:
        """Return a short description of what this agent does."""
        return self._description

    @abstractmethod
    def initialize(self) -> None:
        """Perform any startup logic required before the agent can receive tasks."""

    @abstractmethod
    def can_handle(self, mission: Mission) -> bool:
        """Return True when this agent is responsible for the provided mission."""

    @abstractmethod
    def handle_task(self, message: AgentMessage) -> AgentMessage:
        """Process a task message and return the resulting response message."""

    @abstractmethod
    def review(self, message: AgentMessage) -> AgentMessage:
        """Review a message or mission artifact and return an annotated response."""

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return a health payload used for monitoring and readiness checks."""

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully release resources before agent termination."""

    def log(self, message: str, level: int = logging.INFO) -> None:
        """Log a lifecycle or diagnostic message for the agent."""
        self._logger.log(level, message)

    def validate_message(self, message: AgentMessage) -> bool:
        """Validate that the supplied object is a well-formed agent message."""
        return isinstance(message, AgentMessage)

    def send(self, message: AgentMessage) -> AgentMessage:
        """Prepare an outgoing message for delivery through the agent bus."""
        if not self.validate_message(message):
            raise ValueError("message must be an AgentMessage instance")
        return message

    def attach_to_bus(self, agent_bus: AgentBus) -> None:
        """Attach this agent to an AgentBus so it can receive and send messages.

        Registers an internal listener on the bus under the agent's name.
        """
        self._agent_bus = agent_bus
        agent_bus.register_listener(self.name, self._on_bus_message)

    def detach_from_bus(self) -> None:
        if hasattr(self, "_agent_bus") and self._agent_bus:
            try:
                self._agent_bus.unregister_listener(self.name)
            finally:
                self._agent_bus = None

    def deliver(self, message: AgentMessage) -> None:
        """Deliver a prepared AgentMessage into the attached AgentBus."""
        if not hasattr(self, "_agent_bus") or self._agent_bus is None:
            raise RuntimeError("agent is not attached to an AgentBus")
        self._agent_bus.send_message(message)

    def _on_bus_message(self, message: AgentMessage) -> None:
        """Internal callback invoked by the AgentBus when a message addressed to this agent arrives."""
        # Prevent duplicate processing of the same message
        if message.id in self._processed_message_ids:
            return

        # mark as processed upfront to avoid re-entrancy loops
        self._processed_message_ids.add(message.id)

        try:
            self.receive(message)
        except Exception:
            return

        # Route to task handler or review depending on message type
        try:
            if message.message_type == MessageType.TASK or message.message_type == MessageType.QUESTION:
                response = self.handle_task(message)
            else:
                response = self.review(message)
        except Exception:
            return

        # If a response message was produced, publish it back on the bus
        if response is not None and hasattr(self, "_agent_bus") and self._agent_bus:
            # ensure response links to parent message to help traceability
            if getattr(response, "parent_message_id", None) is None:
                try:
                    response.parent_message_id = message.id
                except Exception:
                    pass
            try:
                self._agent_bus.send_message(response)
            except Exception:
                pass

    def receive(self, message: AgentMessage) -> AgentMessage:
        """Process an inbound message before task handling or review."""
        if not self.validate_message(message):
            raise ValueError("message must be an AgentMessage instance")
        return message


class ResearchAgent(BaseAgent):
    """A simple research specialist agent that demonstrates the base contract."""

    def __init__(self) -> None:
        super().__init__(
            name="Research",
            role="Research Specialist",
            description="Collects market and competitive intelligence for mission objectives.",
        )
        self._started = False

    def initialize(self) -> None:
        self._started = True
        self.log("ResearchAgent initialized.")

    def can_handle(self, mission: Mission) -> bool:
        return "research" in mission.objective.lower()

    def handle_task(self, message: AgentMessage) -> AgentMessage:
        self.receive(message)
        response = message.model_copy(deep=True, update={
            "sender": self.name,
            "receiver": message.sender,
            "message_type": message.message_type,
            "content": f"Research analysis for objective: {message.content}",
            "confidence": 0.9,
        })
        return self.send(response)

    def review(self, message: AgentMessage) -> AgentMessage:
        self.receive(message)
        response = message.model_copy(deep=True, update={
            "sender": self.name,
            "receiver": message.sender,
            "message_type": message.message_type,
            "content": "Research review completed.",
            "confidence": 0.95,
        })
        return self.send(response)

    def health(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "healthy" if self._started else "initializing",
            "role": self.role,
        }

    def shutdown(self) -> None:
        self._started = False
        self.log("ResearchAgent has shut down.")


if __name__ == "__main__":
    from uuid import uuid4

    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Research AI startups in Europe for acquisition.",
        created_by="CEO",
    )

    task_message = AgentMessage(
        id=uuid4(),
        mission_id=mission.id,
        sender="CEO",
        receiver="Research",
        message_type=MessageType.TASK,
        priority=Priority.HIGH,
        content="Gather target evaluation criteria and identify risks.",
        confidence=1.0,
    )

    research_agent = ResearchAgent()
    research_agent.initialize()
    if research_agent.can_handle(mission):
        response = research_agent.handle_task(task_message)
        print("Response message:", response.to_dict())
        print("Health status:", research_agent.health())
    research_agent.shutdown()
