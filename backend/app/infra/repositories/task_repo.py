from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID

from app.infra.models import TaskModel



async def create(
        session = AsyncSession,
        *,
        workspace_id:UUID,
        title:str,
        description: str|None,
        status: str,
        assignee_id: UUID|None,
        deadline:datetime | None,
        created_by:UUID,
)->TaskModel:
    task = TaskModel(
        workspace_id = workspace_id,
        title = title,
        description = description,
        status = status,
        assignee_id = assignee_id,
        deadline = deadline,
        created_by = created_by
    )
    session.add(task)
    await session.flush()
    return task

async def list_for_workspace (
        session : AsyncSession,
        workspace_id: UUID,
        *,
        status:str |None=None,
) -> list[TaskModel]:
    stmt = select(TaskModel).where(TaskModel.workspace_id == workspace_id)
    if status is not None:
        stmt = stmt.where(TaskModel.status == status)
    stmt = stmt.order_by(TaskModel.created_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())
    
