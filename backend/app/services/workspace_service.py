from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession



from app.domain.workspace import Workspace , MemberShip ,WorkspaceRole
from app.infra.models import MemberShipModel , WorkspaceModel
from app.infra.repositories import workspace_repo,membership_repo

class WorkspaceNotFound(Exception):
    pass

class NotAMember(Exception):
    pass

class InsuffcientWorkspaceRole(Exception):
    pass

def _to_workspace_domain(
        model:WorkspaceModel

)->Workspace:
    return Workspace(
        id=model.id,
        name=model.name,
        owner_id=model.owner_id,
        created_at=model.created_at
    )

def _to_membership_domain(
        model:MemberShipModel
) -> MemberShip:
    return MemberShip(
        user_id=model.user_id,
        workspace_id=model.workspace_id,
        role=WorkspaceRole(model.role),
        joined_at=model.joined_at
    )



async def create_workspace(
        session: AsyncSession,
        *,
        name:str,
        creator_id:UUID,

)-> Workspace:
    ws_model = await workspace_repo.create(
        session= session,
        name=name,
        owner_id=creator_id
    )
    await membership_repo.create(
        session=session,
        user_id=creator_id,
        workspace_id=ws_model.id,
        role=WorkspaceRole.ADMIN.value
    )
    await session.commit()
    return _to_workspace_domain(ws_model)

async def list_my_workspaces (
        session: AsyncSession,
        user_id:UUID
) -> list[Workspace]:
    models = await workspace_repo.list_for_user(session,user_id=user_id)
    return list( _to_workspace_domain(model) for model in models )


async def get_workspace_for_member(
        session:AsyncSession,
        *,
        workspace_id:UUID,
        user_id:UUID,
) -> tuple[Workspace,MemberShip]:
    ws_model = await workspace_repo.find_by_id(session,workspace_id=workspace_id)
    if ws_model is None:
        raise NotAMember()
    m_model = await membership_repo.find(
        session=session,user_id=user_id,workspace_id=workspace_id
    )
    if m_model is None:
        raise NotAMember()
    return _to_workspace_domain(ws_model),_to_membership_domain(m_model)
