[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$codexRoot = if ($env:CODEX_HOME) { [IO.Path]::GetFullPath($env:CODEX_HOME) } else { Join-Path $env:USERPROFILE '.codex' }
$skillLink = Join-Path $codexRoot 'skills\visio-diagram'

foreach ($relative in @('SKILL.md','agents\openai.yaml','scripts\render.py','scripts\check_engine.py','references\spec.md','assets\examples\branch-fusion.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $relative) -PathType Leaf)) { throw "Missing skill file: $relative" }
}
$top = & git -C $sourceRoot rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($top) -ne $sourceRoot) { throw 'Run from the cloned visio-diagram repository.' }
$origin = & git -C $sourceRoot remote get-url origin
if ($LASTEXITCODE -ne 0 -or $origin -notmatch '^(https://github\.com/|git@github\.com:)saadxxx847-ai/visio-diagram(?:\.git)?/?$') { throw 'Unexpected origin repository. Expected saadxxx847-ai/visio-diagram; see the README migration instructions for v1.0.0.' }
$branch = & git -C $sourceRoot branch --show-current
$commit = & git -C $sourceRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Repository has no commit.' }

$existing = Get-Item -LiteralPath $skillLink -Force -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    if ($existing.LinkType -ne 'Junction') { throw "Existing path is not the expected junction; preserve it and inspect: $skillLink" }
    $actualTarget = [IO.Path]::GetFullPath([string](@($existing.Target)[0]))
    if ($actualTarget -ne $sourceRoot) { throw "Existing junction points elsewhere: $actualTarget" }
} else {
    if ($VerifyOnly) { throw "Skill junction is missing: $skillLink" }
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $skillLink) -Force
    $null = New-Item -ItemType Junction -Path $skillLink -Target $sourceRoot
}
$verified = Get-Item -LiteralPath $skillLink -Force
if ($verified.LinkType -ne 'Junction' -or [IO.Path]::GetFullPath([string](@($verified.Target)[0])) -ne $sourceRoot) { throw 'Junction verification failed.' }
if ((Get-FileHash -LiteralPath (Join-Path $skillLink 'SKILL.md')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sourceRoot 'SKILL.md')).Hash) { throw 'Skill content verification failed.' }
$status = @(& git -C $sourceRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Git status.' }
[ordered]@{ skill='visio-diagram'; source=$sourceRoot; junction=$skillLink; target=$verified.Target; origin=$origin; branch=$branch; commit=$commit; clean=($status.Count -eq 0); changes=$status } | ConvertTo-Json -Depth 3
