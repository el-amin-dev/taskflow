from fastapi import Depends , HTTPException , Request ,status 
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import Role , User
from app.infra.db import get_db
from app.infra.security import InvalidToken , decode_token
from app.infra.repositories import  user_repo


def _unauthorized() -> HTTPException :
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"detail":"authentication required","code":"invalid_token"},
        headers={"WWW-Authenticate":"Bearer"}
    )

async def get_current_user(
        request : Request,
        session :AsyncSession =Depends( get_db),

) -> User:
    header = request.headers.get("Authorization")

    if header is None :
        raise _unauthorized()
    scheme, _ , token = header.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    
    try:
        claims = decode_token(token=token)
    except InvalidToken:
        raise _unauthorized()
    
    user_id = claims.get("sub")
    if not user_id:
        raise _unauthorized()
    
    
    model = await user_repo.find_by_id(session, user_id)
    if model is None:
        raise _unauthorized()
    
    return User(
        id=model.id,
        email=model.email,
        role=Role(model.role),
        created_at=model.created_at
    )