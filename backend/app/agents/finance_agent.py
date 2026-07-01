from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_finance_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are a Senior Financial Analyst with strict accuracy standards.

Task: {task}

STRICT RULES:
- NEVER invent specific numbers without assumptions
- Always show calculation formulas
- Always provide ranges not exact figures
- Always state your assumptions explicitly
- Flag all estimates clearly with ⚠️ ESTIMATE

Structure your response as:

## REQUIRED ASSUMPTIONS
(List assumptions needed for financial analysis)

## BUDGET RANGES (not exact numbers)
- Low estimate: $X - $Y (formula: ...)
- Mid estimate: $X - $Y (formula: ...)
- High estimate: $X - $Y (formula: ...)

## ROI PROJECTION
- Best case: X% (assumptions: ...)
- Base case: X% (assumptions: ...)
- Worst case: X% (assumptions: ...)

## FINANCIAL RISKS
(Ranked by severity)

## UNCERTAINTY FLAGS
⚠️ Items that need more data before financial commitment

## FINANCIAL CONFIDENCE: [X]%
Reasoning: explain confidence level

No invented numbers. Ranges only. Show your work."""}],
        max_tokens=1000
    )
    return response.choices[0].message.content


from app.agents.base import BaseAgent
from app.core.message import AgentMessage, MessageType, Priority
from uuid import uuid4


class FinanceAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Finance",
            role="Financial Analyst",
            description="Provides financial analysis and funding evaluation.",
        )
        self._started = False

    def initialize(self) -> None:
        self._started = True
        self.log("FinanceAgent initialized.")

    def can_handle(self, mission) -> bool:
        return self.name in getattr(mission, "assigned_agents", []) or "finance" in getattr(mission, "objective", "").lower()

    def handle_task(self, message: AgentMessage) -> AgentMessage:
        # Handle questions or tasks by producing a financial analysis
        self.receive(message)
        task_text = message.content
        try:
            output = run_finance_agent(task_text)
        except Exception:
            output = "Finance analysis could not be completed."

        response = message.model_copy(
            deep=True,
            update={
                "id": uuid4(),
                "sender": self.name,
                "receiver": message.sender,
                "message_type": MessageType.RESPONSE,
                "content": output,
                "confidence": 0.85,
                "parent_message_id": message.id,
            },
        )
        return response

    def review(self, message: AgentMessage) -> AgentMessage:
        self.receive(message)
        response = message.model_copy(deep=True, update={
            "sender": self.name,
            "receiver": message.sender,
            "message_type": MessageType.RESPONSE,
            "content": "Finance review completed.",
            "confidence": 0.9,
        })
        return response

    def health(self) -> dict[str, object]:
        return {"name": self.name, "role": self.role, "status": "healthy" if self._started else "initializing"}

    def shutdown(self) -> None:
        self._started = False
        self.log("FinanceAgent has shut down.")

    def execute(self, task: str) -> str:
        # Provide backward-compatible execute API used by orchestrator
        response_message = self.handle_task(
            AgentMessage(
                mission_id=uuid4(),
                sender="CEO",
                receiver=self.name,
                message_type=MessageType.TASK,
                priority=Priority.HIGH,
                content=task,
                confidence=1.0,
            )
        )
        return response_message.content