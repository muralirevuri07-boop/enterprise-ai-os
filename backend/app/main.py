from fastapi import FastAPI
from app.api.routes.tasks import router as task_router

app = FastAPI(title="Autonomous Enterprise AI OS")

app.include_router(task_router)

@app.get("/")
def root():
    return {"message": "AI OS Running"}