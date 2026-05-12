




from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status , HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_workspace_role
from app.domain.task import Task, TaskStatus
from app.domain.workspace import MemberShip, Workspace
from app.infra.db import get_db
from app.services import task_service

from app.services.task_service import TaskNotFound


router = APIRouter(prefix="/workspaces", tags=["tasks"])


# string literal type so Pydantic enforces it at the wire boundary
StatusLiteral = Literal["todo", "in_progress", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    status: StatusLiteral = "todo"
    assignee_id: UUID | None = None
    deadline: datetime | None = None


class TaskResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: str
    assignee_id: UUID | None
    deadline: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, t: Task) -> "TaskResponse":
        return cls(
            id=t.id,
            workspace_id=t.workspace_id,
            title=t.title,
            description=t.description,
            status=t.status.value,
            assignee_id=t.assignee_id,
            deadline=t.deadline,
            created_by=t.created_by,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )



class TaskUpdate(BaseModel):
    title:str | None = Field(default=None,min_length=1,max_length=200,)
    description:str | None = Field(default=None,max_length=10_000)
    status:StatusLiteral|None = None
    assignee_id: UUID |None = None
    deadline: datetime | None = None




def _error(*,status_code:int,code:str,detail:str):
    return HTTPException(
        status_code=status_code,
        detail={"detail":detail,"code":code}
    )

@router.post(
    "/{workspace_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    workspace_id: UUID,
    payload: TaskCreate,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member"})
    ),
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    _workspace, membership = ctx
    task = await task_service.create_task(
        session,
        workspace_id=workspace_id,
        creator_id=membership.user_id,
        title=payload.title,
        description=payload.description,
        status=TaskStatus(payload.status),
        assignee_id=payload.assignee_id,
        deadline=payload.deadline,
    )
    return TaskResponse.from_domain(task)


@router.get(
    "/{workspace_id}/tasks",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
)
async def list_tasks(
    workspace_id: UUID,
    status: StatusLiteral | None = None,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member", "viewer"})
    ),
    session: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    status_filter = TaskStatus(status) if status is not None else None
    tasks = await task_service.list_tasks(
        session, workspace_id, status_filter=status_filter,
    )
    return [TaskResponse.from_domain(t) for t in tasks]





@router.patch(
    "/{workspace_id}/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse
)
async def update_task(
    workspace_id: UUID,
    task_id: UUID,
    payload: TaskUpdate,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member"})
    ),
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    _workspace, membership = ctx

    fields = payload.model_dump(exclude_unset=True)
    if "status" in fields:
        fields["status"] = TaskStatus(fields["status"])

    try:
        task = await task_service.update_task(
            session,
            task_id=task_id,
            workspace_id=workspace_id,
            caller_id=membership.user_id,
            caller_role=membership.role,
            fields=fields,
        )
    except TaskNotFound:
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="task_not_found",
            detail="task not found",
        )
    return TaskResponse.from_domain(task)