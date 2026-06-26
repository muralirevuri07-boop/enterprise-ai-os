from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.research_agent import ResearchAgent
from app.core.agent_bus import AgentBus
from app.core.conversation import MissionConversation
from app.core.mission import Mission, MissionStatus
from app.core.orchestrator import Orchestrator
from app.core.message import MessageType


def test_mission_flow_end_to_end() -> None:
    """Verify the complete mission execution flow from assignment to CEO decision."""
    agent_bus = AgentBus()

    mission = Mission(
        title="Research AI startups in Europe",
        objective="Identify promising AI startups in Europe for potential partnership or acquisition.",
        created_by="CEO",
    )

    conversation = MissionConversation(mission_id=mission.conversation_id, agent_bus=agent_bus)
    research_agent = ResearchAgent()
    orchestrator = Orchestrator(agent_bus=agent_bus)
    orchestrator.register_agent(research_agent)

    try:
        report = orchestrator.execute_mission(mission)
    except Exception as exc:
        print("Mission execution failed with exception:")
        traceback.print_exc()
        raise

    timeline = conversation.timeline()
    research_responses = [message for message in timeline if message.sender == research_agent.name and message.message_type == MessageType.RESPONSE]

    print(f"Mission ID: {mission.id}")
    print(f"Mission Status: {mission.status.name}")
    print(f"Registered Agents: {orchestrator.available_agents()}")
    print("Conversation Timeline:")
    for message in timeline:
        print(message.summary())

    if research_responses:
        print("Research Agent Response:", research_responses[-1].content)
    print("CEO Final Decision:", report.final_decision)
    print("MISSION COMPLETED SUCCESSFULLY")

    assert mission.status == MissionStatus.COMPLETED
    assert report.final_decision
    assert research_responses
    assert timeline
    assert research_agent.name in orchestrator.available_agents()
