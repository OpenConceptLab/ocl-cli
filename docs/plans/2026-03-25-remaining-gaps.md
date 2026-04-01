# OCL CLI — Remaining Feature Gaps

**Date:** 2026-03-25
**Status:** Planning
**Ticket:** [ocl/ocl-cli:#52 - Remaining CLI feature gaps (export, bulk import, FHIR ops, match expansion)](https://gitea.lab.jpayne.me/ocl/ocl-cli/issues/52)

## Status Summary

| Item | Description | Status | Ticket |
|------|-------------|--------|--------|
| 1a | Repo export | **Done** | [#60](https://gitea.lab.jpayne.me/ocl/ocl-cli/issues/60) |
| 1b | Reference resolution (`$resolveReference`) | Not started | — |
| 2 | Bulk import | **Done** | [ocl_issues#2443](https://github.com/OpenConceptLab/ocl_issues/issues/2443) |
| 3a | Additional match filters | Not started | #18, #4 |
| 3b | Match configuration | Not started | — |
| 3c | Semantic search fallback | Not started | #43 |
| 4a | FHIR `$translate` | Not started | — |
| 4b | FHIR `$lookup` | Not started | — |
| 4c | FHIR `$validate-code` | Not started | — |
| 4d | FHIR `$expand` | Not started | — |
| 5a | Name & description management | Not started | — |
| 5b | User & org command refactor | **Done** | #5, #6, #7 |
| 5c | External concept & mapping UX | Not started | #24, #28 |
| 5d | Concept cloning | Not started | — |
| 5e | Expansion creation | Not started | — |
| 5f | URL registry | Not started | — |
| 5g | Mapping suggest & bulk map | Not started | — |
| 5h | CLI ergonomics | Not started | — |

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

#### 1a. Repository Export (`$export`) — Done

Implemented in [#60](https://gitea.lab.jpayne.me/ocl/ocl-cli/issues/60) as `ocl repo export` subcommand group:

```bash
ocl repo export status OWNER REPO VERSION --type source|collection
ocl repo export create OWNER REPO VERSION --type source|collection
ocl repo export download OWNER REPO VERSION --type source|collection -o FILE
ocl repo export delete OWNER REPO VERSION --type source|collection
```

Demo coverage added to Theme 03 (Repository Lifecycle, section 3.6).

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

### Phase 2: Bulk Import — Done

Implemented in [ocl_issues#2443](https://github.com/OpenConceptLab/ocl_issues/issues/2443) as `ocl import` subcommand group:

```bash
ocl import file FILE [--queue QUEUE] [--no-update] [--parallel N] [--wait]
ocl import status TASK_ID [--wait]
ocl import list [--queue QUEUE]
```

Supports all server-side file formats: JSON/JSONL (.json, .jsonl), CSV (.csv), and OCL export ZIP (.zip). File upload via multipart form-data to `/importers/bulk-import/`.

**Not yet implemented:** `ocl import --stdin` (pipe from stdin), `ocl import cancel TASK_ID`. Demo coverage (Theme 09) not yet added.

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

#### 5b. User & Org Command Refactor (#5, #6, #7) — **Done**

- ~~Implement `ocl user` command group: `user list`, `user get`, `user repos`, `user orgs` (#5)~~
- ~~Implement `ocl org` command group: `org list`, `org get`, `org create`, `org delete`, `org members`, `org repos`, `org add-member`, `org remove-member` (#6)~~
- ~~Remove `ocl owner` command group (#7)~~

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


| Phase | Demo Addition                                                                                                                               |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | **Theme 08: Export & Resolution** — export a version, resolve canonical URLs                                                                |
| 2     | **Theme 09: Bulk Import** — create import file, submit, verify                                                                              |
| 3     | Expand Theme 05 with additional match filter scenarios                                                                                      |
| 4     | **Theme 10: FHIR Operations** — translate, lookup, validate, expand                                                                         |
| 5     | Expand Themes 02–04 with name/desc update/delete, expansion create, org membership; expand Theme 07 with auto-pagination and pipe detection |


## Sequencing Summary


| Phase | Scope                      | Tickets              | Priority   | Depends On                              |
| ----- | -------------------------- | -------------------- | ---------- | --------------------------------------- |
| 1     | Export + $resolveReference | —                    | **High**   | —                                       |
| 2     | Bulk Import                | —                    | **High**   | Phase 1 (export for round-trip testing) |
| 3     | Expand $match              | #4, #18, #43         | **Medium** | —                                       |
| 4     | FHIR Operations            | —                    | **Medium** | —                                       |
| 5     | CRUD Gaps + UX             | #5, #6, #7, #24, #28 | **Low**    | #5 before #7                            |


