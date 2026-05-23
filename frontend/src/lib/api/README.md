# `lib/api/` — typed HTTP client

The frontend's API layer. Three small files, one job: turn typed function
calls into HTTP requests, and turn HTTP responses (success or failure) into
typed JavaScript values (or typed errors).

## Files

| File | Concern |
|------|---------|
| `types.ts` | Generated from the backend's `/openapi.json`. Do not edit by hand. Regenerate with `npm run api:types` whenever the backend contract changes. |
| `errors.ts` | `ErrorCode` union + `ApiError` class. The one place that knows about the backend's `{detail: {detail, code}}` envelope and FastAPI's native `422` shape. |
| `transport.ts` | The fetch wrapper. Resolves base URL from `VITE_API_URL` at module load (fail-fast). Returns parsed JSON on 2xx, throws `ApiError` on anything else. |

Endpoint-specific modules (`auth.ts`, `workspaces.ts`, `tasks.ts`, …) land
with their respective features. They are thin: each function composes
`transport.request<T>(...)` and supplies the path, method, and typed `T`.

## Why this shape

A few specific design decisions worth naming, because they shape every
feature that follows:

**Single source of truth for HTTP — `transport.ts`.** Endpoint modules
never call `fetch` directly. Adding retry, telemetry, or cookie handling
later means editing one file, not auditing every endpoint. (SRP at the
file level; OCP for the project.)

**Single source of truth for error mapping — `errors.ts`.** Pages catch
`ApiError`, branch on `code`, and never know that FastAPI wraps the
project's `{detail, code}` in its own `{detail: ...}` envelope. The
double-nesting is deliberate on the backend (see the backend's
`DECISIONS.md`); flattening it is documented work for later if a
consumer needs it.

**Generated types over hand-written types.** `npm run api:types` runs
`openapi-typescript` against the live `/openapi.json`. The contract is
one source of truth; the frontend cannot lie about it. When the backend
ships a breaking change, regeneration surfaces it as a TypeScript error,
not a runtime bug.

**Functions, not classes.** Endpoint modules are collections of typed
functions, not a god-client class with N methods. Pages import only what
they use. (ISP applied as files, not interfaces — the simpler form.)

**Pages depend on signatures, not on `fetch`.** Page code is testable
against any function that returns the right `Promise<T>`. The transport
is the dependency boundary. (DIP — the page doesn't know there's an
HTTP request behind the call.)

**Throws instead of returning Result types.** Result types (`{ok, value}
| {ok: false, error}`) are nicer in some ecosystems; JavaScript's
ecosystem isn't one of them. Svelte's `<svelte:boundary>` and the
standard try/catch idiom expect throws.

## Tracked design boundaries

A couple of deliberate, non-ideal choices worth naming so a reviewer
finds them in the file rather than discovers them:

**The `ErrorCode` union is hand-maintained.** The backend's OpenAPI
spec does not yet declare the `{detail, code}` error envelope or the
HTTP error responses (only success + native 422). Until it does, the
union in `errors.ts` is the contract — copied from the backend's
`API.md`. When the backend hardens the spec, regenerate types,
delete the hand-typed union, and import from `./types`. Tracked as
work on the backend side, deliberately not blocked on here.

**`legacy-peer-deps=true` in `frontend/.npmrc`.** `openapi-typescript@7.x`
declares `peer typescript@^5.x`; the project uses TypeScript 6. The
codegen tool emits standard TS interfaces — compatibility is fine in
practice. The `.npmrc` carries a comment explaining when to remove the
flag (when the maintainer widens their peer range).

## Verification

The `/debug/health` route exercises the whole stack: SvelteKit server
`load` → `transport.request<HealthResponse>('/health')` → backend `/health`
→ typed response → render. If the wiring breaks, this route is the
fastest way to find out — useful in Phase C (deployed environments)
as an operator probe.

## Adding a new endpoint

1. Backend ships the endpoint; its OpenAPI spec updates automatically.
2. From `frontend/`: `npm run api:types` to regenerate `types.ts`.
3. Create or open the relevant module (`auth.ts`, `tasks.ts`, …).
4. Add a typed function that composes `transport.request<T>(path, {...})`,
   where `T` is the operation's response type from `types.ts`.
5. Pages import the function; never import from `transport.ts` directly
   in a page.

## Not in this layer

- Cookie handling, `Authorization` header forwarding — lives in SvelteKit
  server routes (`src/routes/api/*`), added with the auth Issue.
- Refresh-token rotation, retry-on-401 — same Issue.
- Page-level redirect-on-auth-failure — page concern, not transport.
- Logging, telemetry — wrapped around `transport.request` if/when
  observability lands (Phase C).
