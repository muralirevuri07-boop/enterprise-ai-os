from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def run_web_agent(task: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": f"""You are a Web Intelligence Analyst with strict verification standards.

Task: {task}

STRICT RULES:
- Only reference REAL verified companies
- Never invent competitor names or market data
- Flag all unverified data with ⚠️ UNVERIFIED
- Use only well-known verified sources

Real AI companies you can reference:
OpenAI, Anthropic, Google DeepMind, Microsoft AI, Meta AI,
Mistral, Cohere, Scale AI, Hugging Face, LangChain,
CrewAI, AutoGen, NVIDIA, AWS AI, IBM Watson

Structure your response as:

## VERIFIED COMPETITORS
(Real companies with known facts only)

## MARKET LANDSCAPE
(Verified trends - cite source or flag ⚠️)

## TECHNOLOGY ANALYSIS
(Real tools and frameworks)

## UNVERIFIED DATA
⚠️ Claims that could not be verified

## INTELLIGENCE GAPS
(What data is missing and why it matters)

## WEB CONFIDENCE: [X]%
Reasoning: explain confidence level

No hallucinated companies. No invented data."""}],
        max_tokens=1000
    )
    return response.choices[0].message.content