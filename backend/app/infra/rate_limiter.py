


from urllib.parse import urlparse ,urlunparse
from fastapi import Request , status 

from slowapi import Limiter
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings

def _limiter_storage_url ()-> str :
    parsed = urlparse(get_settings().redis_url)
    return urlunparse(parsed._replace(path="/1"))


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_limiter_storage_url(),
    strategy="fixed-window"
)

async def rate_limit_exceeded_handler(
        request : Request ,
        exc : RateLimitExceeded    
)-> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail" : {
                "detail": "rate limit exceeded",
                "code" : "rate_limit_exceeded"
            }
        }
    )

