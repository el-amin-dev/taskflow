from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


from app.domain.user import Role,User
from app.infra.models import UserModel
from app.infra.repositories import user_repo
from app.infra.security import hash_password , verify_password

_DUMMY_HASH = hash_password("constant-time-dummy-never-matches")

class EmailNotAvailable(Exception):
    pass
class InvalidCredentials(Exception):
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


async def authenticate(
        session:        AsyncSession,
        *,
        email:          str,
        password:       str,
) -> User:
    model       = await user_repo.find_by_email(session,email=email)

    hashed      = model.hashed_password if model is not None else _DUMMY_HASH
    password_ok = verify_password(password,hashed)

    if model is None or not password_ok:
        raise InvalidCredentials()
    return _to_domain(model)