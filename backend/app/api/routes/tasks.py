from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.ceo_agent import run_ceo_agent

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskRequest(BaseModel):
    title: str
    description: str

@router.post("/")
def create_task(task: TaskRequest):
    result = run_ceo_agent(task.title, task.description)

    return {
        "status": "completed",
        "assigned_agent": "ceo",
        "result": result
    }