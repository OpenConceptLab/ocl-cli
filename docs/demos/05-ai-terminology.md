# Theme 5: AI-Powered Terminology Workflows

Advanced matching and verification workflows that showcase OCL's AI capabilities.

## 5.1 Batch Term Standardization
```bash
# Match a batch of clinical terms from a facility
ocl concept match "fever" "high blood pressure" "sugar disease" "TB" "fits" \
  --target-source CIEL --limit 3
```

## 5.2 Match with Concept Class Filtering (requires #17)
```bash
# Only match against Diagnosis concepts
ocl concept match "glucose" --target-source CIEL --concept-class Diagnosis --limit 5
# Compare: without filter returns lab tests and anatomy
ocl concept match "glucose" --target-source CIEL --limit 5
```

## 5.3 Match with Mapping Verification (requires #16)
```bash
# Match and see mapping coverage inline
ocl concept match "malaria" "diabetes" --target-source CIEL --include-mappings --limit 1
```

## 5.4 Cascade-Based Impact Analysis
```bash
# What would be affected if we retire "Diabetes mellitus"?
ocl cascade CIEL CIEL 119481 --levels 2 --cascade-mappings --reverse --verbose
# How many LOINC tests exist under a given analyte?
ocl cascade Regenstrief LOINC LP14635-4 --levels 2 --cascade-hierarchy --no-cascade-mappings --verbose
```

**Note:** Workflows 5.2 and 5.3 depend on open tickets #17 and #16 respectively. Run after those are implemented.

**Validates:** semantic match, concept-class filtering (future), match + mappings (future), cascade as impact analysis.
