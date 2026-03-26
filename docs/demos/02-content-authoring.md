# Theme 2: Content Authoring — Concept & Mapping CRUD

Full lifecycle of creating, enriching, and retiring terminology content.

**Prerequisite:** A test source to work in (created in Theme 3, or use an existing sandbox).

## 2.1 Create a Concept with Names and Descriptions
```bash
ocl concept create <OWNER> <SOURCE> TEST-001 \
  --concept-class Diagnosis --datatype "N/A" \
  --name "Test Fever" --name-locale en --name-type "Fully Specified"
ocl concept get <OWNER> <SOURCE> TEST-001              # verify creation
ocl concept name-add <OWNER> <SOURCE> TEST-001 "Fièvre test" --locale fr --name-type "Fully Specified"
ocl concept names <OWNER> <SOURCE> TEST-001             # verify both names
ocl concept description-add <OWNER> <SOURCE> TEST-001 "A test diagnosis for demo purposes" --locale en
ocl concept descriptions <OWNER> <SOURCE> TEST-001      # verify description
```

## 2.2 Manage Custom Attributes
```bash
ocl concept extra-set <OWNER> <SOURCE> TEST-001 icd_category "infectious"
ocl concept extra-set <OWNER> <SOURCE> TEST-001 severity '["mild","moderate","severe"]'  # JSON value
ocl concept extras <OWNER> <SOURCE> TEST-001            # verify both extras
ocl concept extra-del <OWNER> <SOURCE> TEST-001 severity
ocl concept extras <OWNER> <SOURCE> TEST-001            # verify deletion
```

## 2.3 Create a Mapping Between Concepts
```bash
ocl concept create <OWNER> <SOURCE> TEST-002 \
  --concept-class Diagnosis --name "Test Malaria"
ocl mapping create <OWNER> <SOURCE> \
  --map-type NARROWER-THAN \
  --from-concept-url /orgs/<OWNER>/sources/<SOURCE>/concepts/TEST-001/ \
  --to-concept-url /orgs/<OWNER>/sources/<SOURCE>/concepts/TEST-002/
ocl mapping search --owner <OWNER> --repo <SOURCE> --from-concept TEST-001 --verbose  # verify
```

## 2.4 Update and Retire
```bash
ocl concept update <OWNER> <SOURCE> TEST-001 --concept-class Finding --update-comment "Reclassified"
ocl concept get <OWNER> <SOURCE> TEST-001              # verify class changed
ocl concept versions <OWNER> <SOURCE> TEST-001          # see version history
ocl concept retire <OWNER> <SOURCE> TEST-002 --update-comment "Duplicate"
ocl concept get <OWNER> <SOURCE> TEST-002              # verify retired=True
ocl mapping update <OWNER> <SOURCE> <MAPPING_ID> --map-type NARROWER-THAN
ocl mapping get <OWNER> <SOURCE> <MAPPING_ID>          # verify map type changed
ocl mapping retire <OWNER> <SOURCE> <MAPPING_ID> --update-comment "Source concept retired"
```

**Validates:** concept create/update/retire, name-add, description-add, extra-set/del, mapping create/update/retire, versions.
