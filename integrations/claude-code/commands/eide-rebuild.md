---
description: Rebuild an Embedded IDE for VS Code workspace and return a compact JSON build summary. Use when the user asks to compile, rebuild, or verify a build.
argument-hint: [workspace-or-project-path]
---

Run the shared EIDE rebuild runner for the provided path. Prefer delegating to the `eide-rebuild` subagent so long compiler logs stay out of the main conversation.

1. If an argument is present, use it as the workspace or project path.
2. If no argument is present, infer the current project path only when the current working directory contains exactly one `.code-workspace` file.
3. Ask the `eide-rebuild` subagent to execute:

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py rebuild $ARGUMENTS --stdout summary
```

4. If the subagent is unavailable, execute the same command directly.
5. Return the compact JSON summary and keep `resultPath` available for full JSON, `compilerLog`, `steps`, `artifacts`, and `transcript` follow-up.
