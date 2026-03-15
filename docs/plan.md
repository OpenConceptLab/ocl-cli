# OCL CLI Implementation Plan

## Context

The OCL API (oclapi2) is powerful but complex. The `ocl-mcp` project already wraps it for AI assistants via MCP, but a CLI is more flexible: easier to extend, scriptable, and usable by both humans and agents. The `ocl-cli` repo is empty — this plan creates the full CLI from scratch.

The CLI mirrors OCL's resource hierarchy: **owners** (users/orgs) → **repos** (sources/collections, versioned) → **resources** (concepts/mappings, versioned). Operations are first-class alongside resources.

## Tech Stack

- **Python 3.10+**, **Click** (CLI framework), **httpx** (sync HTTP), **tenacity** (retry)
- Entry point: `ocl` command via `pyproject.toml` `[project.scripts]`
- No async — CLI is sequential; use `httpx.Client` (sync) for simplicity
- No in-memory caching — CLI invocations are short-lived

## Project Structure

```
ocl-cli/
  pyproject.toml
  CLAUDE.md
  README.md
  docs/
    plan.md                          # This file
  src/ocl_cli/
    __init__.py
    __main__.py                      # python -m ocl_cli
    main.py                          # Click root group + global options
    config.py                        # ~/.ocl/config.json management
    api_client.py                    # Sync HTTP client (adapted from ocl-mcp)
    output.py                        # JSON / table formatting
    commands/
      __init__.py
      auth.py                        # login, logout, whoami
      server.py                      # server list/add/remove/use
      owner.py                       # owner search/get, org members
      repo.py                        # repo list/get/create/update/versions (unified source+collection)
      concept.py                     # concept search/get/create/update/retire/names/descriptions/extras/versions/match
      mapping.py                     # mapping search/get/create/update/retire/versions/suggest/bulk-map
      cascade.py                     # $cascade operation
      ref.py                         # collection reference management (add/remove/list)
      expansion.py                   # expansion create/list/get
      import_export.py               # bulk import, export (future)
  tests/
    conftest.py
    test_config.py
    test_api_client.py
    test_commands/
```

## Command Hierarchy

All commands support `--version VERSION` where applicable. The `latest` keyword is the default (matching the OCL API behavior where omitting version returns latest released).

