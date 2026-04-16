[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression

# --- Helpers ---

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$stableTimestamp = [System.DateTimeOffset]::Parse('2024-01-01T00:00:00+00:00')

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalizedContent = Normalize-LineEndings -Content $Content
    [System.IO.File]::WriteAllText($LiteralPath, $normalizedContent, $utf8NoBom)
}

function Normalize-LineEndings {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    return (($Content -replace "`r`n", "`n") -replace "`r", "`n")
}

function Copy-NormalizedTextFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,

        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $content = [System.IO.File]::ReadAllText($SourcePath)
    Write-Utf8File -LiteralPath $DestinationPath -Content $content
}

function Get-ArchiveEntryName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,

        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    $baseUri = [System.Uri](([System.IO.Path]::GetFullPath($BasePath).TrimEnd('\') + '\'))
    $fileUri = [System.Uri]([System.IO.Path]::GetFullPath($FilePath))
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($fileUri).ToString())
}

function New-DeterministicZipArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDir,

        [Parameter(Mandatory = $true)]
        [string]$DestinationPath
    )

    $fileStream = [System.IO.File]::Open($DestinationPath, [System.IO.FileMode]::Create)

    try {
        $archive = [System.IO.Compression.ZipArchive]::new(
            $fileStream,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $false
        )

        try {
            $files = Get-ChildItem -LiteralPath $SourceDir -Recurse -File |
                Sort-Object { Get-ArchiveEntryName -BasePath $SourceDir -FilePath $_.FullName }

            foreach ($file in $files) {
                $entryName = Get-ArchiveEntryName -BasePath $SourceDir -FilePath $file.FullName
                $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = $stableTimestamp

                $sourceStream = [System.IO.File]::OpenRead($file.FullName)
                try {
                    $entryStream = $entry.Open()
                    try {
                        $sourceStream.CopyTo($entryStream)
                    } finally {
                        $entryStream.Dispose()
                    }
                } finally {
                    $sourceStream.Dispose()
                }
            }
        } finally {
            $archive.Dispose()
        }
    } finally {
        $fileStream.Dispose()
    }
}

# --- Paths ---

$bridgeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageFile = Join-Path $bridgeRoot 'package.json'
$distDir = Join-Path $bridgeRoot 'dist'
$buildDir = Join-Path $bridgeRoot '.build'
$stageDir = Join-Path $buildDir 'vsix-root'
$extensionStageDir = Join-Path $stageDir 'extension'

# --- Metadata ---

$package = Get-Content -LiteralPath $packageFile -Raw | ConvertFrom-Json
$extensionId = "$($package.publisher).$($package.name)"
$vsixName = "$extensionId-$($package.version).vsix"
$vsixPath = Join-Path $distDir $vsixName

# --- Stage layout ---

Remove-Item -LiteralPath $buildDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $extensionStageDir | Out-Null
New-Item -ItemType Directory -Force $distDir | Out-Null

foreach ($fileName in @('package.json', 'extension.js', 'README.md')) {
    Copy-NormalizedTextFile `
        -SourcePath (Join-Path $bridgeRoot $fileName) `
        -DestinationPath (Join-Path $extensionStageDir $fileName)
}

# --- VSIX metadata ---

$contentTypes = @'
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="js" ContentType="application/javascript" />
  <Default Extension="md" ContentType="text/markdown" />
  <Default Extension="txt" ContentType="text/plain" />
  <Default Extension="vsixmanifest" ContentType="text/xml" />
  <Default Extension="xml" ContentType="text/xml" />
</Types>
'@

$vsixManifest = @"
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="$extensionId" Version="$($package.version)" Publisher="$($package.publisher)" />
    <DisplayName>$($package.displayName)</DisplayName>
    <Description xml:space="preserve">$($package.description)</Description>
    <Tags>EIDE Rebuild CLI Bridge</Tags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="$($package.engines.vscode)" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" />
    <Asset Type="Microsoft.VisualStudio.Code.Extension" Path="extension" />
  </Assets>
</PackageManifest>
"@

Write-Utf8File -LiteralPath (Join-Path $stageDir '[Content_Types].xml') -Content $contentTypes
Write-Utf8File -LiteralPath (Join-Path $stageDir 'extension.vsixmanifest') -Content $vsixManifest

# --- Package ---

Remove-Item -LiteralPath $vsixPath -Force -ErrorAction SilentlyContinue
New-DeterministicZipArchive -SourceDir $stageDir -DestinationPath $vsixPath

Write-Output "Generated: $vsixPath"
