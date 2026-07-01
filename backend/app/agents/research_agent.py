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


StructuredResearchPayload = dict[str, str | float | list[str]]


class ResearchAgent(BaseAgent):
    """Research specialist for evidence collection and CEO-ready synthesis.

    ``ResearchAgent`` owns the primary research workflow for a mission. It
    analyzes the CEO task, extracts evidence-bearing findings from the mission
    text, decides whether financial analysis is required, and delegates those
    financial questions to ``Finance`` through ``AgentBus``. When a Finance
    response arrives, the agent synthesizes the research findings and financial
    analysis into one structured CEO response.

    The implementation is deterministic and side-effect light by design: it
    does not call external APIs, does not reuse inbound message IDs, and does
    not call ``receive`` from inside task handlers. ``BaseAgent.receive`` is the
    only inbound processing gate, which keeps duplicate tracking and routing
    consistent with the rest of the platform.
    """

    FINANCE_AGENT_NAME = "Finance"
    CEO_NAME = "CEO"

    _FINANCIAL_KEYWORDS: frozenset[str] = frozenset(
        {
            "acquisition",
            "budget",
            "burn",
            "capex",
            "cost",
            "ebitda",
            "finance",
            "financial",
            "funding",
            "investment",
            "margin",
            "mrr",
            "payback",
            "price",
            "profit",
            "revenue",
            "roi",
            "runway",
            "valuation",
        }
    )

    def __init__(self, bus: AgentBus | None = None) -> None:
        """Create a research agent and register it on ``bus``.

        Args:
            bus: Mission-local bus used for agent communication. When omitted,
                a private control bus is created so tests can instantiate the
                agent before an orchestrator rebinds it to an active mission.
        """
        resolved_bus = bus if bus is not None else self._build_default_bus()
        super().__init__(
            name="Research",
            role="Research Specialist",
            description="Collects evidence, frames findings, and synthesizes finance input for CEO decisions.",
            bus=resolved_bus,
        )
        self._started = False
        self._task_context_by_id: dict[UUID, dict[str, Any]] = {}
        self._root_task_by_finance_question_id: dict[UUID, UUID] = {}
        self._finance_questions_by_root_task_id: dict[UUID, UUID] = {}

    def initialize(self) -> None:
        """Mark the agent ready to receive mission work."""
        self._started = True

    def can_handle(self, mission: Mission) -> bool:
        """Return whether this agent should participate in ``mission``.

        Research is eligible when explicitly assigned or when the objective
        asks for research, evidence, market analysis, diligence, comparison,
        recommendation, or decision support.
        """
        objective = mission.objective.lower()
        title = mission.title.lower()
        capability_terms = (
            "research",
            "evidence",
            "market",
            "competitive",
            "diligence",
            "analyze",
            "analysis",
            "compare",
            "recommend",
            "strategy",
        )
        return self.name in mission.assigned_agents or any(term in objective or term in title for term in capability_terms)

    def handle_task(self, message: AgentMessage) -> AgentMessage:
        """Analyze a CEO task and return the next message in the workflow.

        If the task requires financial analysis and Finance has not already
        been asked for the same root task, this method returns a ``QUESTION``
        addressed to ``Finance``. The bus will deliver that question and route
        the Finance ``RESPONSE`` back to ``review``. If financial analysis is
        not needed, or Finance is unavailable, the method returns a structured
        CEO ``RESPONSE`` directly.
        """
        findings = self._generate_research_findings(message.content)
        requires_finance = self._requires_financial_analysis(message.content)
        self._store_task_context(message.id, message, findings, requires_finance)

        if requires_finance and message.id not in self._finance_questions_by_root_task_id:
            if self._receiver_is_registered(self.FINANCE_AGENT_NAME):
                question = self._build_finance_question(message, findings)
                self._finance_questions_by_root_task_id[message.id] = question.id
                self._root_task_by_finance_question_id[question.id] = message.id
                return question

            payload = self._build_structured_payload(
                root_task=message,
                findings=findings,
                finance_response=None,
                risks=[
                    "Financial analysis appears necessary, but no Finance agent is registered on the active bus.",
                    "Recommendation confidence is reduced until valuation, budget, ROI, and risk assumptions are reviewed.",
                ],
                confidence=0.58,
            )
            return self._build_ceo_response(message, payload, parent_message_id=message.id)

        payload = self._build_structured_payload(
            root_task=message,
            findings=findings,
            finance_response=None,
            risks=self._infer_risks(message.content, findings),
            confidence=0.74 if findings else 0.62,
        )
        return self._build_ceo_response(message, payload, parent_message_id=message.id)

    def review(self, message: AgentMessage) -> AgentMessage:
        """Review Finance output and synthesize a structured CEO response.

        Only Finance responses trigger synthesis. Other reviewable messages are
        acknowledged to the CEO without sending work back to the original
        sender, preventing response loops between specialist agents.
        """
        if message.sender == self.FINANCE_AGENT_NAME and self._message_type_matches(message.message_type, MessageType.RESPONSE):
            root_task_id = self._resolve_root_task_id(message)
            root_context = self._task_context_by_id.get(root_task_id)
            root_task = root_context["task"] if root_context is not None else message
            findings = root_context["findings"] if root_context is not None else self._generate_research_findings(message.content)
            if message.parent_message_id is not None:
                self._root_task_by_finance_question_id.pop(message.parent_message_id, None)
            payload = self._build_structured_payload(
                root_task=root_task,
                findings=findings,
                finance_response=message,
                risks=self._merge_unique(self._infer_risks(root_task.content, findings), self._extract_financial_risks(message.content)),
                confidence=self._combined_confidence(root_task.confidence, message.confidence, findings),
            )
            return self._build_ceo_response(
                root_task,
                payload,
                parent_message_id=root_task.id,
                metadata={
                    "finance_response_id": str(message.id),
                    "finance_parent_message_id": str(message.parent_message_id) if message.parent_message_id else None,
                    "synthesized_from": [self.name, self.FINANCE_AGENT_NAME],
                },
            )

        payload = self._empty_payload(
            executive_summary="Research reviewed a non-finance message and found no finance synthesis action to perform.",
            recommended_next_step="Route finance evidence as a Finance RESPONSE when CEO synthesis is required.",
            confidence=0.5,
        )
        return self._build_ceo_response(message, payload, parent_message_id=message.parent_message_id or message.id)

    def health(self) -> dict[str, Any]:
        """Return JSON-safe operating status for monitoring."""
        return {
            "name": self.name,
            "role": self.role,
            "status": "healthy" if self._started else "initializing",
            "processed_messages": len(self.processed_messages),
            "tracked_tasks": len(self._task_context_by_id),
            "pending_finance_questions": len(self._root_task_by_finance_question_id),
        }

    def shutdown(self) -> None:
        """Stop accepting active work and clear mission-local synthesis state."""
        self._started = False
        self._task_context_by_id.clear()
        self._root_task_by_finance_question_id.clear()
        self._finance_questions_by_root_task_id.clear()

    def execute(self, task: str) -> str:
        """Run a standalone research task and return the structured JSON body.

        This compatibility helper is intentionally local-only. It creates a
        temporary mission bus and sends a CEO task through the normal agent
        message path so duplicate tracking and response construction remain
        identical to orchestrated usage.
        """
        mission = Mission(title="Standalone research task", objective=task, assigned_agents=[self.name])
        conversation = MissionConversation.from_mission(mission)
        bus = AgentBus(conversation)
        captured: list[AgentMessage] = []

        def ceo_listener(message: AgentMessage) -> AgentMessage | None:
            captured.append(message)
            return None

        bus.register(self.CEO_NAME, ceo_listener)
        setattr(self, "_bus", bus)
        bus.register(self.name, self.receive)
        self.reset()
        self.initialize()

        direct_response = bus.send(
            AgentMessage(
                mission_id=mission.id,
                sender=self.CEO_NAME,
                receiver=self.name,
                message_type=MessageType.TASK,
                priority=Priority.HIGH,
                content=task,
                confidence=1.0,
                requires_response=True,
            )
        )
        response = captured[-1] if captured else direct_response
        if response is None:
            raise RuntimeError("research task did not produce a response")
        return response.content

    def _store_task_context(
        self,
        task_id: UUID,
        message: AgentMessage,
        findings: list[str],
        requires_finance: bool,
    ) -> None:
        """Store immutable task context needed for later Finance synthesis."""
        self._task_context_by_id[task_id] = {
            "task": deepcopy(message),
            "findings": list(findings),
            "requires_finance": requires_finance,
        }

    def _build_finance_question(self, message: AgentMessage, findings: list[str]) -> AgentMessage:
        """Create a fresh Finance question linked to the CEO task."""
        evidence = "; ".join(findings[:4]) if findings else "No explicit evidence was provided in the task text."
        return AgentMessage(
            mission_id=message.mission_id,
            sender=self.name,
            receiver=self.FINANCE_AGENT_NAME,
            message_type=MessageType.QUESTION,
            priority=Priority.HIGH if message.priority in {Priority.HIGH, Priority.CRITICAL} else Priority.MEDIUM,
            content=(
                "Please evaluate the financial implications for this research mission. "
                f"Mission request: {message.content.strip()} "
                f"Initial research evidence: {evidence} "
                "Return assumptions, budget or valuation ranges, ROI or payback considerations, financial risks, "
                "uncertainty flags, and financial confidence."
            ),
            confidence=min(0.9, max(0.5, message.confidence)),
            metadata={
                "root_task_id": str(message.id),
                "delegated_by": self.name,
                "reason": "financial_analysis_required",
            },
            requires_response=True,
            parent_message_id=message.id,
        )

    def _build_ceo_response(
        self,
        source_message: AgentMessage,
        payload: StructuredResearchPayload,
        *,
        parent_message_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Create a fresh structured CEO response."""
        response_metadata: dict[str, Any] = {"structured_output": True, "schema": "research_ceo_response.v1"}
        if metadata:
            response_metadata.update({key: value for key, value in metadata.items() if value is not None})

        return AgentMessage(
            mission_id=source_message.mission_id,
            sender=self.name,
            receiver=self.CEO_NAME,
            message_type=MessageType.RESPONSE,
            priority=Priority.HIGH,
            content=json.dumps(payload, ensure_ascii=True, indent=2),
            confidence=float(payload["confidence"]),
            metadata=response_metadata,
            requires_response=False,
            parent_message_id=parent_message_id,
        )

    def _build_structured_payload(
        self,
        *,
        root_task: AgentMessage,
        findings: list[str],
        finance_response: AgentMessage | None,
        risks: list[str],
        confidence: float,
    ) -> StructuredResearchPayload:
        """Build the required CEO-facing structured response body."""
        supporting_evidence = self._supporting_evidence(root_task.content, findings, finance_response)
        assumptions = self._assumptions(root_task.content, finance_response)
        finance_summary = f" Finance input: {self._one_line(finance_response.content)}" if finance_response is not None else ""
        executive_summary = (
            f"Research analyzed the mission and identified {len(findings)} evidence-backed finding(s)."
            f"{finance_summary}"
        )
        recommended_next_step = self._recommended_next_step(finance_response, risks, confidence)

        return {
            "executive_summary": executive_summary,
            "key_findings": findings or ["The request needs additional source material before strong findings can be stated."],
            "supporting_evidence": supporting_evidence,
            "risks": risks or ["No material research risks were detected from the supplied mission text."],
            "assumptions": assumptions,
            "confidence": round(max(0.0, min(1.0, confidence)), 2),
            "recommended_next_step": recommended_next_step,
        }

    @staticmethod
    def _empty_payload(*, executive_summary: str, recommended_next_step: str, confidence: float) -> StructuredResearchPayload:
        """Return a complete structured payload for limited-review cases."""
        return {
            "executive_summary": executive_summary,
            "key_findings": [],
            "supporting_evidence": [],
            "risks": ["No Finance response was available for synthesis."],
            "assumptions": ["The inbound message was not part of a Finance delegation flow."],
            "confidence": confidence,
            "recommended_next_step": recommended_next_step,
        }

    def _resolve_root_task_id(self, finance_response: AgentMessage) -> UUID:
        """Resolve a Finance response back to the original CEO task."""
        if finance_response.parent_message_id in self._root_task_by_finance_question_id:
            return self._root_task_by_finance_question_id[finance_response.parent_message_id]

        metadata_root = finance_response.metadata.get("root_task_id")
        if isinstance(metadata_root, str):
            try:
                return UUID(metadata_root)
            except ValueError:
                pass
        return finance_response.parent_message_id or finance_response.id

    def _generate_research_findings(self, content: str) -> list[str]:
        """Generate concise findings from evidence-bearing mission text."""
        sentences = self._sentences(content)
        findings: list[str] = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(term in lowered for term in ("because", "need", "must", "risk", "goal", "objective", "customer", "market", "revenue", "cost")):
                findings.append(sentence)
            elif len(sentence.split()) >= 8 and len(findings) < 3:
                findings.append(sentence)

        return self._merge_unique(findings, [])[:6]

    def _requires_financial_analysis(self, content: str) -> bool:
        """Return whether the task should be delegated to Finance."""
        lowered = content.lower()
        return any(re.search(rf"\b{re.escape(keyword)}\b", lowered) for keyword in self._FINANCIAL_KEYWORDS)

    @staticmethod
    def _infer_risks(content: str, findings: list[str]) -> list[str]:
        """Infer research risks without inventing external facts."""
        risks: list[str] = []
        lowered = content.lower()
        if not findings:
            risks.append("Limited evidence was supplied in the mission text.")
        if any(term in lowered for term in ("urgent", "asap", "immediately")):
            risks.append("Timeline pressure may reduce diligence depth and source verification quality.")
        if any(term in lowered for term in ("acquisition", "investment", "launch", "enterprise")):
            risks.append("Decision impact appears material, so unverified assumptions should be validated before commitment.")
        if not re.search(r"\b(source|data|report|customer|metric|evidence)\b", lowered):
            risks.append("The request does not cite source material, named datasets, or validated metrics.")
        return risks

    @staticmethod
    def _extract_financial_risks(finance_content: str) -> list[str]:
        """Extract risk-like lines from Finance output for CEO synthesis."""
        risks: list[str] = []
        for line in finance_content.splitlines():
            normalized = line.strip(" -\t")
            if normalized and any(term in normalized.lower() for term in ("risk", "uncertain", "assumption", "caveat", "estimate")):
                risks.append(normalized)
        return risks[:5]

    @staticmethod
    def _supporting_evidence(content: str, findings: list[str], finance_response: AgentMessage | None) -> list[str]:
        """Build evidence statements grounded in supplied messages."""
        evidence = [f"CEO task statement: {content.strip()}"]
        evidence.extend(f"Research-derived finding: {finding}" for finding in findings[:4])
        if finance_response is not None:
            evidence.append(f"Finance response: {ResearchAgent._one_line(finance_response.content)}")
        return evidence

    @staticmethod
    def _assumptions(content: str, finance_response: AgentMessage | None) -> list[str]:
        """State assumptions that bound the recommendation."""
        assumptions = [
            "Only evidence present in agent messages was used; no external source retrieval was performed.",
            "The CEO task text accurately reflects the mission scope and decision context.",
        ]
        if finance_response is None:
            assumptions.append("No Finance response was available unless explicitly noted in risks.")
        else:
            assumptions.append("Finance analysis is treated as specialist input and should be validated against source financial data.")
        if "estimate" in content.lower():
            assumptions.append("Any estimates mentioned in the task require source validation before financial commitment.")
        return assumptions

    @staticmethod
    def _recommended_next_step(finance_response: AgentMessage | None, risks: list[str], confidence: float) -> str:
        """Choose a next step based on evidence maturity and confidence."""
        if finance_response is None and any("Finance agent is registered" in risk for risk in risks):
            return "Register Finance and rerun the mission before making a budget, valuation, or investment decision."
        if confidence < 0.65:
            return "Collect source evidence and clarify assumptions before CEO approval."
        if finance_response is not None:
            return "Proceed to CEO review with Finance caveats attached, then authorize deeper diligence if risks are acceptable."
        return "Proceed to CEO review and request Finance analysis only if budget, ROI, valuation, or funding decisions are added."

    @staticmethod
    def _combined_confidence(root_confidence: float, finance_confidence: float, findings: list[str]) -> float:
        """Combine research and finance confidence into one bounded score."""
        evidence_adjustment = 0.08 if findings else -0.08
        return (root_confidence * 0.25) + (finance_confidence * 0.55) + 0.15 + evidence_adjustment

    @staticmethod
    def _sentences(content: str) -> list[str]:
        """Split text into clean, bounded sentence fragments."""
        fragments = re.split(r"(?<=[.!?])\s+|\n+", content.strip())
        return [fragment.strip(" -\t") for fragment in fragments if fragment.strip(" -\t")]

    @staticmethod
    def _one_line(content: str, limit: int = 360) -> str:
        """Return a compact one-line preview for structured evidence fields."""
        preview = " ".join(content.strip().split())
        if len(preview) > limit:
            return f"{preview[: limit - 3]}..."
        return preview

    @staticmethod
    def _merge_unique(first: list[str], second: list[str]) -> list[str]:
        """Merge two string lists while preserving first-seen order."""
        merged: list[str] = []
        seen: set[str] = set()
        for item in [*first, *second]:
            normalized = " ".join(item.split())
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                merged.append(normalized)
        return merged

    def _receiver_is_registered(self, receiver: str) -> bool:
        """Return whether the active bus has a listener for ``receiver``."""
        listeners = getattr(self._bus, "_listeners", {})
        return isinstance(listeners, dict) and receiver in listeners

    @staticmethod
    def _build_default_bus() -> AgentBus:
        """Create a private bus for pre-orchestrator construction."""
        mission = Mission(
            title="Research agent control mission",
            objective="Initialize Research before binding to an orchestrated mission.",
        )
        return AgentBus(MissionConversation.from_mission(mission))


def run_research_agent(task: str) -> str:
    """Run ResearchAgent as a standalone compatibility function."""
    agent = ResearchAgent()
    try:
        return agent.execute(task)
    finally:
        agent.shutdown()


if __name__ == "__main__":
    mission = Mission(
        title="Research acquisition opportunity",
        objective="Assess an enterprise AI acquisition target with revenue, valuation, ROI, and market risks.",
        assigned_agents=["Research", "Finance"],
    )
    conversation = MissionConversation.from_mission(mission)
    bus = AgentBus(conversation=conversation)

    def ceo_listener(message: AgentMessage) -> AgentMessage | None:
        print("CEO received:")
        print(message.content)
        return None

    def finance_listener(message: AgentMessage) -> AgentMessage | None:
        print("Finance received question:")
        print(message.content)
        return AgentMessage(
            mission_id=message.mission_id,
            sender="Finance",
            receiver="Research",
            message_type=MessageType.RESPONSE,
            priority=Priority.HIGH,
            content=(
                "Finance assumptions: revenue durability must be verified; valuation should be evaluated as a range. "
                "Financial risks: integration cost uncertainty, customer concentration risk, and ROI sensitivity to retention."
            ),
            confidence=0.82,
            metadata={"root_task_id": str(message.parent_message_id)} if message.parent_message_id else {},
            parent_message_id=message.id,
        )

    bus.register("CEO", ceo_listener)
    bus.register("Finance", finance_listener)

    agent = ResearchAgent(bus=bus)
    agent.initialize()
    bus.send(
        AgentMessage(
            mission_id=mission.id,
            sender="CEO",
            receiver="Research",
            message_type=MessageType.TASK,
            priority=Priority.HIGH,
            content=(
                "Analyze whether we should pursue an enterprise AI acquisition target. "
                "We need market evidence, revenue quality risks, valuation considerations, and a recommended next step."
            ),
            confidence=0.95,
            requires_response=True,
        )
    )

    print("Health:", json.dumps(agent.health(), indent=2, sort_keys=True))
    agent.shutdown()