```bash
ocl [--json/-j] [--server/-s NAME] [--token TOKEN] [--verbose/-v] [--version]

  # --- Auth ---
  login                                         # Prompt for token, validate via GET /user/, store
  logout                                        # Remove stored token
  whoami                                        # GET /user/ — show current user info

  # --- Server Management ---
  server
    list                                        # List configured servers
    add ID URL [--name] [--token-env]           # Add a server
    remove ID                                   # Remove a server
    use ID                                      # Set default server

  # --- Owners (users & orgs) ---
  owner
    search [QUERY] [--type users|orgs|all] [--limit] [--page]
    get OWNER [--type users|orgs]               # Get user/org details
    members OWNER                               # List org members
    member add OWNER USER                       # Add member to org
    member remove OWNER USER                    # Remove member from org

  # --- Repos (unified source + collection) ---
  repo
    list [QUERY] [--owner] [--owner-type] [--type source|collection|all] [--limit] [--page]
    get OWNER REPO [--owner-type] [--type] [--version VERSION]
                                                # VERSION defaults to HEAD; use "latest" for latest released
    create OWNER REPO_ID NAME --type source|collection
      [--owner-type] [--description] [--default-locale] [--supported-locales]
      [--source-type|--collection-type] [--public-access] [--canonical-url]
      [--custom-validation-schema] [--extras JSON]
    update OWNER REPO [--type] [fields...]
    retire OWNER REPO [--type]                  # Deactivate (soft delete)
    versions OWNER REPO [--type] [--released] [--processing] [--limit] [--page]
    version-create OWNER REPO VERSION_ID        # Create a new version (snapshot)
      [--type] [--description] [--released]
    version-update OWNER REPO VERSION           # Edit version metadata
      [--type] [--description] [--released]
    extras OWNER REPO [--type]                  # List custom attributes
    extra-set OWNER REPO KEY VALUE [--type]     # Set a custom attribute
    extra-del OWNER REPO KEY [--type]           # Delete a custom attribute

  # --- Concepts ---
  concept
    search [QUERY]                              # Global search across all public sources
      [--owner] [--owner-type] [--source] [--version VERSION]
      [--concept-class] [--datatype] [--locale]
      [--include-retired] [--include-mappings] [--include-inverse-mappings]
      [--updated-since DATE] [--sort FIELD] [--verbose]
      [--limit] [--page]
    get OWNER SOURCE CONCEPT_ID                 # Get single concept
      [--owner-type] [--version VERSION]        # --version applies to source version
      [--concept-version CVERSION]              # Specific concept version
      [--include-mappings] [--include-inverse-mappings] [--verbose]
    create OWNER SOURCE CONCEPT_ID              # Create concept in source
      [--owner-type] [--concept-class] [--datatype]
      [--name NAME] [--name-locale LOCALE] [--name-type TYPE]
      [--names-json JSON_OR_FILE]
      [--description TEXT] [--description-locale LOCALE]
      [--descriptions-json JSON_OR_FILE]
      [--external-id] [--extras JSON]
    update OWNER SOURCE CONCEPT_ID [fields...]
      [--owner-type] [--update-comment TEXT]
    retire OWNER SOURCE CONCEPT_ID              # Soft-delete (set retired=true)
      [--owner-type] [--update-comment TEXT]
    versions OWNER SOURCE CONCEPT_ID            # List concept version history
      [--owner-type] [--limit] [--page]

    # --- Concept sub-resources ---
    names OWNER SOURCE CONCEPT_ID               # List names
      [--owner-type]
    name-add OWNER SOURCE CONCEPT_ID NAME       # Add a name/translation
      --locale LOCALE [--name-type TYPE] [--locale-preferred]
    name-update OWNER SOURCE CONCEPT_ID NAME_ID # Update a name
      [--name] [--locale] [--name-type] [--locale-preferred]
    name-del OWNER SOURCE CONCEPT_ID NAME_ID    # Delete a name

    descriptions OWNER SOURCE CONCEPT_ID        # List descriptions
      [--owner-type]
    description-add OWNER SOURCE CONCEPT_ID TEXT
      --locale LOCALE [--description-type TYPE]
    description-update OWNER SOURCE CONCEPT_ID DESC_ID [fields...]
    description-del OWNER SOURCE CONCEPT_ID DESC_ID

    extras OWNER SOURCE CONCEPT_ID              # List concept extras
    extra-set OWNER SOURCE CONCEPT_ID KEY VALUE # Set a custom attribute
    extra-del OWNER SOURCE CONCEPT_ID KEY       # Delete a custom attribute

    match TERM... --target-source SRC           # $match endpoint
      [--target-owner] [--target-version VERSION]  # version appended to target_repo_url
      [--limit] [--verbose]
      [--include-retired] [--semantic] [--best-match]

  # --- Mappings ---
  mapping
    search [QUERY]                              # Global or scoped search
      [--owner] [--owner-type] [--source] [--version VERSION]
      [--map-type] [--from-concept] [--to-concept]
      [--from-source] [--to-source] [--concept]
      [--include-retired] [--updated-since DATE]
      [--sort FIELD] [--verbose]
      [--limit] [--page]
    get OWNER SOURCE MAPPING_ID                 # Get single mapping
      [--owner-type] [--version VERSION]
    create OWNER SOURCE                         # Create mapping
      --map-type TYPE
      [--from-concept-url URL] [--from-concept-code CODE] [--from-source-url URL]
      [--to-concept-url URL] [--to-concept-code CODE] [--to-source-url URL]
      [--owner-type] [--external-id] [--extras JSON]
    update OWNER SOURCE MAPPING_ID [fields...]
      [--owner-type] [--update-comment TEXT]
    retire OWNER SOURCE MAPPING_ID              # Soft-delete
      [--owner-type] [--update-comment TEXT]
    versions OWNER SOURCE MAPPING_ID            # List mapping version history
      [--owner-type] [--limit] [--page]

    suggest TERMS... --target-source SRC        # AI mapping suggestions
      [--target-owner] [--max-suggestions] [--confidence-threshold]
    bulk-map --input FILE_OR_JSON --target-source SRC   # Bulk mapping
      [--target-owner] [--format json|csv|tsv]

  # --- Collection References ---
  ref
    list OWNER COLLECTION [--version] [--limit] [--page]
    add OWNER COLLECTION EXPRESSION...          # Add references (concept/mapping URLs)
      [--cascade none|sourcemappings|sourcetoconcepts] [--async]
    remove OWNER COLLECTION EXPRESSION...       # Remove references
      [--cascade none|sourcemappings|sourcetoconcepts]

  # --- Cascade ---
  cascade OWNER REPO CONCEPT_ID
    [--owner-type] [--repo-type source|collection] [--version VERSION]
    [--map-types LIST] [--exclude-map-types LIST] [--return-map-types LIST]
    [--method sourceMappings|sourceToConcepts]
    [--cascade-hierarchy] [--cascade-mappings]
    [--levels N] [--reverse] [--view flat|hierarchy]
    [--omit-if-exists-in REPO_URL] [--equivalency-map-type TYPE]

  # --- Clone ---
  clone OWNER DEST_SOURCE EXPRESSION...         # $clone — deep copy concepts
    [--owner-type] [--map-types] [--exclude-map-types]
    [--method] [--levels] [--cascade-hierarchy] [--cascade-mappings]

  # --- Resolve Reference ---
  resolve EXPRESSION... [--namespace NAMESPACE]  # $resolveReference

  # --- Expansions ---
  expansion
    list OWNER COLLECTION VERSION [--owner-type]
    get OWNER COLLECTION [--owner-type] [--version] [--expansion-id]
    create OWNER COLLECTION VERSION             # Trigger expansion
      [--owner-type] [--filter TEXT] [--count N] [--offset N]
      [--active-only] [--include-designations] [--include-definition]

  # --- Import/Export (Phase 4) ---
  export OWNER REPO VERSION [--type source|collection]  # Download export
    [--owner-type] [--check]                    # --check = HEAD request (status only)
  import FILE [--async]                         # Bulk import (JSON-lines or CSV)
```

