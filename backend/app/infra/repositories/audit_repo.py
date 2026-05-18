from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.models import AuditLogModel

from datetime import datetime
from sqlalchemy import select,tuple_


async def record (
        session:AsyncSession,
        *,
        actor_user_id:UUID | None,
        workspace_id:UUID | None,
        action : str,
        target_type:str,
        target_id:UUID,
        payload:dict |None=None,
)-> AuditLogModel:
    entry = AuditLogModel(
        actor_user_id=actor_user_id,
        workspace_id=workspace_id,
        action=action,
        target_id=target_id,
        target_type=target_type,
        payload=payload if payload is not None else {}
    )

    session.add(entry)
    await session.flush()
    return entry


async def list_for_workspace(
        session:AsyncSession,
        workspace_id:UUID,
        *,
        limit:int,
        before:tuple[datetime,UUID] | None = None,
        action:str | None=None,
        actions:set[str] | None=None,

)->list[AuditLogModel]:
    stmt = select(AuditLogModel).where(
        AuditLogModel.workspace_id == workspace_id
    )

    if action is not None:
        stmt = stmt.where(AuditLogModel.action == action)
    
    if actions is not None:
        stmt = stmt.where(AuditLogModel.action.in_(actions))

    if before is not None:
        stmt = stmt.where(
            tuple_(AuditLogModel.created_at,AuditLogModel.id) < before
        ) 
    stmt = stmt.order_by(
        AuditLogModel.created_at.desc(),
        AuditLogModel.id.desc()
    ).limit(limit)


    result = await session.execute(stmt)
    return list(result.scalars().all())