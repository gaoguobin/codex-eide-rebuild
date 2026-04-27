# codex-eide-rebuild update for Claude Code

Run the shell blocks with Claude Code's Bash tool or Git Bash.

## One-paste prompt for engineers

Paste this into Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md
```

## Update steps

### 1. Pull latest code

```bash
git -C ~/.codex/codex-eide-rebuild pull --ff-only
```

If the repository does not exist, fetch and follow the install instructions instead:

- `https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md`

### 2. Re-copy templates

```bash
mkdir -p ~/.claude/commands ~/.claude/agents
cp ~/.codex/codex-eide-rebuild/integrations/claude-code/commands/eide-rebuild.md ~/.claude/commands/eide-rebuild.md
cp ~/.codex/codex-eide-rebuild/integrations/claude-code/agents/eide-rebuild.md ~/.claude/agents/eide-rebuild.md
```

### 3. Verify

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py doctor
```

Report the JSON result in the reply.
When the JSON contains `"ok": true`, tell the user to restart Claude Code so it picks up the updated templates.
