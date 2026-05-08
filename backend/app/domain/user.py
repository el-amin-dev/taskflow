from dataclasses import dataclass

from datetime import datetime

from enum import Enum

from uuid import UUID

class Role(str,Enum):
    ADMIN='admin'
    MEMBER='member'
    VIEWER='viewer'

@dataclass(frozen=True,slots=True)
class User:
    id:UUID
    email:str
    role:Role
    created_at:datetime
