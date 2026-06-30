# TaskFlow CLI

Command-line client for [TaskFlow](https://github.com/el-amin-dev/taskflow).
Built with Typer + httpx. Single-use refresh tokens with file-lock theft
protection, atomic 0600 credential storage, scriptable exit codes,
`--json` mode for pipelines.

> **Status** — 20 commands across 5 groups (`auth`, `workspace`, `member`,
> `task`, `comment`) are live, backed by a pytest unit suite covering the
> deterministic modules. Phase B (CI, container image, deployment) is next.
> The map and PR plan: [`work-track.md`](./work-track.md).

---

## Install

### pipx (recommended)

`pipx` isolates the CLI in its own venv and puts `tflowctl` on your
`$PATH` — no system-Python pollution, one-command uninstall.

```bash
# Debian / Ubuntu
sudo apt install pipx
pipx ensurepath

# macOS
brew install pipx
```

Install the CLI from the repo:

```bash
git clone https://github.com/el-amin-dev/taskflow.git
cd taskflow/cli
pipx install .
```

Verify:

```bash
tflowctl --version
# 0.1.0
```

### pip (alternative — for development)

```bash
cd taskflow/cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Quickstart

The backend must be reachable. By default `tflowctl` talks to
`http://localhost:8000`; if your backend lives elsewhere, set
`TASKFLOW_API_URL` (see Configuration).

```bash
# Create an account (does not log you in)
tflowctl auth register --email alice@example.com
# Password: (typed twice)
# ✓ created account for alice@example.com
#   next: tflowctl auth login

# Log in
tflowctl auth login --email alice@example.com
# Password: (typed once, hidden)
# ✓ logged in as alice@example.com

# Show who you are
tflowctl auth whoami
# alice@example.com
#   role: member

# Log out
tflowctl auth logout
# ✓ logged out
```

Credentials are stored at `~/.config/tflowctl/credentials` with mode
`0600` (owner read/write only). They never appear in stdout, argv,
shell history, or logs.

---

## Commands

| Group | Commands |
|---|---|
| **`auth`** | `register` · `login` · `whoami` · `logout` |
| **`workspace`** | `list` · `create` |
| **`member`** | `invite` |
| **`task`** | `list` · `create` · `update` · `status` · `delete` |
| **`comment`** | `list` · `add` · `edit` · `delete` |

Every command supports `--help`:

```bash
tflowctl task status --help
```

Each group has its own section below. Scriptable patterns
(`--json`, stdout/stderr discipline, shell substitution capture) are
documented under **Scripted use**.

---

## Scripted use

### `--json` for machine-readable output

Commands that produce data accept `--json`. Output is pure JSON on
stdout; chatter and errors continue to go to stderr.

```bash
tflowctl auth whoami --json
# {"id": "...", "email": "alice@example.com", "role": "member", "created_at": "..."}

# capture a field
ROLE=$(tflowctl auth whoami --json | jq -r .role)
# without jq:
ROLE=$(tflowctl auth whoami --json | python -c "import sys,json;print(json.load(sys.stdin)['role'])")
```

### Passwords from stdin (never in argv)

A `--password` flag would leak via `ps`, sudo logs, and `~/.bash_history`.
Use `--password-stdin` for scripts:

```bash
echo -n "$PASSWORD" | tflowctl auth login --email "$EMAIL" --password-stdin
```

### Exit codes as the success signal

```bash
if tflowctl auth whoami > /dev/null 2>&1; then
    echo "session live"
else
    echo "logged out (or expired)"
fi
```

---

## Configuration

All config is environment-driven and validated at startup (12-factor §III).

| Env var             | Default                  | Notes                                       |
|---------------------|--------------------------|---------------------------------------------|
| `TASKFLOW_API_URL`  | `http://localhost:8000`  | Backend base URL. Must start with `http(s)://` |
| `XDG_CONFIG_HOME`   | `~/.config`              | Per XDG spec; tokens live under `$XDG_CONFIG_HOME/tflowctl/` |
| `EDITOR`            | falls back to `nano`, then `vi` | Used by `comment add` / `comment edit` when neither `-m` nor `--message-stdin` is given |

Invalid config fails fast, before any HTTP call is attempted:

```bash
TASKFLOW_API_URL=ftp://wrong tflowctl auth whoami
# ConfigError: TASKFLOW_API_URL must start with http:// or https://
```

---

## Exit-code contract

The CLI dev doc puts it plainly: *exit codes are an API*. The mapping
is documented and stable. Scripts can branch on it.

| Code | Meaning              | Triggers                                                                |
|------|----------------------|-------------------------------------------------------------------------|
| `0`  | success              | normal completion                                                       |
| `1`  | generic error        | uncaught fallback                                                       |
| `2`  | usage error          | bad argv — missing required arg, unknown command, invalid enum value    |
| `10` | auth failed          | wrong password, invalid/expired token, session expired                  |
| `11` | not found            | resource doesn't exist *or* not yours (non-disclosure: same response)   |
| `12` | forbidden            | edit/delete by someone without the right (incl. comment author rule)    |
| `13` | conflict             | email already registered, already a member, can't remove owner          |
| `14` | network / transport  | DNS, connection refused, timeout, TLS                                   |
| `15` | bad request          | invalid cursor, 422 validation failure                                  |
| `16` | server error         | any 5xx from the backend                                                |
| `130`| interrupted          | SIGINT (Ctrl-C)                                                         |

---

## Shell completion

Typer ships completion for bash, zsh, and fish:

```bash
tflowctl --install-completion
# follow the printed instructions, then restart your shell
tflowctl <Tab>        # autocompletes subcommands and flags
```

---

## Security posture

Mirrors the backend's discipline; full detail in
[`docs/SECURITY.md`](../docs/SECURITY.md).

- **Credentials file** at `~/.config/tflowctl/credentials`, mode `0600`,
  atomic writes via `os.replace` so a crash mid-write never leaves a
  half-written file.
- **Single-use refresh tokens** rotate on every refresh; a replayed
  token means theft and triggers family-kill server-side. A file
  lock (`fcntl.flock`) serializes the read-call-write critical section
  so two concurrent CLI invocations can't both spend the same token.
- **Tokens never in argv** — no `--token` or `--password` flag.
  `--password-stdin` is the only password-input mechanism for scripts.
- **Non-disclosure** — cross-tenant resources surface as "not found",
  never "you lack permission for X". Matches backend `SECURITY.md`.
- **Failed refresh wipes credentials** — the next command runs as
  anonymous and surfaces a clean "not logged in" message rather than
  retrying a dead session.

---

## Development

```bash
cd cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run against your local backend:
docker compose -f ../docker-compose.yaml up -d
tflowctl auth register --email dev@example.com
```

Layout:

```
cli/
├── pyproject.toml
├── work-track.md           # PR plan + mermaid diagrams
├── README.md               # this file
├── tests/
│   └── unit/
│       ├── test_errors.py
│       ├── test_tokens.py
│       ├── test_editor.py
│       ├── test_transport.py
│       └── test_session.py
└── src/taskflow_cli/
    ├── main.py             # Typer entrypoint + central error handler
    ├── config.py           # env-driven, XDG, fail-fast
    ├── tokens.py           # atomic 0600 + refresh_lock
    ├── errors.py           # exception hierarchy + exit codes
    ├── transport.py        # httpx + error-envelope unwrap
    ├── session.py          # refresh-on-401 + lock orchestration
    ├── api/                # one module per resource
    │   ├── auth.py
    │   ├── workspaces.py
    │   ├── members.py
    │   ├── tasks.py
    │   └── comments.py
    ├── commands/           # Typer subcommand modules
    │   ├── auth.py
    │   ├── workspace.py
    │   ├── member.py
    │   ├── task.py
    │   └── comment.py
    └── util/
        └── editor.py       # message-body composer (-m / stdin / EDITOR)
```

## Workspace commands

Workspaces are the top-level container for tasks. Every user can own multiple
workspaces; every workspace has an owner and zero or more invited members.

### List your workspaces

```sh
tflowctl workspace list
```

Outputs a Rich table to stdout. An empty result prints `no workspaces yet` to
**stderr** (so it doesn't pollute scripts that redirect stdout).

For machine-readable output:

```sh
tflowctl workspace list --json
```

Emits a JSON array of `{id, name, owner_id, created_at}` objects — always valid
JSON, including `[]` when empty.

### Create a workspace

```sh
tflowctl workspace create "Engineering"
```

The success line goes to **stderr**; the new workspace UUID goes to **stdout**.
That separation makes the command scriptable:

```sh
WS_ID=$(tflowctl workspace create "Engineering")
echo "captured: $WS_ID"
```

For the full server response (e.g. `created_at`):

```sh
tflowctl workspace create "Engineering" --json
```

## Member commands

> **Note:** only `invite` is implemented today. Backend issue
> [#85](https://github.com/el-amin-dev/taskflow/issues/85) blocks
> `member list` (no GET-members endpoint yet); `member remove` is
> deferred to a dedicated workspace-membership PR since the DELETE
> endpoint already exists backend-side.

### Invite a user to a workspace

```sh
tflowctl member invite <WORKSPACE_ID> <EMAIL> --role <ROLE>
```

`<ROLE>` is one of `admin`, `member` (default), or `viewer`. An invalid role
exits with code `2` (usage error) before any HTTP request is made — the choice
is validated at the parser layer.

The invitee must already have a TaskFlow account; there is no email-based
invite-link flow yet.

Example:

```sh
tflowctl member invite "$WS_ID" "alice@example.com" --role admin
```

For machine-readable output:

```sh
tflowctl member invite "$WS_ID" "alice@example.com" --json
```

Emits a JSON object of `{user_id, workspace_id, role, joined_at}`. Backend
issue [#86](https://github.com/el-amin-dev/taskflow/issues/86) tracks adding
the invitee's email and display name to this response.

### Exit codes specific to membership

| Code | Meaning                                                  |
|-----:|----------------------------------------------------------|
| `13` | conflict — user is already a member of that workspace    |
| `12` | forbidden — you don't have permission to invite          |
| `11` | not found — no such workspace, or invitee email unknown  |
| `15` | bad request — malformed UUID, invalid email, or bad role |


## Task commands

Tasks live inside a workspace. Every task command takes the workspace ID as
its first positional argument — matching the backend's workspace-scoped routes
and keeping RBAC at the URL layer.

> **Note:** `task show` is not implemented. The backend has no single-task
> GET endpoint; tracked as
> [#105](https://github.com/el-amin-dev/taskflow/issues/105).

### List tasks

```sh
tflowctl task list <WORKSPACE_ID>
```

Outputs a Rich table to stdout. Empty result prints `no tasks yet` to
**stderr**; `--json` emits an empty array.

Filter by status:

```sh
tflowctl task list <WORKSPACE_ID> --status in_progress
```

`--assignee` is not yet supported — backend query param tracked as
[#106](https://github.com/el-amin-dev/taskflow/issues/106).

For machine-readable output:

```sh
tflowctl task list <WORKSPACE_ID> --json
```

### Create a task

```sh
tflowctl task create <WORKSPACE_ID> "Write the runbook"
```

Confirmation line to **stderr**; new task UUID to **stdout** — same pattern as
`workspace create`, scriptable via shell substitution.

Full options:

```sh
tflowctl task create <WORKSPACE_ID> "Refactor auth" \
    --description "Move JWT decode into a service" \
    --status in_progress \
    --assignee <USER_ID> \
    --deadline 2026-07-01T17:00:00Z
```

Status defaults to `todo` when omitted. Description, assignee, and deadline
are all optional.

### Update task metadata

```sh
tflowctl task update <WORKSPACE_ID> <TASK_ID> --title "New title"
```

`update` covers metadata only: title, description, assignee, deadline. **It
does not change status** — that's a separate verb (see below) because state
transitions are semantically distinct and benefit from their own audit trail.

At least one field flag is required; calling `update` with no fields exits
with code `2`.

### Change task status

```sh
tflowctl task status <WORKSPACE_ID> <TASK_ID> in_progress
```

Status is one of `todo`, `in_progress`, `done`. Invalid values exit with
code `2` at the parser layer — no HTTP request is made.

This mirrors the `gh issue close` pattern: high-frequency state changes get
their own command, separate from generic metadata edits.

### Delete a task

```sh
tflowctl task delete <WORKSPACE_ID> <TASK_ID>
```

Prompts for confirmation on stderr. For scripts:

```sh
tflowctl task delete <WORKSPACE_ID> <TASK_ID> --yes
```

### Exit codes specific to tasks

| Code | Meaning                                                    |
|-----:|------------------------------------------------------------|
|  `2` | invalid status value (parser-level), or `update` with no fields |
| `11` | not found — task ID doesn't exist in this workspace        |
| `12` | forbidden — you don't have permission to edit this task    |
| `15` | bad request — invalid UUID, malformed deadline, etc.       |


## Comment commands

Task comments. Every command takes workspace ID, task ID, and (for edit/delete)
the comment ID as positional arguments — same shape as the rest of the
workspace-scoped CLI.

Comments are the first surface that uses cursor pagination
(`CommentPage` from the backend) and the first to accept message bodies via
three input methods.

> **Author rules:** only the comment's author may `edit` or `delete` it.
> Non-author attempts return exit code `12` (forbidden) with a clear message.
> Backend issue
> [#89](https://github.com/el-amin-dev/taskflow/issues/89) tracks adding
> author email and name to the response; until then, the table shows the
> author's user ID (truncated). Comments whose author has been deleted
> render as `(deleted user)`.

### List comments

```sh
tflowctl comment list <WORKSPACE_ID> <TASK_ID>
```

Oldest first. By default shows one page; when more results exist, a hint on
**stderr** offers the next cursor or `--all`:

```sh
tflowctl comment list <WS> <TASK> --limit 20
# … table …
# more available — re-run with --cursor <token> or --all
```

Walk every page in one call:

```sh
tflowctl comment list <WS> <TASK> --all
```

For scripts:

```sh
tflowctl comment list <WS> <TASK> --json
# emits {"items": [...], "next_cursor": "<token>" | null}
```

### Add a comment

Three ways to supply the body, in priority order:

```sh
# Inline (fastest)
tflowctl comment add <WS> <TASK> -m "Quick observation"

# From stdin (for scripts and pipes)
echo "Body from a heredoc-style pipe" | tflowctl comment add <WS> <TASK> --message-stdin

# Editor fallback (default when neither flag is set)
tflowctl comment add <WS> <TASK>
# Opens $EDITOR (or nano, or vi) with a template;
# lines beginning with '#' are stripped;
# empty body aborts with exit 2.
```

Confirmation line goes to **stderr**; the new comment UUID goes to **stdout** —
same scriptable pattern as `task create`. Capture with shell substitution:

```sh
CID=$(echo "Body" | tflowctl comment add "$WS" "$TASK" --message-stdin)
```

Passing both `-m` and `--message-stdin` is a usage error (exit 2). The mutex
check fires *before* stdin is read, so the command never blocks waiting for
input that won't be used.

### Edit a comment

```sh
tflowctl comment edit <WS> <TASK> <COMMENT_ID> -m "Revised body"
```

Same three input methods as `add`. The PATCH semantics are replacement, not
partial — the new body fully overwrites the old one (matches the backend
schema: `CommentCreate` is reused for updates).

Editing a comment you don't own exits with code `12`.

### Delete a comment

```sh
tflowctl comment delete <WS> <TASK> <COMMENT_ID>
```

Prompts for confirmation on **stderr**. For non-interactive scripts:

```sh
tflowctl comment delete <WS> <TASK> <COMMENT_ID> --yes
```

Deleting a comment you don't own exits with code `12`.

### Exit codes specific to comments

| Code | Meaning                                                              |
|-----:|----------------------------------------------------------------------|
|  `2` | `-m` and `--message-stdin` both passed; empty body in editor or pipe |
| `11` | not found — comment ID doesn't exist on this task                    |
| `12` | not the comment author — only authors may edit or delete             |
| `15` | bad request — body too long, malformed UUID, etc.                    |


## Testing

The CLI has a pytest unit test suite covering the deterministic modules
(errors, tokens, editor body composer, transport response parsing, session
orchestration). No network, no real backend, no filesystem outside `tmp_path`.

### Run the tests

```sh
# One-time: install dev dependencies (adds pytest to your venv)
pip install -e ".[dev]"

# Run
pytest
```

Output ends with `N passed in <1s` — the whole suite runs in well under a
second because nothing touches I/O.

### What's covered

| Module | Focus |
|---|---|
| `errors.py` | `CODE_TO_EXCEPTION` mapping; each exception class carries its documented exit code |
| `tokens.py` | Atomic 0600 file write, expiry math with skew, refresh-lock semantics |
| `util/editor.py` | The three input paths (`-m` / stdin / EDITOR), mutex check fires before stdin read, comment-line stripping, EDITOR fallback chain |
| `transport.py` | Error envelope unwrap by backend code, FastAPI 422 shape, 5xx → `ServerError`, `httpx.RequestError` → `NetworkError` |
| `session.py` | Proactive refresh on expired token, reactive refresh on `InvalidToken`, failed refresh wipes credentials, concurrent-refresh detection via re-read |

### What's deliberately deferred

| Surface | Why deferred |
|---|---|
| `api/*.py` | Thin HTTP wrappers around `Transport` — testing them duplicates `transport.py` coverage |
| `commands/*.py` | Typer's `CliRunner` pairs naturally with end-to-end tests against a live backend |
| End-to-end flows (register → login → task → comment) | Needs Postgres and test-mode cleanup; lives in a future integration test PR |

### Stack notes

- **pytest** only — no `respx`, `pytest-httpx`, or coverage tooling. The
  stdlib `unittest.mock` is verbose but explicit; anyone reading the tests
  can follow what's being patched without learning a third-party DSL.
- **`filterwarnings = ["error"]`** in `pyproject.toml` — any
  DeprecationWarning during a test fails the run. Catches Python-version
  drift before it ships.
- **`--strict-markers`** — typo'd `@pytest.mark.unti` would normally silently
  skip; with this it fails loudly.
### Lint

Ruff handles linting and import sorting. Configured for `E`/`F`/`I`/`B`/`UP`
rule families — pycodestyle errors, pyflakes, isort, bugbear's bug patterns,
and pyupgrade hints. Cosmetic-only rules are deliberately off.

```sh
# Check
ruff check src tests

# Auto-fix what's safely fixable
ruff check src tests --fix
```

Per-file ignores live in `pyproject.toml`:
- `tests/**` allows assertions used in test scaffolding (`B011`)
- `src/taskflow_cli/commands/**` permits Typer's `Argument(...)` and
  `Option(...)` as default values (`B008`) — the documented framework
  pattern, not a real bug

### Type-check

Mypy enforces the type hints already in the source. Configured strict-ish:
`warn_return_any`, `warn_unreachable`, `warn_unused_ignores`,
`no_implicit_optional`. Not full `strict` mode — that produces noise on
small codebases without catching proportionally more bugs.

```sh
mypy src
```

Two module overrides in `pyproject.toml`:
- `tests.*` — `ignore_errors = true`. Mocks, monkeypatch, and fixture
  return types defeat strict typing without surfacing real bugs.
- `taskflow_cli.api.*` — `warn_return_any = false`. The api layer is the
  type boundary between the `Any`-typed JSON returned by `httpx.json()`
  and our named shapes. Asking mypy to prove what JSON can't prove is
  the wrong question of the wrong layer.

A `Client` protocol in `transport.py` makes the duck-typed shape that
both `Transport` and `Session` implement explicit — `api/*` functions
accept `Client`, callers pass either.

The next step in this Testing track is a GitHub Actions workflow that runs
`pytest` on every push and PR — see the Phase B plan in
[`work-track.md`](./work-track.md).


Architecture in detail and the PR roadmap live in
[`work-track.md`](./work-track.md).


---

## License

MIT (inherits from the project root [`LICENSE`](../LICENSE)).
