# QA Deep Dive Findings

Ongoing log of observations, open questions, and potential improvements found during the systematic demo walkthrough.

## Open Questions (resolved)

### Table column width cap (60 chars) — accepted

`format_table` caps all columns at 60 characters. Only triggers with artificially long org/source names (e.g. `ocl-cli-sandbox`). Real-world expressions (CIEL, MSF-OCB, WHO) are 35-44 chars — well under the cap. Leave as-is; `-j` gives full data when needed.

### `--from-concept` filter inconsistent on scoped endpoints — #61

Filed as [#61](https://gitea.lab.jpayne.me/ocl/ocl-cli/issues/61). `fromConcept` works for some concepts on scoped endpoints but not others (e.g. 138041 works, 116128 doesn't). Global endpoint works for all. Likely an API/indexing issue. Workaround: omit `--owner`/`--repo` to use the global endpoint.

### `Type` column empty for newly created repos — accepted

API behavior. `source_type`/`collection_type` are null when not set during creation. Not a CLI fix.

### Duplicate concept IDs in search results — accepted

API/indexing issue. CLI shows what the API returns — no client-side deduplication.

## Bugs Fixed

### Group 1 (Demos 01 + 03)


| Bug                                 | Command                                         | Issue                                                             | Fix                                                                                      |
| ----------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Pagination counts wrong             | All list commands                               | `_normalize()` set count=len(page), discarding `num_found` header | Added `_get_list()` method that preserves response headers                               |
| Endpoint scoping                    | `repo list`, `concept search`, `mapping search` | Used global endpoints with redundant owner params                 | Scoped to `/orgs/X/repos/`, removed redundant params                                     |
| Repo list verbose broken            | `repo list --verbose`                           | Formatter called without `verbose=`                               | Pass via lambda                                                                          |
| Repo list concepts column           | `repo list`                                     | `active_concepts` field doesn't exist in API                      | Removed column                                                                           |
| Concept search source empty         | `concept search`                                | Used `source_url` (doesn't exist), not `source`                   | Use `source` field with `source_url` fallback                                            |
| Concept search description empty    | `concept search --verbose`                      | Read `description` (string), API has `descriptions` (array)       | Extract from `descriptions[0].description`                                               |
| Concept names no verbose            | `concept names`                                 | Missing `--verbose` flag                                          | Added flag, shows `external_id` column                                                   |
| `ref add --cascade` ignored         | `ref add`                                       | `params` dict built but not passed to `put()`                     | Added `params` to `put()` method                                                         |
| `expansion get` no formatter        | `expansion get`                                 | `format_expansion_detail` existed but wasn't wired                | Imported and wired                                                                       |
| Org/user list verbose broken        | `org list`, `user list`, etc.                   | Formatters called without `verbose=`                              | Pass via lambda, added verbose columns                                                   |
| Missing pagination everywhere       | Version list, reference list, task list         | No `format_pagination` call                                       | Added page/limit params and pagination display                                           |
| Version list description column     | `repo versions`                                 | API doesn't return description                                    | Removed column                                                                           |
| Repo detail phantom counts          | `repo get`                                      | `active_concepts`/`active_mappings` always null                   | Show conditionally                                                                       |
| Mapping detail field names          | `mapping get`                                   | Wrong date/name/source fields                                     | Use fallbacks: `source`/`source_url`, `from_concept_name_resolved`, `version_created_on` |
| Expansion/reference phantom columns | `expansion list`, `ref list`                    | `concepts`/`mappings` counts don't exist in API                   | Removed; added `Processing` to expansions                                                |


### Group 2 (Demos 02 + 04)


| Bug                                | Command                   | Issue                    | Fix                                         |
| ---------------------------------- | ------------------------- | ------------------------ | ------------------------------------------- |
| `concept name-add` raw JSON output | `concept name-add`        | No formatter             | Added inline formatter showing confirmation |
| `concept description-add` raw JSON | `concept description-add` | No formatter             | Added inline formatter                      |
| `concept descriptions` no verbose  | `concept descriptions`    | Missing `--verbose` flag | Added flag, shows `external_id` column      |
| `ref add` raw JSON output          | `ref add`                 | No formatter             | Added formatter showing count               |
| `ref remove` double output         | `ref remove`              | Printed JSON + echo      | Removed JSON output, keep echo only         |


### Write-Op Testing (Staging Sandbox)


| Bug                                     | Command                         | Issue                                                     | Fix                                                                        |
| --------------------------------------- | ------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------- |
| Concept detail source empty             | `concept get`, `concept create` | Used `_source_from_url(source_url)`, API returns `source` | Use `source` with `source_url` fallback                                    |
| Concept detail phantom description      | `concept get`                   | Showed `Description:` line, field is always null          | Removed line                                                               |
| `concept create` fails without datatype | `concept create`                | API requires `datatype`, no CLI default                   | Default to `"N/A"`                                                         |
| Concept version list wrong format       | `concept versions`              | Showed concept ID as version, no dates/comments           | Detect concept vs repo versions, show version number + comment + timestamp |


### Group 3 (Demos 05 + 06)


| Bug                     | Command                   | Issue                                                    | Fix                                                          |
| ----------------------- | ------------------------- | -------------------------------------------------------- | ------------------------------------------------------------ |
| Match verbose not wired | `concept match --verbose` | Formatter called without `verbose=`; no extra info shown | Pass verbose; show concept class + algorithm in verbose mode |


**No issues found in Demo 06** — task list, task list --verbose, task list --state FAILURE, task get all work correctly with proper pagination.

### Group 4 (Demos 00 + 07)

**No bugs found.** All validated:

- Server add/use/remove/list — correct
- whoami — correct
- Exit codes: 0 (success), 1 (404), 3 (auth error) — all correct
- JSON output: valid for concept search, concept get, cascade, match, repo list, org get, task list, mapping search
- `--show-request`: correct endpoints for all command types (GET and POST)
- `--debug`: shows full URL + request body for POST operations
- `reference --json`: returns 78 commands
- `--token` is a global option (must come before subcommand) — demo 07 doc has correct placement

### Demo doc corrections needed


| Demo | Line | Issue                                                                                  |
| ---- | ---- | -------------------------------------------------------------------------------------- |
| 00   | 0.3  | `ocl -j owner get CIEL` → should be `ocl -j org get CIEL` (owner command removed)      |
| 00   | 0.3  | `ocl concept get NONEXISTENT SOURCE 999` → works, exits 1 correctly                    |
| 07   | 7.2  | `--token BADTOKEN` must come before subcommand: `ocl --token BADTOKEN concept get ...` |


