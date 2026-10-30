from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.auth import DB, CurrentUser
from app.models import Task, User
from app.routers.boards import get_owned_board

router = APIRouter(prefix="/api", tags=["tasks"])


def get_owned_task(db: Session, user: User, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.board.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def renumber(db: Session, board_id: int, status_: str) -> None:
    """Keep positions dense (0..n-1) inside one column."""
    tasks = db.scalars(
        select(Task)
        .where(Task.board_id == board_id, Task.status == status_)
        .order_by(Task.position, Task.id)
    ).all()
    for index, task in enumerate(tasks):
        task.position = index


@router.get("/boards/{board_id}/tasks", response_model=list[schemas.TaskOut])
def list_tasks(board_id: int, user: CurrentUser, db: DB):
    board = get_owned_board(db, user, board_id)
    return db.scalars(
        select(Task).where(Task.board_id == board.id).order_by(Task.status, Task.position)
    ).all()


@router.post(
    "/boards/{board_id}/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED
)
def create_task(board_id: int, payload: schemas.TaskCreate, user: CurrentUser, db: DB):
    board = get_owned_board(db, user, board_id)
    last = db.scalar(
        select(func.max(Task.position)).where(
            Task.board_id == board.id, Task.status == payload.status
        )
    )
    task = Task(
        board_id=board.id,
        title=payload.title.strip(),
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        position=(last + 1) if last is not None else 0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, user: CurrentUser, db: DB):
    task = get_owned_task(db, user, task_id)
    data = payload.model_dump(exclude_unset=True, exclude={"clear_due_date"})
    for field, value in data.items():
        setattr(task, field, value.strip() if field == "title" else value)
    if payload.clear_due_date:
        task.due_date = None
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/move", response_model=schemas.TaskOut)
def move_task(task_id: int, payload: schemas.TaskMove, user: CurrentUser, db: DB):
    task = get_owned_task(db, user, task_id)
    old_status = task.status

    # take the task out of its current column
    task.status = "__moving__"
    db.flush()
    renumber(db, task.board_id, old_status)

    # make room in the target column and drop it in
    siblings = db.scalars(
        select(Task)
        .where(Task.board_id == task.board_id, Task.status == payload.status)
        .order_by(Task.position, Task.id)
    ).all()
    position = min(payload.position, len(siblings))
    for sibling in siblings[position:]:
        sibling.position += 1
    task.status = payload.status
    task.position = position
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, user: CurrentUser, db: DB):
    task = get_owned_task(db, user, task_id)
    board_id, status_ = task.board_id, task.status
    db.delete(task)
    db.flush()
    renumber(db, board_id, status_)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
