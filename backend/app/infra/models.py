from datetime import datetime
from uuid import UUID , uuid4

from typing import Optional

from sqlalchemy import String,DateTime,func , ForeignKey,Text
from sqlalchemy.dialects.postgresql import UUID as pgUUID , JSONB
from sqlalchemy.orm import DeclarativeBase , Mapped , mapped_column

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__= "users"

    id:             Mapped[UUID]    = mapped_column(pgUUID(as_uuid=True),primary_key=True,default=uuid4)
    email:          Mapped[str]     = mapped_column(String(255),unique=True,nullable=False,index=True)
    hashed_password:Mapped[str]     = mapped_column(String(255),nullable=False)
    role:           Mapped[str]     = mapped_column(String(25),nullable=False,default='member')
    created_at:     Mapped[datetime]= mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)


class WorkspaceModel(Base):
    __tablename__ = "workspaces"

    id:         Mapped[UUID]        = mapped_column(pgUUID(as_uuid=True),primary_key=True,default=uuid4)
    name:       Mapped[str]         = mapped_column(String(100),nullable=False)
    owner_id :  Mapped[UUID]        = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)


class MemberShipModel(Base):
    __tablename__ = "workspace_memberships"
    
    
    user_id:      Mapped[UUID]      = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="CASCADE"),primary_key=True)
    workspace_id: Mapped[UUID]      = mapped_column(pgUUID(as_uuid=True),ForeignKey("workspaces.id",ondelete="CASCADE"),primary_key=True,index=True)
    role :        Mapped[str]       = mapped_column(String(25),nullable=False,default="member")
    joined_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)

class TaskModel(Base):
    __tablename__="tasks"

    id :        Mapped[UUID]         = mapped_column(pgUUID(as_uuid=True),primary_key=True,default=uuid4)
    workspace_id:Mapped[UUID]        = mapped_column(pgUUID(as_uuid=True),ForeignKey("workspaces.id",ondelete="CASCADE"),nullable=False,index=True)
    title:      Mapped[str]          = mapped_column(String(200),nullable=False)
    description:Mapped[Optional[str]]     = mapped_column(Text,nullable=True)
    status:     Mapped[str]          = mapped_column(String(25),nullable=False,server_default="todo")
    assignee_id:Mapped[Optional[UUID]]    = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="SET NULL"),nullable=True)
    deadline:   Mapped[Optional[datetime]]= mapped_column(DateTime(timezone=True),nullable=True)
    created_by: Mapped[UUID]         = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="RESTRICT"),nullable=False)
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
    deleted_at: Mapped[datetime|None]= mapped_column(DateTime(timezone=True),nullable=True)


class AuditLogModel(Base):
    __tablename__="audit_log"

    id:             Mapped[UUID]            = mapped_column(pgUUID(as_uuid=True),primary_key=True,default=uuid4)
    actor_user_id:  Mapped[Optional[UUID]]  = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True)
    workspace_id:   Mapped[Optional[UUID]]  = mapped_column(pgUUID(as_uuid=True),ForeignKey("workspaces.id",ondelete="SET NULL"),nullable=True,index=True)
    action:         Mapped[str]             = mapped_column(String(64),nullable=False,index=True)
    target_type:    Mapped[str]             = mapped_column(String(32),nullable=False)
    target_id:      Mapped[UUID]            = mapped_column(pgUUID(as_uuid=True),nullable=False)
    payload:        Mapped[dict]            = mapped_column(JSONB,nullable=False,server_default="{}")
    created_at:     Mapped[datetime]        = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)


class TaskCommentModel(Base):
    __tablename__= "task_comments"
    id:         Mapped[UUID]            = mapped_column(pgUUID(as_uuid=True),primary_key=True,default=uuid4)
    task_id:    Mapped[UUID]            = mapped_column(pgUUID(as_uuid=True),ForeignKey("tasks.id",ondelete="CASCADE"),nullable=False,index=True)
    author_id:  Mapped[Optional[UUID]]  = mapped_column(pgUUID(as_uuid=True),ForeignKey("users.id",ondelete="SET NULL"),nullable=True)
    body:       Mapped[str]             = mapped_column(Text,nullable=False)
    created_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
    deleted_at: Mapped[datetime|None]   = mapped_column(DateTime(timezone=True),nullable=True,)

