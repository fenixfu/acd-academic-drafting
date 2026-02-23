# backup_output.ps1
# Windows equivalent of backup_output.sh
# Usage: .\backup_output.ps1 [-DryRun]

param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$OutputDir = Join-Path $ScriptDir 'output'
$BackupDir = Join-Path $ScriptDir 'former_results'
$SimilarityThreshold = 0.8

# --- DRY RUN banner ---
if ($DryRun) {
    Write-Host "=== DRY RUN mode (no actual changes) ===" -ForegroundColor Cyan
    Write-Host ""
}

# --- Guard: output/ must exist ---
if (-not (Test-Path $OutputDir -PathType Container)) {
    Write-Error "ERROR: 'output' directory does not exist."
    exit 1
}

# --- Collect output files (sorted) ---
$OutputFiles = @(Get-ChildItem -Path $OutputDir -Recurse -File |
    Sort-Object FullName)

$OutputCount = $OutputFiles.Count

if ($OutputCount -eq 0) {
    Write-Host "WARNING: 'output' directory is empty, nothing to back up." -ForegroundColor Yellow
    exit 0
}

Write-Host "=== Backup analysis ===" -ForegroundColor White
Write-Host "Files in output/: $OutputCount"

# --- Ensure former_results/ exists, find latest backup ---
$LatestBackup = $null

if (-not (Test-Path $BackupDir -PathType Container)) {
    if ($DryRun) {
        Write-Host "[DRY RUN] Would create: $BackupDir"
    }
    else {
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
    }
}
else {
    # Match dirs named YYYYMMDD_NNN
    $LatestBackup = Get-ChildItem -Path $BackupDir -Directory |
    Where-Object { $_.Name -match '^\d{8}_\d{3}$' } |
    Sort-Object Name -Descending |
    Select-Object -First 1
}

# --- Similarity check against latest backup ---
$Mode = 'new'
$MatchCount = 0

if ($null -ne $LatestBackup) {
    $LatestName = $LatestBackup.Name
    $BackupFiles = @(Get-ChildItem -Path $LatestBackup.FullName -Recurse -File |
        Sort-Object FullName)
    $BackupCount = $BackupFiles.Count

    foreach ($outFile in $OutputFiles) {
        $RelPath = $outFile.FullName.Substring($OutputDir.Length).TrimStart('\', '/')
        $BackupFile = Join-Path $LatestBackup.FullName $RelPath

        if (Test-Path $BackupFile -PathType Leaf) {
            $OutHash = (Get-FileHash -Algorithm MD5 -LiteralPath $outFile.FullName).Hash
            $BackupHash = (Get-FileHash -Algorithm MD5 -LiteralPath $BackupFile).Hash
            if ($OutHash -eq $BackupHash) { $MatchCount++ }
        }
    }

    $Similarity = if ($OutputCount -gt 0) { $MatchCount / $OutputCount } else { 0 }
    $SimilarityPercent = [math]::Round($Similarity * 100)

    Write-Host "Latest backup : $LatestName ($BackupCount files)"
    Write-Host "Hash matches  : $MatchCount/$OutputCount (${SimilarityPercent}%)"

    if ($Similarity -ge $SimilarityThreshold) {
        Write-Host "-> Append mode"
        $Mode = 'append'
    }
    else {
        Write-Host "-> New backup"
    }
}
else {
    Write-Host "No previous backup found -> New backup"
}

Write-Host ""
Write-Host "=== Executing backup ===" -ForegroundColor White

# -------------------------------------------------------
# APPEND MODE: copy only files not yet in latest backup
# -------------------------------------------------------
if ($Mode -eq 'append') {
    $NewEntries = [System.Collections.Generic.List[hashtable]]::new()

    foreach ($outFile in $OutputFiles) {
        $RelPath = $outFile.FullName.Substring($OutputDir.Length).TrimStart('\', '/')
        $BackupFile = Join-Path $LatestBackup.FullName $RelPath

        if (-not (Test-Path $BackupFile -PathType Leaf)) {
            $NewEntries.Add(@{ Src = $outFile.FullName; Rel = $RelPath })
        }
    }

    if ($NewEntries.Count -eq 0) {
        Write-Host "No new files, skipping copy."
    }
    else {
        Write-Host "New files:"
        foreach ($e in $NewEntries) { Write-Host "  + $($e.Rel)" }
        Write-Host ""

        if ($DryRun) {
            Write-Host "[DRY RUN] Would copy $($NewEntries.Count) file(s) to: $($LatestBackup.FullName)\"
        }
        else {
            foreach ($e in $NewEntries) {
                $DestFile = Join-Path $LatestBackup.FullName $e.Rel
                $DestDir = Split-Path $DestFile -Parent
                if (-not (Test-Path $DestDir)) {
                    New-Item -ItemType Directory -Path $DestDir | Out-Null
                }
                Copy-Item -LiteralPath $e.Src -Destination $DestFile
            }
            Write-Host "Copied to: $($LatestBackup.FullName)\"
        }
    }

    $TargetDir = $LatestBackup.FullName

    # -------------------------------------------------------
    # NEW BACKUP MODE: create YYYYMMDD_NNN and copy all files
    # -------------------------------------------------------
}
else {
    $Today = Get-Date -Format 'yyyyMMdd'

    $TodayCount = @(
        Get-ChildItem -Path $BackupDir -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^${Today}_\d{3}$" }
    ).Count
    $Seq = $TodayCount + 1
    $SeqStr = '{0:D3}' -f $Seq

    $NewBackupName = "${Today}_${SeqStr}"
    $TargetDir = Join-Path $BackupDir $NewBackupName

    if ($DryRun) {
        Write-Host "[DRY RUN] Would create: $NewBackupName\"
        Write-Host "[DRY RUN] Would copy $OutputCount file(s)"
    }
    else {
        New-Item -ItemType Directory -Path $TargetDir | Out-Null

        foreach ($outFile in $OutputFiles) {
            $RelPath = $outFile.FullName.Substring($OutputDir.Length).TrimStart('\', '/')
            $DestFile = Join-Path $TargetDir $RelPath
            $DestDir = Split-Path $DestFile -Parent
            if (-not (Test-Path $DestDir)) {
                New-Item -ItemType Directory -Path $DestDir | Out-Null
            }
            Copy-Item -LiteralPath $outFile.FullName -Destination $DestFile
        }

        Write-Host "New backup created: $NewBackupName\ ($OutputCount files)"
    }
}

# -------------------------------------------------------
# Offer to clear output/
# -------------------------------------------------------
Write-Host ""
if ($DryRun) {
    Write-Host "[DRY RUN] Would prompt: clear output/ directory?"
}
else {
    $Confirm = Read-Host "Clear output/ directory? [y/N]"
    if ($Confirm -match '^[Yy]$') {
        Remove-Item -Path (Join-Path $OutputDir '*') -Recurse -Force
        Write-Host "Done: output/ cleared."
    }
    else {
        Write-Host "Skipped: output/ left intact."
    }
}

Write-Host ""
Write-Host "Backup complete." -ForegroundColor Green
