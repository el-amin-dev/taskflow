import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlparse , urlunparse
from uuid import UUID , uuid4
import redis
from app.core.config import get_settings




@dataclass(slots=True,frozen=True)
class Rotated : 
    new_token:str
    user_id:UUID


@dataclass(slots=True,frozen=True)
class NotFound:
    pass

@dataclass(frozen=True,slots=True)
class ReuseDetected:
    family_id:UUID
    user_id:UUID


RotateResult = Rotated | NotFound | ReuseDetected



def _store_url()-> str:
    parsed = urlparse(get_settings().redis_url)
    return urlunparse(parsed._replace(path="/2"))


def _client() -> redis.Redis:
    return redis.Redis.from_url(_store_url(),decode_responses=True)

def _ttl_seconds() -> int:
    return get_settings().jwt_refresh_ttl_days * 24 * 60 * 60




def create (user_id:UUID) -> tuple[str,str]:
    r = _client ()
    token = secrets.token_urlsafe(32)
    family_id = str(uuid4())
    ttl = _ttl_seconds()

    record = json.dumps({
        "user_id": str(user_id),
        "family_id": family_id,
        "status" : "active"}
    )

    pipe = r.pipeline()
    pipe.set(f"refresh:{token}",record,ex=ttl)
    pipe.sadd(f"family:{family_id}",token)
    pipe.expire(f"family:{family_id}",ttl)
    pipe.execute()

    return token,family_id

def rotate(token:str) -> RotateResult:
    r = _client()
    raw = r.get(f"refresh:{token}")
    if raw is None:
        return NotFound()

    rec = json.loads(raw)
    family_id = rec["family_id"]

    if rec["status"] == "rotated":

        invalidate_family(UUID(family_id)) 
        return ReuseDetected(family_id=UUID(family_id),user_id=UUID(rec['user_id']))


    user_id = rec["user_id"]
    ttl = _ttl_seconds()
    rec["status"] = "rotated"

    new_token = secrets.token_urlsafe(32)
    new_record = json.dumps({
        "user_id": user_id,
        "family_id": family_id,
        "status": "active",
    })

    pipe = r.pipeline()

    pipe.set(f"refresh:{token}", json.dumps(rec), keepttl=True)
    pipe.set(f"refresh:{new_token}", new_record, ex=ttl)
    pipe.sadd(f"family:{family_id}", new_token)
    pipe.expire(f"family:{family_id}", ttl)
    pipe.execute()

    return Rotated(new_token=new_token, user_id=UUID(user_id))


def invalidate_family(family_id: UUID) -> None:

    r = _client()
    fam_key = f"family:{family_id}"
    tokens = r.smembers(fam_key)

    pipe = r.pipeline()
    for t in tokens:
        pipe.delete(f"refresh:{t}")
    pipe.delete(fam_key)
    pipe.execute()



