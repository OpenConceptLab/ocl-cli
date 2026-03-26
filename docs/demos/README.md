# OCL CLI Integration Demo Suite

Structured demo scenarios for validating the OCL CLI before community release. Each theme is self-contained and exercises a different area of the CLI.

| # | Theme | Write Ops? | Production Safe? |
|---|-------|-----------|-----------------|
| [00](00-getting-started.md) | Getting Started — Auth & Server Management | Config only | Yes |
| [01](01-content-exploration.md) | Content Exploration — Search, Match, Cascade | No | Yes |
| [02](02-content-authoring.md) | Content Authoring — Concept & Mapping CRUD | Yes | Needs sandbox |
| [03](03-repository-lifecycle.md) | Repository Lifecycle — Sources, Versioning & Exports | Yes | Needs sandbox |
| [04](04-collection-curation.md) | Collection Curation — References & Expansions | Yes | Needs sandbox |
| [05](05-ai-terminology.md) | AI-Powered Terminology Workflows | No | Yes |
| [06](06-operations.md) | Operations & Task Management | 6.2 only | Mostly |
| [07](07-agent-readiness.md) | Agent & Automation Readiness | No | Yes |

**Run order:** 00 first (establishes auth), then any theme independently. For write-operation themes (02-04), run 03 first to create the test source, then 02, then 04.