## Versioning Model

Versioning is central to OCL and must be explicit in the CLI:

### Repository (source/collection) versions
- **HEAD** — the working/draft version (default when no version specified)
- **`latest`** — most recent *released* version; use `--version latest`
- **Named versions** — e.g., `--version v2024.1`; accessed via `/{owner}/{repo}/{version}/`
- **Version creation** — `ocl repo version-create OWNER REPO v2024.1` creates a snapshot

### Concept/mapping versions
- Auto-created on every edit (each edit = new version)
- **List versions** — `ocl concept versions OWNER SOURCE CONCEPT_ID`
- **Get specific version** — `ocl concept get OWNER SOURCE CONCEPT_ID --concept-version 1a2b3c`
- **Version scoped by source version** — `ocl concept get OWNER SOURCE CONCEPT_ID --version v2024.1` gets the concept as it existed in source version v2024.1

### URL Pattern
```
/{owner_type}/{owner}/{repo_type}/{repo}/                    # HEAD (default)
/{owner_type}/{owner}/{repo_type}/{repo}/latest/             # Latest released
/{owner_type}/{owner}/{repo_type}/{repo}/{version}/          # Specific version
/{owner_type}/{owner}/{repo_type}/{repo}/concepts/{id}/      # Concept in HEAD
/{owner_type}/{owner}/{repo_type}/{repo}/{version}/concepts/{id}/  # Concept in version
/{owner_type}/{owner}/{repo_type}/{repo}/concepts/{id}/{concept_version}/  # Specific concept version
```

## Unified `repo` Command (source + collection)

Sources and collections share 90% of their API surface. They are unified under `ocl repo` with a `--type` flag:

- `--type source` (default) or `--type collection`
- When `--type` is omitted, defaults to `source` for create, inferred from API for get/list
- Collection-specific operations (`ref`, `expansion`) are separate command groups that operate on collections implicitly
- The API URL pattern changes: `/sources/` vs `/collections/` — the client handles this based on `--type`

### What's shared (identical API shape):
- list, get, create, update, retire
- versions, version-create, version-update
- extras management

### What's collection-only:
- `ocl ref` — collection reference management
- `ocl expansion` — ValueSet expansion
- `collection_type` field (vs `source_type` for sources)

