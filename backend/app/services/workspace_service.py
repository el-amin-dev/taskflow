from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


from app.domain.workspace import Workspace , MemberShip ,WorkspaceRole
from app.infra.models import MemberShipModel , WorkspaceModel
from app.infra.repositories import workspace_repo,membership_repo, user_repo

class WorkspaceNotFound(Exception):
    pass

class NotAMember(Exception):
    pass

class InsuffcientWorkspaceRole(Exception):
    pass

class UserNotFound(Exception):
    pass

class AlreadyMember(Exception):
    pass

class CannotRemoveOwner(Exception):
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


async def invite_member(
        session:AsyncSession,
        *,
        workspace_id : UUID,
        invitee_email : str,
        role : WorkspaceRole,
)-> MemberShip:
    
    invitee = await user_repo.find_by_email(
        session=session,
        email=invitee_email 
    )
    if invitee is None:
        raise UserNotFound()
    
    exsisting = await membership_repo.find(
        session=session ,
        user_id=invitee.id,
        workspace_id=workspace_id,
    )
    if exsisting is not None:
        raise AlreadyMember()
    
    m_model = await membership_repo.create(
        session=session,
        user_id=invitee.id,
        workspace_id=workspace_id,
        role=role.value
    )

    await session.commit()

    return _to_membership_domain(m_model)


async def remove_member(
        session:AsyncSession,
        *,
        target_user_id :UUID,
        workspace_id: UUID
)-> None:
    workspace = await workspace_repo.find_by_id(session=session,workspace_id=workspace_id)
    if workspace is None:
        raise NotAMember()
    
    if workspace.owner_id == target_user_id:
        raise CannotRemoveOwner()
    
    deleted = await membership_repo.delete(session, user_id=target_user_id, workspace_id=workspace_id)

    if not deleted:
        raise NotAMember()
    
    await session.commit()