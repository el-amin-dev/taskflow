Migrations live in `backend/migrations/` (Alembic, async). Tests live in `backend/tests/` (pytest, async, integration against a real Postgres).

---

## Status

**Phase A — Backend foundations**

- [x] Layered scaffold + pinned dependencies
- [x] Typed env-driven config (12-factor §III)
- [x] Structured JSON logging (12-factor §XI)
- [x] FastAPI entrypoint + `/health` + `/ready` (real DB check)
- [x] Dockerized stack (api + postgres + redis), non-root runtime
- [x] Async SQLAlchemy engine + db readiness probe
- [x] Alembic migrations (async template, baseline applied)
- [x] User model (UUID PK, indexed email, argon2 hashed password)
- [x] `POST /v1/auth/register` with full vertical slice + integration tests
- [ ] `POST /v1/auth/login` — JWT issuance
- [ ] `GET /v1/auth/me` — JWT verification dependency
- [ ] Workspaces + memberships + RBAC enforcement
- [ ] Tasks with assignment, status, deadlines
- [ ] Comments + activity feed
- [ ] Rate limiting (slowapi)
- [ ] Audit log

**Phase B — Frontend + CLI** *(not started)*

- [ ] SvelteKit web app
- [ ] Python CLI (Typer + httpx)

**Phase C — Production deploy** *(not started)*

- [ ] CI/CD pipeline
- [ ] Kubernetes manifests + Helm chart
- [ ] Terraform AWS infra
- [ ] Prometheus + Grafana observability

---

## Development Discipline

Every change goes through the same loop:

1. Open a GitHub Issue describing the work.
2. Branch off `main` (`feat/`, `fix/`, `docs/`, `refactor/`).
3. Commit using [conventional commits](https://www.conventionalcommits.org/) — `feat(scope):`, `fix(scope):`, `test:`, `docs:`, `refactor:`.
4. One PR per Issue (allow multiple atomic commits inside).
5. Squash-merge to `main` with `closes #N` so the Issue auto-closes.

Security decisions are explicit and reference [OWASP Top 10 (2021)](https://owasp.org/Top10/) where relevant. Examples already in the codebase: A02 (no secrets in committed config files), A03 (parameterized queries via ORM), A07 (argon2 hashing, no email enumeration on duplicate registration), A09 (hashed passwords never appear in API responses).

---

## License

MIT — see [LICENSE](./LICENSE).
