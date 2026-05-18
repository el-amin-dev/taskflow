from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.models import TaskCommentModel
from app.infra.repositories import comment_repo, task_repo, audit_repo


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
