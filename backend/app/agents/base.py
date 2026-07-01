from __future__ import annotations

import abc
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

try:
    from app.core.agent_bus import AgentBus
    from app.core.conversation import MissionConversation
    from app.core.message import AgentMessage, MessageType, Priority
    from app.core.mission import Mission
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from core.agent_bus import AgentBus
    from core.conversation import MissionConversation
    from core.message import AgentMessage, MessageType, Priority
    from core.mission import Mission


class BaseAgent(abc.ABC):
    """Abstract foundation for Enterprise AI OS agents.

    ``BaseAgent`` provides the shared runtime behavior every concrete agent
    needs: immutable identity, bus registration, inbound message validation,
    duplicate-message protection, routing by message type, outbound dispatch,
    metadata storage, and JSON-safe operational introspection.

    Subclasses implement domain behavior through the abstract lifecycle and
    processing methods. The bus calls ``receive`` directly when a message is
    addressed to the agent; ``receive`` then routes tasks to ``handle_task`` and
    reviewable artifacts to ``review``.
    """

    _REVIEW_MESSAGE_TYPES: frozenset[MessageType] = frozenset(
        {
            MessageType.RESPONSE,
            MessageType.ANSWER,
            MessageType.EVIDENCE,
            MessageType.APPROVAL,
        }
    )

    def __init__(self, name: str, role: str, description: str, bus: AgentBus) -> None:
        """Create and register an agent on an ``AgentBus``.

        Args:
            name: Unique bus-facing agent name. Incoming messages must use this
                value as their receiver.
            role: Human-readable operating role for monitoring and governance.
            description: Concise explanation of the agent's responsibility.
            bus: Message bus used for receiving and sending ``AgentMessage``
                instances.

        Raises:
            ValueError: If ``name``, ``role``, or ``description`` is empty.
            TypeError: If ``bus`` does not provide the required bus interface.
        """
        self._name = self._normalize_text(name, "name")
        self._role = self._normalize_text(role, "role")
        self._description = self._normalize_text(description, "description")
        if not all(hasattr(bus, attribute) for attribute in ("register", "send", "mission_id")):
            raise TypeError("bus must provide register(), send(), and mission_id")

        self._id: UUID = uuid4()
        self._created_at: datetime = datetime.now(timezone.utc)
        self._processed_messages: set[UUID] = set()
        self._metadata: dict[str, Any] = {}
        self._bus: AgentBus = bus
        self._lock: Lock = Lock()

        self._bus.register(self._name, self.receive)

    @property
    def id(self) -> UUID:
        """Stable immutable identifier for this agent instance."""
        return self._id

    @property
    def name(self) -> str:
        """Bus-facing canonical agent name."""
        return self._name

    @property
    def role(self) -> str:
        """Human-readable role assigned to the agent."""
        return self._role

    @property
    def description(self) -> str:
        """Short operational description of the agent."""
        return self._description

    @property
    def created_at(self) -> datetime:
        """Timezone-aware UTC creation timestamp."""
        return self._created_at

    @property
    def processed_messages(self) -> set[UUID]:
        """Return a snapshot of processed message identifiers."""
        with self._lock:
            return set(self._processed_messages)

    @property
    def metadata(self) -> dict[str, Any]:
        """Return a deep-copied snapshot of mutable agent metadata."""
        with self._lock:
            return deepcopy(self._metadata)

    @abc.abstractmethod
    def initialize(self) -> None:
        """Prepare the agent for work after construction."""

    @abc.abstractmethod
    def can_handle(self, mission: Mission) -> bool:
        """Return whether this agent is suitable for ``mission``."""

    @abc.abstractmethod
    def handle_task(self, message: AgentMessage) -> AgentMessage | None:
        """Handle a task message and optionally return a response message."""

    @abc.abstractmethod
    def review(self, message: AgentMessage) -> AgentMessage | None:
        """Review a response, answer, evidence item, or approval message."""

    @abc.abstractmethod
    def health(self) -> dict[str, Any]:
        """Return operational health details for monitoring."""

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Release resources and stop accepting work gracefully."""

    def send(self, message: AgentMessage) -> AgentMessage | None:
        """Send an outbound message through the attached bus.

        Outbound messages must be valid ``AgentMessage`` instances for the same
        mission as the bus, and their sender must match this agent's name. The
        bus performs receiver validation and duplicate protection.
        """
        if not self._looks_like_message(message):
            raise TypeError("message must provide the AgentMessage interface")
        if message.sender != self.name:
            raise ValueError(f"outbound message sender must be {self.name}")
        if message.mission_id != self._bus.mission_id:
            raise ValueError("outbound message mission_id does not match the agent bus")
        return self._bus.send(message)

    def receive(self, message: AgentMessage) -> AgentMessage | None:
        """Validate, deduplicate, and route an inbound message."""
        if not self.validate_message(message):
            raise ValueError(f"message is not addressed to agent {self.name}")

        if self.has_processed(message.id):
            return None
        self.mark_processed(message.id)

        if self._message_type_matches(message.message_type, MessageType.TASK):
            result = self.handle_task(message)
            self._report_to_agentwatch(
                event_type=str(message.message_type.value),
                input_data=str(message.content)[:500],
                output_data=str(result.content)[:500] if result else None,
                confidence=getattr(result, "confidence", None),
            )
            return result
        if any(self._message_type_matches(message.message_type, mt) for mt in self._REVIEW_MESSAGE_TYPES):
            return self.review(message)
        return None

    def _report_to_agentwatch(self, event_type: str, input_data: str = None, output_data: str = None, confidence: float = None) -> None:
        import os, threading, requests
        api_key = os.getenv("AGENTWATCH_API_KEY")
        api_url = os.getenv("AGENTWATCH_URL", "https://agentwatch-8eap.onrender.com")
        if not api_key:
            return
        payload = {
            "api_key": api_key,
            "agent_name": self._name,
            "event_type": event_type,
            "input_data": input_data,
            "output_data": output_data,
            "confidence": confidence,
            "is_irreversible": any(k in event_type.lower() for k in ["hire", "fire", "invest", "pricing", "contract", "deploy"]),
        }
        def send():
            try:
                requests.post(f"{api_url}/v1/event", json=payload, timeout=5)
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()
    def validate_message(self, message: AgentMessage) -> bool:
        """Return whether ``message`` is a valid inbound message for this agent."""
        return (
            self._looks_like_message(message)
            and message.receiver == self.name
            and message.mission_id == self._bus.mission_id
        )

    def mark_processed(self, message_id: UUID) -> None:
        """Record a message ID as processed in a thread-safe way."""
        with self._lock:
            self._processed_messages.add(message_id)

    def has_processed(self, message_id: UUID) -> bool:
        """Return whether a message ID has already been processed."""
        with self._lock:
            return message_id in self._processed_messages

    def reset(self) -> None:
        """Clear processed-message state and metadata.

        The agent identity, creation timestamp, and bus registration are
        preserved. This is useful for deterministic tests and mission-local
        reuse where an agent should forget prior message state.
        """
        with self._lock:
            self._processed_messages.clear()
            self._metadata.clear()

    def info(self) -> dict[str, Any]:
        """Return JSON-safe identity and runtime information."""
        with self._lock:
            return {
                "id": str(self._id),
                "name": self._name,
                "role": self._role,
                "description": self._description,
                "created_at": self._created_at.isoformat(),
                "processed_messages": [str(message_id) for message_id in sorted(self._processed_messages)],
                "metadata": deepcopy(self._metadata),
            }

    @staticmethod
    def _normalize_text(value: str, field_name: str) -> str:
        """Strip and validate required constructor text."""
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must be a non-empty string")
        return normalized

    @staticmethod
    def _looks_like_message(message: object) -> bool:
        """Return whether an object provides the required message interface."""
        return all(
            hasattr(message, attribute)
            for attribute in ("id", "mission_id", "sender", "receiver", "message_type")
        )

    @staticmethod
    def _message_type_matches(actual: object, expected: MessageType) -> bool:
        """Return whether two message type representations are equivalent."""
        return getattr(actual, "value", actual) == expected.value


class ExampleAgent(BaseAgent):
    """Minimal concrete agent used to demonstrate the base contract."""

    def __init__(self, bus: AgentBus) -> None:
        super().__init__(
            name="ExampleAgent",
            role="Example Responder",
            description="Demonstrates task handling with a simple response.",
            bus=bus,
        )
        self._started = False

    def initialize(self) -> None:
        """Mark the example agent as ready."""
        self._started = True

    def can_handle(self, mission: Mission) -> bool:
        """Handle missions that include the example agent or mention examples."""
        return self.name in mission.assigned_agents or "example" in mission.objective.lower()

    def handle_task(self, message: AgentMessage) -> AgentMessage | None:
        """Return a concise response to the sender of a task."""
        return AgentMessage(
            mission_id=message.mission_id,
            sender=self.name,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            priority=Priority.MEDIUM,
            content=f"ExampleAgent completed task: {message.content}",
            confidence=0.95,
            parent_message_id=message.id,
        )

    def review(self, message: AgentMessage) -> AgentMessage | None:
        """Acknowledge reviewed artifacts without starting another workflow."""
        return AgentMessage(
            mission_id=message.mission_id,
            sender=self.name,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            priority=Priority.LOW,
            content=f"ExampleAgent reviewed message {message.id}.",
            confidence=0.9,
            parent_message_id=message.id,
        )

    def health(self) -> dict[str, Any]:
        """Return example-agent readiness state."""
        return {
            "name": self.name,
            "role": self.role,
            "status": "healthy" if self._started else "initializing",
        }

    def shutdown(self) -> None:
        """Mark the example agent as stopped."""
        self._started = False


if __name__ == "__main__":
    mission = Mission(
        title="Example agent task.",
        objective="Demonstrate CEO to ExampleAgent task handling.",
        assigned_agents=["ExampleAgent"],
    )
    conversation = MissionConversation.from_mission(mission)
    bus = AgentBus(conversation=conversation)

    def ceo_listener(message: AgentMessage) -> AgentMessage | None:
        print("CEO received:", message.content)
        return None

    bus.register("CEO", ceo_listener)

    agent = ExampleAgent(bus)
    agent.initialize()

    bus.send(
        AgentMessage(
            mission_id=mission.id,
            sender="CEO",
            receiver="ExampleAgent",
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content="Summarize the acquisition research workflow.",
            requires_response=True,
        )
    )

    print("Agent info:", agent.info())
    print("Conversation messages:", [message.summary() for message in bus.history()])
    agent.shutdown()
