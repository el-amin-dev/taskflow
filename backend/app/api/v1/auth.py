


from fastapi import APIRouter ,Depends, HTTPException , status
from pydantic import BaseModel , EmailStr , Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import Role , User
from app.infra.db import get_db
from app.services.user_service import EmailNotAvailable
from app.services import user_service


router = APIRouter (prefix="/auth",tags=["auth"])

class RegisterRequest (BaseModel):
    email:EmailStr
    password: str = Field(min_length=8 , max_length=128)


class UserResponse(BaseModel):
    id          : str
    email       : str
    role        : str
    created_at  : str
    

    @classmethod
    def from_domain(cls, u:User) -> "UserResponse":
        return cls(
            id          = str(u.id),
            email       = u.email,
            role        = u.role,
            created_at  = u.created_at.isoformat(),
        )
    

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    payload:    RegisterRequest,
    session:    AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        user = await user_service.register(
            session =session,
            email   =payload.email,
            password=payload.password,
            role=Role.MEMBER,
        )
    except EmailNotAvailable :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="could not create account"
        )
    return UserResponse.from_domain(u=user)

