from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID



class WorkspaceRole(str, Enum):
    ADMIN   = "admin"
    MEMBER  = "member"
    VIEWER  = "viewer"

@dataclass(frozen=True,slots=True)
class Workspace:
    id          : UUID
    name        : str
    owner_id    : UUID
    created_at  : datetime

@dataclass(frozen=True,slots=True)
class MemberShip:
    user_id     : UUID
    workspace_id: UUID
    role        : WorkspaceRole    
    joined_at   : datetime
