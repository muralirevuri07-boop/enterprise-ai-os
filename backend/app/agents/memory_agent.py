from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

# Persistent in-memory store (upgradeable to DB later)
mission_history = []
successful_strategies = []
failed_approaches = []
recurring_patterns = []

def run_memory_agent(task: str, context: list = []) -> str:
    # Store current mission
    mission_history.append({
        "task": task,
        "mission_count": len(mission_history) + 1
    })

    # Build historical context
    history_text = ""
    if len(mission_history) > 1:
        history_text = f"""
PREVIOUS MISSIONS ({len(mission_history) - 1} total):
{chr(10).join([f"- Mission {m['mission_count']}: {m['task'][:100]}" for m in mission_history[-5:]])}
"""

    strategies_text = ""
    if successful_strategies:
        strategies_text = f"""
SUCCESSFUL STRATEGIES FROM PAST MISSIONS:
{chr(10).join([f"- {s}" for s in successful_strategies[-3:]])}
"""

    patterns_text = ""
    if recurring_patterns:
        patterns_text = f"""
RECURRING PATTERNS DETECTED:
{chr(10).join([f"- {p}" for p in recurring_patterns[-3:]])}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are a Strategic Memory Agent with persistent knowledge.

Current Task: {task}
Mission Number: {len(mission_history)}

{history_text}
{strategies_text}
{patterns_text}

YOUR RESPONSIBILITIES:
1. Connect current task to past missions
2. Surface relevant historical patterns
3. Warn about previously failed approaches
4. Recommend proven successful strategies
5. Build long-term organizational knowledge

Structure your response as:

## HISTORICAL CONTEXT
(Relevant past missions and learnings)

## PATTERN RECOGNITION
(Recurring themes across missions)

## PROVEN STRATEGIES
(What has worked before)

## FAILURE WARNINGS
⚠️ Approaches that failed in past missions

## STRATEGIC RECOMMENDATIONS
(Based on accumulated knowledge)

## KNOWLEDGE GAPS
(What we still need to learn)

## MEMORY CONFIDENCE: [X]%
Reasoning: explain confidence

Be specific. Reference actual past patterns when available."""}],
        max_tokens=800
    )

    result = response.choices[0].message.content

    # Extract and store patterns for future use
    if "success" in result.lower() or "effective" in result.lower():
        successful_strategies.append(f"Mission {len(mission_history)}: {task[:80]}")

    return result