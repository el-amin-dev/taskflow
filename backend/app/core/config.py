from enum import Enum

from functools import lru_cache

from pydantic import Field , SecretStr
from pydantic_settings import BaseSettings , SettingsConfigDict

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf_8" ,
        case_sensitive=False,
        extra="ignore",

    )

    app_name: str = "TaskFlow"
    environment: Environment=Environment.DEV
    debug: bool=False


    database_url: str = Field(
        ...,
        description="postgres dsn example postgresql+asyncpg://user:pass@host:5432/db"
    )
    redis_url : str = Field (
        ...,
        description="redis url exmaple redis://localhost:6379/0"
    )

    jwt_secret: SecretStr = Field (
        ...,
        min_length=32,
        description="HS256 signing key , 32+ chars"
    )

    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30


    cors_origins:list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

@lru_cache(maxsize=1)
def get_settings()-> Settings:
    return Settings()
