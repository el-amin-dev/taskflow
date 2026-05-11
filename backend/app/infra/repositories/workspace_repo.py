from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.models import WorkspaceModel , MemberShipModel


async def create(
        session: AsyncSession,
        *,
        name:str,
        owner_id:UUID
) -> WorkspaceModel:
    workspace = WorkspaceModel(name=name,owner_id=owner_id)
    session.add(workspace)
    await session.flush()
    return workspace

async def find_by_id(
        session:AsyncSession,
        workspace_id:UUID
) -> WorkspaceModel | None:
    return await session.get(WorkspaceModel,workspace_id)

async def list_for_user(
        session:AsyncSession,
        user_id:UUID
) -> list[WorkspaceModel]:
    stmt = (
        select(WorkspaceModel)
        .join(MemberShipModel,MemberShipModel.workspace_id == WorkspaceModel.id)
        .where(MemberShipModel.user_id == user_id)
        .order_by(WorkspaceModel.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
