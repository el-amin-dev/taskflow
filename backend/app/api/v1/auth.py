


from fastapi import APIRouter ,Depends, HTTPException , status
from pydantic import BaseModel , EmailStr , Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.user import Role , User
from app.infra.db import get_db
from app.infra.security import create_access_token
from app.services.user_service import EmailNotAvailable , InvalidCredentials
from app.services import user_service
from app.api.dependencies import get_current_user



router = APIRouter (prefix="/auth",tags=["auth"])

class RegisterRequest (BaseModel):
    email:EmailStr
    password: str = Field(min_length=8 , max_length=128)

class LoginRequest (BaseModel):
    email:EmailStr
    password:str = Field(max_length=128 , min_length=1)


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
    
class TokenResponse(BaseModel):
    access_token:str
    token_type:str = "bearer"
    expires_in:int

class ErrorOut(BaseModel):
    detail:str
    code : str

def _error(
        *,
        status_code : int ,
        code        : str ,
        detail      : str ,
        headers     : dict | None = None ,
)-> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail  = ErrorOut(detail=detail,code=code).model_dump(),
        headers=headers
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
        raise _error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="email_unavailable",
            detail="could not create account"
        )

    return UserResponse.from_domain(u=user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK
)
async def login(
    payload:LoginRequest,
    session: AsyncSession = Depends(get_db),

) -> TokenResponse:
    try:
        user = await user_service.authenticate(
            session=session,
            email=payload.email,
            password=payload.password
        )

    except InvalidCredentials:
        raise _error(
            status_code = status.HTTP_401_UNAUTHORIZED,
            code        = "invalid_credentials",
            detail      = "invalid email or password",
            headers     = { "WWW-Authenticate": "Bearer" },
        )
        
    settings = get_settings()
    token = create_access_token(user_id=user.id , role=user.role.value)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_ttl_minutes * 60
    )

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK
)
async def me (
    user:User = Depends(get_current_user),

) -> UserResponse:
    return UserResponse.from_domain(user)