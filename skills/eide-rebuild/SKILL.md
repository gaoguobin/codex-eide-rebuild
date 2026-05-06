---
name: eide-rebuild
description: EIDE rebuild and compile Agent Skill for Embedded IDE for VS Code workspaces. Runs a Python unify_builder runner and returns one complete JSON build result.
---

Use this skill when the user wants an EIDE project rebuilt from Codex.

## Trigger patterns

- Natural language build requests such as `你自己编译验证下对不对`
- Natural language build requests such as `帮我编译确认一下`
- Natural language build requests such as `先 rebuild 看结果`
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

Environment check:

```powershell
python scripts/eide_rebuild.py doctor
```

## Result handling

- Treat the runner as the source of truth.
- Read one complete JSON object from `stdout`.
- Keep `compilerLog`, `steps`, `artifacts`, and `transcript` intact.
- Use exit code `0` for success, `6` for build failure, and the other exit codes for environment or tool errors.

## Subagent guidance

- When the user explicitly asks for `subagent rebuild`, delegate the rebuild to a worker subagent.
- The worker should run the same Python runner and return the full `stdout`.
- The main agent should parse the JSON result and keep the full log fields available for analysis.
