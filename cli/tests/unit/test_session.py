"""Tests for session.py: orchestration of tokens.py + transport.py + api_auth.

Mocking strategy:
- Patch `session.tokens.load` / `.save` / `.delete` / `.refresh_lock` at the
  point-of-use boundary inside session module.
- Patch `session.api_auth.refresh` / `.logout` to control auth-server outcomes.
- Patch `session.Transport` so .get/.post/etc. inside _call return canned values.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from taskflow_cli import session as session_mod
from taskflow_cli.errors import InvalidToken
from taskflow_cli.session import Session, SessionExpired
from taskflow_cli.tokens import Tokens

# --- fixtures -------------------------------------------------------------

@pytest.fixture
def cfg(tmp_path):
    """A Config-like object with the two attributes Session reads."""
    c = MagicMock()
    c.api_url = "http://test.local"
    c.credentials_path = tmp_path / "credentials"
    return c


def _tok(*, access="a", refresh="r", expires_at=10_000_000_000) -> Tokens:
    """A token that is, by default, very far from expiring."""
    return Tokens(access_token=access, refresh_token=refresh, token_type="bearer", expires_at=expires_at)


@contextmanager
def _noop_lock(_path):
    yield


@pytest.fixture
def patched_session(cfg, monkeypatch):
    """Session with all I/O seams mockable. Returns (session, mocks dict).

    Default state: authenticated, fresh token, no refresh needed.
    Individual tests override mocks before exercising behavior.
    """
    initial = _tok()
    mocks = {
        "load": MagicMock(return_value=initial),
        "save": MagicMock(),
        "delete": MagicMock(),
        "refresh_lock": MagicMock(side_effect=_noop_lock),
        "auth_refresh": MagicMock(),
        "auth_logout": MagicMock(),
        "Transport": MagicMock(),
    }
    monkeypatch.setattr(session_mod.tokens, "load", mocks["load"])
    monkeypatch.setattr(session_mod.tokens, "save", mocks["save"])
    monkeypatch.setattr(session_mod.tokens, "delete", mocks["delete"])
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", mocks["refresh_lock"])
    monkeypatch.setattr(session_mod.api_auth, "refresh", mocks["auth_refresh"])
    monkeypatch.setattr(session_mod.api_auth, "logout", mocks["auth_logout"])
    monkeypatch.setattr(session_mod, "Transport", mocks["Transport"])

    sess = Session(cfg)
    return sess, mocks


# --- construction + state -------------------------------------------------

def test_construction_loads_tokens_from_disk(cfg, monkeypatch):
    load = MagicMock(return_value=_tok(access="X"))
    monkeypatch.setattr(session_mod.tokens, "load", load)
    s = Session(cfg)
    load.assert_called_once_with(cfg.credentials_path)
    assert s.is_authenticated is True
    assert s.access_token == "X"


def test_construction_with_no_credentials_file(cfg, monkeypatch):
    monkeypatch.setattr(session_mod.tokens, "load", MagicMock(return_value=None))
    s = Session(cfg)
    assert s.is_authenticated is False
    assert s.access_token is None


# --- save_tokens / clear --------------------------------------------------

def test_save_tokens_persists_and_caches(patched_session):
    sess, mocks = patched_session
    body = {"access_token": "new-a", "refresh_token": "new-r", "expires_in": 900}
    sess.save_tokens(body)
    # Cache updated
    assert sess.access_token == "new-a"
    # And persisted
    mocks["save"].assert_called_once()


def test_clear_wipes_in_memory_and_disk(patched_session):
    sess, mocks = patched_session
    sess.clear()
    assert sess.is_authenticated is False
    mocks["delete"].assert_called_once()


def test_clear_is_idempotent_when_already_empty(cfg, monkeypatch):
    monkeypatch.setattr(session_mod.tokens, "load", MagicMock(return_value=None))
    delete = MagicMock()
    monkeypatch.setattr(session_mod.tokens, "delete", delete)
    s = Session(cfg)
    s.clear()  # never errors even though we were already empty
    delete.assert_called_once()


# --- logout ---------------------------------------------------------------

def test_logout_calls_server_then_clears(patched_session):
    sess, mocks = patched_session
    sess.logout()
    mocks["auth_logout"].assert_called_once()
    mocks["delete"].assert_called_once()
    assert sess.is_authenticated is False


def test_logout_swallows_server_error_and_still_clears(patched_session):
    sess, mocks = patched_session
    from taskflow_cli.errors import NetworkError
    mocks["auth_logout"].side_effect = NetworkError("server unreachable")
    sess.logout()  # must not raise
    mocks["delete"].assert_called_once()
    assert sess.is_authenticated is False


def test_logout_with_no_tokens_skips_server_call(cfg, monkeypatch):
    monkeypatch.setattr(session_mod.tokens, "load", MagicMock(return_value=None))
    auth_logout = MagicMock()
    delete = MagicMock()
    monkeypatch.setattr(session_mod.api_auth, "logout", auth_logout)
    monkeypatch.setattr(session_mod.tokens, "delete", delete)
    s = Session(cfg)
    s.logout()
    auth_logout.assert_not_called()
    delete.assert_called_once()


# --- _request without auth ------------------------------------------------

def test_request_when_not_authenticated_raises_session_expired(cfg, monkeypatch):
    monkeypatch.setattr(session_mod.tokens, "load", MagicMock(return_value=None))
    s = Session(cfg)
    with pytest.raises(SessionExpired) as exc:
        s.get("/v1/x")
    assert exc.value.exit_code == 10  # EXIT_AUTH


# --- _request happy path (no refresh) -------------------------------------

def test_get_proxies_through_transport(patched_session):
    sess, mocks = patched_session
    transport_inst = MagicMock()
    transport_inst.__enter__ = MagicMock(return_value=transport_inst)
    transport_inst.__exit__ = MagicMock(return_value=None)
    transport_inst.get.return_value = {"data": "ok"}
    mocks["Transport"].return_value = transport_inst

    result = sess.get("/v1/x", params={"q": "1"})
    assert result == {"data": "ok"}
    transport_inst.get.assert_called_once_with("/v1/x", params={"q": "1"})
    # Refresh was NOT called — token is fresh
    mocks["auth_refresh"].assert_not_called()


# --- proactive refresh (token already expired before request) -------------

def test_proactive_refresh_when_access_expired(cfg, monkeypatch):
    """Token is past its expiry → refresh fires before the call."""
    # Expired token: expires_at in the past
    expired = Tokens(access_token="old", refresh_token="rt-1", token_type="bearer", expires_at=0)
    refreshed_body = {"access_token": "NEW", "refresh_token": "RT-2", "expires_in": 900}

    load = MagicMock(return_value=expired)
    save = MagicMock()
    auth_refresh = MagicMock(return_value=refreshed_body)

    monkeypatch.setattr(session_mod.tokens, "load", load)
    monkeypatch.setattr(session_mod.tokens, "save", save)
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", MagicMock(side_effect=_noop_lock))
    monkeypatch.setattr(session_mod.api_auth, "refresh", auth_refresh)

    # Transport that returns successfully
    transport_inst = MagicMock()
    transport_inst.__enter__ = MagicMock(return_value=transport_inst)
    transport_inst.__exit__ = MagicMock(return_value=None)
    transport_inst.get.return_value = {"ok": True}
    Transport_cls = MagicMock(return_value=transport_inst)
    monkeypatch.setattr(session_mod, "Transport", Transport_cls)

    s = Session(cfg)
    result = s.get("/v1/x")

    assert result == {"ok": True}
    auth_refresh.assert_called_once()
    save.assert_called_once()
    # The Transport for the actual call was built with the NEW access token
    last_kwargs = Transport_cls.call_args_list[-1].kwargs
    assert last_kwargs.get("access_token") == "NEW"


# --- reactive refresh (server rejects token mid-request) -------------------

def test_reactive_refresh_on_invalid_token(cfg, monkeypatch):
    """Server rejects access_token with InvalidToken → refresh → retry."""
    fresh = _tok(access="old", refresh="rt-1")
    refreshed_body = {"access_token": "NEW", "refresh_token": "RT-2", "expires_in": 900}

    load = MagicMock(return_value=fresh)
    save = MagicMock()
    auth_refresh = MagicMock(return_value=refreshed_body)

    monkeypatch.setattr(session_mod.tokens, "load", load)
    monkeypatch.setattr(session_mod.tokens, "save", save)
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", MagicMock(side_effect=_noop_lock))
    monkeypatch.setattr(session_mod.api_auth, "refresh", auth_refresh)


    def _ctx_mock(**attrs):
        """A MagicMock that's a no-op context manager, with extra attrs configured."""
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=None)
        for k, v in attrs.items():
            setattr(m, k, v)
        return m

    bad = _ctx_mock()
    bad.get.side_effect = InvalidToken("token rejected")

    anon = _ctx_mock()  # used inside _refresh; api_auth.refresh is already mocked

    good = _ctx_mock()
    good.get.return_value = {"ok": True}

    Transport_cls = MagicMock(side_effect=[bad, anon, good])
    monkeypatch.setattr(session_mod, "Transport", Transport_cls)
    s = Session(cfg)
    result = s.get("/v1/x")

    assert result == {"ok": True}
    auth_refresh.assert_called_once()
    assert bad.get.call_count == 1   # original attempt
    assert good.get.call_count == 1  # retry after refresh
    # Verify the retry Transport was built with the refreshed token
    third_call_kwargs = Transport_cls.call_args_list[2].kwargs
    assert third_call_kwargs.get("access_token") == "NEW"


