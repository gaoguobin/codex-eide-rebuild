# codex-eide-rebuild install for Claude Code

Use these instructions on Windows to install the EIDE rebuild skill for Claude Code.
Run the shell blocks with Claude Code's Bash tool or Git Bash.

## One-paste prompt for engineers

Paste this into Claude Code:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md
```

## What this installs

- Git repo: `~/.codex/codex-eide-rebuild` (shared with Codex if present)
- Slash command: `~/.claude/commands/eide-rebuild.md`
- Subagent: `~/.claude/agents/eide-rebuild.md`

## Install steps

### 1. Check for existing Claude Code install

If `~/.claude/commands/eide-rebuild.md` already exists, this skill is already installed.
Fetch and follow the update instructions instead:

- `https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md`

### 2. Prerequisites

Verify these are available before continuing:

```bash
[[ "$OS" == "Windows_NT" ]] && echo "ok: windows" || echo "FAIL: windows only"
command -v git   >/dev/null && echo "ok: git"      || echo "FAIL: git not found"
command -v python >/dev/null && echo "ok: python"   || echo "FAIL: python not found"
```

Stop and report any failures to the user.

### 3. Install or update the repository

If `~/.codex/codex-eide-rebuild` already exists (e.g. from a Codex install), update it before copying templates.

```bash
if [ -d ~/.codex/codex-eide-rebuild/.git ]; then
  git -C ~/.codex/codex-eide-rebuild pull --ff-only
else
  git clone https://github.com/gaoguobin/codex-eide-rebuild.git ~/.codex/codex-eide-rebuild
fi
```

### 4. Install Python dependencies

```bash
python -m pip install --user PyYAML
```

### 5. Copy command and agent templates

```bash
mkdir -p ~/.claude/commands ~/.claude/agents
cp ~/.codex/codex-eide-rebuild/integrations/claude-code/commands/eide-rebuild.md ~/.claude/commands/eide-rebuild.md
cp ~/.codex/codex-eide-rebuild/integrations/claude-code/agents/eide-rebuild.md ~/.claude/agents/eide-rebuild.md
```

### 6. Verify

```bash
python ~/.codex/codex-eide-rebuild/runtime/python/eide_rebuild.py doctor
```

Report the JSON result in the reply.
When the JSON contains `"ok": true`, tell the user to run `/reload-plugins` so Claude Code picks up the new command and agent.

## After install

Use natural language or an explicit path:

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `/eide-rebuild D:\path\project.code-workspace`

## Existing install

If the skill is already installed, fetch and follow:

- `https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md`
