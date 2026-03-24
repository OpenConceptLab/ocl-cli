# Theme 4: Collection Curation — References & Expansions

Build a curated collection by adding concept/mapping references, then expand it.

## 4.1 Create a Collection
```bash
ocl repo create <OWNER> demo-collection "Demo Collection" --type collection \
  --description "Curated set for demo" --default-locale en
ocl repo get <OWNER> demo-collection --type collection
```

## 4.2 Add and Manage References
```bash
ocl ref add <OWNER> demo-collection \
  /orgs/CIEL/sources/CIEL/concepts/116128/ \
  /orgs/CIEL/sources/CIEL/concepts/139084/            # add Malaria + Headache
ocl ref list <OWNER> demo-collection                   # verify references
ocl ref add <OWNER> demo-collection \
  /orgs/CIEL/sources/CIEL/concepts/119481/ --cascade sourcemappings  # add Diabetes with mappings
ocl ref list <OWNER> demo-collection --limit 50        # see all refs including cascaded
ocl ref remove <OWNER> demo-collection \
  /orgs/CIEL/sources/CIEL/concepts/139084/             # remove Headache
ocl ref list <OWNER> demo-collection                   # verify removal
```

## 4.3 Version and Expand
```bash
ocl repo version-create <OWNER> demo-collection v1.0 --type collection --description "First cut"
ocl expansion list <OWNER> demo-collection v1.0        # list expansions
ocl expansion get <OWNER> demo-collection --version v1.0  # get default expansion details
```

**Validates:** collection create, ref add/remove/list with cascade, version-create, expansion list/get.
