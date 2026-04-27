# codex-eide-rebuild

`codex-eide-rebuild` provides a Windows Python runner and agent skill for rebuilding Embedded IDE for VS Code projects. It supports both Codex and Claude Code, returning one complete JSON result.

## Install

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md
```

The agent follows the install doc, runs `doctor`, and reports the JSON result. Restart the agent after `doctor.ok=true`.

## Update

### Codex

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md`

### Claude Code

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md`

## Uninstall

### Codex

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md`

### Claude Code

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UNINSTALL.md`

## Natural language entry

After the skill is installed, the agent can proactively use the runner for prompts such as:

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `先 rebuild 看结果`
- `用 EIDE 编一下`

Explicit command-style prompts also work:

- `EIDE rebuild C:\work\demo\project.code-workspace`
- `EIDE subagent rebuild C:\work\demo\project.code-workspace`
- `/eide-rebuild C:\work\demo\project.code-workspace` (Claude Code slash command)

## What it does

- Resolves a `.code-workspace` file or a project directory with exactly one workspace file
- Reads the current `.eide/eide.yml` project model and related config files
- Generates `builder.params` on demand
- Auto-discovers the latest EIDE extension, model/tools, `unify_builder`, and `dotnet`
- Matches GCC to the EIDE workspace configuration when a `.code-workspace` file provides a configured install directory
- Runs `dotnet exec --roll-forward Major <unify_builder.dll> -p <builder.params>`
- Returns one complete JSON result to the agent
- Fails hung build steps with `STEP_TIMEOUT` after 60 seconds
- Reports structured `doctor.toolChecks` diagnostics for setup failures

## Output protocol

```json
{
  "ok": true,
  "errorCode": "OK",
  "targets": [
    {
      "name": "Debug",
      "ok": true
    }
  ]
}
```

## Repository layout

```text
.codex/             Codex-facing install, update, and uninstall guides
runtime/
  python/          Shared Python runner
  tests/           Unit tests and repository audits
skills/
  eide-rebuild/    GitHub-installable Codex skill
integrations/
  claude-code/     Claude Code install docs, command and agent templates
scripts/
  sync_skill_runtime.py
```

## Development

Sync the runtime and run tests:

```powershell
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## Security and privacy

This repository uses sanitized examples and generic paths only. Runtime tests and smoke checks use mock data. See `SECURITY.md` for reporting guidance.

## Upstream reference

This project automates rebuild flows for the Embedded IDE for VS Code extension from the upstream EIDE project.
