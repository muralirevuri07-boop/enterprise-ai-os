from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_sales_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Sales Agent of an Enterprise AI OS.
Your job is to create sales strategies and outreach plans.

Task: {task}

Provide:
1. Target prospects list
2. Outreach strategy
3. Email templates
4. Pipeline recommendations

Be specific and actionable."""}],
        max_tokens=1000
    )
    return response.choices[0].message.content