# codex-eide-rebuild uninstall for Claude Code

Run the shell blocks with Claude Code's Bash tool or Git Bash.

## One-paste prompt for engineers

Paste this into Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UNINSTALL.md
```

## Uninstall steps

### 1. Remove command and agent templates

```bash
rm -f ~/.claude/commands/eide-rebuild.md
rm -f ~/.claude/agents/eide-rebuild.md
```

### 2. Remove the repository (optional)

The repository at `~/.codex/codex-eide-rebuild` may be shared with a Codex install.
Check before removing:

```bash
test -L ~/.agents/skills/codex-eide-rebuild && echo "Codex skill junction exists — keep the repo" || echo "No Codex junction — safe to remove"
```

Only remove the repository if no Codex junction exists:

```bash
rm -rf ~/.codex/codex-eide-rebuild
```

If the Codex junction exists, warn the user that removing the repo will also break the Codex skill. Let the user decide.

### 3. Done

Tell the user to run `/reload-plugins` so the removed command and agent are no longer loaded.
