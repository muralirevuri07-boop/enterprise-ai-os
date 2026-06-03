from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_support_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Customer Support Agent of an Enterprise AI OS.
Task: {task}
Provide:
1. Support strategy
2. FAQ responses
3. Escalation plan
4. Customer satisfaction tips
Be empathetic and helpful."""}],
        max_tokens=800
    )
    return response.choices[0].message.content