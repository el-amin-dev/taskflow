import time 

from fastapi import APIRouter 
router = APIRouter(tags=["meta"])

_started_at = time.monotonic()

@router.get("/health")
async def health() -> dict[str , object]:
    return {"status": "ok" , "uptime_seconds": round(time.monotonic() - _started_at,1)}

@router.get("/ready")
async def ready() -> dict [str,object]:

    checks : dict [str, object] = {}
    
    # check postgres and redis will be here 

    is_ready = all (v == "ok" for v in checks.values())
    return {
        "status" : "ready" if is_ready else "not ready",
        "checks" : checks
    }