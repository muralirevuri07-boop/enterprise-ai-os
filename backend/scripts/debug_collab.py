from uuid import uuid4
from app.core.agent_bus import AgentBus
from app.core.conversation import MissionConversation
from app.core.mission import Mission
from app.core.orchestrator import Orchestrator
from app.agents.research_agent import ResearchAgent
from app.agents.finance_agent import FinanceAgent

def run():
    bus = AgentBus()
    mission = Mission(
        title="Debug",
        objective="Research funding options",
        created_by="CEO",
    )
    mission.assign_agents(["Research"])
    conv = MissionConversation(mission.conversation_id, bus)
    research = ResearchAgent(); research.initialize()
    finance = FinanceAgent(); finance.initialize()
    orch = Orchestrator(agent_bus=bus)
    orch.register_agent(research)
    orch.register_agent(finance)
    orch.assign_tasks(mission)
    timeline = conv.timeline()
    for m in timeline:
        print(m.to_dict())

if __name__ == '__main__':
    run()
