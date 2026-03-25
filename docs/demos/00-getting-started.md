# Theme 0: Getting Started — Auth & Server Management

First-run experience. Can a new user configure the CLI, authenticate, and orient themselves?

## 0.1 Multi-Server Setup
```bash
ocl server list                                    # see defaults
ocl server add staging https://api.staging.openconceptlab.org --name "OCL Staging"
ocl server use staging                             # switch default
ocl server list                                    # verify default marker
ocl server use ocl-prod                            # switch back
ocl server remove staging                          # clean up
```

## 0.2 Authentication Flow
```bash
ocl whoami                                         # current user on default server
ocl login                                          # store token (interactive)
ocl whoami                                         # verify identity
ocl logout                                         # remove token
ocl whoami                                         # should fail (auth error, exit code 3)
ocl login                                          # re-authenticate for remaining demos
```

## 0.3 Global Flags
```bash
ocl -j owner get CIEL                             # JSON output for agent consumption
ocl -d concept search malaria --owner CIEL --repo CIEL --limit 1  # debug: show HTTP request + body
ocl concept get NONEXISTENT SOURCE 999; echo $?   # exit code 1 (client error)
```

**Validates:** server add/remove/use/list, login/logout/whoami, `--json`, `--debug`, exit codes.
