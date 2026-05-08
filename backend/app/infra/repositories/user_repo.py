from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.models import UserModel

async def create(
        session: AsyncSession , 
        *,
        email:str,
        hashed_password: str,
        role: str = 'member',

) -> UserModel:
    user = UserModel(email=email , hashed_password=hashed_password, role=role,)
    session.add(user)
    await session.flush()
    return user




async def find_by_email(
        session:AsyncSession ,
        email:str
) -> UserModel | None:
    result = await session.execute(
        select(UserModel).where(UserModel.email == email)
    )
    return result.scalar_one_or_none()




async def find_by_id(
        session:AsyncSession,
        user_id:UUID
) -> UserModel | None:
    return await session.get(UserModel, user_id)

