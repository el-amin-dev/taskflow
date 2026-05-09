from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from datetime import datetime, timedelta ,timezone
from uuid import UUID

import jwt 
from app.core.config import get_settings


_hasher = PasswordHasher()

def hash_password (plaintext:str) -> str:
    return _hasher.hash(plaintext)

def verify_password (plaintext:str,hashed:str) -> bool:
    try:
        _hasher.verify(hashed,plaintext) 
        return True
    except VerifyMismatchError:
        return False


class InvalidToken(Exception):
    pass

def create_access_token(*,user_id: UUID , role:str) -> str:
    settings= get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub" : str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp())
    } 

    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm='HS256')


def decode_token(token: str)-> dict  :
    try:
        return jwt.decode(
            token,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=["HS256"]
        )
    except jwt.PyJWTError as e:
        raise InvalidToken() from e