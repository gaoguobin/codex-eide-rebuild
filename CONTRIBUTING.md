# Contributing

## Development flow

1. Keep examples generic and sanitized.
2. Sync the runtime into the skill bundle.
3. Run unit tests and repository audits before opening a pull request.

## Local commands

```powershell
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## Pull requests

- Keep changes focused.
- Update documentation when behavior changes.
- Preserve JSON result and exit-code compatibility.
