"""Tests for transport.py: response parsing, error envelope unwrap, NetworkError mapping.

Mocking strategy:
- Construct a Transport against a stub base_url (no real httpx connection ever made).
- Replace transport._client with a MagicMock; configure its .request(...) return value.
- Each test exercises one branch of _parse() or one path of _request().
"""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from taskflow_cli import transport as transport_mod
from taskflow_cli.errors import (
    ApiError,
    InvalidCredentials,
    NetworkError,
    NotCommentAuthor,
    ServerError,
    ValidationError,
)
from taskflow_cli.transport import Transport


# --- helpers ---------------------------------------------------------------

def _resp(*, status: int, json_body=None, text: str = "", content: bytes | None = None):
    """Build a MagicMock that quacks like an httpx.Response for our _parse path."""
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    # content drives the "204 or no content" branch
    if content is not None:
        r.content = content
    elif json_body is None and not text:
        r.content = b""
    else:
        r.content = b"x"  # non-empty placeholder; actual content is irrelevant past the check
    r.text = text
    if json_body is None:
        # Make .json() blow up the same way httpx would on non-JSON
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_body
    return r


def _transport_with(response_or_exc) -> Transport:
    """Return a Transport whose _client.request returns/raises as specified."""
    t = Transport("http://unused")
    t._client = MagicMock()
    if isinstance(response_or_exc, BaseException):
        t._client.request.side_effect = response_or_exc
    else:
        t._client.request.return_value = response_or_exc
    return t


# --- happy paths -----------------------------------------------------------

def test_get_returns_parsed_json_on_200():
    t = _transport_with(_resp(status=200, json_body={"ok": True}))
    assert t.get("/v1/x") == {"ok": True}


def test_post_returns_parsed_json_on_201():
    t = _transport_with(_resp(status=201, json_body={"id": "u-1"}))
    assert t.post("/v1/x", json={"a": 1}) == {"id": "u-1"}


def test_returns_none_on_204():
    t = _transport_with(_resp(status=204, content=b""))
    assert t.delete("/v1/x") is None


def test_returns_none_on_2xx_with_empty_body():
    """200 with no body (some endpoints) also yields None."""
    t = _transport_with(_resp(status=200, content=b""))
    assert t.get("/v1/x") is None


# --- 4xx envelope unwrap ---------------------------------------------------

def test_4xx_with_known_code_raises_typed_exception():
    body = {"detail": {"detail": "wrong creds", "code": "invalid_credentials"}}
    t = _transport_with(_resp(status=401, json_body=body))
    with pytest.raises(InvalidCredentials) as exc:
        t.post("/v1/auth/login")
    assert exc.value.message == "wrong creds"
    assert exc.value.code == "invalid_credentials"
    assert exc.value.http_status == 401


def test_4xx_with_not_comment_author_code_maps_to_forbidden_exit():
    body = {"detail": {"detail": "you can only edit your own", "code": "not_comment_author"}}
    t = _transport_with(_resp(status=403, json_body=body))
    with pytest.raises(NotCommentAuthor) as exc:
        t.patch("/v1/.../comments/1")
    assert exc.value.exit_code == 12


def test_4xx_with_unknown_code_falls_back_to_apierror():
    body = {"detail": {"detail": "mystery", "code": "brand_new_thing"}}
    t = _transport_with(_resp(status=400, json_body=body))
    with pytest.raises(ApiError) as exc:
        t.get("/v1/x")
    # Falls back to ApiError, not a typed subclass
    assert type(exc.value) is ApiError
    assert exc.value.message == "mystery"


def test_4xx_with_no_code_falls_back_to_apierror():
    """detail object without a code field — typical handler that didn't bother with the slug."""
    body = {"detail": {"detail": "something off"}}
    t = _transport_with(_resp(status=400, json_body=body))
    with pytest.raises(ApiError) as exc:
        t.get("/v1/x")
    assert type(exc.value) is ApiError
    assert exc.value.message == "something off"


