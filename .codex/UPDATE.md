# codex-eide-rebuild update for Codex

Use these instructions on Windows to update an existing local install and refresh the direct-builder runtime.

## Update steps

Run this PowerShell block exactly:

```powershell
$repoRoot = Join-Path $HOME '.codex\codex-eide-rebuild'
$skillsRoot = Join-Path $HOME '.agents\skills'
$skillNamespace = Join-Path $skillsRoot 'codex-eide-rebuild'
$agentsRoot = Join-Path $HOME '.codex\agents'
$agentTemplate = Join-Path $agentsRoot 'eide-rebuild.toml'

if ($env:OS -ne 'Windows_NT') {
    throw 'codex-eide-rebuild currently supports Windows only.'
}

if (-not (Test-Path $repoRoot)) {
    throw 'codex-eide-rebuild is not installed. Follow INSTALL.md first.'
}

if (-not (Test-Path $skillNamespace)) {
    throw 'The skill namespace junction is missing. Follow INSTALL.md to restore the install layout.'
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git is required before updating codex-eide-rebuild.'
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'python is required before updating codex-eide-rebuild.'
}

git -C $repoRoot fetch --tags origin
git -C $repoRoot switch main
git -C $repoRoot pull --ff-only
New-Item -ItemType Directory -Force -Path $agentsRoot | Out-Null
Copy-Item -LiteralPath "$repoRoot\integrations\codex\agents\eide-rebuild.toml" -Destination $agentTemplate -Force
python -m pip install --user PyYAML
python "$repoRoot\skills\eide-rebuild\scripts\eide_rebuild.py" doctor
```

## After update

Restart Codex so it rescans the skill namespace, custom agents, and updated docs.
