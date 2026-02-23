# setup-windows-antigravity.ps1
# Run once after git clone on Windows.
# Creates an NTFS junction .agent -> .opencode so Antigravity can read skills/workflows.
# Not needed on WSL/opencode.

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path

# Step 1: Add .agent/ to local git exclude (does not affect remote repo)
$excludeFile = Join-Path $repo ".git\info\exclude"
$excludeEntry = ".agent/"
$content = Get-Content $excludeFile -Raw
if ($content -notmatch [regex]::Escape($excludeEntry)) {
    Add-Content $excludeFile "`n# Windows/Antigravity local junction - not tracked by git`n$excludeEntry"
    Write-Host "Step 1: .agent/ added to .git/info/exclude" -ForegroundColor Green
} else {
    Write-Host "Step 1: .agent/ already in .git/info/exclude, skipping" -ForegroundColor Yellow
}

# Step 2: Create NTFS junction .agent -> .opencode
$junction = Join-Path $repo ".agent"
$target   = Join-Path $repo ".opencode"
if (Test-Path $junction) {
    Write-Host "Step 2: .agent already exists, skipping" -ForegroundColor Yellow
} else {
    cmd /c mklink /J "$junction" "$target"
    Write-Host "Step 2: junction .agent -> .opencode created" -ForegroundColor Green
}

# Verify
Write-Host "`nVerifying git status:" -ForegroundColor Cyan
git -C $repo status
Write-Host "`nVerifying .agent\skills:" -ForegroundColor Cyan
Get-ChildItem (Join-Path $junction "skills") -ErrorAction SilentlyContinue | Select-Object Name
