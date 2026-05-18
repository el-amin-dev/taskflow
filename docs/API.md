# API Reference

The HTTP contract: every endpoint, who may call it, what it returns,
and how errors are shaped.

This is the **narrative** contract. The backend also serves an
**executable** one:

- **Swagger UI** — `http://localhost:8000/docs`
- **ReDoc** — `http://localhost:8000/redoc`
- **OpenAPI JSON** — `http://localhost:8000/openapi.json`

> **Note.** The live OpenAPI spec currently documents success responses
> and `422` validation errors only; the `400/401/403/404` error
> contract below is not yet reflected in the spec. Hardening the
> generated spec (declared error responses, a Bearer security scheme,
> per-route auth) is tracked as separate work. Until then, **this
> document is the authoritative error and auth reference.**

---

## Base & versioning

- All resource endpoints are under `/v1`
- `meta` endpoints (`/health`, `/ready`) are unversioned (infra
  concern, not API surface)
- Content type is `application/json` throughout

---

## Authentication model

- **Scheme** — `Authorization: Bearer <access_token>` on every
  protected route
- **Access token** — HS256 JWT. `sub` = user id, `role` claim.
  Stateless. TTL = `JWT_ACCESS_TTL_MINUTES` (default 15 min);
  `expires_in` in the token response is that value in **seconds**
- **Refresh token** — opaque string, returned alongside the access
  token, used at `POST /v1/auth/refresh` to get a new pair
- **Token response shape** (`/login`, `/refresh`):

  ```json
  {
    "access_token": "<jwt>",
    "refresh_token": "<opaque>",
    "token_type": "bearer",
    "expires_in": 900
  }
  ```

Refresh-token rotation, theft detection, and logout semantics:
[SECURITY.md](./SECURITY.md).

---

## Authorization model

Two tiers, applied in order:

1. **Workspace membership + role** (route-level) —
   `require_workspace_role({...})` confirms the caller is a member of
   the workspace with one of the listed roles. Failure → `404` (never
   `403` — non-members are not told the workspace exists).
2. **Row-level ownership** (service-level) — e.g. only a comment's
   author may edit it; author *or* workspace admin may delete it.
   Failure → `403` (`not_comment_author`).

Roles: `admin` ⊃ `member` ⊃ `viewer` in capability, but enforcement is
explicit per route (not inherited) — see the RBAC column below.

---

## Endpoint inventory

### Meta (unversioned, no auth)

| Method | Path      | Success | Body |
|--------|-----------|---------|------|
| GET    | `/health` | 200 | `{"status":"ok","uptime_seconds":<float>}` |
| GET    | `/ready`  | 200 | `{"status":"ready","checks":{"postgres":"ok"}}` — returns `"not ready"` (still 200, not 500) if a dependency is down |

### Auth (`/v1/auth`)

| Method | Path        | Auth | Body in | Success | Errors |
|--------|-------------|------|---------|---------|--------|
| POST   | `/register` | none | `RegisterRequest` (email, password 8–128) | 201 `UserResponse` | 400 `email_unavailable`, 422 |
| POST   | `/login`    | none | `LoginRequest` (email, password 1–128) | 200 `TokenResponse` | 401 `invalid_credentials`, 422 |
| GET    | `/me`       | Bearer | — | 200 `UserResponse` | 401 `invalid_token` |
| POST   | `/refresh`  | none¹ | `RefreshRequest` (refresh_token) | 200 `TokenResponse` | 401 `invalid_token`², 422 |
| POST   | `/logout`   | none¹ | `LogoutRequest` (refresh_token) | 204 | 422 |

¹ The refresh token in the body *is* the credential — no Bearer header
needed.
² All refresh failures (unknown, expired, reuse-detected) return one
identical `401` — no oracle. Reuse additionally kills the token family
and is audited.

### Workspaces (`/v1/workspaces`)

| Method | Path | Auth | RBAC | Success | Errors |
|--------|------|------|------|---------|--------|
| POST | `` | Bearer | any authenticated user | 201 `WorkspaceResponse` | 422 |
| GET | `` | Bearer | caller's own memberships | 200 `WorkspaceResponse[]` | — |
| POST | `/{ws}/members` | Bearer | `admin` | 201 `MemberResponse` | 404 `user_not_found`, 409 `already_member`, 422 |
| DELETE | `/{ws}/members/{user_id}` | Bearer | `admin` | 204 | 400 `cannot_remove_owner`, 404 `member_not_found`, 422 |
| GET | `/{ws}/audit` | Bearer | `admin` | 200 `AuditPage` | 400 `invalid_cursor`, 404, 422 |
| GET | `/{ws}/activity` | Bearer | `admin` · `member` · `viewer` | 200 `ActivityPage` | 400 `invalid_cursor`, 404, 422 |

### Tasks (`/v1/workspaces/{ws}/tasks`)

