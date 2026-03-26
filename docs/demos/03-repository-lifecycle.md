# Theme 3: Repository Lifecycle — Sources & Versioning

Create a source from scratch, populate it, snapshot versions, and manage releases.

## 3.1 Create and Configure a Source
```bash
ocl repo create <OWNER> demo-source "Demo Source" --type source \
  --description "Integration test source" \
  --default-locale en --supported-locales "en,fr,es" \
  --public-access View
ocl repo get <OWNER> demo-source                       # verify creation
ocl repo update <OWNER> demo-source --description "Updated description"
ocl repo get <OWNER> demo-source                       # verify update
```

## 3.2 Populate and Snapshot
```bash
# Create a few concepts (from Theme 2 pattern)
ocl concept create <OWNER> demo-source DEMO-001 --concept-class Diagnosis --name "Demo Concept A"
ocl concept create <OWNER> demo-source DEMO-002 --concept-class Procedure --name "Demo Concept B"
ocl repo version-create <OWNER> demo-source v1.0 --description "Initial release"
ocl repo versions <OWNER> demo-source                  # verify version exists
ocl repo get <OWNER> demo-source --repo-version v1.0    # inspect versioned snapshot
```

## 3.3 Manage Repository Extras
```bash
ocl repo extra-set <OWNER> demo-source maintainer "OCL Demo Team"
ocl repo extras <OWNER> demo-source                    # verify
ocl repo extra-del <OWNER> demo-source maintainer
```

## 3.4 Version Management
```bash
ocl repo version-update <OWNER> demo-source v1.0 --description "Initial release (updated)" --released
ocl repo versions <OWNER> demo-source --released true  # filter released versions
```

## 3.5 Organization CRUD
```bash
ocl owner create-org demo-org "Demo Organization"
ocl owner get demo-org                                # verify creation
ocl owner delete-org demo-org --yes                   # clean up
ocl owner get demo-org                                # verify 404
```

## 3.6 Version Exports

Full export lifecycle — check availability, trigger creation, download, and clean up.

```bash
# 1. Check if an export is available for the demo version
ocl repo export status <OWNER> demo-source v1.0 --type source
#    → "No export exists" (newly created version)

# 2. Trigger export creation
ocl repo export create <OWNER> demo-source v1.0 --type source
#    → "Export creation started"

# 3. Poll status until ready (may take a few seconds)
ocl repo export status <OWNER> demo-source v1.0 --type source
#    → "Export is currently being generated" or "Export is ready for download"

# 4. Check status with JSON output (useful for scripting)
ocl repo export status <OWNER> demo-source v1.0 --type source -j
#    → {"status": "ready", "status_code": 200, "filename": "..."}

# 5. Download the export to a local file
ocl repo export download <OWNER> demo-source v1.0 --type source -o demo-export.zip
#    → "Saved to demo-export.zip (N bytes)"

# 6. Delete the cached export
ocl repo export delete <OWNER> demo-source v1.0 --type source
#    → "Export deleted."

# 7. Verify it's gone
ocl repo export status <OWNER> demo-source v1.0 --type source
#    → "No export exists"
```

### Export with a real-world collection
```bash
# Works the same way for collections — just use --type collection
ocl repo export status MSF-OCB Aswan Aswan-V2-26 --type collection
ocl repo export download MSF-OCB Aswan Aswan-V2-26 --type collection -o aswan-export.zip
```

**Validates:** repo create/update/get, version-create/update, extras, versions with released filter, org create/delete, export status/create/download/delete.
