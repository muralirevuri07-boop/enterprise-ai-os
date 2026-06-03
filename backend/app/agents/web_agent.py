from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_web_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Web Intelligence Agent of an Enterprise AI OS.
Task: {task}
Provide:
1. Web research findings
2. Competitor analysis
3. Industry trends
4. Key URLs and sources
Be data-driven and thorough."""}],
        max_tokens=800
    )
    return response.choices[0].message.content