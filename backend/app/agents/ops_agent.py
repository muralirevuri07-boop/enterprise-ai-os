from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_ops_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Operations Agent of an Enterprise AI OS.
Task: {task}
Provide:
1. Workflow plan
2. Timeline
3. Resource requirements
4. Process optimization tips
Be practical and detailed."""}],
        max_tokens=800
    )
    return response.choices[0].message.content