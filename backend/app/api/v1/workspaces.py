from datetime import datetime
from uuid import UUID

from fastapi import APIRouter,Depends,status

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.domain.workspace import Workspace
from app.domain.user import User
from app.infra.db import get_db
from app.services import workspace_service


router = APIRouter(prefix="/workspaces",tags=["workspaces"])

class WorkspaceCreate(BaseModel):
    name:str = Field(min_length=1 , max_length=100)

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

@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_workspace(
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
async def list_workspaces(
    user : User = Depends(get_current_user),
    session : AsyncSession = Depends(get_db)
) -> list[WorkspaceResponse]:
    workspaces  = await workspace_service.list_my_workspaces(session=session , user_id= user.id)
    return [WorkspaceResponse.from_domain(workspace) for workspace in workspaces]
