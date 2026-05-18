# tests

Integration-first. These tests drive the **real HTTP app against real
Postgres + Redis** (in Compose) — they assert on security boundaries
and contracts, not on mocks.

## Running

The stack must be up. From `backend/`, with the env vars prefixed:

```bash
DATABASE_URL='postgresql+asyncpg://taskflow_user:taskflow_password@localhost:5432/taskflow_db' \
REDIS_URL='redis://localhost:6379/0' \
JWT_SECRET='a-test-secret-at-least-32-characters-long' \
pytest -q
```

Full setup: [`../../docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md).

## How these tests work

- **Self-isolating** — each test creates unique data (UUID emails, a
  fresh workspace). There is **no per-test database reset**;
  workspace-scoped queries keep tests from bleeding into each other.
  The rate-limiter's Redis DB is flushed by an autouse fixture.
- **HTTP-driven** — tests call the app through an `AsyncClient`, the
  same way a real client would. The one deliberate exception is the
  activity-feed security test, which inserts an impossible
  workspace-scoped `auth.*` row via the real audit write path to prove
  the allowlist excludes it even then (documented in-file).
- **Security is the point** — non-disclosure 404s, byte-identical auth
  failures, RBAC matrices, the audit trail, theft detection. The happy
  path is the easy part.

## Expected noise

You will see `Event loop is closed` / "Future attached to a different
loop" lines **after** results are decided — an asyncpg +
pytest-asyncio teardown artifact, **not** a failure. Only the final
`N passed` line is the verdict.

Suites: `test_auth`, `test_workspaces`, `test_tasks`, `test_comments`,
`test_activity`, `test_audit`, `test_refresh_flow`,
`test_refresh_store`, `test_rate_limiter`, `test_rate_limits_applied`
— 93 tests.
