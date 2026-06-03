from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_marketing_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Marketing Agent of an Enterprise AI OS.
Your job is to create marketing strategies and campaigns.

Task: {task}

Provide:
1. Campaign strategy
2. Content ideas
3. Social media plan
4. Key messaging

Be creative and specific."""}],
        max_tokens=1000
    )
    return response.choices[0].message.content