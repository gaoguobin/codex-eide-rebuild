# codex-eide-rebuild install for Codex

Use these instructions on Windows to install the repository in the same style as `obra/superpowers`.

## One-paste prompt for engineers

Paste this into Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md

After install, run:
python "$HOME\\.codex\\codex-eide-rebuild\\skills\\eide-rebuild\\scripts\\eide_rebuild.py" doctor

Report the JSON result.
When ok=true, tell me to restart Codex.
```

## What this installs

- Git repo: `%USERPROFILE%\.codex\codex-eide-rebuild`
- Skill namespace junction: `%USERPROFILE%\.agents\skills\codex-eide-rebuild -> %USERPROFILE%\.codex\codex-eide-rebuild\skills`

## Install steps

Run this PowerShell block exactly:

```powershell
$repoRoot = Join-Path $HOME '.codex\codex-eide-rebuild'
$skillsRoot = Join-Path $HOME '.agents\skills'
$skillNamespace = Join-Path $skillsRoot 'codex-eide-rebuild'

if ($env:OS -ne 'Windows_NT') {
    throw 'codex-eide-rebuild currently supports Windows only.'
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git is required before installing codex-eide-rebuild.'
}

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    throw 'VS Code CLI command `code` is required before installing codex-eide-rebuild.'
}

if (Test-Path $repoRoot) {
    throw 'codex-eide-rebuild is already installed. Follow UPDATE.md instead.'
}

if (Test-Path $skillNamespace) {
    throw 'The skill namespace junction already exists. Remove it or follow UNINSTALL.md before reinstalling.'
}

New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null
git clone https://github.com/gaoguobin/codex-eide-rebuild.git $repoRoot
cmd /d /c "mklink /J `"$skillNamespace`" `"$repoRoot\skills`""
```

## After install

The engineer flow ends after pasting the prompt above.
Codex handles install and runs `doctor`.
Restart Codex after Codex reports `doctor.ok=true` so it rescans `~/.agents/skills`.

Run this environment check once:

```powershell
python "$repoRoot\skills\eide-rebuild\scripts\eide_rebuild.py" doctor
```

Expected: one JSON object with `"ok": true`

Then use natural language or an explicit path:

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `EIDE rebuild D:\path\project.code-workspace`

## Existing install

If the repository already exists, fetch and follow:

- `https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md`
