---
description: Rebuild an Embedded IDE for VS Code workspace and return a compact JSON build summary. Use when the user asks to compile, rebuild, or verify a build.
argument-hint: [workspace-or-project-path]
---

Run the shared EIDE rebuild runner for the provided path. Default to direct execution for normal single-project requests because the runner already returns compact JSON and writes full logs to `resultPath`.

1. If an argument is present, use it as the workspace or project path.
2. If no argument is present, infer the current project path only when the current working directory contains exactly one `.code-workspace` file.
3. For normal single-project requests, execute:

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py rebuild $ARGUMENTS --stdout summary
```

4. Use the `eide-rebuild` subagent only when the user explicitly asks for subagent/delegated/background work, or explicitly asks to run independent projects in parallel.
5. Never run multiple rebuild workers against the same project/build directory concurrently.
6. Return only a low-noise summary from compact JSON: `ok`, `exitCode`, `errorCode`, `summary`, `targetNames`, failure count, diagnostic count, `resultPath`, and key artifact identity fields.
7. Do not paste full logs or long artifact lists on success. Read `compilerLog`, `steps`, `artifacts`, and `transcript` from `resultPath` only on failure or explicit request.
