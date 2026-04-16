# codex-eide-rebuild update for Codex

Use these instructions on Windows to update an existing local install and immediately refresh the VS Code bridge extension.

## Before updating

Close VS Code windows that are actively using the EIDE rebuild bridge. The bridge VSIX reinstall is most reliable after those windows are closed.

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

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    throw 'VS Code CLI command `code` is required before updating codex-eide-rebuild.'
}

git -C $repoRoot fetch --tags origin
git -C $repoRoot switch main
git -C $repoRoot pull --ff-only

$vsixPath = Get-ChildItem -LiteralPath (Join-Path $repoRoot 'runtime\bridge\dist') -Filter 'eide-rebuild.cli-bridge-*.vsix' |
    Sort-Object Name -Descending |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $vsixPath) {
    throw 'Bundled bridge VSIX is missing after update.'
}

code --install-extension $vsixPath --force
```

## After update

Restart Codex so it rescans the skill namespace and picks up the updated docs.

The next `rebuild` run will use the refreshed bridge extension and the updated runner.
