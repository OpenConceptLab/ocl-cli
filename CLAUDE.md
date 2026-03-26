# OCL CLI

Command-line interface for the Open Concept Lab (OCL) API.

## Setup

```bash
cd /Users/jonathanpayne/projects/ocl/ocl-cli
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Architecture

- **`src/ocl_cli/api_client.py`** — Sync HTTP client with all high-level API methods. Business logic lives here (not in Click commands) so it can be reused by a future MCP server wrapper.
- **`src/ocl_cli/config.py`** — Server registry and auth token resolution. Config stored at `~/.ocl/config.json`.
- **`src/ocl_cli/output.py`** — JSON and human-readable table formatters.
- **`src/ocl_cli/main.py`** — Click root group, global options, command registration.
- **`src/ocl_cli/commands/`** — Thin Click command wrappers that parse args → call client → format output.

## Conventions

- Click commands are thin wrappers. All API logic goes in `api_client.py`.
- Default `owner_type` is `"orgs"` for targeted operations, `"all"` for search/list.
- Default `repo_type` is `"all"` for search/list, required for targeted operations.
- `--json` / `-j` global flag outputs raw API JSON (unmodified) for agent consumption.
- `--debug` / `-d` global flag shows HTTP requests on stderr.
- `--show-request` global flag shows server URL and API request paths on stderr (cleaner than `--debug`).
- `--verbose` per-command flag on search/list commands passes `?verbose=true` to the OCL API, which returns full details (names, descriptions, extras) instead of summary. Default is summary (no verbose).
- Version parameters are type-specific: `--repo-version` for sources/repos, `--collection-version` for collections, `--concept-version` for concept versions. Never use a bare `--version` for these.
- Exit codes: 0=success, 1=client error (4xx), 2=server error (5xx), 3=auth error.
- **When changing command arguments or flags**, always update `README.md` and `docs/demos/` to match.

## Running

```bash
ocl --help
ocl whoami --token YOUR_TOKEN
ocl concept search malaria --owner CIEL --source CIEL
```

## Testing

```bash
pytest
```

## Related repos

- `ocl-mcp` — MCP server for AI assistants (async, different interface)
- `ocl-docs` — API documentation at docs.openconceptlab.org
- `oclapi2` — The OCL API backend

## Issues / Tickets

- Issues for `ocl-cli` are tracked at https://gitea.lab.jpayne.md/ocl/ocl-cli. Use `tea` CLI by default, and direct API access to Gitea is also available. Note: this repo will transition to the OCL GitHub in the future.
