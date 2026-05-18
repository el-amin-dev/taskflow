# Security

The threat model, the defenses, and the boundaries — stated plainly.
Every defense here is enforced by a test, not just described.

---

## Posture in one paragraph

TaskFlow treats every request as hostile until proven otherwise.
Authentication is constant-time and leaks nothing. Authorization is
deny-by-default and tenant-isolated — you cannot even *detect* the
existence of a resource in a workspace you don't belong to. Secrets
never enter logs or config. Where a defense has a deliberate limit,
that limit is filed as a tracked issue and named below, not hidden.

---

## OWASP Top 10 (2021) — what's addressed

| Risk | Addressed by |
|------|--------------|
| **A01 Broken Access Control** | Every workspace-scoped route gated by `require_workspace_role`; row-level checks (author-or-admin) in the service; cross-tenant access is indistinguishable from "not found" |
| **A02 Cryptographic Failures** | argon2id password hashing; HS256 JWT signed with a ≥32-char secret (Pydantic enforces length); secrets are `SecretStr`; no secrets in committed config |
| **A03 Injection** | Parameterized queries via SQLAlchemy ORM only — no string-concatenated SQL anywhere; Pydantic validates every request body at the door |
| **A05 Security Misconfiguration** | Non-root container user (uid 1001); `.env` gitignored, `.env.example` documents the schema; `DEBUG` off by default; fail-fast config |
| **A07 Identification & Authentication Failures** | Constant-time login; unified 401 for any auth failure; no account enumeration on register or login; single `InvalidToken` for all JWT failures; HS256 hardcoded in the decoder |
| **A09 Security Logging & Monitoring Failures** | Append-only audit log of security-relevant events; `hashed_password` never appears in any response (asserted by test); emails never echoed in error bodies |

Deferred risks (no current attack surface) are tracked, not ignored —
see **Known boundaries** below.

---

## Non-disclosure: the core discipline

The system never reveals what an attacker hasn't earned the right to
know.

- **Account enumeration — closed.**
  - Registering an email already in use → generic `400`
    (`email_unavailable`), same as any other rejection
  - Login failure → identical `401` (`invalid_credentials`) whether the
    password was wrong, the account doesn't exist, or anything else
  - `authenticate()` runs a full argon2 verify **even when the user
    doesn't exist** — so timing can't distinguish the two paths.
    Measured timing ratio between "wrong password" and "no such user":
    **~1.04** (both ~80ms). Enforced by test.

- **Resource existence — not disclosed across tenants.**
  - A request for a task / comment / workspace you have no access to
    returns a `404` that is **byte-identical** to one for a resource
    that genuinely doesn't exist
  - An outsider, a non-member, and a request for a random UUID all get
    the same response — you cannot probe "does workspace X exist" or
    "is there a task here" from outside

- **Token failures — single bucket.**
  - Missing, malformed, expired, or bad-signature tokens all collapse
    into one `InvalidToken` → identical `401` (`invalid_token`). The
    client learns "not authenticated," never *why*.

---

## The uniform error contract

Every API error has the same shape — a machine-readable `code` plus a
human message:

```json
{ "detail": { "detail": "human message", "code": "machine_slug" } }
```

The `code` set in use:

| Code | Meaning | Typical HTTP |
|------|---------|--------------|
| `email_unavailable`   | Registration email already taken            | 400 |
| `invalid_credentials` | Login failed (cause not disclosed)          | 401 |
| `invalid_token`       | Auth token missing/malformed/expired/bad    | 401 |
| `user_not_found`      | Target user does not exist                   | 404 |
| `member_not_found`    | Target is not a member of the workspace      | 404 |
| `already_member`      | Invitee is already a workspace member        | 400/409 |
| `cannot_remove_owner` | Attempt to remove the workspace owner        | 400 |
| `task_not_found`      | Task absent, or not in this workspace        | 404 |
| `comment_not_found`   | Comment absent, or not under this task       | 404 |
| `not_comment_author`  | Edit/delete by someone without the right     | 403 |
| `invalid_cursor`      | Malformed pagination cursor                  | 400 |

Clients branch on `code`, never on prose. The doubled `detail` nesting
is FastAPI's envelope wrapping ours — accepted deliberately (see
[DECISIONS.md](./DECISIONS.md)); a custom exception handler can flatten
it later if a consumer needs it.

---

## Sessions & refresh tokens

Access tokens are short-lived; long-lived sessions use opaque,
rotating refresh tokens with theft detection.

- **Access token** — HS256 JWT, `sub` = user id, `role` claim,
  15-minute TTL (configurable). Stateless; never stored server-side.
- **Refresh token** — opaque random string, stored in Redis (its own
  logical DB), 30-day TTL.
- **Single-use rotation** — every refresh exchanges the old token for
  a new one; the old one is retained marked spent (retention *is* the
  theft signal).
- **Family kill on replay** — replaying an already-spent token means it
  was stolen (legitimate clients never reuse). The system invalidates
  the **entire token family**, forcing re-authentication. The event is
  recorded in the audit log, attributable to the user.
- **Role re-read on refresh** — a refresh re-reads the user's current
  role, so a role change takes effect within one access-token TTL, not
  30 days.
- **Logout** — revokes the refresh token; idempotent (re-logout or an
  unknown token still returns success; a real session death is
  audited).

---

## Known boundaries (tracked, not hidden)

Deliberate limits. Each is a filed issue, named here so a reviewer
doesn't have to discover it.

- **Auth/security audit events have no operator read path** —
  *(tracked: #50)*. Authentication events (token refresh, detected
  theft, logout) are durably recorded, but the only audit read
  endpoint is workspace-scoped, and auth events are workspace-agnostic
  by design. The data is captured correctly; a global, admin-only read
  path is its own design effort, deliberately not bundled into
  unrelated work.

- **Task creation is not audited** — *(tracked: #55)*. Task *deletion*
  is recorded; task *creation* is not. An asymmetry an auditor would
  flag. Surfaced while building the activity feed; the fix (emit
  `task.created`) is a small, separate audit-layer change, filed
  rather than scope-crept into a read-only feature.

Why this section exists: a system's documented limits are part of its
security posture. Knowing what *isn't* covered, and tracking it, is the
difference between a blind spot and a managed risk.

---

## Deferred (no current surface)

- **A04 Insecure Design** — a formal threat model document; deferred
- **A06 Vulnerable Components** — dependency scanning lands with CI
  (Phase C)
- **A08 Software/Data Integrity** — artifact signing lands with the
  Kubernetes phase (Phase C)
- **A10 SSRF** — not applicable; the service makes no outbound requests
  from user input

These are listed so their absence is a *decision*, not an oversight.

---

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md) — where authz lives (route vs.
  service) and why
- [API.md](./API.md) — per-endpoint auth requirements
- [DECISIONS.md](./DECISIONS.md) — the reasoning behind the error
  envelope, the seams, and the tradeoffs