| Method | Path | Auth | RBAC | Success | Errors |
|--------|------|------|------|---------|--------|
| POST | `` | Bearer | `admin` · `member` | 201 `TaskResponse` | 404, 422 |
| GET | `` | Bearer | `admin` · `member` · `viewer` | 200 `TaskResponse[]` | 404, 422 |
| PATCH | `/{task_id}` | Bearer | `admin` · `member` | 200 `TaskResponse` | 404 `task_not_found`, 422 |
| DELETE | `/{task_id}` | Bearer | `admin` | 204 | 404 `task_not_found`, 422 |

`GET` accepts `?status=todo|in_progress|done`.

### Comments (`/v1/workspaces/{ws}/tasks/{task_id}/comments`)

| Method | Path | Auth | RBAC | Success | Errors |
|--------|------|------|------|---------|--------|
| POST | `` | Bearer | `admin` · `member` · `viewer` | 201 `CommentResponse` | 404 `task_not_found`, 422 |
| GET | `` | Bearer | `admin` · `member` · `viewer` | 200 `CommentPage` | 400 `invalid_cursor`, 404, 422 |
| PATCH | `/{comment_id}` | Bearer | author only | 200 `CommentResponse` | 403 `not_comment_author`, 404 `comment_not_found`, 422 |
| DELETE | `/{comment_id}` | Bearer | author **or** workspace `admin` | 204 | 403 `not_comment_author`, 404 `comment_not_found`, 422 |

`viewer`s may comment (a viewer is a participant in discussion, not
just a reader — see [DECISIONS.md](./DECISIONS.md)). Edit is
author-only even for admins; admins moderate by **deleting**, never by
editing another's words.

---

## The error contract

Every handled error (not framework `422`) has one shape:

```json
{ "detail": { "detail": "human message", "code": "machine_slug" } }
```

- **`code`** is the stable, machine-readable contract — clients branch
  on this, never on the prose
- The doubled `detail` is FastAPI's envelope wrapping the app's
  `{detail, code}` object; accepted deliberately (rationale in
  [DECISIONS.md](./DECISIONS.md))
- Framework validation failures use FastAPI's native `422`
  (`HTTPValidationError`: a `detail[]` of `{loc, msg, type}`) — a
  different shape, by design (it's a different class of error)

| Code | Meaning | HTTP |
|------|---------|------|
| `email_unavailable` | Registration email already in use | 400 |
| `invalid_credentials` | Login failed (cause never disclosed) | 401 |
| `invalid_token` | Auth/refresh token missing, malformed, expired, or reused | 401 |
| `user_not_found` | Target user does not exist | 404 |
| `member_not_found` | Target is not a member of the workspace | 404 |
| `already_member` | Invitee already a member | 409 |
| `cannot_remove_owner` | Attempt to remove the workspace owner | 400 |
| `task_not_found` | Task absent, or not in this workspace | 404 |
| `comment_not_found` | Comment absent, or not under this task | 404 |
| `not_comment_author` | Edit/delete by someone without the right | 403 |
| `invalid_cursor` | Malformed pagination cursor | 400 |

---

## Pagination

Audit, activity, and comment lists are **keyset-paginated** (stable
under inserts — unlike offset paging):

- Query params: `?limit=<1..100>&cursor=<opaque>`
- `limit` is clamped server-side (max 100); the client is never
  trusted
- Response: `{ "items": [...], "next_cursor": <string|null> }`
- `next_cursor` is an opaque base64 token. Treat it as a black box —
  do not parse or construct it. `null` means the last page.
- A malformed `cursor` → `400 invalid_cursor` (never a `500`)
- Ordering: audit & activity are **newest-first**; comments are
  **oldest-first** (a thread reads top-to-bottom — see
  [DECISIONS.md](./DECISIONS.md))

---

## Schemas (response shapes)

Authoritative definitions live in `/openapi.json`
(`components.schemas`). Key ones:

- **`UserResponse`** — `id, email, role, created_at`. Never includes
  `hashed_password` (asserted by test).
- **`TokenResponse`** — `access_token, refresh_token,
  token_type="bearer", expires_in` (seconds).
- **`TaskResponse`** — `id, workspace_id, title, description, status,
  assignee_id, deadline, created_by, created_at, updated_at`.
- **`CommentResponse`** — `id, task_id, author_id, body, created_at,
  updated_at`. `author_id` is nullable (a deleted author's comments
  survive as authored-by-nobody).
- **`AuditResponse` / `ActivityResponse`** — identical shape (`id,
  actor_user_id, workspace_id, action, target_type, target_id,
  payload, created_at`), deliberately separate contracts (see
  [DECISIONS.md](./DECISIONS.md)).
- **`*Page`** — `{ items: [...], next_cursor: string|null }`.

---

## See also

- [SECURITY.md](./SECURITY.md) — non-disclosure, the auth/refresh
  internals, why errors look the way they do
- [ARCHITECTURE.md](./ARCHITECTURE.md) — where each rule is enforced
- [DECISIONS.md](./DECISIONS.md) — the tradeoffs behind the contract