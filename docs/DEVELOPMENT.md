# Development

Run it, test it, change the schema, ship a change — and the gotchas
that will bite you if you don't know them.

Written so someone with zero prior context (including the author, a
year from now) can be productive in ten minutes.

---

## Prerequisites

- Docker + Docker Compose (the only hard requirement to *run* it)
- Python 3.12 + a virtualenv (only needed to run **tests** and
  **migrations** from the host)

No local Postgres or Redis — Compose owns both.

---

## Run it

```bash
git clone https://github.com/el-amin-dev/taskflow.git
cd taskflow
cp backend/.env.example backend/.env
docker compose up -d
```

Three services come up: `db` (Postgres 16), `cache` (Redis 7), `api`
(FastAPI). All are healthchecked; `api` waits for `db` and `cache` to
be healthy before starting.

Apply migrations once the stack is up (one-time, and after any new
migration):

```bash
docker compose exec api alembic upgrade head
```

Verify:

```bash
curl localhost:8000/health   # {"status":"ok","uptime_seconds":<float>}
curl localhost:8000/ready    # {"status":"ready","checks":{"postgres":"ok"}}
```

Stop without losing data:

```bash
docker compose down          # keeps named volumes (postgres_data, redis_data)
docker compose down -v       # NUKES the volumes — fresh DB next start
```

---

## Configuration

All config is environment-driven and **validated at startup** — a
missing or invalid required var crashes the process immediately, not
on the first request (12-factor §III, fail-fast).

| Var | Required | Default | Notes |
|-----|----------|---------|-------|
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://…` |
| `REDIS_URL` | ✅ | — | `redis://…` |
| `JWT_SECRET` | ✅ | — | **≥32 chars** (Pydantic enforces). Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_ACCESS_TTL_MINUTES` | | `15` | access-token lifetime |
| `JWT_REFRESH_TTL_DAYS` | | `30` | refresh-token lifetime |
| `CORS_ORIGINS` | | `["http://localhost:5173"]` | JSON-style list |
| `ENVIRONMENT` | | `dev` | `dev` \| `staging` \| `prod` |
| `DEBUG` | | `false` | never `true` in prod |

> **Host vs. container URLs.** `.env` uses `localhost` (correct for
> host-run tests/migrations). Compose **overrides** `DATABASE_URL` /
> `REDIS_URL` for the `api` container to the service names `db` /
> `cache` — that's why the same `.env` works both places. Don't
> "fix" the localhost values to service names; you'll break host
> tooling.

`get_settings()` is `lru_cache`d — settings load once per process. (If
you ever see config changes not taking effect in a long-running shell,
that cache, plus import-time binding, is why — see Gotchas.)

---

## Run the tests

Tests run from the **host venv** against the **Compose Postgres +
Redis** (integration-first — they exercise the real app over HTTP, not
mocks). The stack must be up.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # first time
pip install -r requirements-dev.txt                  # first time

DATABASE_URL='postgresql+asyncpg://taskflow_user:taskflow_password@localhost:5432/taskflow_db' \
REDIS_URL='redis://localhost:6379/0' \
JWT_SECRET='a-test-secret-at-least-32-characters-long' \
pytest -q
```

- **93 tests** across 10 suites: `test_auth`, `test_workspaces`,
  `test_tasks`, `test_comments`, `test_activity`, `test_audit`,
  `test_refresh_flow`, `test_refresh_store`, `test_rate_limiter`,
  `test_rate_limits_applied`
- Tests **self-isolate** by unique data (UUID emails, fresh workspace
  per test) — there is no per-test DB reset; the limiter's Redis DB is
  flushed by an autouse fixture
- Run one suite: `pytest tests/test_comments.py -v`

> **Teardown noise is expected.** You'll see `Event loop is closed` /
> "Future attached to a different loop" lines *after* results are
> decided — an asyncpg + pytest-asyncio teardown artifact, not a
> failure. Only the final `N passed` line is the verdict. Filter it if
> it bothers you (`pytest -q 2>&1 | tail -3`).

---

## Add a migration

Migrations are **Alembic, async**, and run from the **host venv** —
**not** the container.

> **Why not in the container?** `/app` is owned by the non-root `app`
> user and not writable at runtime (OWASP A05, by design). `alembic
> revision` inside the container fails to write the file — correctly.
> Generate on the host; the file lands on disk; rebuild/redeploy picks
> it up.

