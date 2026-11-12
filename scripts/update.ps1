[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$origin = & git -C $sourceRoot remote get-url origin
if ($LASTEXITCODE -ne 0 -or $origin -notmatch '^(https://github\.com/|git@github\.com:)EvanKKAI/visio-diagram(?:\.git)?/?$') { throw 'Unexpected origin repository.' }
$status = @(& git -C $sourceRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect Git status.' }
if ($status.Count) { throw 'Local changes exist. Inspect and preserve them before updating.' }
$branch = & git -C $sourceRoot branch --show-current
if (-not $branch) { throw 'Detached HEAD: select the intended branch before updating.' }
$upstream = & git -C $sourceRoot rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
if ($LASTEXITCODE -ne 0 -or $upstream -notlike 'origin/*') { throw 'Expected an origin tracking branch.' }

& git -C $sourceRoot fetch origin --prune
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed; working files were not updated.' }
$counts = (& git -C $sourceRoot rev-list --left-right --count 'HEAD...@{upstream}') -split '\s+'
if ($LASTEXITCODE -ne 0 -or $counts.Count -ne 2) { throw 'Could not compare local and upstream history.' }
$ahead = [int]$counts[0]; $behind = [int]$counts[1]
if ($ahead -gt 0) { throw "Local-only commits: $ahead; upstream-only commits: $behind. Review histories; no merge was attempted." }
if ($behind -gt 0) {
    & git -C $sourceRoot diff --stat 'HEAD..@{upstream}'
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the incoming diff.' }
    & git -C $sourceRoot merge --ff-only '@{upstream}'
    if ($LASTEXITCODE -ne 0) { throw 'Fast-forward update failed; inspect the repository.' }
}
& (Join-Path $PSScriptRoot 'install.ps1') -VerifyOnly
if (@(& git -C $sourceRoot status --porcelain).Count) { throw 'Working tree is not clean after update.' }
