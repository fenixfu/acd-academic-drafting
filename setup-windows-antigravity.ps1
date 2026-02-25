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
}
else {
    Write-Host "Step 1: .agent/ already in .git/info/exclude, skipping" -ForegroundColor Yellow
}
$excludeEntry2 = "GEMINI.md"
$content = Get-Content $excludeFile -Raw
if ($content -notmatch [regex]::Escape($excludeEntry2)) {
    Add-Content $excludeFile "$excludeEntry2"
    Write-Host "Step 2: GEMINI.md added to .git/info/exclude" -ForegroundColor Green
}
else {
    Write-Host "Step 2: GEMINI.md already in .git/info/exclude, skipping" -ForegroundColor Yellow
}

# Step 2: Create NTFS junction .agent -> .opencode
$junction = Join-Path $repo ".agent"
$target = Join-Path $repo ".opencode"
if (Test-Path $junction) {
    Write-Host "Step 2: .agent already exists, skipping" -ForegroundColor Yellow
}
else {
    cmd /c mklink /J "$junction" "$target"
    Write-Host "Step 2: junction .agent -> .opencode created" -ForegroundColor Green
}

# Step 3: Create NTFS junction GEMINI.md -> AGENTS.md
$junction2 = Join-Path $repo "GEMINI.md"
$target2 = Join-Path $repo "AGENTS.md"
if (Test-Path $junction2) {
    Write-Host "Step 3: GEMINI.md already exists, skipping" -ForegroundColor Yellow
}
else {
    cmd /c mklink /H "$junction2" "$target2"
    Write-Host "Step 3: junction GEMINI.md -> AGENTS.md created" -ForegroundColor Green
}

# Verify
Write-Host "Verifying git status:" -ForegroundColor Cyan
git -C $repo status

Write-Host "Verifying .agent\skills:" -ForegroundColor Cyan
Get-ChildItem (Join-Path $junction "skills") -ErrorAction SilentlyContinue | Select-Object Name

Write-Host "Verifying GEMINI.md:" -ForegroundColor Cyan
Get-ChildItem -Filter "GEMINI.md" -Path $repo