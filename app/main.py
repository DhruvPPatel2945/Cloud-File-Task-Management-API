import logging
import time

from .logging_config import configure_logging

configure_logging()
logger = logging.getLogger("task_api")

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import db_models
from .auth import router as auth_router
from .database import get_db
from .model import TaskCreate, TaskResponse, TaskUpdate
from .security import get_current_user


# Best-effort table creation at import so TestClient without
# lifespan context still works when DB is reachable.
# Never crash import if DB is down.



app = FastAPI(title="Task API - Phase 3 Authentication")
app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.middleware("http")
async def log_requests(request, call_next):
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "request_failed",
            extra={
                "fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(exc).__name__,
                }
            },
        )
        raise

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

    logger.info(
        "request_completed",
        extra={
            "fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
            }
        },
    )

    return response

def _get_owned_task(
    task_id: int,
    user_id: int,
    db: Session,
) -> db_models.Task:
    task = (
        db.query(db_models.Task)
        .filter(
            db_models.Task.id == task_id,
            db_models.Task.user_id == user_id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    data: TaskCreate,
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
):
    new_task = db_models.Task(
        title=data.title,
        description=data.description,
        completed=data.completed,
        user_id=current_user.id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
):
    return (
        db.query(db_models.Task)
        .filter(db_models.Task.user_id == current_user.id)
        .all()
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
):
    return _get_owned_task(task_id, current_user.id, db)


@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user.id, db)

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.completed is not None:
        task.completed = data.completed

    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user.id, db)

    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}