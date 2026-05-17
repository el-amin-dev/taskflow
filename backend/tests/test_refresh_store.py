

from uuid import uuid4, UUID

import pytest
import redis

from app.infra import refresh_store as rs
from app.infra.refresh_store import _store_url


@pytest.fixture(autouse=True)
def fresh_store():
    r = redis.Redis.from_url(_store_url(), decode_responses=True)
    r.flushdb()
    yield
    r.flushdb()


def test_create_returns_token_and_family() -> None:
    uid = uuid4()
    token, family_id = rs.create(uid)
    assert token
    assert str(UUID(family_id)) == family_id


def test_rotate_active_returns_rotated_new_token() -> None:
    uid = uuid4()
    token, _ = rs.create(uid)
    res = rs.rotate(token)
    assert isinstance(res, rs.Rotated)
    assert res.new_token != token
    assert res.user_id == uid


def test_rotation_chain_successor_also_rotates() -> None:
    token, _ = rs.create(uuid4())
    r1 = rs.rotate(token)
    assert isinstance(r1, rs.Rotated)
    r2 = rs.rotate(r1.new_token)
    assert isinstance(r2, rs.Rotated)
    assert r2.new_token != r1.new_token


def test_unknown_token_is_not_found() -> None:
    assert isinstance(rs.rotate("never-existed"), rs.NotFound)


def test_replay_spent_token_kills_entire_family() -> None:
    uid = uuid4()
    tok1, fam = rs.create(uid)
    r1 = rs.rotate(tok1)            
    tok2 = r1.new_token
    r2 = rs.rotate(tok2)
    tok3 = r2.new_token

    replay = rs.rotate(tok1)
    assert isinstance(replay, rs.ReuseDetected)
    assert str(replay.family_id) == fam

    assert isinstance(rs.rotate(tok2), rs.NotFound)
    assert isinstance(rs.rotate(tok3), rs.NotFound)


def test_invalidate_family_is_idempotent() -> None:
    _, fam = rs.create(uuid4())
    rs.invalidate_family(UUID(fam))
    rs.invalidate_family(UUID(fam))
