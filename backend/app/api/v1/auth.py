

from fastapi import APIRouter ,Depends, HTTPException , status
from pydantic import BaseModel , EmailStr , Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.user import Role , User
from app.infra.db import get_db
from app.infra.security import create_access_token
from app.services.user_service import EmailNotAvailable , InvalidCredentials
from app.services import user_service
from app.api.dependencies import get_current_user , _user_id_or_ip


from fastapi import Request
from app.infra.rate_limiter import limiter,SIXTY_PER_MINUTE

from app.infra import refresh_store

from app.infra.repositories import audit_repo, user_repo

from app.api.errors import UNAUTHORIZED, BAD_REQUEST

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
    refresh_token:str
    token_type:str = "bearer"
    expires_in:int

class ErrorOut(BaseModel):
    detail:str
    code : str

class RefreshRequest(BaseModel):
    refresh_token:str

class LogoutRequest(BaseModel):
    refresh_token:str


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


_INVALID_REFRESH = "invalid or expired refresh token"    


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**BAD_REQUEST}
)
@limiter.limit("10/hour")
async def register(
    request:    Request,
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
    status_code=status.HTTP_200_OK,
    responses={**UNAUTHORIZED}
)
@limiter.limit("5/minute")
async def login(
    request:Request,
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
    refresh_token,_family_id = refresh_store.create(user.id)

    return TokenResponse(
        access_token=token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_ttl_minutes * 60
    )

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={**UNAUTHORIZED}
)
@limiter.limit(SIXTY_PER_MINUTE,key_func=_user_id_or_ip)
async def me (
    request:Request,
    user:User = Depends(get_current_user),

) -> UserResponse:
    return UserResponse.from_domain(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={**UNAUTHORIZED}
)
@limiter.limit(SIXTY_PER_MINUTE,key_func=_user_id_or_ip)
async def refresh(
    request:Request,
    payload:RefreshRequest,
    session:AsyncSession = Depends(get_db)

)-> TokenResponse:
    result = refresh_store.rotate(payload.refresh_token)

    if isinstance(result,refresh_store.NotFound):
        raise _error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            detail=_INVALID_REFRESH,
            headers={"WWW-Authenticate":"Bearer"}
        )
    if isinstance(result,refresh_store.ReuseDetected):
        await audit_repo.record(
            session,
            actor_user_id=result.user_id,
            workspace_id=None,
            action="auth.refresh_reuse_detected",
            target_type="user",
            target_id=result.user_id,
            payload={"family_id":str(result.family_id)}
        )
        await session.commit()
        raise _error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            detail=_INVALID_REFRESH,
            headers={"WWW-Authenticate" : "Bearer"}
        )
    
    user = await user_repo.find_by_id(session,result.user_id)
    if user is None:
        raise _error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            detail=_INVALID_REFRESH,
            headers={"WWW-Authenticate" : "Bearer"}
        )
    await audit_repo.record(
        session=session,
        actor_user_id=user.id,
        action="auth.refreshed",
        workspace_id=None,
        target_id=user.id,
        target_type="user",
        payload={}
    )
    await session.commit()

    settings = get_settings()

    access = create_access_token(user_id=user.id,role=user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=result.new_token,
        expires_in=settings.jwt_access_ttl_minutes * 60
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit(SIXTY_PER_MINUTE,key_func=_user_id_or_ip)
async def logout(
    request:Request,
    payload:LogoutRequest,
    session:AsyncSession = Depends(get_db)
)-> None:
    killed  = refresh_store.revoke(payload.refresh_token)

    if killed is not None:
        family_id , user_id = killed
        await audit_repo.record(
            session=session,
            actor_user_id=user_id,
            workspace_id=None,
            action="auth.logged_out",
            target_id=user_id,
            target_type="user",
            payload={"family_id":str(family_id)}
        )
        await session.commit()
    
    return None
