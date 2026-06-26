from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Set, TypedDict
from uuid import UUID

from .agent_bus import AgentBus
from .message import AgentMessage, MessageType, Priority


class ConversationSummary(TypedDict):
    total_messages: int
    participating_agents: List[str]
    first_timestamp: Optional[str]
    last_timestamp: Optional[str]


class MissionConversation:
    """Manage a mission-level conversation across collaborating agents.

    The MissionConversation layer is responsible for creating, routing, and
    summarizing every message exchanged between agents for a single mission.
    It relies on the shared AgentBus to persist messages in timestamp order and
    to isolate message storage from external mutation.
    """

    def __init__(self, mission_id: UUID, agent_bus: AgentBus) -> None:
        self.mission_id = mission_id
        self.agent_bus = agent_bus

    def start(self) -> AgentMessage:
        """Start the mission conversation with a system kickoff message."""
        message = AgentMessage(
            mission_id=self.mission_id,
            sender="System",
            receiver="Mission",
            message_type=MessageType.SYSTEM,
            priority=Priority.MEDIUM,
            content=f"Mission {self.mission_id} conversation started.",
            confidence=1.0,
        )
        self.agent_bus.send_message(message)
        return message

    def send(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: str,
        priority: Priority = Priority.MEDIUM,
        confidence: float = 1.0,
    ) -> AgentMessage:
        """Send a single message from one agent to another."""
        message = AgentMessage(
            mission_id=self.mission_id,
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            priority=priority,
            content=content,
            confidence=confidence,
        )
        self.agent_bus.send_message(message)
        return message

    def broadcast(
        self,
        sender: str,
        recipients: Iterable[str],
        message_type: MessageType,
        content: str,
        priority: Priority = Priority.MEDIUM,
        confidence: float = 1.0,
    ) -> List[AgentMessage]:
        """Broadcast a message from one agent to multiple recipients."""
        cleaned_recipients = [recipient.strip() for recipient in recipients if recipient and recipient.strip()]
        if not cleaned_recipients:
            raise ValueError("recipients must contain at least one non-empty agent name")

        base_message = AgentMessage(
            mission_id=self.mission_id,
            sender=sender,
            receiver=cleaned_recipients[0],
            message_type=message_type,
            priority=priority,
            content=content,
            confidence=confidence,
            metadata={"broadcast": True, "recipients": cleaned_recipients},
        )

        self.agent_bus.broadcast(base_message, cleaned_recipients)

        return [
            base_message.model_copy(
                deep=True,
                update={
                    "receiver": recipient,
                    "metadata": {**base_message.metadata, "recipient": recipient},
                },
            )
            for recipient in cleaned_recipients
        ]

    def history(self) -> List[AgentMessage]:
        """Return the full conversation history for this mission."""
        return self.agent_bus.conversation_history(self.mission_id)

    def timeline(self) -> List[AgentMessage]:
        """Return mission messages ordered by timestamp."""
        return sorted(self.history(), key=lambda message: message.timestamp)

    def participants(self) -> Set[str]:
        """Return all unique agent names that participated in the mission."""
        participants: Set[str] = set()
        for message in self.history():
            participants.add(message.sender)
            participants.add(message.receiver)
        return participants

    def latest(self) -> Optional[AgentMessage]:
        """Return the latest message published in the mission, or None if empty."""
        return self.agent_bus.latest_message(self.mission_id)

    def summary(self) -> ConversationSummary:
        """Return a compact summary of the mission conversation."""
        messages = self.timeline()
        participants = sorted(self.participants())
        first_timestamp = messages[0].timestamp.isoformat() if messages else None
        last_timestamp = messages[-1].timestamp.isoformat() if messages else None

        return ConversationSummary(
            total_messages=len(messages),
            participating_agents=participants,
            first_timestamp=first_timestamp,
            last_timestamp=last_timestamp,
        )

    def export(self) -> dict[str, object]:
        """Return a serializable export payload for the mission conversation."""
        return {
            "mission_id": str(self.mission_id),
            "summary": self.summary(),
            "participants": sorted(self.participants()),
            "messages": [message.to_dict() for message in self.timeline()],
        }


if __name__ == "__main__":
    from uuid import uuid4

    mission_id = uuid4()
    agent_bus = AgentBus()
    conversation = MissionConversation(mission_id=mission_id, agent_bus=agent_bus)

    conversation.start()
    conversation.send(
        sender="CEO",
        receiver="Research",
        message_type=MessageType.TASK,
        content="Please investigate customer adoption trends for our AI product.",
        priority=Priority.HIGH,
    )

    conversation.send(
        sender="Research",
        receiver="Finance",
        message_type=MessageType.QUESTION,
        content="What financial metrics should we use to benchmark adoption growth?",
        priority=Priority.MEDIUM,
        confidence=0.92,
    )

    conversation.send(
        sender="Finance",
        receiver="Research",
        message_type=MessageType.ANSWER,
        content="Use ARR, gross margin, and customer acquisition cost for the first three quarters.",
        priority=Priority.MEDIUM,
        confidence=0.87,
    )

    summary = conversation.summary()
    print("Conversation summary:", summary)
    print("Export payload:", conversation.export())
