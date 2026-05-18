# backend

The TaskFlow API service — FastAPI, async SQLAlchemy, Postgres, Redis.

This is one component of the [TaskFlow monorepo](../README.md). It is
API-first: it serves a complete OpenAPI contract so the planned
frontend and CLI can be built against it independently.

## Run / test / migrate

Everything is in [`../docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md):
the Compose flow, the `.env` setup, running the test suite, and adding
a migration. The short version:

```bash
cp .env.example .env
docker compose up -d            # from repo root
docker compose exec api alembic upgrade head
curl localhost:8000/health
```

Interactive API docs (live): `/docs` (Swagger), `/redoc` (ReDoc),
`/openapi.json`.

## Layout (one screen)

```
app/
├── api/        HTTP routes + request/response schemas
├── services/   business logic, owns transactions
├── domain/     pure types — no framework imports
├── infra/      DB engine, ORM models, repositories, security, Redis
└── core/       config (env-driven, fail-fast), logging
migrations/     Alembic (async)
tests/          pytest, integration-first (real Postgres + Redis)
```

The one rule: **dependencies point inward** — the domain knows nothing
about HTTP, SQL, or Redis. Full explanation:
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). Why things are
the way they are: [`../docs/DECISIONS.md`](../docs/DECISIONS.md).
