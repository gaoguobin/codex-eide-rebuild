# Claude Code integration templates

These files prepare the phase 2 Claude Code integration without duplicating the shared runtime.

## Layout

- `commands/eide-rebuild.md` contains a reusable slash-command template
- `agents/eide-rebuild.md` contains a reusable subagent template

## How to use

1. Copy `commands/eide-rebuild.md` to `.claude/commands/eide-rebuild.md` in your project or user configuration.
2. Copy `agents/eide-rebuild.md` to `.claude/agents/eide-rebuild.md`.
3. Update the Python runner path if your checkout lives somewhere else.

Both templates call the shared runner:

```powershell
python runtime/python/eide_rebuild.py rebuild <workspace-or-project-path>
```
