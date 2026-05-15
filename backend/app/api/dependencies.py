from fastapi import Depends , HTTPException , Request ,status 
from sqlalchemy.ext.asyncio import AsyncSession

from slowapi.util import get_remote_address

from app.domain.user import Role , User
from app.infra.db import get_db
from app.infra.security import InvalidToken , decode_token
from app.infra.repositories import  user_repo


from typing import Callable,Awaitable

from uuid import UUID
from app.domain.workspace import MemberShip , Workspace , WorkspaceRole
from app.services import  workspace_service
from app.services.workspace_service import NotAMember


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


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"detail":"workspace not found","code":"workspace_not_found"},
    )

def require_workspace_role (
        allowed_roles:set[WorkspaceRole|str],


) -> Callable[...,Awaitable[tuple[Workspace,MemberShip]]]:

    normalized :set[WorkspaceRole] = {
        WorkspaceRole(r) if isinstance(r,str) else r 
        for r in allowed_roles
    }    

    async def _checker(
             workspace_id:UUID,
             user:User = Depends(get_current_user),
             session : AsyncSession = Depends(get_db),
             )-> tuple[Workspace,MemberShip]:
        
        try:
            workspace,membership = await workspace_service.get_workspace_for_member(
                session,workspace_id=workspace_id , user_id= user.id
            )
        except NotAMember:
            raise _not_found()
        

        if membership.role not in normalized:
            raise _not_found()
        
        return workspace , membership
    
    return _checker
     

def _user_id_or_ip(request:Request) -> str :
    auth_header = request.headers.get("authorization","")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        try:
            claims  = decode_token(token=token)
            return f"user:{claims['sub']}"
        except (InvalidToken,KeyError):
            pass
    return f"ip:{get_remote_address(request)}"