### What's source-only:
- `source_type` field
- Concepts and mappings are *created* in sources (collections only reference them)

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CLI framework | Click | More control than Typer, mature, no magic |
| Sync HTTP | httpx.Client | CLI is sequential; no asyncio complexity |
| Config location | `~/.ocl/config.json` | Standard pattern (like gh, aws cli) |
| Output | `--json` flag, tables by default | Agents use `--json`; humans get readable tables |
| No caching | Omit | Short-lived CLI processes; add later if needed |
| Unified repo command | `ocl repo --type` | 90% shared API surface; `/repos/` endpoint exists; reduces command surface |
| owner-type default | "orgs" | Most users work with org-owned repos |
| Version default | HEAD (no version) | Matches API default; `--version latest` for latest released |

## Implementation Phases

### Phase 1 — Foundation
1. `pyproject.toml` — package with Click, httpx, tenacity, python-dotenv
2. `config.py` — load/save `~/.ocl/config.json`, token resolution (CLI flag → env var → config file)
3. `api_client.py` — sync HTTP client adapted from ocl-mcp (GET/POST/PUT/PATCH/DELETE, retry logic, error handling). Drop caching, drop async, add PUT/DELETE.
4. `output.py` — `output_result()` dispatcher, table formatter, pagination footer, error formatting to stderr
5. `main.py` — Click root group with global options, context object setup
6. `commands/auth.py` — `login` (prompt for token, validate via GET /user/, store), `logout`, `whoami`
7. `commands/server.py` — `list`, `add`, `remove`, `use`
8. `CLAUDE.md` — dev setup and conventions

### Phase 2 — Core Read Commands
1. `commands/owner.py` — `search`, `get`, `members`
2. `commands/repo.py` — `list`, `get` (with `--version`), `versions`
3. `commands/concept.py` — `search`, `get` (with `--version` and `--concept-version`), `versions`, `names`, `descriptions`, `extras`
4. `commands/mapping.py` — `search`, `get` (with `--version`), `versions`
5. `commands/cascade.py` — full `$cascade` operation
6. `commands/ref.py` — `list` (collection references)
7. `commands/expansion.py` — `list`, `get`
8. `resolve` command — `$resolveReference`

### Phase 3 — Write Commands
1. `repo create`, `repo update`, `repo retire`, `repo version-create`, `repo version-update`, `repo extra-set/del`
2. `concept create`, `concept update`, `concept retire`, `concept name-add/update/del`, `concept description-add/update/del`, `concept extra-set/del`
3. `mapping create`, `mapping update`, `mapping retire`
4. `ref add`, `ref remove` (collection references)
5. `expansion create`
6. `clone` command
7. `concept match`, `mapping suggest`, `mapping bulk-map`
8. `owner member add/remove`

### Phase 4 — Advanced (future)
- `import` / `export` commands (async bulk operations)
- `--all` auto-pagination
- Shell completions (Click built-in)
- Pipe detection (auto-JSON when stdout is not a TTY)
- Canonical URL registry (`url-registry` commands)
- User/org create (admin operations)
- MCP server wrapper (reuse `api_client.py` directly — no subprocess needed)

## AI Discoverability

When `ocl` is installed globally (via pip, brew, etc.), AI assistants like Claude Code have no CLAUDE.md or project context to draw from. They must discover the CLI's capabilities at runtime. This section outlines strategies for making `ocl` AI-friendly, ordered by implementation priority.

### Implemented: `ocl reference` command

A single command that dumps the entire command tree — all groups, subcommands, arguments, options, and help text — in one output. This eliminates the N+1 `--help` round-trips an AI agent would otherwise need to discover the CLI surface. Built by programmatically walking Click's command tree.

```bash
ocl reference          # Full CLI reference, human-readable
ocl reference --json   # Machine-readable JSON schema of all commands
```

This is the highest-leverage feature for AI consumption. An agent runs one command and has complete knowledge of every operation available.

### Future: Enhanced `--help` output

Ensure every command and subcommand has:
- A clear one-line description
- Documented arguments with types and defaults
- Usage examples in the help epilog (Click supports `epilog=` on commands)

