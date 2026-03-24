# Theme 7: Agent & Automation Readiness

Verify the CLI works well as a backend for AI agents and scripts.

## 7.1 JSON Output for Programmatic Consumption
```bash
# Every command should produce valid, parseable JSON with -j
ocl -j concept search malaria --owner CIEL --repo CIEL --limit 2 | python -m json.tool
ocl -j concept get CIEL CIEL 116128 --include-mappings | python -m json.tool
ocl -j cascade Regenstrief LOINC 2345-7 --levels 1 --cascade-hierarchy --no-cascade-mappings --reverse | python -m json.tool
ocl -j concept match "malaria" --target-source CIEL --limit 1 | python -m json.tool
```

## 7.2 Exit Code Contract
```bash
ocl concept get CIEL CIEL 116128; echo "Exit: $?"          # 0 — success
ocl concept get CIEL CIEL NONEXISTENT; echo "Exit: $?"     # 1 — 404 client error
ocl concept get CIEL CIEL 116128 --token BADTOKEN; echo "Exit: $?"  # 3 — auth error
```

## 7.3 Command Reference for Agent Discovery
```bash
ocl reference --json | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['commands']), 'commands')"
```

## 7.4 Debug Output for Troubleshooting
```bash
ocl -d concept match "malaria" --target-source CIEL --limit 1  # shows POST URL + body on stderr
```

**Validates:** JSON output validity, exit code contract, reference command for agent use, debug output.
