from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    from app.agents.base import BaseAgent
    from app.core.agent_bus import AgentBus
    from app.core.conversation import MissionConversation
    from app.core.message import AgentMessage, MessageType, Priority
    from app.core.mission import Mission
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from agents.base import BaseAgent
    from core.agent_bus import AgentBus
    from core.conversation import MissionConversation
    from core.message import AgentMessage, MessageType, Priority
    from core.mission import Mission


MarketingPayload = dict[str, object]


class MarketingAgent(BaseAgent):
    """
    Enterprise AI OS Marketing Agent.

    Responsibilities
    - Market analysis
    - ICP generation
    - TAM/SAM/SOM estimation
    - Competitor landscape
    - Positioning
    - Go-To-Market strategy
    - Marketing risk analysis

    Deterministic implementation.
    No external APIs.
    """

    _MARKETING_TERMS = frozenset(
        {
            "market",
            "customer",
            "startup",
            "competition",
            "pricing",
            "growth",
            "launch",
            "marketing",
            "brand",
            "product",
            "positioning",
            "sales",
            "gtm",
            "go-to-market",
            "acquisition",
        }
    )

    def __init__(self, bus: AgentBus | None = None) -> None:
        resolved_bus = bus if bus else self._default_bus()

        super().__init__(
            name="Marketing",
            role="Marketing Strategist",
            description="Analyzes markets and builds GTM strategies.",
            bus=resolved_bus,
        )

        self._started = False
        self._analysis: dict[UUID, MarketingPayload] = {}

    def initialize(self) -> None:
        self._started = True

    def shutdown(self) -> None:
        self._started = False
        self._analysis.clear()

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "status": "healthy" if self._started else "initializing",
            "processed_messages": len(self.processed_messages),
            "tracked_threads": len(self._analysis),
        }

    def can_handle(self, mission: Mission) -> bool:
        text = f"{mission.title} {mission.objective}".lower()

        return (
            self.name in mission.assigned_agents
            or any(term in text for term in self._MARKETING_TERMS)
        )

    def receive(self, message: AgentMessage):
        if not self.validate_message(message):
            raise ValueError("Message not intended for Marketing.")

        if self.has_processed(message.id):
            return None

        self.mark_processed(message.id)

        if message.message_type in (
            MessageType.TASK,
            MessageType.QUESTION,
        ):
            return self.handle_task(message)

        return self.review(message)

    def handle_task(self, message: AgentMessage):
        payload = self._generate_analysis(message.content)

        thread = message.parent_message_id or message.id

        self._analysis[thread] = deepcopy(payload)

        return AgentMessage(
            mission_id=message.mission_id,
            sender=self.name,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            priority=Priority.MEDIUM,
            content=json.dumps(payload, indent=2),
            confidence=float(payload["confidence"]),
            metadata={
                "agent": "Marketing",
                "structured": True,
            },
            requires_response=False,
            parent_message_id=message.id,
        )

    def review(self, message: AgentMessage):
        thread = message.parent_message_id or message.id

        payload = deepcopy(
            self._analysis.get(thread, self._generate_analysis(message.content))
        )

        payload["reviewed"] = True
        payload["recommended_next_step"] = (
            "CEO should validate GTM assumptions before execution."
        )

        return AgentMessage(
            mission_id=message.mission_id,
            sender=self.name,
            receiver=message.sender,
            message_type=MessageType.RESPONSE,
            priority=Priority.MEDIUM,
            content=json.dumps(payload, indent=2),
            confidence=float(payload["confidence"]),
            metadata={
                "review": True,
            },
            requires_response=False,
            parent_message_id=message.id,
        )

    def _generate_analysis(self, text: str) -> MarketingPayload:
        keywords = self._keywords(text)

        return {
            "executive_summary":
                "Market opportunity appears attractive based on the supplied mission context.",

            "target_market": {
                "primary": "Technology organizations",
                "secondary": "Enterprise digital transformation teams",
            },

            "ideal_customer_profile": {
                "industry": "Technology",
                "company_size": "50-5000 employees",
                "decision_makers": [
                    "CEO",
                    "CTO",
                    "Head of AI",
                    "Product Director",
                ],
                "pain_points": [
                    "Slow decision making",
                    "Fragmented AI tools",
                    "Poor operational visibility",
                ],
            },

            "tam": {
                "description":
                    "Global organizations investing in AI transformation.",
                "confidence": "Medium",
            },

            "sam": {
                "description":
                    "Mid-market and enterprise companies adopting GenAI.",
                "confidence": "Medium",
            },

            "som": {
                "description":
                    "Early adopters reachable within first GTM phase.",
                "confidence": "Medium",
            },

            "competitors": [
                {
                    "name": "Microsoft Copilot",
                    "strength": "Enterprise ecosystem",
                    "weakness": "Limited customization",
                },
                {
                    "name": "OpenAI Enterprise",
                    "strength": "General intelligence",
                    "weakness": "Not vertically specialized",
                },
                {
                    "name": "Anthropic Claude",
                    "strength": "Safety",
                    "weakness": "Smaller ecosystem",
                },
            ],

            "positioning": (
                "Enterprise AI Operating System enabling multiple AI agents "
                "to collaborate on strategic business decisions."
            ),

            "marketing_channels": [
                "LinkedIn",
                "GitHub",
                "Technical blogs",
                "AI conferences",
                "Product Hunt",
                "Founder communities",
            ],

            "acquisition_strategy": [
                "Content marketing",
                "Thought leadership",
                "Case studies",
                "Open-source demo",
                "Founder outreach",
            ],

            "pricing_strategy": {
                "starter": "Free",
                "professional": "Subscription",
                "enterprise": "Custom pricing",
            },

            "launch_plan": [
                "Private alpha",
                "Pilot customers",
                "Public beta",
                "Enterprise launch",
            ],

            "marketing_risks": [
                {
                    "severity": "High",
                    "risk": "Crowded AI market",
                    "mitigation": "Differentiate using multi-agent collaboration",
                },
                {
                    "severity": "Medium",
                    "risk": "Low awareness",
                    "mitigation": "Educational content",
                },
                {
                    "severity": "Medium",
                    "risk": "Long enterprise sales cycle",
                    "mitigation": "Pilot programs",
                },
            ],

            "keywords": keywords,

            "confidence": 0.86,

            "recommended_next_step":
                "Validate ICP with pilot customers and refine GTM messaging.",
        }

    @staticmethod
    def _keywords(text: str) -> list[str]:
        words = re.findall(r"[A-Za-z]{4,}", text.lower())

        stop = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "will",
            "into",
            "about",
            "their",
            "there",
            "which",
            "should",
            "would",
            "could",
            "using",
        }

        seen = set()
        result = []

        for word in words:
            if word in stop:
                continue

            if word not in seen:
                seen.add(word)
                result.append(word)

        return result[:15]

    @staticmethod
    def _default_bus() -> AgentBus:
        """
        Create an isolated AgentBus so the agent can be instantiated
        before being attached to an Orchestrator.
        """
        mission = Mission(
            title="Marketing Control Mission",
            objective="Initialize MarketingAgent.",
            assigned_agents=["Marketing"],
        )

        conversation = MissionConversation.from_mission(mission)
        return AgentBus(conversation)


