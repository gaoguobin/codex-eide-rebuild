# codex-eide-rebuild uninstall for Codex

Use these instructions on Windows to remove the local `codex-eide-rebuild` skill installation.

## Before uninstalling

No VS Code window or VS Code CLI is required. This direct-builder skill does not install a VS Code bridge or extension.

## Uninstall steps

Run this PowerShell block exactly:

```powershell
$repoRoot = Join-Path $HOME '.codex\codex-eide-rebuild'
$skillsRoot = Join-Path $HOME '.agents\skills'
$skillNamespace = Join-Path $skillsRoot 'codex-eide-rebuild'
$agentTemplate = Join-Path $HOME '.codex\agents\eide-rebuild.toml'

if ($env:OS -ne 'Windows_NT') {
    throw 'codex-eide-rebuild currently supports Windows only.'
}

foreach ($path in @($skillNamespace, $agentTemplate, $repoRoot)) {
    if (Test-Path $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}
```

## After uninstall

Restart Codex so it drops the removed skill namespace and custom agent from its next scan.

This uninstall keeps VS Code itself, `cl.eide`, Python, `.NET`, EIDE toolchains, and your project directories intact.
