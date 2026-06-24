# TaskFlow CLI

Command-line client for [TaskFlow](https://github.com/el-amin-dev/taskflow).
Built with Typer + httpx. Single-use refresh tokens with file-lock theft
protection, atomic 0600 credential storage, scriptable exit codes,
`--json` mode for pipelines.

> **Status** — auth commands (`register`, `login`, `whoami`, `logout`)
> are live. Workspaces, tasks, comments, activity, and audit ship in
> subsequent PRs. The map and PR plan: [`work-track.md`](./work-track.md).

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

| Command                    | What it does                                  |
|----------------------------|-----------------------------------------------|
| `tflowctl auth register`   | Create a new account. Does not log in.        |
| `tflowctl auth login`      | Log in and save credentials.                  |
| `tflowctl auth whoami`     | Show the authenticated user.                  |
| `tflowctl auth logout`     | Revoke session + wipe local credentials.      |

Every command supports `--help`:

```bash
tflowctl auth login --help
```

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
| `2`  | usage error          | bad argv — missing required arg, unknown command                        |
| `10` | auth failed          | wrong password, invalid/expired token, session expired                  |
| `11` | not found            | resource doesn't exist *or* not yours (non-disclosure: same response)   |
| `12` | forbidden            | edit/delete by someone without the right                                |
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
pip install -e .

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
└── src/taskflow_cli/
    ├── main.py             # Typer entrypoint + central error handler
    ├── config.py           # env-driven, XDG, fail-fast
    ├── tokens.py           # atomic 0600 + refresh_lock
    ├── errors.py           # exception hierarchy + exit codes
    ├── transport.py        # httpx + error-envelope unwrap
    ├── session.py          # refresh-on-401 + lock orchestration
    ├── api/                # one module per resource
    │   └── auth.py
    └── commands/           # Typer subcommand modules
        └── auth.py
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

> **Note:** only `invite` is implemented today. Listing and removing members
> are blocked by backend issue
> [#85](https://github.com/el-amin-dev/taskflow/issues/85). Once that lands,
> `member list` and `member remove` will follow.

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


Architecture in detail and the PR roadmap live in
[`work-track.md`](./work-track.md).

---

## License

MIT (inherits from the project root [`LICENSE`](../LICENSE)).