def run_marketing_agent(task: str) -> str:
    """
    Compatibility helper for standalone execution.
    """

    agent = MarketingAgent()

    try:
        mission = Mission(
            title="Standalone Marketing Task",
            objective=task,
            assigned_agents=["Marketing"],
        )

        conversation = MissionConversation.from_mission(mission)
        bus = AgentBus(conversation)

        responses: list[AgentMessage] = []

        def requester(message: AgentMessage):
            responses.append(message)
            return None

        bus.register("Requester", requester)

        setattr(agent, "_bus", bus)

        bus.register(agent.name, agent.receive)

        agent.initialize()

        bus.send(
            AgentMessage(
                mission_id=mission.id,
                sender="Requester",
                receiver="Marketing",
                message_type=MessageType.TASK,
                priority=Priority.HIGH,
                content=task,
                confidence=1.0,
                requires_response=True,
            )
        )

        if not responses:
            raise RuntimeError("MarketingAgent produced no response.")

        return responses[-1].content

    finally:
        agent.shutdown()


if __name__ == "__main__":

    mission = Mission(
        title="AI OS Launch",
        objective=(
            "Build a go-to-market strategy for an Enterprise AI Operating "
            "System targeting enterprise customers."
        ),
        assigned_agents=["Marketing"],
    )

    conversation = MissionConversation.from_mission(mission)

    bus = AgentBus(conversation)

    def ceo_listener(message: AgentMessage):
        print("\n===== MARKETING REPORT =====\n")
        print(message.content)
        return None

    bus.register("CEO", ceo_listener)

    marketing = MarketingAgent(bus)

    marketing.initialize()

    bus.send(
        AgentMessage(
            mission_id=mission.id,
            sender="CEO",
            receiver="Marketing",
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content=(
                "Prepare a GTM strategy for Enterprise AI OS. "
                "Identify ICP, TAM, SAM, SOM, competitors, "
                "marketing channels, pricing, positioning, "
                "launch strategy and risks."
            ),
            confidence=1.0,
            requires_response=True,
        )
    )

    print("\n===== HEALTH =====")
    print(json.dumps(marketing.health(), indent=2))

    marketing.shutdown()