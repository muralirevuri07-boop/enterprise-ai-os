from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_finance_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Finance Agent of an Enterprise AI OS.
Task: {task}
Provide:
1. Budget estimation
2. Cost breakdown
3. ROI projection
4. Financial risks
Be specific with numbers."""}],
        max_tokens=800
    )
    return response.choices[0].message.content