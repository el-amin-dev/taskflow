from datetime import datetime
from uuid import UUID , uuid4

from sqlalchemy import String,DateTime,func , ForeignKey
from sqlalchemy.dialects.postgresql import UUID as pgUUID
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