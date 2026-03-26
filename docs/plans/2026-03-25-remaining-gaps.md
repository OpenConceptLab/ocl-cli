# OCL CLI — Remaining Feature Gaps

**Date:** 2026-03-25
**Status:** Planning
**Ticket:** [ocl/ocl-cli:#52 - Remaining CLI feature gaps (export, bulk import, FHIR ops, match expansion)](https://gitea.lab.jpayne.me/ocl/ocl-cli/issues/52)

## Where We Are

The CLI covers the core OCL workflow: concept/mapping/repo CRUD, collection curation, cascade traversal, semantic matching, task monitoring, and server management. A full smoke test of the demo suite (Themes 00–07) passes against production, with the following capabilities verified:

- **Read:** concept/mapping/repo search & get, names, descriptions, extras, versions, cascade, match (with concept-class filter and inline mappings), expansions, tasks, owner profiles
- **Write:** concept/mapping create/update/retire, repo create/update/delete, version create/update (incl. match-algorithms), extras set/del, collection refs add/remove, org create/delete
- **Automation:** JSON output on all commands, exit code contract, debug output, command reference

## What's Missing

Grouped and sequenced by priority. Each phase should include corresponding demo scenarios added to the suite.

---

### Phase 1: Export & Reference Resolution

High priority — these are foundational operations for automation and interoperability workflows.

#### 1a. Repository Export (`$export`)

Enable downloading and managing repo version exports.

**API endpoints:**
- `POST /:ownerType/:owner/:repoType/:repo/:version/export/` — trigger export
- `HEAD /:ownerType/:owner/:repoType/:repo/:version/export/` — check export status
- `GET /:ownerType/:owner/:repoType/:repo/:version/export/` — download export
- `DELETE /:ownerType/:owner/:repoType/:repo/:version/export/` — delete export

**Proposed CLI commands:**
```bash
ocl repo export OWNER REPO VERSION          # trigger + poll + download
ocl repo export-status OWNER REPO VERSION   # check status only
ocl repo export-delete OWNER REPO VERSION   # delete export file
```

**Demo scenario:** Export a CIEL version, check status, download the JSON, inspect it with `jq`.

#### 1b. Reference Resolution (`$resolveReference`)

Resolve canonical URLs or relative references to repository definitions. Essential for FHIR interop.

**API endpoint:**
- `POST /$resolveReference/` — resolve one or more references (batch supported)

**Proposed CLI commands:**
```bash
ocl resolve URL...                          # resolve one or more canonical URLs
ocl resolve --namespace /orgs/WHO/ URL...   # resolve with namespace context
```

**Demo scenario:** Resolve a FHIR canonical URL to its OCL source, resolve a relative reference within an org namespace.

---

### Phase 2: Bulk Import

High priority for automation — currently the only way to bulk-load content is via the API directly.

**API endpoints:**
- `POST /importers/bulk-import/` — submit bulk import (standard queue, parallel)
- `POST /importers/bulk-import/:queue/` — submit to named queue (sequential)
- `GET /importers/bulk-import/` — list active/recent imports
- `GET /importers/bulk-import/:queue/` — list imports in specific queue
- `DELETE /importers/bulk-import/?task_id=:taskId&signal=SIGKILL` — cancel import
- `GET /manage/bulkimport/?task=:taskId&result=json` — get import results

**Proposed CLI commands:**
```bash
ocl import FILE [--queue QUEUE]             # submit import from JSON file
ocl import --stdin [--queue QUEUE]          # submit from stdin (pipe-friendly)
ocl import list [--queue QUEUE]             # list active imports
ocl import status TASK_ID                   # get import status/results
ocl import cancel TASK_ID                   # cancel running import
```

**Demo scenario:** Create a small JSON import file with a few concepts and mappings, submit it, poll for completion, verify the imported content.

---

### Phase 3: Expand `$match` Operation

Current support covers basic semantic matching with concept-class filtering and inline mappings. The API supports additional capabilities.

#### 3a. Additional match filters (#18, #4)

**Not yet exposed in CLI:**
- `--property KEY=VALUE` filter for custom source properties (#18)
- Replace hardcoded `--concept-class` / `--datatype` with FHIR-compatible property and filter params (#4)
- `--locale` filter for locale-specific matching
- `--encoder-model` to specify embedding model
- `--reranker` flag to enable reranking

**Proposed additions to `ocl concept match`:**
```bash
ocl concept match TERM --target-source CIEL --datatype "N/A" --locale en
ocl concept match TERM --target-source CIEL --property "level=1"
```

#### 3b. Match configuration

**Not yet exposed:**
- `map_config` — mapping-based matching configuration
- `target_repo` — alternative to `target_repo_url` (structured repo params)
- `--num-candidates` / `--k-nearest` — tune vector search parameters

#### 3c. Graceful semantic search fallback (#43)

When the API returns 400 "This repo version does not support semantic search", the CLI should auto-fall back to keyword search with a warning, or suggest `--no-semantic` / a released `--repo-version`.

**Demo scenario:** Match with locale filter, match with property filter, compare semantic vs keyword-only results.

---

### Phase 4: FHIR Operations

Lower priority for CLI (these are typically used via FHIR clients), but valuable for testing and interop validation.

#### 4a. `$translate` (ConceptMap)
```bash
ocl fhir translate --system SYSTEM --code CODE --url CONCEPT_MAP_URL
```

#### 4b. `$lookup` (CodeSystem)
```bash
ocl fhir lookup --system SYSTEM --code CODE
```

#### 4c. `$validate-code` (CodeSystem + ValueSet)
```bash
ocl fhir validate-code --system SYSTEM --code CODE [--url VALUESET_URL]
```

#### 4d. `$expand` (ValueSet)
```bash
ocl fhir expand --url VALUESET_URL [--filter TEXT]
```

**Demo scenario (new Theme 08):** End-to-end FHIR workflow — look up a code, translate it via a concept map, validate it against a value set, expand a value set.

---

### Phase 5: Remaining CRUD Gaps

Lower priority — fill in missing operations for completeness.

#### 5a. Name & Description Management
- `concept name-update` / `concept name-del`
- `concept description-update` / `concept description-del`

#### 5b. User & Org Command Refactor (#5, #6, #7)
- Implement `ocl user` command group: `user get`, `user search` (#5)
- Implement `ocl org` command group: `org get`, `org search`, `org create`, `org delete`, `org update`, `org members`, `org member-add`, `org member-remove` (#6)
- Remove `ocl owner` command group after `user` and `org` are complete (#7 — blocked on #5, #6)

#### 5c. External Concept & Mapping UX (#24, #28)
- Improve 404 error message for external concepts — detect external sources and explain that only the code is stored in OCL (#28)
- Indicate whether mapping targets are resolvable or external-only in `concept get --include-mappings` and `mapping search` output (#24)

#### 5d. Concept Cloning
```bash
ocl concept clone OWNER SOURCE CONCEPT_ID --to-source DEST_SOURCE [--cascade]
```

#### 5e. Expansion Creation
```bash
ocl expansion create OWNER COLLECTION VERSION [--filter TEXT] [--count N] [--offset N]
```
Currently only `expansion list` and `expansion get` exist. The create/trigger operation is missing.

#### 5f. URL Registry
```bash
ocl url-registry list [--owner OWNER]
ocl url-registry lookup URL [--namespace NAMESPACE]
ocl url-registry create --url URL --repo-url REPO_URL
```

#### 5g. Mapping Suggest & Bulk Map
The original plan included AI-powered mapping operations:
- `mapping suggest TERMS... --target-source SRC` — AI mapping suggestions
- `mapping bulk-map --input FILE --target-source SRC` — bulk mapping from file

These depend on whether the API supports dedicated suggest/bulk-map endpoints beyond `$match`. Investigate API surface before implementing.

#### 5h. CLI Ergonomics
- `--all` flag for auto-pagination (fetch all pages automatically)
- Shell completions via Click's built-in support (`ocl --install-completion`)
- Pipe detection: auto-enable `--json` when stdout is not a TTY

**Demo scenario:** Add to existing Themes 02/03 for name/description management; new Theme for org membership and URL registry.

---

## Demo Suite Expansion

Each phase should add demo coverage. Proposed new themes:

| Phase | Demo Addition |
|---|---|
| 1 | **Theme 08: Export & Resolution** — export a version, resolve canonical URLs |
| 2 | **Theme 09: Bulk Import** — create import file, submit, verify |
| 3 | Expand Theme 05 with additional match filter scenarios |
| 4 | **Theme 10: FHIR Operations** — translate, lookup, validate, expand |
| 5 | Expand Themes 02–04 with name/desc update/delete, expansion create, org membership; expand Theme 07 with auto-pagination and pipe detection |

## Sequencing Summary

| Phase | Scope | Tickets | Priority | Depends On |
|---|---|---|---|---|
| 1 | Export + $resolveReference | — | **High** | — |
| 2 | Bulk Import | — | **High** | Phase 1 (export for round-trip testing) |
| 3 | Expand $match | #4, #18, #43 | **Medium** | — |
| 4 | FHIR Operations | — | **Medium** | — |
| 5 | CRUD Gaps + UX | #5, #6, #7, #24, #28 | **Low** | #5 before #7 |
