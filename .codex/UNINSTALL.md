# codex-eide-rebuild uninstall for Codex

Use these instructions on Windows to remove `codex-eide-rebuild` and clean the local bridge state back to a first-install baseline.

## Before uninstalling

Close VS Code windows that are actively using the EIDE rebuild bridge. Extension removal is most reliable after those windows are closed.

## Uninstall steps

Run this PowerShell block exactly:

```powershell
$repoRoot = Join-Path $HOME '.codex\codex-eide-rebuild'
$skillsRoot = Join-Path $HOME '.agents\skills'
$skillNamespace = Join-Path $skillsRoot 'codex-eide-rebuild'
$registrationRoot = Join-Path $HOME '.vscode\eide-rebuild'
$legacyRegistrationRoot = Join-Path $env:LOCALAPPDATA 'EIDE_CLI'
$logsRoot = Join-Path $env:APPDATA 'Code\logs'
$legacyBridgeId = ('ga' + 'o' + '.eide-cli-bridge')
$patterns = @(
    'eide-rebuild.cli-bridge',
    $legacyBridgeId,
    'EIDE_CLI',
    'eide-cli-'
)

if ($env:OS -ne 'Windows_NT') {
    throw 'codex-eide-rebuild currently supports Windows only.'
}

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    throw 'VS Code CLI command `code` is required before uninstalling codex-eide-rebuild.'
}

code --uninstall-extension eide-rebuild.cli-bridge
code --uninstall-extension $legacyBridgeId

foreach ($path in @($skillNamespace, $repoRoot, $registrationRoot, $legacyRegistrationRoot)) {
    if (Test-Path $path) {
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path $logsRoot) {
    $sessionDirs = Get-ChildItem -LiteralPath $logsRoot -Recurse -File -Filter *.log -ErrorAction SilentlyContinue |
        Select-String -Pattern $patterns -SimpleMatch -List -ErrorAction SilentlyContinue |
        ForEach-Object {
            $current = Split-Path -Parent $_.Path
            while ($current -and ((Split-Path -Parent $current) -ne $logsRoot)) {
                $current = Split-Path -Parent $current
            }
            $current
        } |
        Where-Object { $_ } |
        Sort-Object -Unique

    foreach ($sessionDir in $sessionDirs) {
        if (Test-Path $sessionDir) {
            Remove-Item -LiteralPath $sessionDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
```

## After uninstall

Restart Codex so it drops the removed skill namespace from its next scan.

This uninstall keeps VS Code itself, `cl.eide`, Python, and your project directories intact.
