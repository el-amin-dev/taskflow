

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.task import Task, TaskStatus
from app.infra.models import TaskModel
from app.infra.repositories import task_repo

from app.domain.workspace import WorkspaceRole

def _to_task_domain(model: TaskModel) -> Task:
    return Task(
        id=model.id,
        workspace_id=model.workspace_id,
        title=model.title,
        description=model.description,
        status=TaskStatus(model.status),
        assignee_id=model.assignee_id,
        deadline=model.deadline,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )





async def create_task(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    creator_id: UUID,
    title: str,
    description: str | None,
    status: TaskStatus,
    assignee_id: UUID | None,
    deadline: datetime | None,
) -> Task:

    model = await task_repo.create(
        session,
        workspace_id=workspace_id,
        title=title,
        description=description,
        status=status.value,
        assignee_id=assignee_id,
        deadline=deadline,
        created_by=creator_id,
    )
    await session.commit()
    return _to_task_domain(model)


async def list_tasks(
    session: AsyncSession,
    workspace_id: UUID,
    *,
    status_filter: TaskStatus | None = None,
) -> list[Task]:

    status_str = status_filter.value if status_filter is not None else None
    models = await task_repo.list_for_workspace(
        session, workspace_id, status=status_str,
    )
    return [_to_task_domain(m) for m in models]



class TaskNotFound(Exception):
    pass



def _assert_task_authz(
        task: TaskModel,
        caller_id:UUID,
        caller_role:WorkspaceRole
)-> None:
    if caller_role == WorkspaceRole.ADMIN:
        return
    if task.created_by != caller_id:
        raise TaskNotFound()
    

async def get_task(
        session:AsyncSession,
        *,
        task_id:UUID,
        workspace_id:UUID,
        caller_id:UUID,
        caller_role:WorkspaceRole
)-> Task:
    model = await task_repo.find_by_id(session,task_id)
    if model is None:
        raise TaskNotFound()
    if model.workspace_id != workspace_id:
        raise TaskNotFound()
    
    return _to_task_domain(model)

async def update_task(
        session:AsyncSession,
        *,
        task_id:UUID,
        workspace_id:UUID,
        caller_id:UUID,
        caller_role:WorkspaceRole,
        fields:dict,
)->Task:
    model = await task_repo.find_by_id(session,task_id)
    if model is None:
        raise TaskNotFound()
    if model.workspace_id != workspace_id:
        raise TaskNotFound()
    
    _assert_task_authz(model,caller_id=caller_id,caller_role=caller_role)

    if "status" in fields and isinstance(fields["status"],TaskStatus):
        fields["status"] = fields["status"].value
    
    updated = await task_repo.update(session,task_id,fields=fields)
    await session.commit()
    return _to_task_domain(updated)


async def delete_task(
        session: AsyncSession,
        *,
        task_id:UUID,
        workspace_id:UUID
) -> None:
    model = await task_repo.find_by_id(
        session = session ,task_id=task_id
    )
    if model is None:
        raise TaskNotFound()
    if model.workspace_id != workspace_id :
        raise TaskNotFound()
    
    await task_repo.soft_delete(session=session,task_id=task_id)
    await session.commit()