```bash
cd backend
source .venv/bin/activate

# 1. edit the model in app/infra/models.py first

# 2. autogenerate (note: prefix the env vars — alembic reads settings)
DATABASE_URL='postgresql+asyncpg://taskflow_user:taskflow_password@localhost:5432/taskflow_db' \
REDIS_URL='redis://localhost:6379/0' \
JWT_SECRET='a-test-secret-at-least-32-characters-long' \
alembic revision --autogenerate -m "add <thing>"

# 3. INSPECT the generated file before applying — see warning below

# 4. apply
DATABASE_URL='…' REDIS_URL='…' JWT_SECRET='…' alembic upgrade head

# rollback one step
DATABASE_URL='…' REDIS_URL='…' JWT_SECRET='…' alembic downgrade -1
```

> **Always read the autogenerated migration before applying.**
> Alembic autogenerate frequently **drops `ondelete` on foreign keys**
> — a `CASCADE`/`SET NULL` silently downgraded to `NO ACTION` is a
> real data-integrity bug that won't surface until a delete happens.
> Confirm each `ForeignKeyConstraint` carries its intended `ondelete=`
> and that `down_revision` chains off the current head. Verify the
> rule landed in Postgres, not just the file:
>
> ```bash
> docker compose exec db psql -U taskflow_user -d taskflow_db \
>   -c "SELECT conname, confdeltype FROM pg_constraint
>       WHERE conrelid = '<table>'::regclass AND contype='f';"
> # confdeltype: c=CASCADE  n=SET NULL  a=NO ACTION  r=RESTRICT
> ```

Migrations are applied as a **discrete step**, never auto-run on API
startup (a race with multiple replicas).

---

## Contribution loop

Every change, no exceptions:

1. **Open an Issue** describing the work (product-level — the outcome,
   not the implementation)
2. **Branch** off `main`: `feat/…`, `fix/…`, `docs/…`, `refactor/…`,
   `test/…`
3. **Commit** in atomic, conventional commits — one concern per
   commit, verified end-to-end before each:
   - `feat:` `fix:` `docs:` `refactor:` `test:` `chore:` `perf:`
     `build:` `ci:` `style:`
4. **PR** into `main`, body scoped to *this* change only; reference
   discovered-but-out-of-scope work as tracked issues, don't bundle it
5. **Squash-merge** with `closes #N` — one clean commit per PR on
   `main`; the Issue auto-closes
6. **Delete the branch**

History is meant to be read. A reviewer should be able to follow the
story from the Issue list and the commit log alone.

---

## Gotchas (you *will* hit these)

- **`docker-compose.override.yaml` is gitignored.** It carries the
  dev-only hot-reload bind-mount + `--reload`. A fresh clone won't
  have it — code changes won't live-reload until you recreate it.
  (Intentional: the override is a local dev convenience, not part of
  the committed stack.)

- **Teardown FK ordering.** When wiping test data by hand, delete
  **child rows before parent rows**, scoped by ownership, in separate
  statements. `workspaces.owner_id` is `ON DELETE RESTRICT` (by
  design) — `DELETE FROM users` while a workspace references them is
  *correctly* refused, and a single multi-statement transaction rolls
  back wholly on that failure. Order: audit_log → memberships →
  workspaces → users.

- **Import-time snapshot of mutable module state.** `from app.infra.db
  import _session_factory` snapshots `None` at import; `init_engine()`
  rebinds the module attribute, but the imported name still points at
  the old `None`. Import the module (`from app.infra import db`) and
  reference `db._session_factory` so every read is current.

- **`func.now()` is transaction-start time.** Rows inserted in the
  *same* transaction get an *identical* `created_at` — keyset
  tiebreak then falls to the (random) UUID. Real usage commits per
  request so timestamps differ; test setups that need ordering must
  commit per row.

- **Zero-arg call vs. reference.** `default=uuid4` (reference — called
  per row) vs `default=uuid4()` (called once at import — every row
  gets the *same* value). Same trap inverted: a bare function name
  where a call was meant. When reading `foo.bar`, ask "is `foo` a
  function I forgot to call?"

- **(Local, zsh)** an `alias deactivate='deactivate'` in `.zshrc`
  breaks `source .venv/bin/activate` with a parse error. `unalias
  deactivate` per shell, or delete the alias line permanently.

---

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md) — the layering you're working
  within
- [API.md](./API.md) — the contract your change must not silently
  break
- [DECISIONS.md](./DECISIONS.md) — why things are the way they are,
  before you "fix" them