# --- failed refresh wipes credentials --------------------------------------

def test_failed_refresh_wipes_credentials_and_raises(cfg, monkeypatch):
    """Refresh token is dead → clear() + SessionExpired."""
    expired = Tokens(access_token="old", refresh_token="dead", token_type="bearer", expires_at=0)
    load = MagicMock(return_value=expired)
    delete = MagicMock()
    auth_refresh = MagicMock(side_effect=InvalidToken("refresh token rejected"))

    monkeypatch.setattr(session_mod.tokens, "load", load)
    monkeypatch.setattr(session_mod.tokens, "delete", delete)
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", MagicMock(side_effect=_noop_lock))
    monkeypatch.setattr(session_mod.api_auth, "refresh", auth_refresh)
    monkeypatch.setattr(session_mod, "Transport", MagicMock())

    s = Session(cfg)
    with pytest.raises(SessionExpired) as exc:
        s.get("/v1/x")

    assert exc.value.exit_code == 10
    delete.assert_called_once()
    assert s.is_authenticated is False


# --- concurrent refresh detection -----------------------------------------

def test_refresh_detects_other_process_already_refreshed(cfg, monkeypatch):
    """If a concurrent CLI refreshed while we held for the lock,
    we re-read and adopt their token instead of spending ours."""
    our_view = Tokens(access_token="old", refresh_token="rt-old", token_type="bearer", expires_at=0)
    their_fresh = _tok(access="THEIRS", refresh="rt-NEW")  # different refresh_token

    # First load (in __init__) returns our_view; second load (inside _refresh
    # after lock acquired) returns their_fresh
    load = MagicMock(side_effect=[our_view, their_fresh])
    auth_refresh = MagicMock()  # MUST NOT be called

    monkeypatch.setattr(session_mod.tokens, "load", load)
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", MagicMock(side_effect=_noop_lock))
    monkeypatch.setattr(session_mod.api_auth, "refresh", auth_refresh)

    transport_inst = MagicMock()
    transport_inst.__enter__ = MagicMock(return_value=transport_inst)
    transport_inst.__exit__ = MagicMock(return_value=None)
    transport_inst.get.return_value = {"ok": True}
    Transport_cls = MagicMock(return_value=transport_inst)
    monkeypatch.setattr(session_mod, "Transport", Transport_cls)

    s = Session(cfg)
    result = s.get("/v1/x")

    assert result == {"ok": True}
    auth_refresh.assert_not_called()  # we did NOT spend our refresh token
    # And we used THEIR access token for the call
    last_kwargs = Transport_cls.call_args_list[-1].kwargs
    assert last_kwargs.get("access_token") == "THEIRS"


