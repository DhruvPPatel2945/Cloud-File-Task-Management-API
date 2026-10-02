from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: datetime
    updated_at: datetime

# in-memory store
tasks = {}
next_id = 1

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/tasks", status_code=201)
def create_task(data: TaskCreate):
    global next_id
    now = datetime.now()
    task = Task(id=next_id, title=data.title, description=data.description, completed=data.completed, created_at=now, updated_at=now)
    tasks[next_id] = task
    next_id += 1
    return task

@app.get("/tasks")
def get_all_tasks():
    return list(tasks.values())

@app.get("/tasks/{task_id}")
def get_one_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.put("/tasks/{task_id}")
def update_task(task_id: int, data: TaskCreate):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    t = tasks[task_id]
    t.title = data.title
    t.description = data.description
    t.completed = data.completed
    t.updated_at = datetime.now()
    tasks[task_id] = t
    return t

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    del tasks[task_id]
    return {"message": "Task deleted"}