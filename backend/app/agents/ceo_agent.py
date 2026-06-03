from groq import Groq
from app.core.config import settings
from app.agents.research_agent import run_research_agent
from app.agents.sales_agent import run_sales_agent
from app.agents.marketing_agent import run_marketing_agent
from app.agents.finance_agent import run_finance_agent
from app.agents.ops_agent import run_ops_agent
from app.agents.web_agent import run_web_agent
from app.agents.memory_agent import run_memory_agent

client = Groq(api_key=settings.GROQ_API_KEY)

def run_ceo_agent(task_title: str, task_description: str) -> str:
    research = run_research_agent(task_description)
    web = run_web_agent(task_description)
    sales = run_sales_agent(task_description)
    marketing = run_marketing_agent(task_description)
    finance = run_finance_agent(task_description)
    ops = run_ops_agent(task_description)
    memory = run_memory_agent(task_description)

    summary_prompt = f"""You are the CEO Agent. Create an executive summary from all agent reports.

RESEARCH: {research[:300]}
WEB INTEL: {web[:300]}
SALES: {sales[:300]}
MARKETING: {marketing[:300]}
FINANCE: {finance[:300]}
OPS: {ops[:300]}
MEMORY: {memory[:300]}

Write a concise executive action plan."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=1000
    )

    final = f"""## 🤖 CEO EXECUTIVE SUMMARY
{response.choices[0].message.content}

---
## 📊 RESEARCH AGENT
{research}

---
## 🌐 WEB INTELLIGENCE
{web}

---
## 💼 SALES AGENT
{sales}

---
## 📣 MARKETING AGENT
{marketing}

---
## 💰 FINANCE AGENT
{finance}

---
## ⚙️ OPERATIONS AGENT
{ops}

---
## 🧠 MEMORY AGENT
{memory}
"""
    return final