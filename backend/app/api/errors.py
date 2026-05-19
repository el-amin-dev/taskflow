
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    detail: str
    code: str


class ErrorOut(BaseModel):
    detail: ErrorDetail

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": {
                    "detail": "human-readable message",
                    "code": "machine_readable_slug",
                }
            }
        }
    }


def _resp(description: str) -> dict:
    return {
        "model": ErrorOut,
        "description": description,
    }


UNAUTHORIZED = {401: _resp("Missing, malformed, expired, or reused token. "
                           "Body: {detail:{detail, code}}.")}
FORBIDDEN = {403: _resp("Authenticated but not permitted (e.g. not the "
                        "comment author).")}
NOT_FOUND = {404: _resp("Resource absent, or not visible to the caller "
                        "(cross-tenant access is indistinguishable from "
                        "absence — by design).")}
BAD_REQUEST = {400: _resp("Invalid request (e.g. malformed pagination "
                          "cursor, duplicate registration).")}
CONFLICT = {409: _resp("State conflict (e.g. already a member, cannot "
                       "remove the owner).")}
