---
name: eide-rebuild
description: Rebuilds an Embedded IDE for VS Code workspace through a Python runner and returns the full compiler.log as plain text. Use when the user asks to compile, rebuild, verify a build, or says phrases like "你自己编译验证下对不对", "帮我编译确认一下", "先 rebuild 看结果", or "用 EIDE 编一下".
---

Use this skill when the user wants an EIDE project rebuilt from Codex.

## Trigger patterns

- Natural language build requests such as `你自己编译验证下对不对`
- Explicit requests such as `EIDE rebuild C:\work\demo\project.code-workspace`
- Long-log requests such as `EIDE subagent rebuild C:\work\demo\project.code-workspace`

## How to execute

1. Resolve the target path.
2. Prefer a user-provided `.code-workspace` path.
3. If the user points at a project directory, pass that directory to the runner and let the runner resolve the single workspace file.
4. If no path is supplied, inspect the current working directory. Use it when it contains exactly one `.code-workspace` file.
5. If the current working directory does not identify one workspace, ask the user for the path.

Run:

```powershell
python scripts/eide_rebuild.py rebuild <workspace-or-project-path>
```

## Result handling

- Treat the runner as the source of truth.
- Read the `[EIDE-CLI]` protocol lines from `stdout`.
- Keep the full `compiler.log` content intact.
- Use exit code `0` for success, `6` for build failure, and the other exit codes for environment or bridge errors.

## Subagent guidance

- When the user explicitly asks for `subagent rebuild`, delegate the rebuild to a worker subagent.
- The worker should run the same Python runner and return the full `stdout`.
- The main agent should consume the protocol header and full log, then continue analysis.