def test_4xx_with_string_detail_falls_back_to_apierror():
    """Some non-conforming routes return {detail: 'string'}; we tolerate it."""
    body = {"detail": "raw string detail"}
    t = _transport_with(_resp(status=400, json_body=body))
    with pytest.raises(ApiError) as exc:
        t.get("/v1/x")
    assert type(exc.value) is ApiError
    assert "raw string detail" in exc.value.message


def test_4xx_with_unparseable_body_uses_raw_text():
    """Backend returns 4xx with plain-text body — we surface it via ApiError."""
    t = _transport_with(_resp(status=400, text="proxy says no"))
    with pytest.raises(ApiError) as exc:
        t.get("/v1/x")
    assert exc.value.message == "proxy says no"
    assert exc.value.http_status == 400


def test_4xx_with_unparseable_empty_body_uses_status_fallback():
    """If even .text is empty, we surface 'http <status>'."""
    t = _transport_with(_resp(status=400, text=""))
    with pytest.raises(ApiError) as exc:
        t.get("/v1/x")
    assert exc.value.message == "http 400"


# --- 422 validation envelope -----------------------------------------------

def test_422_fastapi_shape_formats_loc_and_msg():
    body = {
        "detail": [
            {"loc": ["body", "email"], "msg": "not a valid email", "type": "value_error.email"}
        ]
    }
    t = _transport_with(_resp(status=422, json_body=body))
    with pytest.raises(ValidationError) as exc:
        t.post("/v1/auth/register")
    assert exc.value.message == "body.email: not a valid email"
    assert exc.value.http_status == 422
    assert exc.value.exit_code == 15


def test_422_with_only_msg_no_loc():
    body = {"detail": [{"msg": "validation failed"}]}
    t = _transport_with(_resp(status=422, json_body=body))
    with pytest.raises(ValidationError) as exc:
        t.post("/v1/x")
    assert exc.value.message == "validation failed"


def test_422_with_empty_detail_uses_default_message():
    body = {"detail": []}
    t = _transport_with(_resp(status=422, json_body=body))
    with pytest.raises(ValidationError) as exc:
        t.post("/v1/x")
    assert exc.value.message == "validation failed"


def test_422_with_non_list_detail_uses_default():
    body = {"detail": "scalar"}
    t = _transport_with(_resp(status=422, json_body=body))
    with pytest.raises(ValidationError) as exc:
        t.post("/v1/x")
    assert exc.value.message == "validation failed"


# --- 5xx -------------------------------------------------------------------

def test_5xx_raises_server_error():
    t = _transport_with(_resp(status=500, json_body={"any": "thing"}))
    with pytest.raises(ServerError) as exc:
        t.get("/v1/x")
    assert exc.value.http_status == 500
    assert exc.value.exit_code == 16


def test_503_also_server_error():
    t = _transport_with(_resp(status=503, text=""))
    with pytest.raises(ServerError):
        t.get("/v1/x")


# --- httpx.RequestError → NetworkError -------------------------------------

def test_connect_error_becomes_network_error():
    t = _transport_with(httpx.ConnectError("refused"))
    with pytest.raises(NetworkError) as exc:
        t.get("/v1/x")
    assert "ConnectError" in exc.value.message
    assert exc.value.exit_code == 14


def test_read_timeout_becomes_network_error():
    t = _transport_with(httpx.ReadTimeout("timed out"))
    with pytest.raises(NetworkError) as exc:
        t.get("/v1/x")
    assert "ReadTimeout" in exc.value.message


# --- header threading + lifecycle ------------------------------------------

def test_authorization_header_set_when_access_token_provided():
    t = Transport("http://unused", access_token="abc123")
    # We pulled the real httpx.Client; inspect its default headers.
    auth = t._client.headers.get("Authorization")
    assert auth == "Bearer abc123"
    t.close()


def test_no_authorization_header_when_no_token():
    t = Transport("http://unused")
    assert "Authorization" not in t._client.headers
    t.close()


def test_context_manager_closes_client():
    """Exiting the with-block closes the underlying client."""
    t = Transport("http://unused")
    t._client = MagicMock()
    with t:
        pass
    t._client.close.assert_called_once()
