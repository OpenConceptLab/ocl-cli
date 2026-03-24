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
