# codex-eide-rebuild

[![CI](https://github.com/gaoguobin/codex-eide-rebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/gaoguobin/codex-eide-rebuild/actions/workflows/ci.yml)

Rebuild Embedded IDE for VS Code (EIDE) workspaces from Codex or Claude Code and return one complete structured JSON build result.

`codex-eide-rebuild` packages an Agent Skill plus a Windows-first Python runner. The runner reads the current EIDE project model, generates fresh `builder.params`, invokes EIDE `unify_builder` through `dotnet`, and preserves compiler logs, artifacts, memory usage, stack reports, and setup diagnostics for the agent.

[Chinese](README.zh-CN.md) · [Agent Skill](#agent-skill-and-discovery) · [Install](#install) · [Verify](#verify) · [Output](#output-protocol) · [Safety](#safety-model) · [Plugin](#plugin-readiness) · [Development](#development)

## Why

This project is for firmware and embedded teams that already build EIDE projects locally and want agents to run the same rebuild flow without relying on VS Code bridge registration. It keeps the agent-facing protocol simple: one command in, one JSON object out.

The project is designed for real workspace validation. Agents can run `doctor`, rebuild all EIDE targets, inspect failed build steps, and quote the exact compiler log path and artifact paths without scraping terminal output by hand.

## Highlights

| Capability | What it means |
| --- | --- |
| Agent-ready JSON | Returns one complete JSON result with `ok`, `errorCode`, target summaries, logs, steps, artifacts, and transcript. |
| Fresh build parameters | Generates `builder.params` from `.eide/eide.yml`, `.eide/env.ini`, `.eide/files.options.yml`, and workspace GCC settings before each rebuild. |
| EIDE rebuild semantics | Runs `dotnet exec --roll-forward Major <unify_builder.dll> -p <builder.params> --rebuild`. |
| Tool discovery | Finds EIDE extension tools, model files, `unify_builder`, `dotnet`, and the GCC root configured by the workspace. |
| Setup diagnostics | `doctor` reports structured `toolChecks`, PyYAML status, and .NET runtime probing results. |
| Timeout guard | Long-running build steps return `STEP_TIMEOUT` after 60 seconds. |
| Multi-agent fit | The skill can delegate long rebuilds to a worker subagent while the main agent keeps the parsed result. |
| Runtime sync guard | CI verifies the shared runner and bundled skill copy stay synchronized. |

## Compatibility

- Windows-first workflow.
- Python 3.11+ with PyYAML.
- Embedded IDE for VS Code (`cl.eide`) installed in VS Code.
- .NET runtime compatible with the installed EIDE `unify_builder`.
- EIDE workspaces with `.code-workspace` and `.eide/eide.yml`.
- Codex skill installation and Claude Code command/subagent templates are both included.

## Agent Skill and Discovery

This repository includes one Agent Skill:

- Skill name: `eide-rebuild`
- Skill path: `skills/eide-rebuild/SKILL.md`
- Primary use case: let an agent rebuild EIDE / Embedded IDE for VS Code firmware workspaces and return structured JSON build results.
- Trigger examples: `帮我编译确认一下`, `先 rebuild 看结果`, `EIDE rebuild C:\work\demo\project.code-workspace`, `/eide-rebuild C:\work\demo\project.code-workspace`.
- Runner entry point: `skills/eide-rebuild/scripts/eide_rebuild.py`
- Environment check: `python skills/eide-rebuild/scripts/eide_rebuild.py doctor`

Tools that index public GitHub repositories for Agent Skills, including SkillsMP-style GitHub indexers, can discover the skill at the path above. This repository uses explicit skill metadata, a stable skill path, and `.codex-plugin/plugin.json` discovery metadata to make the bundled skill easy to identify.

Project status: community GitHub project with Agent Skill and preparatory Codex plugin metadata. No SkillsMP listing, marketplace listing, or OpenAI official status is claimed.

## Plugin Readiness

Codex plugin documentation defines `.codex-plugin/plugin.json` as the required plugin manifest and keeps `skills/` at the plugin root. This repository includes `.codex-plugin/plugin.json` metadata that points to `./skills/` so plugin-aware tools can identify the bundled skill.

Current supported installation remains the Codex-managed or Claude Code-managed flow in [Install](#install). The plugin metadata is discovery and packaging metadata only. Runtime impact: none. Hook installation, permission changes, user configuration edits, background services, and rebuild behavior changes stay out of scope.

## Install

### Codex

Paste this into Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

The install flow clones the repository into `~/.codex/codex-eide-rebuild`, installs PyYAML, links the skill namespace into `~/.agents/skills`, and runs `doctor`.

After `doctor.ok=true`, restart Codex so it rescans installed skills.

### Claude Code

Paste this into Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md
```

The Claude Code integration installs command and subagent templates. Run `/reload-plugins` after install.

## Update

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md
```

Restart Codex or run `/reload-plugins` in Claude Code after updates that change skill files.

## Uninstall

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UNINSTALL.md
```

## Verify

Run the environment check from the installed skill directory:

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py doctor
```

Run a rebuild against a workspace file or project directory:

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py rebuild C:\work\demo\project.code-workspace
```

Expected agent behavior:

- Read one complete JSON object from `stdout`.
- Treat `exitCode=0` as success.
- Treat `exitCode=6` as build failure.
- Use other non-zero exit codes for setup, configuration, runtime, or timeout failures.
- Preserve `compilerLog`, `steps`, `artifacts`, and `transcript` for analysis.

## Output Protocol

```json
{
  "schemaVersion": "1",
  "ok": true,
  "exitCode": 0,
  "errorCode": "OK",
  "mode": "rebuild-all",
  "targets": [
    {
      "name": "Debug",
      "ok": true,
      "builderParamsPath": "C:/work/demo/build/Debug/builder.params",
      "compilerLogPath": "C:/work/demo/build/Debug/compiler.log",
      "artifacts": [
        {
          "path": "C:/work/demo/build/Debug/app.bin",
          "kind": "bin",
          "size": 139104
        }
      ]
    }
  ]
}
```

## Common Commands

Agents should use the runner as the source of truth:

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py doctor
python skills/eide-rebuild/scripts/eide_rebuild.py rebuild C:\work\demo\project.code-workspace
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

Default paths:

| Item | Path |
| --- | --- |
| Codex install repo | `~/.codex/codex-eide-rebuild` |
| Codex skill namespace | `~/.agents/skills/codex-eide-rebuild` |
| Skill file | `skills/eide-rebuild/SKILL.md` |
| Runner script | `skills/eide-rebuild/scripts/eide_rebuild.py` |
| Rebuild result | `<project>/build/rebuild_result.json` |
| Per-target compiler log | `<project>/<outDir>/<target>/compiler.log` |

## Safety Model

- The runner executes local EIDE rebuild commands in the target workspace.
- The runner writes generated `builder.params`, compiler logs, artifacts, and `build/rebuild_result.json` under the project output directories.
- The runner reads project configuration from `.code-workspace`, `.eide/eide.yml`, `.eide/env.ini`, and `.eide/files.options.yml`.
- The runner may execute pre-build and post-build tasks defined by the EIDE project because those tasks are part of the EIDE build model.
- Out of scope for the runner: VS Code extension installation, VS Code bridge registration, source edits, Codex configuration edits, VS Code settings edits, and hook installation.
- The installer links this repository's `skills/` directory into the user's agent skill directory and installs PyYAML for the current user.
- Runtime tests and smoke checks in this repository use sanitized examples and mock data.

## Repository Layout

```text
.codex/              Codex install, update, and uninstall guides
.codex-plugin/       Codex plugin discovery manifest
runtime/
  python/            Shared Python runner
  tests/             Unit tests and repository audits
skills/
  eide-rebuild/      Agent Skill and bundled runner copy
integrations/
  claude-code/       Claude Code install docs, command, and subagent templates
scripts/
  sync_skill_runtime.py
```

## Development

Sync the runtime into the skill bundle and run tests:

```powershell
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
python -m compileall runtime\python scripts
```

## Security and Privacy

This repository uses sanitized examples and generic paths only. Runtime tests and smoke checks use mock data. See [SECURITY.md](SECURITY.md) for reporting guidance.

## Upstream Reference

This project automates rebuild flows for the Embedded IDE for VS Code extension from the upstream EIDE project.

## License

MIT - see [LICENSE](LICENSE).
