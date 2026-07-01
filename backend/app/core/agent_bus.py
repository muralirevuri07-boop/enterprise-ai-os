from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from threading import Lock
from typing import Callable
from uuid import UUID

try:
    from .conversation import MissionConversation
    from .message import AgentMessage, MessageType, Priority
    from .mission import Mission
except ImportError:
    from conversation import MissionConversation
    from message import AgentMessage, MessageType, Priority
    from mission import Mission


AgentCallback = Callable[[AgentMessage], AgentMessage | None]


class AgentBus:
    """Thread-safe direct message bus for a mission conversation.

    ``AgentBus`` coordinates synchronous agent-to-agent dispatch for one
    ``MissionConversation``. Every accepted message is validated, deep-copied,
    stored chronologically, and delivered to the registered listener whose name
    matches the message receiver. If a listener returns a response message, the
    bus dispatches that response immediately, allowing simple agent workflows to
    chain while still enforcing duplicate-message and maximum-depth protections.
    """

    def __init__(self, conversation: MissionConversation, max_depth: int = 10) -> None:
        """Create a bus for ``conversation``.

        Args:
            conversation: Conversation that owns all messages accepted by this
                bus. Messages for any other mission are rejected.
            max_depth: Maximum recursive listener-response depth allowed during
                one dispatch chain. The value must be at least ``1``.
        """
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")

        self._conversation: MissionConversation = conversation
        self._listeners: dict[str, AgentCallback] = {}
        self._history: list[AgentMessage] = []
        self._processed_ids: set[UUID] = set()
        self._lock: Lock = Lock()
        self._max_depth: int = max_depth

    @property
    def mission_id(self) -> UUID:
        """Return the mission identifier served by this bus."""
        return self._conversation.mission_id

    def register(self, agent_name: str, callback: AgentCallback) -> None:
        """Register a receiver callback for an agent.

        The callback receives a deep-copied ``AgentMessage`` and may return a
        new ``AgentMessage`` to continue the dispatch chain. Registering a name
        that already exists replaces the previous callback.
        """
        normalized_name = self._normalize_agent(agent_name)
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            self._listeners[normalized_name] = callback

    def unregister(self, agent_name: str) -> None:
        """Remove an agent listener registration.

        Unregistering an unknown agent is treated as an idempotent no-op.
        """
        normalized_name = self._normalize_agent(agent_name)
        with self._lock:
            self._listeners.pop(normalized_name, None)

    def send(self, message: AgentMessage) -> AgentMessage | None:
        """Store and deliver one message to its registered receiver.

        ``None`` values are ignored for runtime robustness. Duplicate message
        IDs, mission mismatches, unknown receivers, and recursive dispatch
        chains beyond ``_max_depth`` are rejected.
        """
        return self._send(message, depth=0)

    def broadcast(self, messages: list[AgentMessage]) -> list[AgentMessage]:
        """Send multiple messages in the provided order.

        ``None`` entries are ignored. The return value contains the non-``None``
        listener responses produced directly by each top-level message, in the
        same order as the accepted input messages.
        """
        responses: list[AgentMessage] = []
        for message in messages:
            if message is None:
                continue
            response = self.send(message)
            if response is not None:
                responses.append(deepcopy(response))
        return responses

    def history(self) -> list[AgentMessage]:
        """Return a deep-copied chronological history of accepted messages."""
        with self._lock:
            return deepcopy(self._history)

    def latest(self) -> AgentMessage | None:
        """Return the latest accepted message, or ``None`` if the bus is empty."""
        with self._lock:
            if not self._history:
                return None
            return deepcopy(self._history[-1])

    def messages_for(self, agent: str) -> list[AgentMessage]:
        """Return all messages sent or received by ``agent``."""
        normalized_agent = self._normalize_agent(agent)
        with self._lock:
            return deepcopy(
                [
                    message
                    for message in self._history
                    if message.sender == normalized_agent or message.receiver == normalized_agent
                ]
            )

    def pending(self, agent: str) -> list[AgentMessage]:
        """Return response-requiring messages addressed to ``agent``.

        The bus dispatches synchronously, so "pending" means messages whose
        receiver is ``agent`` and whose ``requires_response`` flag is set. The
        returned messages are deep copies in chronological order.
        """
        normalized_agent = self._normalize_agent(agent)
        grouped: defaultdict[str, list[AgentMessage]] = defaultdict(list)

        with self._lock:
            for message in self._history:
                if message.receiver == normalized_agent and message.requires_response:
                    grouped[normalized_agent].append(message)
            return deepcopy(grouped[normalized_agent])

    def participants(self) -> list[str]:
        """Return all conversation participants as a sorted list."""
        return self._conversation.participants_list()

    def clear(self) -> None:
        """Clear stored messages and processed IDs while preserving listeners."""
        with self._lock:
            self._history.clear()
            self._processed_ids.clear()
        self._conversation.clear()

    def _send(self, message: AgentMessage | None, depth: int) -> AgentMessage | None:
        """Internal recursive dispatch implementation."""
        if message is None:
            return None
        if depth > self._max_depth:
            raise RuntimeError(f"self-recursive dispatch exceeded max_depth={self._max_depth}")
        if message.mission_id != self._conversation.mission_id:
            raise ValueError(
                f"message mission_id {message.mission_id} does not match bus mission_id {self._conversation.mission_id}"
            )

        stored_message = deepcopy(message)

        with self._lock:
            if stored_message.id in self._processed_ids:
                raise ValueError(f"duplicate message id rejected: {stored_message.id}")

            listener = self._listeners.get(stored_message.receiver)
            if listener is None:
                raise ValueError(f"unknown receiver rejected: {stored_message.receiver}")

            self._processed_ids.add(stored_message.id)

        try:
            self._conversation.add_message(stored_message)
        except Exception:
            with self._lock:
                self._processed_ids.discard(stored_message.id)
            raise

        with self._lock:
            self._history.append(deepcopy(stored_message))

        listener_message = deepcopy(stored_message)
        response = listener(listener_message)
        if response is None:
            return None

        response_copy = deepcopy(response)
        self._send(response_copy, depth=depth + 1)
        return deepcopy(response_copy)

    @staticmethod
    def _normalize_agent(agent_name: str) -> str:
        """Return a stripped non-empty agent name."""
        normalized_name = agent_name.strip()
        if not normalized_name:
            raise ValueError("agent_name must be a non-empty string")
        return normalized_name


