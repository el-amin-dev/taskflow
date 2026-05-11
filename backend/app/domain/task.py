

from dataclasses import dataclass
from datetime import datetime

from enum import Enum
from uuid import UUID


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class Task:
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    assignee_id: UUID | None
    deadline: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
