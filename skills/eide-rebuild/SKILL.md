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

Decision table:

| Request shape | Default execution |
| --- | --- |
| Single project, normal compile/rebuild request | Run the runner directly in the main agent. |
| Single project, explicit subagent/delegated/background request | Use the `eide-rebuild` custom agent when available. |
| Multiple independent projects, explicit subagent/parallel/delegated request | Use one rebuild worker per project when the host supports delegation. |
| Same project or same build directory | Never run rebuild workers concurrently. |

Run:

```powershell
python scripts/eide_rebuild.py rebuild <workspace-or-project-path> --stdout summary
```

The relative `scripts/eide_rebuild.py` path is relative to this installed skill directory. Host integrations can use their own installed absolute runner path.

Environment check:

```powershell
python scripts/eide_rebuild.py doctor
```

## Result handling

- Treat the runner as the source of truth.
- Prefer `--stdout summary` for normal agent work. It prints a compact JSON summary and still writes the complete result to `resultPath`.
- Use `--stdout full` or omit `--stdout` only when the full JSON is explicitly needed on stdout.
- First inspect `ok`, `exitCode`, `errorCode`, `summary`, `targetNames`, `targets[].ok`, `targets[].failures`, `targets[].diagnostics`, and `targets[].artifacts`.
- On success, report only a low-noise summary by default: `ok`, `exitCode`, `errorCode`, `summary`, `targetNames`, failure count, diagnostic count, `resultPath`, and key artifact identity fields.
- Use `targets[].artifacts[].sha256` as artifact identity/provenance data. Do not treat hash changes across different rebuilds as success/failure evidence unless the user explicitly asks for reproducibility or deterministic build checks.
- Keep the complete JSON available at `resultPath`; it includes `compilerLog`, `steps`, `artifacts`, and `transcript`.
- Do not paste full logs or long artifact lists on successful builds.
- Read `compilerLog`, `transcript`, and `steps[].stdout/stderr` from `resultPath` only when the build fails, the user asks for details, or the structured `failures` / `diagnostics` fields are not enough.
- Use exit code `0` for success, `6` for build failure, and the other exit codes for environment or tool errors.

## Subagent guidance

- Prefer the `eide-rebuild` custom agent when the user explicitly asks for subagent/delegated rebuild work and the host supports delegation.
- Otherwise use direct runner execution for normal single-project requests.
- Use generic worker subagents only when the host supports delegation, policy allows it, and the user explicitly asks for subagent/parallel/delegated/background work.
- The worker should run the same Python runner with `--stdout summary`.
- The worker should return only the compact summary stdout plus a short factual conclusion, not paste the full result JSON, full logs, or long artifact lists.
- The main agent should keep `resultPath` available for follow-up analysis.
- Do not run multiple rebuild workers against the same project/build directory concurrently.