if __name__ == "__main__":
    mission = Mission(
        title="Research AI startups in Europe for acquisition.",
        objective="Coordinate research and finance review for European AI acquisition targets.",
    )
    conversation = MissionConversation.from_mission(mission)
    bus = AgentBus(conversation=conversation)

    def ceo_listener(message: AgentMessage) -> AgentMessage | None:
        print(f"CEO received: {message.content}")
        return None

    def research_listener(message: AgentMessage) -> AgentMessage | None:
        print(f"Research received: {message.content}")
        if message.sender == "CEO":
            return AgentMessage(
                mission_id=mission.id,
                sender="Research",
                receiver="Finance",
                message_type=MessageType.QUESTION,
                priority=Priority.MEDIUM,
                content="Can you assess revenue quality and valuation ranges for the shortlist?",
                parent_message_id=message.id,
                requires_response=True,
            )
        if message.sender == "Finance":
            return AgentMessage(
                mission_id=mission.id,
                sender="Research",
                receiver="CEO",
                message_type=MessageType.RESPONSE,
                priority=Priority.HIGH,
                content="Finance validated two targets for deeper diligence.",
                parent_message_id=message.id,
                confidence=0.88,
            )
        return None

    def finance_listener(message: AgentMessage) -> AgentMessage | None:
        print(f"Finance received: {message.content}")
        return AgentMessage(
            mission_id=mission.id,
            sender="Finance",
            receiver="Research",
            message_type=MessageType.RESPONSE,
            priority=Priority.MEDIUM,
            content="Two companies show durable revenue and acceptable valuation ranges.",
            parent_message_id=message.id,
            confidence=0.84,
        )

    bus.register("CEO", ceo_listener)
    bus.register("Research", research_listener)
    bus.register("Finance", finance_listener)

    bus.send(
        AgentMessage(
            mission_id=mission.id,
            sender="CEO",
            receiver="Research",
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content="Research AI startups in Europe for acquisition.",
            requires_response=True,
        )
    )

    print("Participants:", bus.participants())
    print("Conversation history:")
    for item in bus.history():
        print(item.summary())
