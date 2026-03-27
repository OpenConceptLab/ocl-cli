# QA Sandbox Guide

Write-operation testing uses the **OCL Staging server** with a dedicated `ocl-cli-sandbox` org.

## Setup

### Token

Add to `.env` in the project root (gitignored):
```
OCL_API_TOKEN_STAGING=your-token-here
```

Source before running commands:
```bash
set -a && source .env && set +a
```

Verify: `ocl --server ocl-staging whoami`

### Create sandbox (if needed)

```bash
ocl --server ocl-staging org create ocl-cli-sandbox "OCL CLI QA Sandbox"
ocl --server ocl-staging repo create ocl-cli-sandbox ocl-cli-sandbox-source "Sandbox Source" \
  --type source --default-locale en --supported-locales "en,fr,es" --public-access View
ocl --server ocl-staging repo create ocl-cli-sandbox ocl-cli-sandbox-collection "Sandbox Collection" \
  --type collection --default-locale en
```

## Usage

All write commands use `--server ocl-staging` (global option, before subcommand):

```bash
ocl --server ocl-staging concept create ocl-cli-sandbox ocl-cli-sandbox-source TEST-001 \
  --concept-class Diagnosis --name "Test Fever" --name-locale en
```

## Teardown

```bash
ocl --server ocl-staging repo delete ocl-cli-sandbox ocl-cli-sandbox-collection --type collection --yes
ocl --server ocl-staging repo delete ocl-cli-sandbox ocl-cli-sandbox-source --yes
ocl --server ocl-staging org delete ocl-cli-sandbox --yes
```

## Notes

- Staging has a copy of prod data (CIEL, WHO, etc.) for read-only cross-referencing.
- Deleting a source/collection removes its concepts/mappings.
- `.env` is gitignored — tokens never committed.
