"""API error contract: exception hierarchy + exit-code mapping.

Mirrors the backend's machine-readable error envelope:
    { "detail": { "detail": "human message", "code": "machine_slug" } }

Clients branch on the exception type (or .code), never on prose.
Each exception knows its own exit code per the documented scheme.
"""
from __future__ import annotations

# Exit codes — the scriptable contract. Documented in the CLI README.
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_USAGE = 2          # Typer raises this for bad argv (we don't)
EXIT_AUTH = 10
EXIT_NOT_FOUND = 11
EXIT_FORBIDDEN = 12
EXIT_CONFLICT = 13
EXIT_NETWORK = 14
EXIT_BAD_REQUEST = 15
EXIT_SERVER = 16


class ApiError(Exception):
    """Base for any error originating from API interaction."""

    exit_code: int = EXIT_GENERIC
    code: str | None = None

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status


# ---------- by-`code` subclasses (one per backend slug) ----------

class InvalidCredentials(ApiError):
    """401 — login failed; cause never disclosed (non-disclosure discipline)."""
    exit_code = EXIT_AUTH
    code = "invalid_credentials"


class InvalidToken(ApiError):
    """401 — access/refresh missing, malformed, expired, or reused. One bucket."""
    exit_code = EXIT_AUTH
    code = "invalid_token"


class EmailUnavailable(ApiError):
    """400 — registration email already taken."""
    exit_code = EXIT_CONFLICT
    code = "email_unavailable"


class UserNotFound(ApiError):
    """404 — target user does not exist."""
    exit_code = EXIT_NOT_FOUND
    code = "user_not_found"


class MemberNotFound(ApiError):
    """404 — target is not a member of the workspace."""
    exit_code = EXIT_NOT_FOUND
    code = "member_not_found"


class AlreadyMember(ApiError):
    """409 — invitee is already a workspace member."""
    exit_code = EXIT_CONFLICT
    code = "already_member"


class CannotRemoveOwner(ApiError):
    """400 — attempt to remove the workspace owner."""
    exit_code = EXIT_CONFLICT
    code = "cannot_remove_owner"


class TaskNotFound(ApiError):
    """404 — task absent, or not in this workspace (non-disclosure)."""
    exit_code = EXIT_NOT_FOUND
    code = "task_not_found"


class CommentNotFound(ApiError):
    """404 — comment absent, or not under this task."""
    exit_code = EXIT_NOT_FOUND
    code = "comment_not_found"


class NotCommentAuthor(ApiError):
    """403 — edit/delete by someone without the right."""
    exit_code = EXIT_FORBIDDEN
    code = "not_comment_author"


class InvalidCursor(ApiError):
    """400 — malformed pagination cursor."""
    exit_code = EXIT_BAD_REQUEST
    code = "invalid_cursor"


# ---------- structural errors (no backend `code` slug) ----------

class ValidationError(ApiError):
    """422 — Pydantic validation failure. Different envelope shape entirely."""
    exit_code = EXIT_BAD_REQUEST
    code = None


class NetworkError(ApiError):
    """Connection refused, DNS failure, timeout, TLS — anything below HTTP."""
    exit_code = EXIT_NETWORK
    code = None


class ServerError(ApiError):
    """5xx — not the client's fault."""
    exit_code = EXIT_SERVER
    code = None


# ---------- lookup table ----------

# Used by transport.py to turn a backend `code` slug into the right
# exception subclass after unwrapping {detail, code} envelope.
# Unknown codes fall back to base ApiError (handled in transport).
CODE_TO_EXCEPTION: dict[str, type[ApiError]] = {
    "invalid_credentials": InvalidCredentials,
    "invalid_token": InvalidToken,
    "email_unavailable": EmailUnavailable,
    "user_not_found": UserNotFound,
    "member_not_found": MemberNotFound,
    "already_member": AlreadyMember,
    "cannot_remove_owner": CannotRemoveOwner,
    "task_not_found": TaskNotFound,
    "comment_not_found": CommentNotFound,
    "not_comment_author": NotCommentAuthor,
    "invalid_cursor": InvalidCursor,
}
