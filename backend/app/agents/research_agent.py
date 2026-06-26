import json
from uuid import uuid4

from groq import Groq
from app.agents.base import BaseAgent
from app.core.message import AgentMessage, MessageType, Priority
from app.core.mission import Mission
from app.core.config import settings
from uuid import uuid4


class ResearchAgent(BaseAgent):
    """Specialist research agent that produces structured evidence summaries."""

    def __init__(self) -> None:
        super().__init__(
            name="Research",
            role="Research Specialist",
            description="Collects market and competitive intelligence for mission objectives.",
        )
        self._started = False
        self._requested_finance_missions: set = set()
        self._client = Groq(api_key=settings.GROQ_API_KEY)

    def initialize(self) -> None:
        self._started = True
        self.log("ResearchAgent initialized.")

    def can_handle(self, mission: Mission) -> bool:
        return self.name in mission.assigned_agents or "research" in mission.objective.lower()

    def handle_task(self, message: AgentMessage) -> AgentMessage:
        self.receive(message)

        # If this is the initial task from CEO, ask Finance to evaluate funding
        if message.message_type == MessageType.TASK:
            # only request finance once per mission to avoid cycles
            if message.mission_id in self._requested_finance_missions:
                # already requested; acknowledge without re-issuing
                # already requested; do not send progress notifications to CEO
                return None

            self._requested_finance_missions.add(message.mission_id)
            # kick off a question to Finance; this will synchronously notify any attached Finance agent
            question = AgentMessage(
                mission_id=message.mission_id,
                sender=self.name,
                receiver="Finance",
                message_type=MessageType.QUESTION,
                priority=Priority.MEDIUM,
                content=f"Please evaluate funding and financial implications for: {message.content}",
                confidence=0.9,
                requires_response=True,
                parent_message_id=message.id,
            )

            # publish the question via the attached bus if available
            if hasattr(self, "_agent_bus") and self._agent_bus:
                # tag the question so it references the originating task
                question.parent_message_id = message.id
                self._agent_bus.send_message(question)

            # Do not send intermediate progress notifications to CEO; wait for Finance response
            return None

        # If this is a response from another agent (e.g., Finance), synthesize and send to CEO
        # Do not re-request Finance when processing a Finance response.
        if message.sender == "Finance" and message.message_type == MessageType.RESPONSE:
            raw_output = message.content
            payload = {
                "executive_summary": f"Synthesis using input: {raw_output}",
                "confidence": 0.85,
            }

            response_message = message.model_copy(
                deep=True,
                update={
                    "id": uuid4(),
                    "sender": self.name,
                    "receiver": "CEO",
                    "message_type": MessageType.RESPONSE,
                    "content": json.dumps(payload, ensure_ascii=False),
                    "metadata": {"synthesized_from": message.sender},
                    "confidence": float(payload.get("confidence", 0.0)),
                    "parent_message_id": message.id,
                },
            )
            return response_message

        # Any other non-task messages: default synthesis
        raw_output = message.content
        payload = {"executive_summary": str(raw_output), "confidence": 0.5}
        response_message = message.model_copy(deep=True, update={
            "sender": self.name,
            "receiver": "CEO",
            "message_type": MessageType.RESPONSE,
            "content": json.dumps(payload, ensure_ascii=False),
            "confidence": payload["confidence"],
        })
        return response_message

    def review(self, message: AgentMessage) -> AgentMessage:
        self.receive(message)

        # If this is a finance response, synthesize and return recommendation to CEO.
        if message.sender == "Finance" and message.message_type == MessageType.RESPONSE:
            try:
                finance_content = message.content
            except Exception:
                finance_content = ""

            review_payload = {
                "executive_summary": f"Research synthesis using Finance input: {finance_content}",
                "key_findings": [],
                "supporting_evidence": [],
                "confidence": 0.9,
                "assumptions": [],
                "recommended_next_step": "Proceed with CEO review and consider financial caveats.",
            }

            response_message = message.model_copy(
                deep=True,
                update={
                    "sender": self.name,
                    "receiver": "CEO",
                    "message_type": MessageType.RESPONSE,
                    "content": json.dumps(review_payload, ensure_ascii=False),
                    "metadata": {"synthesized_from": "Finance", "structured_review": True},
                    "confidence": review_payload["confidence"],
                },
            )
            return response_message

        # Default review behavior for other message types or senders: return a short acknowledgement
        review_payload = {
            "executive_summary": "Research review completed.",
            "key_findings": [],
            "supporting_evidence": [],
            "confidence": 0.6,
            "assumptions": [],
            "recommended_next_step": "No further action required.",
        }

        response_message = message.model_copy(
            deep=True,
            update={
                "sender": self.name,
                "receiver": message.sender,
                "message_type": MessageType.RESPONSE,
                "content": json.dumps(review_payload, ensure_ascii=False),
                "metadata": {"structured_review": True},
                "confidence": review_payload["confidence"],
            },
        )
        return response_message

    def health(self) -> dict[str, object]:
        return {
            "name": self.name,
            "role": self.role,
            "status": "healthy" if self._started else "initializing",
        }

    def shutdown(self) -> None:
        self._started = False
        self.log("ResearchAgent has shut down.")

    def execute(self, task: str) -> str:
        dummy_message = AgentMessage(
            mission_id=uuid4(),
            sender="CEO",
            receiver=self.name,
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content=task,
            confidence=1.0,
        )
        response_message = self.handle_task(dummy_message)
        return response_message.content

    def _run_research_task(self, task: str) -> str:
        prompt = f"""You are a Senior Research Analyst with strict evidence standards.

Task: {task}

RULES:
- NEVER invent statistics or numbers
- Every claim must have a source or be flagged as UNVERIFIED
- Challenge weak assumptions
- Flag low-confidence findings clearly
- Return the response as valid JSON with these fields:
  - executive_summary
  - key_findings
  - supporting_evidence
  - confidence
  - assumptions
  - recommended_next_step

The JSON values must be concise and factual.
"""
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    def _build_structured_payload(self, raw_output: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "executive_summary": raw_output.strip(),
            "key_findings": [],
            "supporting_evidence": [],
            "confidence": 0.0,
            "assumptions": [],
            "recommended_next_step": "",
        }

        text = raw_output.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

        if isinstance(parsed, dict):
            for key in payload:
                if key in parsed and parsed[key] is not None:
                    payload[key] = parsed[key]

        if not isinstance(payload["key_findings"], list):
            payload["key_findings"] = [str(payload["key_findings"])] if payload["key_findings"] else []
        if not isinstance(payload["supporting_evidence"], list):
            payload["supporting_evidence"] = [str(payload["supporting_evidence"])] if payload["supporting_evidence"] else []
        if not isinstance(payload["assumptions"], list):
            payload["assumptions"] = [str(payload["assumptions"])] if payload["assumptions"] else []

        try:
            payload["confidence"] = float(payload["confidence"])
        except (TypeError, ValueError):
            payload["confidence"] = 0.0

        return payload


def run_research_agent(task: str) -> str:
    agent = ResearchAgent()
    agent.initialize()
    response_message = agent.handle_task(
        AgentMessage(
            mission_id=uuid4(),
            sender="CEO",
            receiver="Research",
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content=task,
            confidence=1.0,
        )
    )
    agent.shutdown()
    return response_message.content
