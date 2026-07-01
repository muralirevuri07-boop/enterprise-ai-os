from __future__ import annotations

from bisect import bisect_right
from threading import Lock
from typing import Dict, List
from uuid import UUID, uuid4

from app.core.message import AgentMessage, MessageType, Priority


class AgentBus:
    """Thread-safe internal bus for agent-to-agent communication.

    The AgentBus stores messages grouped by mission_id and preserves the
    chronological ordering of every mission conversation. It supports multiple
    concurrent missions and provides query methods for mission and agent
    interactions while protecting stored messages from accidental mutation.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._conversations: Dict[UUID, List[AgentMessage]] = {}
        self._listeners: Dict[str, callable] = {}
        self._observers: List[callable] = []
        self.max_depth: int = 10

    def _clone_message(self, message: AgentMessage) -> AgentMessage:
        return message.model_copy(deep=True)

    def _insert_chronologically(self, mission_id: UUID, message: AgentMessage) -> None:
        conversation = self._conversations.setdefault(mission_id, [])
        if not conversation or message.timestamp >= conversation[-1].timestamp:
            conversation.append(message)
            return

        timestamps = [item.timestamp for item in conversation]
        index = bisect_right(timestamps, message.timestamp)
        conversation.insert(index, message)

    def send_message(self, message: AgentMessage) -> None:
        """Publish a single AgentMessage to its mission conversation.

        The message is stored in timestamp order and isolated from subsequent
        external mutation by keeping a deep copy internally.

        Args:
            message: The AgentMessage to publish.

        Raises:
            TypeError: If the provided value is not an AgentMessage.
        """
        if not isinstance(message, AgentMessage):
            raise TypeError("message must be an AgentMessage instance")

        copy = self._clone_message(message)
        # enforce and propagate a depth counter in metadata to avoid infinite cycles
        depth = int(copy.metadata.get("depth", 0) or 0) + 1
        copy.metadata = {**copy.metadata, "depth": depth}
        # Insert message under lock, but notify listeners/observers after releasing it
        listener = None
        observers: List[callable] = []
        with self._lock:
            self._insert_chronologically(copy.mission_id, copy)
            # capture recipient listener and observers to notify outside the lock
            listener = self._listeners.get(copy.receiver)
            observers = list(self._observers)

        # Notify observer callbacks and the specific recipient listener outside the lock
        for obs in observers:
            try:
                obs(copy.model_copy(deep=True))
            except Exception:
                continue

        # If message depth exceeds maximum, do not deliver to agent listeners to prevent cycles.
        if depth > self.max_depth:
            return

        if listener:
            try:
                listener(copy.model_copy(deep=True))
            except Exception:
                pass

    def broadcast(self, message: AgentMessage, recipients: List[str]) -> None:
        """Publish a message to a list of recipients within the same mission.

        Each recipient receives an isolated copy of the original message, which
        preserves the message ordering and keeps stored messages immutable.

        Args:
            message: The base AgentMessage to broadcast.
            recipients: Names of agents that should receive the broadcast.

        Raises:
            TypeError: If the provided value is not an AgentMessage.
            ValueError: If recipients is empty or contains only blank names.
        """
        if not isinstance(message, AgentMessage):
            raise TypeError("message must be an AgentMessage instance")

        cleaned_recipients = [recipient.strip() for recipient in recipients if recipient.strip()]
        if not cleaned_recipients:
            raise ValueError("recipients must contain at least one non-empty agent name")

        for recipient in cleaned_recipients:
            broadcast_message = message.model_copy(
                deep=True,
                update={
                    "receiver": recipient,
                    "metadata": {**message.metadata, "broadcast": True, "recipient": recipient},
                },
            )
            self.send_message(broadcast_message)

    def register_listener(self, agent_name: str, callback: callable) -> None:
        """Register a callback to be invoked when a message addressed to agent_name arrives.

        The callback receives a single argument: an `AgentMessage` copy.
        """
        name = agent_name.strip()
        if not name:
            raise ValueError("agent_name must be a non-empty string")
        with self._lock:
            self._listeners[name] = callback

    def unregister_listener(self, agent_name: str) -> None:
        name = agent_name.strip()
        if not name:
            return
        with self._lock:
            self._listeners.pop(name, None)

    def register_observer(self, callback: callable) -> None:
        """Register an observer callback that receives every message published on the bus."""
        with self._lock:
            self._observers.append(callback)

    def unregister_observer(self, callback: callable) -> None:
        with self._lock:
            try:
                self._observers.remove(callback)
            except ValueError:
                pass

    def get_messages(self, mission_id: UUID) -> List[AgentMessage]:
        """Return a chronological list of messages for the requested mission."""
        with self._lock:
            return [message.model_copy(deep=True) for message in self._conversations.get(mission_id, [])]

    def conversation_history(self, mission_id: UUID) -> List[AgentMessage]:
        """Return the mission conversation history. Alias for get_messages."""
        return self.get_messages(mission_id)

    def latest_message(self, mission_id: UUID) -> AgentMessage | None:
        """Return the latest message for the requested mission, or None if empty."""
        with self._lock:
            conversation = self._conversations.get(mission_id)
            if not conversation:
                return None
            return conversation[-1].model_copy(deep=True)

    def pending_messages(self, agent_name: str) -> List[AgentMessage]:
        """Return messages that are addressed to the given agent."""
        name = agent_name.strip()
        if not name:
            return []

        with self._lock:
            pending: List[AgentMessage] = []
            for conversation in self._conversations.values():
                for message in conversation:
                    if message.receiver == name:
                        pending.append(message.model_copy(deep=True))
            pending.sort(key=lambda message: message.timestamp)
            return pending

    def get_agent_messages(self, agent_name: str) -> List[AgentMessage]:
        """Return all messages sent or received by the specified agent."""
        name = agent_name.strip()
        if not name:
            return []

        with self._lock:
            results: List[AgentMessage] = []
            for conversation in self._conversations.values():
                for message in conversation:
                    if message.sender == name or message.receiver == name:
                        results.append(message.model_copy(deep=True))
            results.sort(key=lambda message: message.timestamp)
            return results

    def clear_mission(self, mission_id: UUID) -> None:
        """Remove all stored messages for a specific mission."""
        with self._lock:
            self._conversations.pop(mission_id, None)

    def clear_all(self) -> None:
        """Remove all stored messages from the bus."""
        with self._lock:
            self._conversations.clear()


if __name__ == "__main__":
    mission_id = uuid4()
    bus = AgentBus()

    task_message = AgentMessage(
        mission_id=mission_id,
        sender="CEO",
        receiver="Research Agent",
        message_type=MessageType.TASK,
        priority=Priority.HIGH,
        content="Evaluate market entry options for our new product line.",
        confidence=0.98,
        requires_response=True,
    )

    evidence_message = AgentMessage(
        mission_id=mission_id,
        sender="Research Agent",
        receiver="CEO",
        message_type=MessageType.EVIDENCE,
        priority=Priority.MEDIUM,
        content="Preliminary research indicates demand strength in the target segment.",
        confidence=0.91,
        requires_response=False,
    )

    bus.send_message(task_message)
    bus.send_message(evidence_message)

    history = bus.conversation_history(mission_id)
    print("Conversation history:")
    for message in history:
        print(message.summary())

    finance_view = bus.get_agent_messages("Finance Agent")
    print("Finance Agent view:", [message.to_dict() for message in finance_view])