# --- lock is used during refresh ------------------------------------------

def test_refresh_acquires_the_lock(cfg, monkeypatch):
    """Sanity: refresh_lock IS entered during a refresh — protects the race."""
    expired = Tokens(access_token="old", refresh_token="rt", token_type="bearer", expires_at=0)
    refreshed_body = {"access_token": "NEW", "refresh_token": "RT-2", "expires_in": 900}

    refresh_lock = MagicMock(side_effect=_noop_lock)

    monkeypatch.setattr(session_mod.tokens, "load", MagicMock(return_value=expired))
    monkeypatch.setattr(session_mod.tokens, "save", MagicMock())
    monkeypatch.setattr(session_mod.tokens, "refresh_lock", refresh_lock)
    monkeypatch.setattr(session_mod.api_auth, "refresh", MagicMock(return_value=refreshed_body))

    transport_inst = MagicMock()
    transport_inst.__enter__ = MagicMock(return_value=transport_inst)
    transport_inst.__exit__ = MagicMock(return_value=None)
    transport_inst.get.return_value = {"ok": True}
    monkeypatch.setattr(session_mod, "Transport", MagicMock(return_value=transport_inst))

    s = Session(cfg)
    s.get("/v1/x")

    refresh_lock.assert_called_once_with(cfg.credentials_path)


# --- method proxies share the same code path ------------------------------

@pytest.mark.parametrize("method, kwargs", [
    ("post", {"json": {"a": 1}}),
    ("patch", {"json": {"b": 2}}),
    ("delete", {}),
])
def test_other_methods_proxy_through_transport(patched_session, method, kwargs):
    sess, mocks = patched_session
    transport_inst = MagicMock()
    transport_inst.__enter__ = MagicMock(return_value=transport_inst)
    transport_inst.__exit__ = MagicMock(return_value=None)
    getattr(transport_inst, method).return_value = {"r": method}
    mocks["Transport"].return_value = transport_inst

    result = getattr(sess, method)("/v1/x", **kwargs)
    assert result == {"r": method}


# --- anonymous_client -----------------------------------------------------

def test_anonymous_client_has_no_token(patched_session):
    sess, mocks = patched_session
    sess.anonymous_client()
    # Last Transport construction had no access_token kwarg (or None)
    args, kwargs = mocks["Transport"].call_args
    assert kwargs.get("access_token") is None
