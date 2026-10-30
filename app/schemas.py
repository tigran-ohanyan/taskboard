from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["todo", "doing", "done"]
Priority = Literal["low", "medium", "high"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class BoardUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
    task_count: int = 0


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: Status = "todo"
    priority: Priority = "medium"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    clear_due_date: bool = False


class TaskMove(BaseModel):
    status: Status
    position: int = Field(ge=0)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    board_id: int
    title: str
    description: str
    status: Status
    priority: Priority
    position: int
    due_date: date | None
    created_at: datetime
    updated_at: datetime
