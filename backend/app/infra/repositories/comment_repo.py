from uuid import UUID
from datetime import datetime

from sqlalchemy import select, tuple_, update as sa_update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.models import TaskCommentModel




async def create(
        session: AsyncSession,
        *,
        task_id: UUID,
        author_id: UUID,
        body: str,
) -> TaskCommentModel:
    entry = TaskCommentModel(
        task_id=task_id,
        author_id=author_id,
        body=body,
    )
    session.add(entry)
    await session.flush()
    return entry






async def list_for_task(
        session: AsyncSession,
        task_id: UUID,
        *,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
) -> list[TaskCommentModel]:
    

    stmt = select(TaskCommentModel).where(
        TaskCommentModel.task_id == task_id,
        TaskCommentModel.deleted_at.is_(None),
    )

    if after is not None:
        stmt = stmt.where(
            tuple_(TaskCommentModel.created_at, TaskCommentModel.id) > after
        )

    stmt = stmt.order_by(
        TaskCommentModel.created_at.asc(),
        TaskCommentModel.id.asc(),
    ).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())






async def find_by_id(
        session: AsyncSession,
        comment_id: UUID,
) -> TaskCommentModel | None:
    stmt = select(TaskCommentModel).where(
        TaskCommentModel.id == comment_id,
        TaskCommentModel.deleted_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()






async def update_body(
        session: AsyncSession,
        comment_id: UUID,
        body: str,
) -> TaskCommentModel | None:
    stmt = (
        sa_update(TaskCommentModel)
        .where(
            TaskCommentModel.id == comment_id,
            TaskCommentModel.deleted_at.is_(None),
        )
        .values(body=body)
        .returning(TaskCommentModel)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one_or_none()





async def soft_delete(
        session: AsyncSession,
        comment_id: UUID,
) -> None:
    stmt = (
        sa_update(TaskCommentModel)
        .where(
            TaskCommentModel.id == comment_id,
            TaskCommentModel.deleted_at.is_(None),
        )
        .values(deleted_at=func.now())
    )
    await session.execute(stmt)
    await session.flush()