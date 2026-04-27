# Claude Code integration templates

These files provide Claude Code command and subagent templates that call the shared Python runtime.

## Layout

- `commands/eide-rebuild.md` contains a reusable slash-command template
- `agents/eide-rebuild.md` contains a reusable subagent template

## How to use

For normal installs, follow `INSTALL.md`, `UPDATE.md`, or `UNINSTALL.md`.

1. Copy `commands/eide-rebuild.md` to `.claude/commands/eide-rebuild.md` in your project or user configuration.
2. Copy `agents/eide-rebuild.md` to `.claude/agents/eide-rebuild.md`.
3. If your checkout is not at `~/.codex/codex-eide-rebuild`, update the runner path in both templates after copying.

Both templates call the shared runner at the default Codex install location:

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py rebuild <workspace-or-project-path>
```
