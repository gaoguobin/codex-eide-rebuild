# Contributing

## Development flow

1. Keep examples generic and sanitized.
2. Build the bridge VSIX after bridge changes.
3. Sync the runtime into the skill bundle.
4. Run unit tests and repository audits before opening a pull request.

## Local commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\bridge\build-vsix.ps1
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## Pull requests

- Keep changes focused.
- Update documentation when behavior changes.
- Preserve the plain-text protocol and exit-code compatibility.
