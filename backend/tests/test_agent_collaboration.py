from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uuid import uuid4

from app.core.agent_bus import AgentBus
from app.core.conversation import MissionConversation
from app.core.mission import Mission
from app.core.orchestrator import Orchestrator
from app.agents.research_agent import ResearchAgent
from app.agents.finance_agent import FinanceAgent
from app.core.message import MessageType


def test_agent_to_agent_collaboration_flow() -> None:
    bus = AgentBus()
    mission = Mission(
        title="Evaluate funding for pilot",
        objective="Research funding options for pilot deployment",
        created_by="CEO",
    )

    # Ensure CEO assigns only Research for this demo
    mission.assign_agents(["Research"])

    conversation = MissionConversation(mission_id=mission.conversation_id, agent_bus=bus)

    research = ResearchAgent()
    finance = FinanceAgent()

    research.initialize()
    finance.initialize()

    orchestrator = Orchestrator(agent_bus=bus)
    orchestrator.register_agent(research)
    orchestrator.register_agent(finance)

    # Assign tasks; this will send a CEO -> Research TASK which Research will handle,
    # ask Finance, receive Finance's reply, and synthesize back to CEO via the bus.
    orchestrator.assign_tasks(mission)

    timeline = conversation.timeline()

    # Print timeline for debugging
    for msg in timeline:
        print(msg.to_dict())

    # Expected ordered sequence of senders/receivers/types up to Research -> CEO response
    expected_prefix = [
        ("System", "Mission", "SYSTEM"),
        ("CEO", "Research", "TASK"),
        ("Research", "Finance", "QUESTION"),
        ("Finance", "Research", "RESPONSE"),
        ("Research", "CEO", "RESPONSE"),
    ]

    actual = [(m.sender, m.receiver, m.message_type.name) for m in timeline]
    assert len(actual) >= len(expected_prefix)
    assert actual[: len(expected_prefix)] == expected_prefix

    # Ensure Research did not send intermediate progress notifications to CEO
    intermediate_acks = [m for m in timeline if m.sender == "Research" and m.receiver == "CEO" and "requested a finance evaluation" in m.content]
    assert len(intermediate_acks) == 0

    # ensure depth is bounded and no message exceeded bus max depth
    depths = [int(m.metadata.get("depth", 0) or 0) for m in timeline]
    assert all(d <= 10 for d in depths)

    # Emit CEO mission decision and verify it appears at the end of the timeline
    final_decision = "Proceed with pilot under CFO review"
    orchestrator.complete_mission(mission, final_decision=final_decision)

    timeline = conversation.timeline()
    # last message should be the CEO -> Mission decision
    assert timeline[-1].sender == "CEO"
    assert timeline[-1].receiver == "Mission"
    assert timeline[-1].message_type.name == "DECISION"