Good `--help` output is the universal fallback — it works for every CLI tool, every AI assistant, and every human. The better structured it is, the fewer follow-up queries an agent needs.

### Future: Man pages

Click can generate man pages via `click-man`. When installed via a package manager (brew, apt), man pages are automatically available. An AI agent can run `man ocl` or `man ocl-concept` for detailed documentation. More verbose than `--help` but useful for comprehensive reference.

### Future: Shell completions

Click has built-in support for Bash, Zsh, and Fish completions. These primarily help human users but also signal to AI agents what subcommands and options are available. Ship as `ocl --install-completion`.

### Future: MCP server as companion package

The `ocl-mcp` project already wraps the OCL API for AI assistants via the Model Context Protocol. MCP tools are directly registered with typed schemas, descriptions, and parameters — the richest possible AI integration. A future `pip install ocl-mcp` gives any MCP-capable client (Claude Code, Cursor, etc.) native tool access without CLI discovery. The `ocl-cli` API client is designed for reuse by `ocl-mcp` (see MCP-Readiness Architecture below).

### Comparison

| Approach | AI effort to discover | Richness | Install complexity | Works for humans too |
|----------|----------------------|----------|--------------------|---------------------|
| `ocl reference` | 1 command | High — full tree | Zero (built-in) | Yes |
| `--help` (per-command) | N+1 commands | Medium | Zero (built-in) | Yes |
| Man pages | 1 command | High | Package manager | Yes |
| Shell completions | N/A (autocomplete) | Low | One-time setup | Yes |
| MCP server | Zero (auto-registered) | Highest — typed schemas | `pip install ocl-mcp` | No |

## MCP-Readiness Architecture

Business logic lives in `api_client.py` (high-level methods like `search_concepts()`, `create_mapping()`), NOT in Click command handlers. Click commands are thin wrappers: parse args → call client method → format output. This means a future MCP server can `from ocl_cli.api_client import OCLAPIClient` and call the same methods directly, without subprocess overhead. The `output.py` layer is CLI-only; MCP would use its own response formatting.

## API Coverage Comparison

### Covered by ocl-mcp and included in this plan:
- Search owners, repos, concepts, mappings
- Get repos, concepts, mappings
- Repo versions
- Create/update sources, collections, concepts, mappings
- Concept names (translations)
- $cascade, $match
- Expansions
- Mapping suggest, bulk-map
- Multi-server support

### NOT in ocl-mcp but added to this plan:
- Owner get, org member management
- Repo create/update/retire (full CRUD, not just save)
- Repo version create/update (snapshot management)
- Concept/mapping retire (soft delete)
- Concept/mapping version history
- Concept descriptions sub-resource (full CRUD)
- Concept extras sub-resource (full CRUD)
- Repo extras management
- Collection reference management (add/remove/list)
- Expansion creation (trigger)
- `$clone` operation
- `$resolveReference` operation
- Export/import (Phase 4)
- Canonical URL registry (Phase 4)
- Version-scoped resource retrieval (`--version` on concept/mapping get)

## Files to Reuse From ocl-mcp

- **`ocl-mcp/src/ocl_mcp/api_client.py`** — Adapt all high-level methods to sync. Keep retry decorator pattern, connection pooling, error handling. Drop caching decorator, async, and logging infrastructure.
- **`ocl-mcp/src/ocl_mcp/tools.py`** — Reference for parameter signatures and response shaping.
- **`ocl-mcp/src/ocl_mcp/server_registry.py`** — Adapt server config loading pattern for `config.py`.

## Verification

1. `pip install -e .` in the ocl-cli directory
2. `ocl --help` shows all command groups
3. `ocl whoami --token <token>` returns user info
4. `ocl owner search WHO --json` returns JSON
5. `ocl concept search malaria --source CIEL --owner CIEL` returns results with pagination
6. `ocl repo get CIEL CIEL --type source` returns source details
7. `ocl repo get CIEL CIEL --type source --version latest` returns latest released version
8. `ocl concept get CIEL CIEL 116128 --json` returns a specific concept as JSON
9. `ocl concept get CIEL CIEL 116128 --version v2024.1` returns concept from specific source version
10. Write commands tested against dev server (`--server ocl-dev`)
