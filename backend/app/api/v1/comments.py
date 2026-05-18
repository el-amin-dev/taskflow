from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_workspace_role, _user_id_or_ip
from app.domain.workspace import MemberShip, Workspace
from app.infra.db import get_db
from app.infra.models import TaskCommentModel
from app.services import comment_service
from app.services.comment_service import TaskNotFound
from app.infra.rate_limiter import limiter, SIXTY_PER_MINUTE

COMMENT_MAX_LENGTH = 10000

router = APIRouter(prefix="/workspaces", tags=["comments"])


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=COMMENT_MAX_LENGTH)


class CommentResponse(BaseModel):
    id: UUID
    task_id: UUID
    author_id: UUID | None
    body: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: TaskCommentModel) -> "CommentResponse":
        return cls(
            id=m.id,
            task_id=m.task_id,
            author_id=m.author_id,
            body=m.body,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )





def _error(*, status_code: int, code: str, detail: str):
    from fastapi import HTTPException
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "code": code},
    )


@router.post(
    "/{workspace_id}/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(SIXTY_PER_MINUTE, key_func=_user_id_or_ip)
async def create_comment(
    request: Request,
    workspace_id: UUID,
    task_id: UUID,
    payload: CommentCreate,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member", "viewer"})
    ),
    session: AsyncSession = Depends(get_db),
) -> CommentResponse:
    _workspace, membership = ctx
    try:
        comment = await comment_service.create_comment(
            session,
            workspace_id=workspace_id,
            task_id=task_id,
            author_id=membership.user_id,
            body=payload.body,
        )
    except TaskNotFound:
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="task_not_found",
            detail="task not found",
        )
    return CommentResponse.from_model(comment)
