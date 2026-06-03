from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_document_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Document Intelligence Agent of an Enterprise AI OS.
Task: {task}
Provide:
1. Document structure
2. Key sections
3. Executive summary
4. Action items
Be thorough and organized."""}],
        max_tokens=800
    )
    return response.choices[0].message.content