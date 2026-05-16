from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.models import AuditLogModel

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