---
name: eide-rebuild
description: EIDE rebuild and compile Agent Skill for Embedded IDE for VS Code workspaces. Runs a Python unify_builder runner and returns compact or full JSON build results.
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
python scripts/eide_rebuild.py rebuild <workspace-or-project-path> --stdout summary
```

Environment check:

```powershell
python scripts/eide_rebuild.py doctor
```

## Result handling

- Treat the runner as the source of truth.
- Prefer `--stdout summary` for normal agent work. It prints a compact JSON summary and still writes the complete result to `resultPath`.
- Use `--stdout full` or omit `--stdout` only when the full JSON is explicitly needed on stdout.
- First inspect `ok`, `exitCode`, `errorCode`, `summary`, `targetNames`, `targets[].ok`, `targets[].failures`, `targets[].diagnostics`, and `targets[].artifacts`.
- Use `targets[].artifacts[].sha256` when reporting final firmware identity.
- Keep the complete JSON available at `resultPath`; it includes `compilerLog`, `steps`, `artifacts`, and `transcript`.
- Read `compilerLog`, `transcript`, and `steps[].stdout/stderr` from `resultPath` only when the user asks for details or when the structured `failures` / `diagnostics` fields are not enough.
- Use exit code `0` for success, `6` for build failure, and the other exit codes for environment or tool errors.

## Subagent guidance

- Prefer a worker subagent when the host supports delegation and policy allows it; fall back to direct execution otherwise.
- The worker should run the same Python runner with `--stdout summary`.
- The worker should return the compact summary stdout, not paste the full result JSON.
- The main agent should keep `resultPath` available for follow-up analysis.
- Do not run multiple rebuild workers against the same project/build directory concurrently.
