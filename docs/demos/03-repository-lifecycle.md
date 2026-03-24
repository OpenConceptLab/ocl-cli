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
ocl repo get <OWNER> demo-source --version v1.0        # inspect versioned snapshot
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

**Validates:** repo create/update/get, version-create/update, extras, versions with released filter.
