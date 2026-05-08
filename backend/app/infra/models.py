from datetime import datetime
from uuid import UUID , uuid4

from sqlalchemy import String,DateTime,func
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


