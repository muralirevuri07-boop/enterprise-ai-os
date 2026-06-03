from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_research_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Research Agent of an Enterprise AI OS.
Your job is to research and gather intelligence on the given topic.

Task: {task}

Provide:
1. Key findings
2. Market data
3. Top players/companies
4. Trends and insights

Be specific and data-driven."""}],
        max_tokens=1000
    )
    return response.choices[0].message.content