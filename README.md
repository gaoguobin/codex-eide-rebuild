# codex-eide-rebuild

`codex-eide-rebuild` provides a GitHub-installable Codex skill and a Windows Python runner for rebuilding Embedded IDE for VS Code projects and returning one complete JSON result.

## Install

One-paste prompt for engineers:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

Primary Codex install flow:

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md`

Fallback GitHub installer:

```powershell
python install-skill-from-github.py --repo gaoguobin/codex-eide-rebuild --path skills/eide-rebuild
```

The first install usually needs one approval to clone the repository and create the skill junction. The agent follows `INSTALL.md`, runs `doctor`, and reports the JSON result. Restart Codex after `doctor.ok=true`.

## Update

Update an existing install with:

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md`

This flow fast-forwards the local repo and refreshes the bundled direct-builder runtime. Restart Codex after update.

## Uninstall

Remove the skill, the local repo, and legacy bridge leftovers from older installs with:

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md`

This flow cleans the install back to a first-use baseline. Restart Codex after uninstall.

## Natural language entry

After the skill is installed, Codex can proactively use the runner for prompts such as:

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `先 rebuild 看结果`
- `用 EIDE 编一下`

Explicit command-style prompts also work:

- `EIDE rebuild C:\work\demo\project.code-workspace`
- `EIDE subagent rebuild C:\work\demo\project.code-workspace`

## What it does

- Resolves a `.code-workspace` file or a project directory with exactly one workspace file
- Reads the current `.eide/eide.yml` project model and related config files
- Generates `builder.params` on demand
- Auto-discovers the latest EIDE extension, model/tools, `unify_builder`, and `dotnet`
- Matches GCC to the EIDE workspace configuration when a `.code-workspace` file provides a configured install directory
- Runs `dotnet exec --roll-forward Major <unify_builder.dll> -p <builder.params>`
- Returns one complete JSON result to the agent

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
  claude-code/     Phase 2 Claude Code templates
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
