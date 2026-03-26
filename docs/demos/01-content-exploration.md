# OCL CLI Integration Demos

Multi-step CLI scenarios that exercise real-world workflows against the production OCL API. Each builds on the previous in complexity and serves as both a demo and an integration test.

## Demo 1: Explore an Organization and Its Concepts

**Scenario:** Profile the CIEL organization, browse its repositories, then deep-dive on a single concept — translations, description, and cross-terminology mappings.

**Steps:**
1. `ocl org get CIEL` — org profile
2. `ocl org repos CIEL` — sources and collections owned by CIEL
3. `ocl concept search malaria --owner CIEL --repo CIEL` — find a concept
4. `ocl concept names CIEL CIEL 116128` — all translations (11 names across 9 languages)
5. `ocl mapping search --owner CIEL --repo CIEL --from-concept 138041 --verbose` — outbound mappings with target source display
6. `ocl mapping get CIEL CIEL 162820` — full detail showing from/to source URLs and codes

**Validates:** org lookup, org repo listing, concept search, name listing, mapping search with target source display, mapping detail.

---

## Demo 2: AI-Powered Term Matching + Verification

**Scenario:** A clinic submits raw clinical terms. Use OCL's `$match` endpoint (semantic search enabled by default) to find CIEL equivalents, then verify each top match has external terminology mappings.

**Steps:**
1. `ocl concept match "malaria" "diabetes" "headache" --target-source CIEL --limit 3` — semantic match
2. For each top hit: `ocl concept get CIEL CIEL <id> --include-mappings` — verify cross-terminology coverage
3. Assess results: all three terms should match with high confidence and have mappings to ICD-10, ICD-11, SNOMED, and other systems

**Expected results:**

| Term | Match | Key Mappings |
|---|---|---|
| malaria | 116128 Malaria | ICD-10 B54, ICD-11 1F4Z, SNOMED 61462000 |
| diabetes | 119481 Diabetes mellitus | ICD-10 E14.9, ICD-11 5A14, SNOMED 73211009 |
| headache | 139084 Headache | ICD-10 R51, ICD-11 MB6Y, SNOMED 25064002 |

**Validates:** `$match` with semantic search, `--include-mappings` rendering on concept get, match-then-verify workflow.

---

## Demo 3: Cross-Terminology Rosetta Stone

**Scenario:** Starting from CIEL's Malaria concept, trace it across every external terminology it maps to and build a cross-reference table.

**Steps:**
1. `ocl concept get CIEL CIEL 116128 --include-mappings` — anchor concept with all outbound mappings in one call
2. `ocl concept get WHO ICD-10-WHO B54` — resolve the ICD-10 target (one of few with imported concepts)
3. `ocl concept get PIH PIH 123` — resolve the PIH target

**Expected cross-reference:**

| Terminology | Code | Map Type | Resolvable? |
|---|---|---|---|
| CIEL | 116128 | (anchor) | Yes |
| WHO/ICD-10-WHO | B54 | SAME-AS | Yes — "Unspecified malaria" |
| WHO/ICD-11-WHO | 1F4Z | SAME-AS | No — external source, no imported concepts |
| IHTSDO/SNOMED-CT | 61462000 | SAME-AS | No — external source |
| WICC/ICPC2 | A73 | NARROWER-THAN | No — external source |
| IMO/IMO-ProblemIT | 28660 | SAME-AS | No — external source |
| PIH/PIH | 123 | SAME-AS | Yes — "Malaria" |
| AMPATH/AMPATH | 906, 123 | SAME-AS | No — 404 |

**Key finding:** `concept get --include-mappings` collapses this demo to essentially one command. Most external terminologies are empty shells in OCL (mapping targets only, no imported concepts), so resolving them returns 404s.

**Validates:** `--include-mappings` with target source labels, cross-source concept resolution, understanding external vs hosted sources.

---

## Demo 4: Cascade Exploration — Concept Neighborhood

Two sub-scenarios showing different cascade strengths.

### 4a: CIEL Concept Graph Walk (reverse cascade + CONCEPT-SET traversal)

**Scenario:** Start from "Diabetes mellitus" in CIEL. Use forward and reverse cascade to discover how this concept relates to others.

**Steps:**
1. `ocl concept search "diabetes mellitus" --owner CIEL --repo CIEL` — find root (119481)
2. `ocl cascade CIEL CIEL 119481 --levels 1 --cascade-mappings` — forward cascade shows Q-AND-A links to Yes/No/Unknown and cross-terminology mappings
3. `ocl cascade CIEL CIEL 119481 --levels 1 --cascade-mappings --reverse --no-cascade-hierarchy` — **reverse cascade** reveals that Diabetes belongs to "Nutritional, endocrine and metabolic diagnoses" (160180) via CONCEPT-SET
4. `ocl concept get CIEL CIEL 160180 --include-mappings` — inspect the ConvSet
5. `ocl cascade CIEL CIEL 160180 --levels 1 --cascade-mappings --map-types "CONCEPT-SET" --no-cascade-hierarchy` — cascade from ConvSet to see all 11 sibling diagnoses (Kwashiorkor, Marasmus, DM Type 2, etc.)

**Key finding:** Forward cascade from Diabetes was limited (mappings point to external terminologies). **Reverse cascade** was the breakthrough — it revealed the clinical grouping. `--map-types` filtering was essential to follow only CONCEPT-SET relationships.

### 4b: LOINC Hierarchy Navigation (tree view + verbose)

**Scenario:** Navigate LOINC's multi-level hierarchy starting from a lab test code, walking up to the category level and back down.

**Steps:**
1. `ocl concept search "glucose" --owner Regenstrief --repo LOINC --limit 5` — find LOINC 2345-7 "Glucose [Mass/volume] in Serum or Plasma"
2. `ocl cascade Regenstrief LOINC 2345-7 --levels 3 --cascade-hierarchy --no-cascade-mappings --reverse` — walk **up** the hierarchy (tree view is now the default)

   ```
   2345-7 - Glucose [Mass/volume] in Serum or Plasma
   └── LP385540-2 - Glucose | Serum or Plasma | Chemistry - non-challenge
       └── LP14635-4 - Glucose
           ├── LP31399-6 - Sugars/Sugar metabolism
           ├── LP234174-3 - Chemistry - routine challenge
           ├── LP40317-7 - Analytes
           └── LP65098-3 - Sugar
   ```

3. `ocl cascade Regenstrief LOINC LP65098-3 --levels 1 --cascade-hierarchy --no-cascade-mappings --verbose` — siblings of Glucose under "Sugar"

   ```
   LP65098-3 - Sugar [LOINC Part]
   ├── LP14635-4 - Glucose [LOINC Part]
   ├── LP15263-4 - Galactose [LOINC Part]
   ├── LP15269-1 - Lactose [LOINC Part]
   ├── LP173648-9 - Lactulose [LOINC Part]
   ├── LP392439-8 - Sugar | Dose | Drug doses [LOINC Part (Multiaxial)]
   └── LP14638-8 - Xylose [LOINC Part]
   ```

4. `ocl cascade Regenstrief LOINC LP14635-4 --levels 2 --cascade-hierarchy --no-cascade-mappings --verbose` — cascade **down** from Glucose to see all 813 descendants with concept class labels

**Validates:** hierarchy cascade (forward and reverse), tree view with box-drawing characters, `--verbose` showing concept_class/datatype, large cascade truncation (100 node cap), `--map-types` filtering, `--reverse` flag.
