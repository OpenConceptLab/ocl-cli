# OCL CLI Comparison: ocl-cli vs OpenConceptLab/oclcli

**Date:** 2026-03-20
**Purpose:** Analyze differences between our `ocl-cli` and Filipe's `OpenConceptLab/oclcli`, identify what to learn from each, and plan convergence into a single upstream PR.

## Repo Overview

| Aspect | Our `ocl-cli` | Filipe's `oclcli` |
|--------|---------------|-------------------|
| **Repo** | `ocl/ocl-cli` (local) | [OpenConceptLab/oclcli](https://github.com/OpenConceptLab/oclcli) |
| **Author** | Jonathan Payne | Filipe Lopes |
| **Version** | 0.1.0 | 0.1.0 |
| **Framework** | Click | Typer (wraps Click + Rich) |
| **HTTP client** | httpx (sync) | requests |
| **Python** | >=3.10 | >=3.8 (but uses 3.10+ syntax) |
| **Package layout** | `src/ocl_cli/` (proper namespace) | `src/` (flat — collision-prone) |
| **License** | — | MPL-2.0 |
| **Activity** | Active (4+ commits, ongoing) | 5 days of work (Dec 2025), dormant since |

## Architecture Comparison

### API Client Pattern

| | Our `ocl-cli` | Filipe's `oclcli` |
|-|---------------|-------------------|
| **Design** | Centralized `api_client.py` with all business logic | No centralized client; HTTP calls scattered in command files |
| **Retry logic** | Yes (tenacity, 3 retries, exponential backoff) | No |
| **MCP-readiness** | Explicit goal — client reusable by MCP wrapper | Not designed for reuse |

**Verdict:** Our architecture is significantly stronger here. The centralized client is a prerequisite for the MCP server (`ocl-mcp`). This is non-negotiable for the upstream PR.

### Configuration & Auth

| | Our `ocl-cli` | Filipe's `oclcli` |
|-|---------------|-------------------|
| **Config path** | `~/.ocl/config.json` | `~/.ocl-cli/config.json` |
| **Multi-server** | Yes — server registry with prod/dev/qa/staging | No — single base URL at a time |
| **Token resolution** | `--token` → env var → server-specific env → config file | `.env` → config file → defaults |
| **Token format** | Bearer and Token schemes | Token only (rejects Bearer) |
| **Server override** | `--server` / `-s` flag + `OCL_SERVER` env | Not supported |
| **Login flow** | `ocl login` stores token, validates via GET /user/ | Similar, but also stores username |
| **Config commands** | `ocl server list/add/remove/use` | `ocl config` (interactive), `ocl config reset` |

**Verdict:** Our multi-server registry is superior. Filipe's `.env` integration and `config reset` command are nice touches we could optionally adopt. His approach of storing the username in config is a minor convenience.

### Output & UX

| | Our `ocl-cli` | Filipe's `oclcli` |
|-|---------------|-------------------|
| **JSON output** | `--json` / `-j` global flag (raw API response) | Not available |
| **Debug mode** | `--debug` / `-d` shows HTTP on stderr | Not available |
| **Verbose API** | `--verbose` per-command passes `?verbose=true` | Not available |
| **Table formatting** | Custom aligned tables via `output.py` | Plain text (no Rich tables despite having Rich) |
| **Exit codes** | 0/1/2/3 documented | Ad hoc 1/2 |
| **Agent support** | `ocl reference` command dumps CLI tree | Not available |

**Verdict:** Our output system is more complete. `--json` is essential for scripting and agent consumption.

## Feature Comparison: Commands

### Commands We Have That Filipe Doesn't

These are the bulk of our advantage:

- **Concept search** — global and scoped, with rich filtering (`--concept-class`, `--datatype`, `--locale`, `--include-retired`, `--updated-since`, `--sort`)
- **Concept CRUD** — create, update, retire, names, descriptions, extras
- **Concept match** — `ocl concept match TERM... --target-source CIEL` (FHIR $match)
- **Mapping search** — global and scoped, with filtering (`--map-type`, `--from-source`, `--to-concept`, etc.)
- **Mapping CRUD** — create, update, retire
- **Cascade** — `ocl cascade` with full parameter support
- **Collection references** — add/remove/list
- **Collection expansions** — list/get/create
- **Repo CRUD** — create, update, versions, extras
- **Repo versioning** — create/update versions
- **Owner members** — list org members
- **CLI reference** — `ocl reference` for agent consumption

### Commands Filipe Has That We Don't

| Command | Description | Priority | Notes |
|---------|-------------|----------|-------|
| **`ocl task list`** | List async tasks (ID, STATE, NAME, UPDATED) | **High** | Async tasks are critical for bulk operations. `--verbose` adds timing details. Note: documented `--state` and `--mine` flags are NOT implemented in code. |
| **`ocl org create`** | Create organization | Medium | We have `ocl repo create` but no org CRUD. |
| **`ocl org delete`** | Delete organization (with `--yes` confirm) | Medium | Destructive; needs confirmation UX. |
| **`ocl config reset`** | Reset config to defaults | Low | Nice-to-have convenience. |
| **`ocl tool recreate_collection_with_versionless_references`** | Migration tool: deversion, dedup, prune, bulk import | **Interesting** | Very specialized. Not a general CLI command, but the reference resolution and cascade pruning logic is valuable. See analysis below. |

### The "task" Command — Deep Dive

Filipe's task command is minimal but points to an important gap:

```
ocl task list [--limit N] [--verbose]
```

- Hits `GET /user/tasks/` with `limit` parameter
- Renders table: ID | STATE | NAME | UPDATED
- `--verbose` adds: User | Started | Finished | Runtime | Message
- **Missing** (documented in README but not implemented): `--state STARTED`, `--mine`, `--all`

**What we should build (goes beyond Filipe's implementation):**

1. `ocl task list` — list tasks with filtering by state
2. `ocl task get <task_id>` — get task details
3. `ocl task wait <task_id>` — poll until complete (useful for scripts)
4. Consider: task cancel, task retry

### The "tool" Command — Analysis

`ocl tool recreate_collection_with_versionless_references` is the most complex feature in Filipe's CLI. It's a pipeline that:

1. Loads a collection export JSON file
2. Resolves versioned references (e.g., `/concepts/100/1/`) to base URLs (`/concepts/100/`)
3. Deduplicates references, preferring stronger cascade methods
4. Skips mapping references (pulled in via cascade)
5. Prunes child concepts already covered by parent concept sets (via cascade API lookups)
6. Outputs a bulk-import-ready JSON file
7. Optionally deletes + recreates the collection and runs bulk import

**Assessment:** This is a specialized migration/operational tool, not a general-purpose CLI command. The underlying logic (reference resolution, dedup, cascade pruning) is well-structured. Rather than port this specific tool, we should:

- Add the `task` command (high value, general purpose)
- Consider a `tool` command group for operational utilities in the future
- Study the cascade pruning logic if we ever need collection migration tooling

## What We Should Adopt from Filipe's Work

### High Priority

1. **Task command** — `ocl task list` and `ocl task get`. Async task visibility is a real gap in our CLI.
2. **Org CRUD** — `ocl org create` / `ocl org delete` (we already have org search/get via `ocl owner`). Consider adding `ocl owner create-org` and `ocl owner delete-org` to our existing `owner` command group.

### Medium Priority

3. **Username storage in config** — Filipe stores `username` alongside the token. Minor convenience for display/debugging.
4. **Interactive prompts for create commands** — Filipe's org/collection create commands prompt for missing required args. We could adopt this pattern for our create commands.

### Low Priority / Skip

5. **Config reset** — Nice but not essential. `ocl server remove` + re-add achieves similar.
6. **The `tool` command** — Too specialized for v1. File as a future enhancement.
7. **Typer framework** — Not adopting. Click is more mature, we're already invested, and Typer's main advantage (type hints as CLI args) doesn't outweigh the migration cost.
8. **`.env` file support** — We already have env var support via `OCL_API_TOKEN`. dotenv loading adds a dependency for marginal benefit.

## What Filipe Should Adopt from Our Work

When we submit the PR, these are the key improvements over the existing `oclcli`:

1. **Centralized API client** — prerequisite for MCP server, clean separation of concerns
2. **Multi-server registry** — essential for teams working across environments
3. **`--json` flag** — raw API output for scripting and AI agents
4. **`--debug` flag** — HTTP tracing for troubleshooting
5. **Concept/mapping search and CRUD** — the core OCL workflow
6. **Concept match** — AI-powered terminology mapping via FHIR $match
7. **Cascade command** — hierarchy navigation
8. **Collection references and expansions** — full collection management
9. **Retry logic with backoff** — production resilience
10. **Proper package namespace** — `ocl_cli` not `src`
11. **Documented exit codes** — 0/1/2/3 convention
12. **`ocl reference` command** — CLI tree dump for agent consumption

## Convergence Plan

### Phase 1: Incorporate Task Command (Now)

- Add `ocl task list` and `ocl task get` to our CLI
- Add API client methods: `list_tasks()`, `get_task()`
- Implement `--state` and `--verbose` flags properly (unlike Filipe's aspirational README)
- Add formatter in `output.py`

### Phase 2: Add Org CRUD (Soon)

- Add `ocl owner create-org` and `ocl owner delete-org` commands
- Add API client methods: `create_org()`, `delete_org()`
- Include `--yes` confirmation for destructive delete

### Phase 3: Submit PR to OpenConceptLab/oclcli (After Phase 1-2)

**Strategy:** This will be a significant PR since the architecture is fundamentally different. Options:

- **Option A: Full replacement PR** — Replace the codebase with our architecture, preserving Filipe's task/tool features. Clean but may feel like we're throwing away his work.
- **Option B: Incremental PRs** — Start with a discussion issue, then submit PRs that migrate feature-by-feature. More collaborative but slower.
- **Option C: New repo proposal** — Propose `ocl-cli` as the successor, with attribution. Filipe's repo becomes archived.

**Recommended: Option A with strong attribution.** The architectures are too different for incremental migration. The PR description should:
- Credit Filipe's pioneering work
- Explain the MCP-readiness motivation
- Show that his task command is incorporated
- Reference the tool command as a future enhancement
- Invite him as a collaborator

### Phase 4: Ongoing

- Keep task/tool features parity
- Coordinate on new features via GitHub issues
- Eventually, `ocl-cli` becomes the canonical OCL CLI across pypi

## File-by-File Mapping

| Filipe's file | Our equivalent | Notes |
|---------------|---------------|-------|
| `src/cli.py` | `src/ocl_cli/main.py` | Root app setup |
| `src/config.py` | `src/ocl_cli/config.py` | Our version is richer (multi-server) |
| `src/http.py` | `src/ocl_cli/api_client.py` | Our version is centralized |
| `src/identity.py` | (inline in api_client) | Username extraction |
| `src/helpers/auth.py` | `src/ocl_cli/config.py` | Token handling |
| `src/helpers/text.py` | — | `normalize_id()`, `slugify()` — we don't need these yet |
| `src/helpers/validators.py` | `src/ocl_cli/config.py` | URL/token normalization |
| `src/commands/login.py` | `src/ocl_cli/commands/auth.py` | We also have logout, whoami |
| `src/commands/user/get.py` | `src/ocl_cli/commands/auth.py` | `whoami` equivalent |
| `src/commands/config/manage.py` | `src/ocl_cli/commands/server.py` | Our server registry is richer |
| `src/commands/org/list.py` | `src/ocl_cli/commands/owner.py` | We have search + get |
| `src/commands/org/create.py` | — | **Gap: we need this** |
| `src/commands/org/delete.py` | — | **Gap: we need this** |
| `src/commands/source/list.py` | `src/ocl_cli/commands/repo.py` | We have full CRUD |
| `src/commands/collection/list.py` | `src/ocl_cli/commands/repo.py` | We have full CRUD |
| `src/commands/collection/create.py` | `src/ocl_cli/commands/repo.py` | We have this |
| `src/commands/collection/delete.py` | — | We have update but not delete |
| `src/commands/task/list.py` | — | **Gap: high priority** |
| `src/commands/tool/*` | — | Specialized migration tool; future enhancement |
