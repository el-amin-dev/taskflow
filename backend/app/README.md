# app

The application package. Clean Architecture — **dependencies point
inward**.

```
api  ──▶  services  ──▶  domain
 │            │            ▲
 │            ▼            │
 └────────▶  infra  ───────┘
```

| Layer       | Does                                              | May import        |
|-------------|---------------------------------------------------|-------------------|
| `api/`      | HTTP routes, Pydantic wire schemas, status codes  | services, domain  |
| `services/` | Business logic; **owns the transaction boundary** | domain, infra     |
| `domain/`   | Pure frozen dataclasses + enums; no framework     | (nothing)         |
| `infra/`    | DB engine, ORM models, repositories, security, Redis | domain         |
| `core/`     | Config (env-driven, fail-fast), structured logging | stdlib + pydantic |

A dependency pointing *outward* (e.g. a domain type importing an ORM
model) is an architecture violation, not a style nit.

Repositories **flush**; services **commit** — the service decides the
unit of work.

Full rationale, the request lifecycle, and the transaction-ownership
rule: [`../../docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).
