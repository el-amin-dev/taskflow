from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.models import TaskCommentModel
from app.infra.repositories import comment_repo, task_repo, audit_repo

from datetime import datetime


class TaskNotFound(Exception):
    pass

class CommentNotFound(Exception):
    pass

class NotCommentAuthor(Exception):
    pass

async def _task_in_workspace(
    session: AsyncSession, *, task_id: UUID, workspace_id: UUID
) -> None:
    
    
    task = await task_repo.find_by_id(session=session, task_id=task_id)
    if task is None or task.workspace_id != workspace_id:
        raise TaskNotFound()


async def create_comment(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        task_id: UUID,
        author_id: UUID,
        body: str,
) -> TaskCommentModel:
    await _task_in_workspace(
        session, task_id=task_id, workspace_id=workspace_id
    )
    comment = await comment_repo.create(
        session, task_id=task_id, author_id=author_id, body=body
    )
    await audit_repo.record(
        session,
        actor_user_id=author_id,
        workspace_id=workspace_id,
        action="comment.created",
        target_type="comment",
        target_id=comment.id,
        payload={"task_id": str(task_id)},
    )
    await session.commit()
    return comment


async def list_comments(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        task_id: UUID,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
) -> list[TaskCommentModel]:
    await _task_in_workspace(
        session, task_id=task_id, workspace_id=workspace_id
    )
    return await comment_repo.list_for_task(
        session, task_id, limit=limit, after=after
    )


async def _load_scoped_comment(
    session: AsyncSession, *, workspace_id: UUID, task_id: UUID,
    comment_id: UUID,
) -> TaskCommentModel:
    await _task_in_workspace(
        session, task_id=task_id, workspace_id=workspace_id
    )
    comment = await comment_repo.find_by_id(session, comment_id)
    if comment is None or comment.task_id != task_id:
        raise CommentNotFound()
    return comment


async def edit_comment(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        task_id: UUID,
        comment_id: UUID,
        caller_id: UUID,
        body: str,
) -> TaskCommentModel:
    comment = await _load_scoped_comment(
        session, workspace_id=workspace_id, task_id=task_id,
        comment_id=comment_id,
    )
    if comment.author_id != caller_id:
        raise NotCommentAuthor()

    updated = await comment_repo.update_body(session, comment_id, body)
    await session.commit()
    return updated


async def delete_comment(
        session: AsyncSession,
        *,
        workspace_id: UUID,
        task_id: UUID,
        comment_id: UUID,
        caller_id: UUID,
        caller_role: str,
) -> None:
    comment = await _load_scoped_comment(
        session, workspace_id=workspace_id, task_id=task_id,
        comment_id=comment_id,
    )
    is_author = comment.author_id == caller_id
    if not is_author and caller_role != "admin":
        raise NotCommentAuthor()

    await comment_repo.soft_delete(session, comment_id)
    await audit_repo.record(
        session,
        actor_user_id=caller_id,
        workspace_id=workspace_id,
        action="comment.deleted",
        target_type="comment",
        target_id=comment_id,
        payload={"task_id": str(task_id), "was_author": is_author},
    )
    await session.commit()
