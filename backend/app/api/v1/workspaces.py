from datetime import datetime
from uuid import UUID

from fastapi import APIRouter,Depends,status , HTTPException , Request

from pydantic import BaseModel, Field ,EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user ,require_workspace_role , _user_id_or_ip
from app.domain.workspace import Workspace , MemberShip ,WorkspaceRole
from app.domain.user import User
from app.infra.db import get_db
from app.services import workspace_service
from app.services.workspace_service import UserNotFound,AlreadyMember,CannotRemoveOwner,NotAMember

from app.infra.rate_limiter import limiter


from typing import Literal



router = APIRouter(prefix="/workspaces",tags=["workspaces"])

class WorkspaceCreate(BaseModel):
    name:str = Field(min_length=1 , max_length=100)

class MemberInvite(BaseModel):
    email:EmailStr
    role : Literal["admin","member","viewer"]

class MemberResponse(BaseModel):
    user_id:UUID
    workspace_id:UUID
    role: str
    joined_at:datetime

    @classmethod
    def from_domain(cls , m : MemberShip):
        return cls(
            user_id= m.user_id,
            workspace_id = m.workspace_id,
            role = m.role.value,
            joined_at= m.joined_at
        )
class WorkspaceResponse(BaseModel):
    id : UUID
    name : str
    owner_id : UUID
    created_at :datetime

    @classmethod
    def from_domain(cls , w:Workspace ) -> "WorkspaceResponse":
        return cls(
            id = w.id,
            name = w.name,
            owner_id = w.owner_id,
            created_at = w.created_at
        )
    

def _error(*,status_code:int, code:str,detail:str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail":detail,"code":code}
    )

@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute",key_func=_user_id_or_ip)
async def create_workspace(
    request:Request,
    payload: WorkspaceCreate,
    user: User = Depends(get_current_user),
    session:AsyncSession = Depends (get_db),
)-> WorkspaceResponse:
    ws = await workspace_service.create_workspace(
        session=session , 
        name=payload.name ,
        creator_id=user.id
           
    )
    return WorkspaceResponse.from_domain(ws)

@router.get(
    "",
    response_model=list[WorkspaceResponse],
    status_code=status.HTTP_200_OK
)
@limiter.limit("60/minute",key_func=_user_id_or_ip)
async def list_workspaces(
    request:Request,
    user : User = Depends(get_current_user),
    session : AsyncSession = Depends(get_db)
) -> list[WorkspaceResponse]:
    workspaces  = await workspace_service.list_my_workspaces(session=session , user_id= user.id)
    return [WorkspaceResponse.from_domain(workspace) for workspace in workspaces]


@router.post(
    "/{workspace_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("60/minute",key_func=_user_id_or_ip)
async def invite_member(
    request: Request,
    workspace_id:UUID,
    payload : MemberInvite,
    session : AsyncSession = Depends(get_db),
    ctx :tuple[Workspace,MemberShip] = Depends(require_workspace_role({"admin"}))


)-> MemberResponse:
    try:
        m = await workspace_service.invite_member(
            session=session,
            workspace_id=workspace_id,
            invitee_email=payload.email,
            role=WorkspaceRole(payload.role)

        )

    except AlreadyMember:
        raise _error(
            status_code=status.HTTP_409_CONFLICT,
            code="already_member",
            detail="user is already member of this workspace"
        )
    except UserNotFound:
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="user_not_found",
            detail="no user with this mail "
        )
    return MemberResponse.from_domain(m)



@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("60/minute",key_func=_user_id_or_ip)
async def remove_member(
    request:Request,
    workspace_id: UUID,
    user_id: UUID,
    ctx: tuple[Workspace, MemberShip] = Depends(require_workspace_role({"admin"})),
    session: AsyncSession = Depends(get_db),
) -> None:

    try:
        await workspace_service.remove_member(
            session, workspace_id=workspace_id, target_user_id=user_id,
        )
    except CannotRemoveOwner:
        raise _error(
            status_code=status.HTTP_409_CONFLICT,
            code="cannot_remove_owner",
            detail="cannot remove the workspace owner",
        )
    except NotAMember:
        raise _error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="member_not_found",
            detail="that user is not a member of this workspace",
        )