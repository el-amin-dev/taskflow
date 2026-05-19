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
from app.services.comment_service import TaskNotFound , CommentNotFound, NotCommentAuthor
from app.infra.rate_limiter import limiter, SIXTY_PER_MINUTE
from app.api.errors import UNAUTHORIZED, BAD_REQUEST,FORBIDDEN,NOT_FOUND

import base64

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




class CommentPage(BaseModel):
    items: list[CommentResponse]
    next_cursor: str | None


def _encode_cursor(m: TaskCommentModel) -> str:
    raw = f"{m.created_at.isoformat()}|{m.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, id_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), UUID(id_str)




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
    responses={**UNAUTHORIZED,**NOT_FOUND}
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





@router.get(
    "/{workspace_id}/tasks/{task_id}/comments",
    response_model=CommentPage,
    status_code=status.HTTP_200_OK,
    responses={**UNAUTHORIZED,**NOT_FOUND,**BAD_REQUEST}
)
@limiter.limit(SIXTY_PER_MINUTE, key_func=_user_id_or_ip)
async def list_comments(
    request: Request,
    workspace_id: UUID,
    task_id: UUID,
    limit: int = 50,
    cursor: str | None = None,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member", "viewer"})
    ),
    session: AsyncSession = Depends(get_db),
) -> CommentPage:
    limit = max(1, min(limit, 100))  # clamp; never trust the client
    after: tuple[datetime, UUID] | None = None
    if cursor is not None:
        try:
            after = _decode_cursor(cursor)
        except (ValueError, TypeError):
            raise _error(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_cursor",
                detail="malformed pagination cursor",
            )
    try:
        rows = await comment_service.list_comments(
            session,
            workspace_id=workspace_id,
            task_id=task_id,
            limit=limit + 1,
            after=after,
        )
    except TaskNotFound:
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="task_not_found",
            detail="task not found",
        )
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more else None
    return CommentPage(
        items=[CommentResponse.from_model(r) for r in page],
        next_cursor=next_cursor,
    )


@router.patch(
    "/{workspace_id}/tasks/{task_id}/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    responses={**UNAUTHORIZED,**FORBIDDEN,**NOT_FOUND}
)
@limiter.limit(SIXTY_PER_MINUTE, key_func=_user_id_or_ip)
async def edit_comment(
    request: Request,
    workspace_id: UUID,
    task_id: UUID,
    comment_id: UUID,
    payload: CommentCreate,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member", "viewer"})
    ),
    session: AsyncSession = Depends(get_db),
) -> CommentResponse:
    _workspace, membership = ctx
    try:
        updated = await comment_service.edit_comment(
            session,
            workspace_id=workspace_id,
            task_id=task_id,
            comment_id=comment_id,
            caller_id=membership.user_id,
            body=payload.body,
        )
    except (TaskNotFound, CommentNotFound):
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="comment_not_found",
            detail="comment not found",
        )
    except NotCommentAuthor:
        raise _error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="not_comment_author",
            detail="only the author can edit this comment",
        )
    return CommentResponse.from_model(updated)


@router.delete(
    "/{workspace_id}/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**UNAUTHORIZED,**FORBIDDEN,**NOT_FOUND}
)
@limiter.limit(SIXTY_PER_MINUTE, key_func=_user_id_or_ip)
async def delete_comment(
    request: Request,
    workspace_id: UUID,
    task_id: UUID,
    comment_id: UUID,
    ctx: tuple[Workspace, MemberShip] = Depends(
        require_workspace_role({"admin", "member", "viewer"})
    ),
    session: AsyncSession = Depends(get_db),
) -> None:
    _workspace, membership = ctx
    try:
        await comment_service.delete_comment(
            session,
            workspace_id=workspace_id,
            task_id=task_id,
            comment_id=comment_id,
            caller_id=membership.user_id,
            caller_role=membership.role,
        )
    except (TaskNotFound, CommentNotFound):
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="comment_not_found",
            detail="comment not found",
        )
    except NotCommentAuthor:
        raise _error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="not_comment_author",
            detail="not allowed to delete this comment",
        )
    return None
