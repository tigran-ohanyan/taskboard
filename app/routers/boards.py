from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.auth import DB, CurrentUser
from app.models import Board, Task, User

router = APIRouter(prefix="/api/boards", tags=["boards"])


def get_owned_board(db: Session, user: User, board_id: int) -> Board:
    board = db.get(Board, board_id)
    if board is None or board.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Board not found")
    return board


def with_count(db: Session, board: Board) -> schemas.BoardOut:
    count = db.scalar(select(func.count()).select_from(Task).where(Task.board_id == board.id))
    return schemas.BoardOut(
        id=board.id, name=board.name, created_at=board.created_at, task_count=count or 0
    )


@router.get("", response_model=list[schemas.BoardOut])
def list_boards(user: CurrentUser, db: DB):
    boards = db.scalars(
        select(Board).where(Board.owner_id == user.id).order_by(Board.created_at)
    ).all()
    return [with_count(db, b) for b in boards]


@router.post("", response_model=schemas.BoardOut, status_code=status.HTTP_201_CREATED)
def create_board(payload: schemas.BoardCreate, user: CurrentUser, db: DB):
    board = Board(name=payload.name.strip(), owner_id=user.id)
    db.add(board)
    db.commit()
    db.refresh(board)
    return with_count(db, board)


@router.get("/{board_id}", response_model=schemas.BoardOut)
def get_board(board_id: int, user: CurrentUser, db: DB):
    return with_count(db, get_owned_board(db, user, board_id))


@router.patch("/{board_id}", response_model=schemas.BoardOut)
def rename_board(board_id: int, payload: schemas.BoardUpdate, user: CurrentUser, db: DB):
    board = get_owned_board(db, user, board_id)
    board.name = payload.name.strip()
    db.commit()
    db.refresh(board)
    return with_count(db, board)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int, user: CurrentUser, db: DB):
    board = get_owned_board(db, user, board_id)
    db.delete(board)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
