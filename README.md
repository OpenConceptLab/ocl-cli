# OCL CLI

Command-line interface for the [Open Concept Lab](https://openconceptlab.org) API. Search, browse, and manage medical terminology — concepts, mappings, sources, and collections — from your terminal.

Designed for both humans and AI agents.

## Installation

### From source (recommended for now)

```bash
git clone https://github.com/OpenConceptLab/ocl-cli.git
cd ocl-cli
pip install .
```

### For development

```bash
git clone https://github.com/OpenConceptLab/ocl-cli.git
cd ocl-cli
pip install -e ".[dev]"
```

### Verify installation

```bash
ocl --version
ocl --help
```

## Quick Start

### 1. Browse without authentication

Many OCL resources are public. You can search and browse without logging in:

```bash
# Search for organizations
ocl owner search WHO

# Search for sources
ocl repo list --owner CIEL --type source

# Search for concepts
ocl concept search malaria --owner CIEL --source CIEL

# Get a specific concept
ocl concept get CIEL CIEL 116128

# Search for mappings
ocl mapping search --owner CIEL --source CIEL --from-concept 116128
```

### 2. Authenticate for write operations

To create or modify resources, you need an API token from [app.openconceptlab.org](https://app.openconceptlab.org):

```bash
# Store your token (prompts securely)
ocl login

# Verify authentication
ocl whoami
```

Or pass a token directly:

```bash
ocl --token YOUR_TOKEN whoami
```

Or set an environment variable:

```bash
export OCL_API_TOKEN=your_token_here
ocl whoami
```

### 3. JSON output for scripting and agents

Use the `-j` flag (before the subcommand) for machine-readable JSON output:

```bash
ocl -j concept search malaria --owner CIEL --source CIEL
ocl -j concept get CIEL CIEL 116128
```

### 4. Verbose vs summary output

Search/list commands return a **summary** by default (compact, fast). Use `--verbose` to get **full details** (names, descriptions, extras, timestamps):

```bash
# Summary (default)
ocl concept search malaria --owner CIEL --source CIEL

# Verbose — more columns, more data from API
ocl concept search malaria --owner CIEL --source CIEL --verbose

# Debug — show HTTP requests on stderr
ocl -d concept search malaria --owner CIEL --source CIEL
```

The `--verbose` flag controls the OCL API's `?verbose=true` parameter. With `-j`, it returns more fields in the JSON response.

## Commands

### Owners (users & organizations)

```bash
ocl owner search [QUERY] [--owner-type users|orgs|all]
ocl owner get OWNER [--owner-type users|orgs]
ocl owner members ORG
```

### Repositories (sources & collections)

Sources and collections are unified under `ocl repo` with a `--type` flag.

```bash
# Browse
ocl repo list [QUERY] [--owner OWNER] [--type source|collection|all]
ocl repo get OWNER REPO [--type source|collection] [--version VERSION]
ocl repo versions OWNER REPO [--type source|collection]

# Create & update (requires auth)
ocl repo create OWNER REPO_ID NAME --type source|collection [options]
ocl repo update OWNER REPO [--name NAME] [--description DESC]
ocl repo version-create OWNER REPO VERSION_ID [--released/--no-released]

# Custom attributes
ocl repo extras OWNER REPO
ocl repo extra-set OWNER REPO KEY VALUE
ocl repo extra-del OWNER REPO KEY
```

### Concepts

```bash
# Search & browse
ocl concept search [QUERY] [--owner OWNER] [--source SOURCE] [--concept-class CLASS]
ocl concept get OWNER SOURCE CONCEPT_ID [--version VERSION] [--concept-version CVER]
ocl concept versions OWNER SOURCE CONCEPT_ID
ocl concept names OWNER SOURCE CONCEPT_ID
ocl concept descriptions OWNER SOURCE CONCEPT_ID
ocl concept extras OWNER SOURCE CONCEPT_ID

# Create & update (requires auth)
ocl concept create OWNER SOURCE CONCEPT_ID --concept-class CLASS --name NAME
ocl concept update OWNER SOURCE CONCEPT_ID [--concept-class CLASS] [--datatype TYPE]
ocl concept retire OWNER SOURCE CONCEPT_ID
ocl concept name-add OWNER SOURCE CONCEPT_ID NAME --locale LOCALE
ocl concept description-add OWNER SOURCE CONCEPT_ID TEXT --locale LOCALE
ocl concept extra-set OWNER SOURCE CONCEPT_ID KEY VALUE
ocl concept extra-del OWNER SOURCE CONCEPT_ID KEY

# Intelligent matching
ocl concept match TERM... --target-source SOURCE [--target-owner OWNER] [--target-version VER]
```

### Mappings

```bash
# Search & browse
ocl mapping search [QUERY] [--owner OWNER] [--source SOURCE] [--map-type TYPE]
ocl mapping get OWNER SOURCE MAPPING_ID [--version VERSION]
ocl mapping versions OWNER SOURCE MAPPING_ID

# Create & update (requires auth)
ocl mapping create OWNER SOURCE --map-type TYPE --from-concept-url URL --to-concept-url URL
ocl mapping update OWNER SOURCE MAPPING_ID [--map-type TYPE]
ocl mapping retire OWNER SOURCE MAPPING_ID
```

### Cascade

Navigate concept hierarchies and related mappings:

```bash
ocl cascade OWNER REPO CONCEPT_ID [--version VERSION] [--levels N] [--reverse]
```

### Collection References

```bash
ocl ref list OWNER COLLECTION [--version VERSION]
ocl ref add OWNER COLLECTION EXPRESSION... [--cascade sourcemappings|sourcetoconcepts]
ocl ref remove OWNER COLLECTION EXPRESSION...
```

### Expansions

```bash
ocl expansion list OWNER COLLECTION VERSION
ocl expansion get OWNER COLLECTION [--version VERSION] [--expansion-id ID]
ocl expansion create OWNER COLLECTION VERSION
```

### Server Management

OCL CLI supports multiple OCL server environments:

```bash
# List configured servers
ocl server list

# Add a custom server
ocl server add my-server https://api.my-ocl.org --name "My OCL Server"

# Switch default server
ocl server use ocl-dev

# Use a specific server for one command
ocl -s ocl-qa concept search malaria
```

**Pre-configured servers:** `ocl-prod` (default), `ocl-dev`, `ocl-qa`, `ocl-staging`

## Versioning

OCL resources are versioned. Use `--version` to access specific versions:

```bash
# Get latest released version of a source
ocl repo get CIEL CIEL --version latest

# Get a named version
ocl repo get CIEL CIEL --version v2026-01-26

# Get a concept as it existed in a specific source version
ocl concept get CIEL CIEL 116128 --version v2026-01-26

# Omit --version to get HEAD (working draft)
ocl concept get CIEL CIEL 116128
```

## Configuration

Config is stored at `~/.ocl/config.json`. It's created automatically on first use.

### Token resolution order

1. `--token` CLI flag
2. `OCL_API_TOKEN` environment variable
3. Server-specific env var (e.g. `OCL_API_TOKEN_PROD`)
4. Token stored via `ocl login`

### Server resolution order

1. `--server` / `-s` CLI flag
2. `OCL_SERVER` environment variable
3. `default_server` in config file

## Agent Integration

The CLI is designed for use by AI agents via subprocess calls. Key features:

- **`-j` flag** outputs structured JSON on stdout
- **Exit codes**: 0 = success, 1 = client error, 2 = server error, 3 = auth error
- **Errors go to stderr**, data goes to stdout
- **Non-interactive**: all parameters via flags/args (except `ocl login`)

Example agent usage:

```bash
# Search and parse results
ocl -j concept search "diabetes" --owner CIEL --source CIEL --limit 10

# Get a specific concept
ocl -j concept get CIEL CIEL 116128

# Create a mapping (with token via env var)
OCL_API_TOKEN=xxx ocl -j mapping create MYORG MYSOURCE \
  --map-type SAME-AS \
  --from-concept-url /orgs/CIEL/sources/CIEL/concepts/116128/ \
  --to-concept-url /orgs/WHO/sources/ICD-10-WHO/concepts/B54/
```

## Requirements

- Python 3.10+
- Dependencies: click, httpx, tenacity, python-dotenv
