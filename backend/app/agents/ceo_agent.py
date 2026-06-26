from groq import Groq
from app.core.config import settings
from app.agents.research_agent import run_research_agent
from app.agents.sales_agent import run_sales_agent
from app.agents.marketing_agent import run_marketing_agent
from app.agents.finance_agent import run_finance_agent
from app.agents.ops_agent import run_ops_agent
from app.agents.web_agent import run_web_agent
from app.agents.memory_agent import run_memory_agent
import json

client = Groq(api_key=settings.GROQ_API_KEY)

def detect_conflicts(outputs: dict) -> list:
    """CEO detects conflicts between agent outputs"""
    conflicts = []
    
    prompt = f"""You are a conflict detection system. Analyze these agent reports and identify ANY contradictions, disagreements, or inconsistencies.

Research Report: {outputs['research'][:500]}
Web Intelligence: {outputs['web'][:500]}
Sales Report: {outputs['sales'][:500]}
Marketing Report: {outputs['marketing'][:500]}
Finance Report: {outputs['finance'][:500]}

Return a JSON array of conflicts. Each conflict must have:
- agents: which agents disagree
- topic: what they disagree about
- positions: what each agent claims
- severity: LOW/MEDIUM/HIGH

Return ONLY valid JSON array. Example:
[{{"agents": ["Research", "Marketing"], "topic": "market size", "positions": {{"Research": "market is weak", "Marketing": "market is strong"}}, "severity": "HIGH"}}]

If no conflicts found return: []"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    try:
        text = response.choices[0].message.content
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            conflicts = json.loads(text[start:end])
    except:
        conflicts = []
    
    return conflicts

def score_confidence(outputs: dict, conflicts: list) -> dict:
    """Calculate confidence scores for the overall report"""
    base_score = 85
    conflict_penalty = len(conflicts) * 10
    confidence = max(40, base_score - conflict_penalty)
    
    return {
        "overall": confidence,
        "evidence_quality": "Strong" if confidence > 75 else "Moderate" if confidence > 55 else "Weak",
        "risk_level": "Low" if confidence > 75 else "Medium" if confidence > 55 else "High",
        "requires_approval": confidence < 60 or len(conflicts) > 2
    }

def resolve_conflicts(conflicts: list, outputs: dict) -> str:
    """CEO resolves conflicts between agents"""
    if not conflicts:
        return ""
    
    conflict_text = json.dumps(conflicts, indent=2)
    
    prompt = f"""You are a CEO resolving disagreements between your AI agents.

Conflicts detected:
{conflict_text}

As CEO, provide a clear resolution for each conflict. Be decisive. Use evidence. Explain your reasoning.
Keep it concise — 2-3 sentences per conflict."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400
    )
    return response.choices[0].message.content

def run_ceo_agent(task_title: str, task_description: str) -> str:
    # Step 1: Run all agents
    research = run_research_agent(task_description)
    web = run_web_agent(task_description)
    sales = run_sales_agent(task_description)
    marketing = run_marketing_agent(task_description)
    finance = run_finance_agent(task_description)
    ops = run_ops_agent(task_description)
    memory = run_memory_agent(task_description)

    outputs = {
        'research': research,
        'web': web,
        'sales': sales,
        'marketing': marketing,
        'finance': finance,
        'ops': ops,
        'memory': memory
    }

    # Step 2: Detect conflicts
    conflicts = detect_conflicts(outputs)
    
    # Step 3: Score confidence
    scores = score_confidence(outputs, conflicts)
    
    # Step 4: Resolve conflicts
    resolution = resolve_conflicts(conflicts, outputs)

    # Step 5: CEO generates executive report
    conflict_summary = f"\n\nCONFLICTS DETECTED: {len(conflicts)}\n{json.dumps(conflicts, indent=2)}" if conflicts else "\nNo conflicts detected."
    resolution_summary = f"\n\nCEO CONFLICT RESOLUTION:\n{resolution}" if resolution else ""

    executive_prompt = f"""You are the CEO of an autonomous AI company. Generate a professional executive report.

TASK: {task_title}

AGENT REPORTS SUMMARY:
Research: {research[:400]}
Web Intel: {web[:400]}
Sales: {sales[:400]}
Marketing: {marketing[:400]}
Finance: {finance[:400]}
Operations: {ops[:400]}

CONFIDENCE SCORE: {scores['overall']}%
EVIDENCE QUALITY: {scores['evidence_quality']}
RISK LEVEL: {scores['risk_level']}
{conflict_summary}
{resolution_summary}

Generate a structured executive report with these sections:
1. Executive Summary (3-4 sentences)
2. Key Verified Findings (bullet points with evidence)
3. Strategic Recommendations (prioritized)
4. Financial Overview (ranges, not invented numbers)
5. Risk Assessment
6. Required Human Decisions
7. Overall Confidence: {scores['overall']}% | Risk: {scores['risk_level']} | Evidence: {scores['evidence_quality']}

Use concise executive language. No filler. No invented statistics."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": executive_prompt}],
        max_tokens=1500
    )

    executive_summary = response.choices[0].message.content

    # Build final report
    confidence_badge = f"""
## 📊 GOVERNANCE SCORECARD
| Metric | Value |
|--------|-------|
| Overall Confidence | {scores['overall']}% |
| Evidence Quality | {scores['evidence_quality']} |
| Risk Level | {scores['risk_level']} |
| Conflicts Detected | {len(conflicts)} |
| Requires Approval | {'⚠️ YES' if scores['requires_approval'] else '✅ NO'} |
"""

    conflict_report = ""
    if conflicts:
        conflict_report = f"\n## ⚠️ CONFLICTS DETECTED & RESOLVED\n"
        for c in conflicts:
            conflict_report += f"\n**{c.get('topic', 'Unknown')}** ({c.get('severity', 'MEDIUM')} severity)\n"
            conflict_report += f"Agents: {', '.join(c.get('agents', []))}\n"
        if resolution:
            conflict_report += f"\n**CEO Resolution:**\n{resolution}\n"

    final = f"""## 🤖 CEO EXECUTIVE REPORT
{executive_summary}

{confidence_badge}
{conflict_report}
---
## 📊 RESEARCH AGENT
{research}

---
## 🌐 WEB INTELLIGENCE
{web}

---
## 💼 SALES AGENT
{sales}

---
## 📣 MARKETING AGENT
{marketing}

---
## 💰 FINANCE AGENT
{finance}

---
## ⚙️ OPERATIONS AGENT
{ops}

---
## 🧠 MEMORY AGENT
{memory}
"""
    return final