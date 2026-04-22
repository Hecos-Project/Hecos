# Auto-Wiki-Deploy.ps1
# This script automates the synchronization and deployment of Zentra Core documentation to GitHub Wiki.

param(
    [string]$WikiPath = "C:\Zentra-Core-Wiki",
    [string]$CommitMsg = "Automated Documentation Update"
)

$ErrorActionPreference = "Stop"

# 1. Run Local Content Sync
Write-Host "`n[1/2] Synchronizing local files..." -ForegroundColor Cyan
& "$PSScriptRoot\Sync-Wiki.ps1" -WikiPath $WikiPath

# 2. Execute Git Deployment
Write-Host "`n[2/2] Deploying to GitHub Wiki..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $WikiPath ".git"))) {
    Write-Error "The path $WikiPath is not a valid git repository."
    exit 1
}

$CurrentDir = Get-Location
try {
    Set-Location $WikiPath
    
    # Check for changes
    $status = git status --porcelain
    if (-not $status) {
        Write-Host "No changes detected. Skipping commit/push." -ForegroundColor Yellow
        return
    }

    Write-Host "Changes detected. Committing..." -ForegroundColor Gray
    git add -A
    git commit -m "$CommitMsg ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
    
    Write-Host "Pushing to remote..." -ForegroundColor Gray
    git push
    
    Write-Host "`n🚀 SUCCESS: Wiki is now updated and live on GitHub!" -ForegroundColor Green
}
catch {
    Write-Host "`n❌ ERROR: Deployment failed." -ForegroundColor Red
    Write-Host $_
}
finally {
    Set-Location $CurrentDir
}
