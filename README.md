# codex-eide-rebuild

`codex-eide-rebuild` provides a GitHub-installable Codex skill, a Windows Python runner, and a minimal VS Code bridge extension for rebuilding Embedded IDE for VS Code projects and returning the complete `compiler.log` as plain text.

## Install

Primary Codex install flow:

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md`

Fallback GitHub installer:

```powershell
python install-skill-from-github.py --repo gaoguobin/codex-eide-rebuild --path skills/eide-rebuild
```

The first install usually needs one approval to clone the repository and create the skill junction. Restart Codex after install.

## Update

Update an existing install with:

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md`

This flow fast-forwards the local repo and force-reinstalls the bundled bridge VSIX. Restart Codex after update.

## Uninstall

Remove the skill, the local repo, the bridge extension, and the related bridge state with:

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
- Reuses an open VS Code window for the target workspace
- Opens the workspace when no live bridge registration exists
- Installs the bundled bridge VSIX into the default VS Code profile
- Triggers `eide.project.rebuild`
- Waits for completion using EIDE build artifacts
- Prints a plain-text protocol plus the full `compiler.log`

## Output protocol

```text
[EIDE-CLI] begin workspace=C:\work\demo\project.code-workspace
[EIDE-CLI] target=Debug
[EIDE-CLI] logPath=C:\work\demo\build\Debug\compiler.log
[EIDE-CLI] result=success
[EIDE-CLI] durationMs=1234
[EIDE-CLI] compiler-log-begin
...full compiler.log text...
[EIDE-CLI] compiler-log-end
[EIDE-CLI] end exitCode=0
```

## Repository layout

```text
.codex/             Codex-facing install, update, and uninstall guides
runtime/
  bridge/          VS Code bridge extension source and VSIX pack script
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

Build the bridge VSIX and sync it into the skill bundle:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\bridge\build-vsix.ps1
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## Security and privacy

This repository uses sanitized examples and generic paths only. Runtime tests and smoke checks use mock data. See `SECURITY.md` for reporting guidance.

## Upstream reference

This project automates rebuild flows for the Embedded IDE for VS Code extension from the upstream EIDE project.
