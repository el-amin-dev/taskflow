# Frontend Auth

How the SvelteKit frontend authenticates against the TaskFlow backend,
and the decisions behind it.

The backend issues a short-lived access JWT plus a long-lived, single-use
refresh token (see the backend's `SECURITY.md`). The frontend's job is to
hold those tokens **out of reach of browser JavaScript** and keep a session
alive across access-token expiry without the user noticing.

## The one rule

**Tokens live in httpOnly cookies, never in JavaScript.** The browser never
reads, stores, or transmits a raw token from JS. Every token touch happens
server-side — in SvelteKit server routes or `hooks.server.ts`. This closes
the XSS token-theft vector: a script injected into the page cannot read an
httpOnly cookie.

## The pieces

| File | Role |
|------|------|
| `src/lib/api/auth.ts` | Typed wrappers over `/v1/auth/*`. Cookie-unaware — pure HTTP. |
| `src/lib/server/cookies.ts` | Sets/clears the two cookies; owns names, TTLs, attributes. |
| `src/lib/server/refresh.ts` | Single-flight refresh (dedupes concurrent refreshes). |
| `src/routes/api/auth/{register,login,logout}/+server.ts` | Browser-facing endpoints. Translate token-pair-in-body to httpOnly cookies. |
| `src/hooks.server.ts` | Runs on every request: validates the access cookie, refreshes on expiry, populates `event.locals.user`. |
| `src/routes/+layout.server.ts` | Surfaces `locals.user` to the layout so the header reflects login state. |
| `src/routes/{login,register}/+page.svelte` | The forms. Thin clients over the server routes. |
| `src/routes/{login,register}/+page.server.ts` | Redirect home if already logged in. |

## The cookies

Two cookies, both `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` in
production (HTTP allowed in dev so localhost works):

- `taskflow_access` — the access JWT. TTL from `VITE_ACCESS_TTL_SECONDS`
  (default 900 = 15 min), matching the backend's `JWT_ACCESS_TTL_MINUTES`.
- `taskflow_refresh` — the opaque refresh token. TTL from
  `VITE_REFRESH_TTL_SECONDS` (default 2592000 = 30 days), matching
  `JWT_REFRESH_TTL_DAYS`.

The TTLs are env-driven so they stay in sync with the backend's TTLs without
hardcoding. `SameSite=Lax` blocks the common CSRF vectors while still allowing
top-level navigations.

## Request lifecycle

Every server request flows through `hooks.server.ts`, which resolves auth
state into `event.locals.user`:

1. **Valid access token** → validate via `/v1/auth/me`, set `locals.user`.
2. **Expired/invalid access token** → attempt a silent refresh (below). On
   success, write fresh cookies and set `locals.user`. On failure, clear
   cookies and set `locals.user = null`.
3. **No access token, but a refresh token exists** → attempt refresh (covers
   a returning user whose access expired but whose 30-day refresh is still
   good).
4. **Nothing** → `locals.user = null`.

A logged-in user therefore sees no interruption when their 15-minute access
token expires mid-session — the next request silently refreshes it. The new
cookies land in the response transparently.

## Silent refresh and the single-use race

The backend's refresh tokens are **single-use with theft detection**: each
refresh returns a new refresh token and marks the old one spent. Replaying a
spent token is treated as theft, and the backend kills the entire token
family — logging the user out.

This creates a race in a browser: a page firing several requests in parallel
(or two tabs) can each hit an expired access token at the same moment, each
read the same refresh token, and each call `/refresh`. The first succeeds; the
rest replay a now-spent token and trigger the theft response — the user is
logged out for no reason ("it randomly logs me out").

`src/lib/server/refresh.ts` defends against this with **single-flight**: an
in-memory map keyed by the refresh-token value. Concurrent refreshes of the
same token share one in-flight `/refresh` call instead of each firing their
own. One backend call, one rotation, no spent-token replay.

## Tracked boundaries

Deliberate limits, named here so a reviewer finds them rather than discovers
them:

- **Single-flight is single-process.** The in-memory map lives in one Node
  process. With multiple SvelteKit replicas (Phase C / Kubernetes), each has
  its own map and the race returns across replicas. The real fix at that scale
  is a shared lock (Redis) or sticky sessions. Sufficient for single-process
  Phase A/B.

- **Session validation hits `/me` on every request.** `hooks.server.ts`
  validates the access token by calling the backend, a round-trip per request.
  Fine at current scale; a future optimization is local JWT signature
  verification (no network call), which trades a little complexity for latency.

- **No email verification.** Registration logs the user in immediately. The
  backend has no email infrastructure; production would add a verification
  step. Tracked as future scope, not built.

- **No automatic redirect on session loss yet.** A user whose session dies
  mid-action is not force-redirected to `/login` from a protected page —
  there are no protected pages yet (every route is currently public). The
  redirect guard ships with the first authenticated-only route (the workspaces
  UI). The inverse guard — redirecting logged-in users away from `/login` and
  `/register` — is in place.

## Why these choices

- **httpOnly cookies over in-memory tokens** — survives page reload (better UX
  than re-login on refresh) while staying immune to XSS token theft. The cost
  is the SvelteKit server must mediate every token touch; that's the right
  trade for a security-focused project.

- **Server routes as the cookie boundary** — the browser talks to
  `/api/auth/*` (same origin), which talks to the backend. The token pair never
  crosses into JS. This is the whole reason `adapter-node` was chosen over a
  static SPA build.

- **Branch on error `code`, never prose** — forms read the backend's
  machine-readable `code` (e.g. `invalid_credentials`, `email_unavailable`) and
  map it to a message. The login form deliberately shows the same message for
  wrong-password and unknown-email, faithfully surfacing the backend's
  non-disclosure discipline — no account enumeration through the UI.

## See also

- `src/lib/api/README.md` — the API client layer (transport, errors, types).
- Backend `SECURITY.md` — the refresh state machine, theft detection, the
  non-disclosure model the frontend mirrors.
