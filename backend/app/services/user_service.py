from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


from app.domain.user import Role,User
from app.infra.models import UserModel
from app.infra.repositories import user_repo
from app.infra.security import hash_password


class EmailNotAvailable(Exception):
    pass

def _to_domain(model:UserModel) -> User:
    return User (
        id=model.id,
        email=model.email,
        role=Role(model.role),
        created_at=model.created_at
    )

async def register (
        session: AsyncSession,
        *,
        email:str,
        password: str ,
        role: Role =Role.MEMBER,
) -> User:
    try:

        model = await user_repo.create(
            session,email=email,
            hashed_password=hash_password(password),
            role=role.value
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise EmailNotAvailable() from None
    return _to_domain(model)
