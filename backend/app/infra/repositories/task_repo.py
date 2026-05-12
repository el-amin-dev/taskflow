from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update as sa_update

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
    
async def find_by_id(
        session:AsyncSession,
        task_id:UUID
)-> TaskModel:
    return await session.get(TaskModel,task_id)

async def update(
        session:AsyncSession,
        task_id:UUID,
        *,
        fields:dict,


) -> TaskModel|None:
    if not fields:
        return await find_by_id(session,task_id)
    
    stmt = (
        sa_update(TaskModel)
        .where(TaskModel.id == task_id)
        .values(**fields)
        .returning(TaskModel)
    )

    result = await session.execute(stmt)
    row = result . scalar_one_or_none()
    await session.flush()
    return row
