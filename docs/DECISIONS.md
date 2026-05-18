# Decisions

The reasoning behind the locked choices — so they aren't relitigated,
and so a reviewer sees *why*, not just *what*.

Each entry: **the decision**, **why**, **the tradeoff accepted**, and
**status**. A decision being here doesn't mean it's permanent — it
means changing it should be a deliberate act with the original
reasoning in view, not an accidental drift.

---

## Architecture

### Clean Architecture, dependencies point inward
- **Why** — the domain must outlive any framework. FastAPI, SQLAlchemy,
  and Redis are replaceable details; business rules are not.
- **Tradeoff** — more layers and explicit mapping (domain ↔ ORM) than a
  flat app. Accepted: the seams are where testability and change-safety
  come from.
- **Status** — enforced across every feature, not aspirational.

### Services own transactions; repositories only flush
- **Why** — the transaction boundary is a *business* decision ("the
  comment and its audit row commit together or not at all"). Only the
  service knows the full unit of work.
- **Tradeoff** — repositories can't be used standalone without a
  service managing the commit. Acceptable — that's the intended usage.
- **Status** — invariant. A repo that commits is a bug.

### Repositories are functions, not classes
- **Why** — YAGNI. A class earns its place when it needs per-instance
  state (caching, a unit-of-work, injected policy). None of that exists
  yet. Functions are simpler to read and test.
- **Tradeoff** — if a caching or RBAC layer arrives, some repos become
  classes then. Cheap to refactor when there's a real second use case;
  expensive to carry speculative abstraction now.
- **Status** — holds until a feature genuinely needs instance state.

### Not every persisted thing has a domain type
- **Why** — a domain type earns its place when it has *behaviour* or
  invariants. Audit-log rows and comments are records — data, not
  behaviour-bearing entities. The service maps the ORM model straight
  to a response schema (`from_model`), no domain dataclass in between.
- **Tradeoff** — slight inconsistency ("some things have domain types,
  some don't"). Accepted: forcing a hollow domain type on a pure record
  is ceremony, not architecture.
- **Status** — applied to audit and comments deliberately.

---

## Data & persistence

### UUID primary keys
- **Why** — no enumeration of resources by sequential id; safe to
  expose in URLs; distributed-friendly.
- **Tradeoff** — larger keys, non-sequential index inserts. Negligible
  at this scale; the security property is worth it.
- **Status** — every table.

### Soft delete everywhere (`deleted_at`)
- **Why** — recoverable, audit-friendly, and history-preserving. A
  deleted task's comments don't need cascading cleanup — they're hidden
  with the task.
- **Tradeoff** — every read must filter `deleted_at IS NULL`; a missed
  filter leaks deleted rows. Mitigated by doing it consistently in the
  repo layer.
- **Status** — tasks and comments.

### `func.now()` server-default for timestamps
- **Why** — the database owns time-of-birth; no client clock trust, no
  app/DB clock skew.
- **Tradeoff** — `func.now()` is *transaction-start* time, so rows
  written in one transaction share a timestamp; keyset tiebreak then
  falls to the UUID. Accepted — real usage commits per request, so
  timestamps differ; the tiebreak is deterministic regardless.
- **Status** — all `created_at` / `updated_at`.

### Foreign-key `ondelete` is always explicit
- **Why** — delete behaviour is a correctness decision, not a default
  to inherit. `RESTRICT` (can't orphan a workspace owner), `CASCADE`
  (memberships die with their workspace), `SET NULL` (a comment
  survives its author's deletion as authored-by-nobody).
- **Tradeoff** — must be hand-verified after Alembic autogenerate,
  which frequently drops `ondelete`. Accepted; the verification is
  documented (see DEVELOPMENT.md).
- **Status** — every FK.

---

## API contract

### The doubled `{detail:{detail,code}}` envelope
- **Why** — the app raises `{detail, code}`; FastAPI wraps any
  `HTTPException.detail` in its own `{detail: …}`. The result nests.
  Flattening it needs a custom exception handler.
- **Tradeoff** — the nesting is slightly ugly. Accepted for now (YAGNI)
  — no consumer has needed it flattened; a custom handler is a clean
  later change if one does. The machine-readable `code` is stable
  regardless of nesting.
- **Status** — accepted, revisitable.

### Keyset pagination, not offset
- **Why** — stable under concurrent inserts (offset paging skips/repeats
  rows when the set shifts); O(1) per page regardless of depth.
- **Tradeoff** — opaque cursor, no random-page access ("jump to page
  7"). Acceptable for feeds/logs — nobody random-accesses page 7 of an
  activity stream.
- **Status** — audit, activity, comments.

### Audit & activity newest-first; comments oldest-first
- **Why** — a log/feed is read latest-first ("what just happened"); a
  comment thread is read top-to-bottom (a conversation). Order follows
  how a human consumes it.
- **Tradeoff** — two pagination directions to keep straight. Accepted —
  the direction matches the mental model of each surface.
- **Status** — locked.

---

## Security

### Constant-time login, byte-identical failures
- **Why** — OWASP A07. Any difference (status, body, *timing*) between
  "wrong password" and "no such user" is an account-enumeration oracle.
- **Tradeoff** — login always runs a full argon2 verify, even for
  nonexistent users (wasted CPU on invalid attempts). Accepted — the
  cost *is* the defense.
- **Status** — enforced, timing ratio ~1.04, test-locked.

### Cross-tenant access returns 404, never 403
- **Why** — a 403 ("forbidden") confirms the resource exists. A 404
  identical to "doesn't exist" discloses nothing about other tenants'
  data.
- **Tradeoff** — a legitimately confused user gets "not found" instead
  of "not allowed." Accepted — non-disclosure outranks that UX nicety
  for a multi-tenant system.
- **Status** — every workspace-scoped route.

### Refresh tokens: single-use rotation + family kill on replay
- **Why** — a replayed (already-spent) refresh token means theft;
  legitimate clients never reuse one. Killing the whole family forces
  re-auth and contains the breach.
- **Tradeoff** — a client that loses the rotated token (crash mid-
  exchange) must re-login. Accepted — rare, and the security gain is
  large.
- **Status** — implemented, audited, test-locked.

---

## Product / RBAC

### Viewers can comment
- **Why** — a "viewer" is a participant in the discussion (a
  stakeholder watching a task), not a read-only spectator. Commenting
  isn't mutating the task.
- **Tradeoff** — "viewer" no longer means strictly read-only. Accepted
  — the alternative (a separate "commenter" role) is unjustified
  complexity for this product.
- **Status** — locked; test-asserted.

### Admins moderate by deleting, never by editing
- **Why** — editing another person's words puts words in their mouth.
  An admin may *remove* a comment (moderation); never *rewrite* it.
- **Tradeoff** — an admin can't fix a typo in someone's comment, only
  delete it. Correct — that's the point.
- **Status** — locked; an admin-edit attempt returns 403, test-asserted.

### Comment max length is a module constant, not config
- **Why** — it's part of the API *contract*, not a per-environment
  *operational* knob. No deployment legitimately varies it. A single
  named constant (`COMMENT_MAX_LENGTH`) is one source of truth, no
  drift, no config ceremony.
- **Tradeoff** — changing it needs a code change, not an env var.
  Correct — a contract change *should* be a code change. (If it ever
  becomes a per-tier business rule, *that* justifies config — driven by
  the requirement, not anticipated.)
- **Status** — locked (showcase-appropriate simplicity over speculative
  flexibility).

### Activity feed is a filtered view over the audit log
- **Why** — every activity event is *already* an audit event. A second
  event store would mean a double write and two sources of "what
  happened" that can drift. Reuse the single source; filter by an
  explicit allowlist (`ACTIVITY_ACTIONS`), applied at the query so
  keyset pagination stays correct.
- **Tradeoff** — audit (forensic, admin) and activity (social, member)
  are coupled to one table; the allowlist is a maintenance point. If
  the product ever needs seen-state, muting, or independent retention,
  activity must split into its own stream.
- **Status** — locked as **Option A**, with that split named as a
  deliberate, documented seam — not an oversight.

---

## 12-Factor App

The project claims 12-factor design as a headline credential — so here
is where each factor is actually honored, or honestly deferred. (The
same way [SECURITY.md](./SECURITY.md) maps OWASP: a claim you can
verify, not just assert.)

| # | Factor | Status | Where / how |
|---|--------|--------|-------------|
| I | Codebase | ✅ | One repo, tracked in git; every deploy is a revision of it |
| II | Dependencies | ✅ | Explicitly declared and **pinned** (`requirements.lock`); installed in an isolated build stage — no reliance on system packages |
| III | **Config** | ✅ | All config from the environment via typed Pydantic Settings; **fail-fast** (invalid/missing required var crashes at startup, not first request); secrets are `SecretStr`; `.env` gitignored, `.env.example` documents the schema |
| IV | Backing services | ✅ | Postgres and Redis are attached resources addressed purely by URL (`DATABASE_URL`, `REDIS_URL`) — swappable without code change; the host-vs-container URL override proves the binding is external |
| V | Build, release, run | ◑ | Build (multi-stage Dockerfile) and run (Compose) are separated; migrations are a discrete release step (`alembic upgrade head`), never auto-run on boot. A formal release pipeline lands in **Phase C** (CI/CD) |
| VI | **Processes** | ✅ | The API is stateless — no session state in-process; auth is a stateless JWT; all state lives in Postgres/Redis |
| VII | Port binding | ✅ | The app is self-contained (uvicorn) and exports HTTP by binding a port; nothing is injected by a runtime web server |
| VIII | Concurrency | ◑ | Stateless processes scale horizontally by definition; migrations-as-discrete-step exists *because* multiple replicas are anticipated. Actual horizontal scaling is a **Phase C** (orchestration) concern |
| IX | Disposability | ✅ | Containerized, fast startup, healthchecked; non-root, no local writable state — instances are cattle, killable and replaceable |
| X | **Dev/prod parity** | ✅ | Same Postgres 16 + Redis 7 in dev as intended for prod; **one async driver (`asyncpg`) everywhere** — no SQLite-in-dev divergence; same image dev→prod |
| XI | **Logs** | ✅ | Treated as an event stream to stdout — structured JSON in prod, human-readable in dev; the process never manages log files |
| XII | Admin processes | ✅ | One-off admin tasks (migrations) run as the same code in the same environment (host venv against the same DB), not a separate ad-hoc path |

- **✅ honored** · **◑ partially — completed in Phase C**
- The two `◑` factors (V, VIII) are *deliberately* partial: a real
  release pipeline and real horizontal scaling belong to the cloud
  phase. Marked honestly rather than overclaimed — the same discipline
  as the tracked boundaries below.
- The bolded factors (III, VI, X, XI) are the ones this backend leans
  on hardest; they're cross-referenced from
  [ARCHITECTURE.md](./ARCHITECTURE.md) and
  [DEVELOPMENT.md](./DEVELOPMENT.md).

---

## Tracked boundaries

Deliberate limits, filed as issues so they're managed, not forgotten.
Documented here because *what a system doesn't do, and why, is part of
its design*.

| Boundary | Issue | Why deferred |
|----------|-------|--------------|
| Auth/security audit events have no operator read path | **#50** | The only audit read endpoint is workspace-scoped; auth events are workspace-agnostic by design. A global admin read path is its own design effort, not bundled into unrelated work. |
| Task creation is not audited (only deletion is) | **#55** | Surfaced while building the activity feed. The fix (emit `task.created`) is a small, separate audit-layer change, deliberately not scope-crept into a read-only feature. |

---

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md) — the structure these decisions
  shape
- [SECURITY.md](./SECURITY.md) — the security decisions in full
- [API.md](./API.md) — the contract these decisions produce