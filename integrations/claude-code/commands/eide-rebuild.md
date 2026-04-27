---
description: Rebuild an Embedded IDE for VS Code workspace and return the full compiler.log. Use when the user asks to compile, rebuild, or verify a build.
argument-hint: [workspace-or-project-path]
---

Run the shared EIDE rebuild runner for the provided path.

1. If an argument is present, use it as the workspace or project path.
2. If no argument is present, infer the current project path only when the current working directory contains exactly one `.code-workspace` file.
3. Execute:

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py rebuild $ARGUMENTS
```

4. Return the complete JSON result and keep `compilerLog`, `steps`, `artifacts`, and `transcript` intact.
