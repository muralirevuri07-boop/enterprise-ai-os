from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

memory_store = []

def run_memory_agent(task: str, context: list = []) -> str:
    memory_store.append({"task": task})
    
    context_text = "\n".join([f"- {m['task']}" for m in memory_store[-5:]])
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are the Memory Agent of an Enterprise AI OS.
Current task: {task}

Recent context:
{context_text}

Provide:
1. Relevant past context
2. Key patterns identified
3. Recommendations based on history
4. Memory summary
Be insightful."""}],
        max_tokens=800
    )
    return response.choices[0].message.content