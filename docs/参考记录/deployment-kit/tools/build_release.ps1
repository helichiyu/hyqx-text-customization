param(
    [Parameter(Mandatory=$true)][string]$SourceDir,
    [Parameter(Mandatory=$true)][string]$AppName,
    [Parameter(Mandatory=$true)][string]$OutputZip,
    [string]$EnvFile = "",
    [switch]$IncludeEnvFile
)

$source = [IO.Path]::GetFullPath($SourceDir)
if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "SourceDir not found: $source"
}
$zipPath = [IO.Path]::GetFullPath($OutputZip)
$outputDir = Split-Path -Parent $zipPath
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
if ($zipPath.StartsWith($source + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputZip must be outside SourceDir to avoid recursive packaging"
}

$stagingRoot = Join-Path $outputDir ("_release_staging_" + [guid]::NewGuid().ToString("N"))
$stageApp = Join-Path $stagingRoot $AppName
New-Item -ItemType Directory -Path $stageApp -Force | Out-Null

$excludeDirs = @('.git', '.pytest_cache', '__pycache__', 'runtime', 'dist', 'datasets', 'datasets_external', 'outputs', 'node_modules', '.venv', 'private', '.private', '.ssh')
$args = @($source, $stageApp, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
foreach ($d in $excludeDirs) {
    $args += '/XD'
    $args += (Join-Path $source $d)
}
$args += '/XF'
$args += '.env'
& robocopy @args | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}

Get-ChildItem -LiteralPath $stageApp -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @('__pycache__', '.pytest_cache', 'runtime', 'manual_data', 'outputs', 'datasets_external') -or $_.Name -like 'pip-*' } |
    Sort-Object FullName -Descending |
    ForEach-Object {
        $p = [IO.Path]::GetFullPath($_.FullName)
        if ($p.StartsWith($stageApp + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $p -Recurse -Force
        }
    }

# Remove secrets even when the source tree contains them. .env.example is safe.
Get-ChildItem -LiteralPath $stageApp -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -ne '.env.example' -and (
            $_.Name -eq '.env' -or
            $_.Name -like '.env.*' -or
            $_.Name -eq 'server.env' -or
            $_.Name -eq 'X_TOKEN.txt' -or
            $_.Name -eq 'ACCESS.md' -or
            $_.Extension -in @('.key', '.pem', '.p12', '.pfx')
        )
    } |
    ForEach-Object {
        $p = [IO.Path]::GetFullPath($_.FullName)
        if ($p.StartsWith($stageApp + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $p -Force
        }
    }

if ($IncludeEnvFile) {
    if (-not $EnvFile -or -not (Test-Path -LiteralPath $EnvFile)) {
        throw "-IncludeEnvFile requires a valid -EnvFile"
    }
    Copy-Item -LiteralPath $EnvFile -Destination (Join-Path $stageApp '.env') -Force
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path $stageApp -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -LiteralPath $stagingRoot -Recurse -Force
Write-Host "Created: $zipPath"
Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath | Format-List Path,Hash

$global:LASTEXITCODE = 0
