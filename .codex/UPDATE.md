# codex-eide-rebuild update for Codex

Use these instructions on Windows to update an existing local install and refresh the direct-builder runtime.

## Update steps

Run this PowerShell block exactly:

```powershell
$repoRoot = Join-Path $HOME '.codex\codex-eide-rebuild'
$skillsRoot = Join-Path $HOME '.agents\skills'
$skillNamespace = Join-Path $skillsRoot 'codex-eide-rebuild'

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

git -C $repoRoot fetch --tags origin
git -C $repoRoot switch main
git -C $repoRoot pull --ff-only
python "$repoRoot\skills\eide-rebuild\scripts\eide_rebuild.py" doctor
```

## After update

Restart Codex so it rescans the skill namespace and picks up the updated docs.
