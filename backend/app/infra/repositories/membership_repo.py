from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select , delete as sa_delete

from app.infra.models import  MemberShipModel


async def create(
    session:AsyncSession,
    *,
    user_id:UUID,
    workspace_id:UUID,
    role:str
) -> MemberShipModel:
    membership = MemberShipModel(
        user_id = user_id,
        workspace_id = workspace_id,
        role=role,

    )    

    session.add(membership)
    await session.flush()
    return membership

async def find(
        session:AsyncSession,
        *,
        user_id:UUID,
        workspace_id:UUID,

)-> MemberShipModel | None:
    return await session.get(MemberShipModel , (user_id,workspace_id))


async def delete (
        session:AsyncSession,
        *,
        user_id:UUID,
        workspace_id:UUID,
) -> bool:
    stmt = (
        sa_delete(MemberShipModel)
        .where(MemberShipModel.user_id == user_id , MemberShipModel.workspace_id == workspace_id)
    )

    result = await session.execute(stmt)
    return result.rowcount > 0

async def list_for_workspace(
        session:AsyncSession,
        workspace_id:UUID
        
)-> list[MemberShipModel]:
    stmt = select (MemberShipModel).where(MemberShipModel.workspace_id==workspace_id).order_by(MemberShipModel.joined_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())