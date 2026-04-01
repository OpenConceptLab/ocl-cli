# Theme 6: Operations & Task Management

Monitor async operations and manage background tasks.

## 6.1 Task Monitoring
```bash
ocl task list                                          # list recent tasks
ocl task list --state FAILURE --verbose                # find failed tasks with details
ocl task get <TASK_ID>                                 # inspect a specific task
```

## 6.2 Bulk Operations via Collection Tool
```bash
# Export a collection, strip versions, and preview what would be reimported
ocl tool recreate-collection --input <export.json> --org <OWNER> --name <COLLECTION> --dry-run
# Execute (when ready)
ocl tool recreate-collection --input <export.json> --org <OWNER> --name <COLLECTION> --no-dry-run
```

**Validates:** task list/get with state filter and verbose, tool recreate-collection dry-run.

## 6.3 Bulk Import
```bash
# Submit a JSON Lines file for import
ocl import file sample-concepts.jsonl

# Submit an OCL export ZIP to a named queue, wait for completion
ocl import file ciel-export.zip --queue ciel-load --wait

# Submit a CSV file without updating existing resources
ocl import file new-mappings.csv --no-update

# Check import status
ocl import status <TASK_ID>

# List active/recent imports
ocl import list
```

**Validates:** import file with multiple formats (.jsonl, .zip, .csv), queue routing, --wait polling, status check, import list.
