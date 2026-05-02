# Sync-Wiki.ps1
# Usage: .\Sync-Wiki.ps1 -WikiPath "C:\path\to\Hecos.wiki"

param(
    [Parameter(Mandatory=$true)]
    [string]$WikiPath
)

if (-not (Test-Path $WikiPath)) {
    Write-Error "Wiki path does not exist: $WikiPath"
    exit 1
}

$RepoRoot = Get-Item $PSScriptRoot\..
$DocsDir = Join-Path $RepoRoot.FullName "docs"

Write-Host "--- Starting Documentation Sync to Wiki ---"

# Step 0: Clean up destination (except for git metadata and sidebar)
Write-Host "Cleaning destination Wiki folder..." -ForegroundColor Gray
# Exclude _Sidebar.md from cleanup to preserve navigation
Get-ChildItem -Path $WikiPath -Filter *.md -File | Where-Object { $_.Name -ne "_Sidebar.md" } | Remove-Item -Force
Write-Host "Clean complete."

# Define source groups
$Groups = @("user", "tech")

foreach ($Group in $Groups) {
    $GroupDir = Join-Path $DocsDir $Group
    if (-not (Test-Path $GroupDir)) { continue }

    Write-Host "Syncing group: $Group"
    
    $Files = Get-ChildItem -Path $GroupDir -Filter "*.md"
    foreach ($File in $Files) {
        $TargetName = $File.Name
        $TargetPath = Join-Path $WikiPath $TargetName
        
        Copy-Item -Path $File.FullName -Destination $TargetPath -Force
        Write-Host "  Copied: $TargetName"
    }
}

# Step 2: Copy _Sidebar.md if exists in docs root
$SidebarSrc = Join-Path $DocsDir "_Sidebar.md"
if (Test-Path $SidebarSrc) {
    Copy-Item -Path $SidebarSrc -Destination $WikiPath -Force
    Write-Host "`nCopied: _Sidebar.md" -ForegroundColor Cyan
}

Write-Host "`nSync Complete!"
Write-Host "Don't forget to commit and push inside the Wiki repository:"
Write-Host "cd $WikiPath"
Write-Host "git add ."
# Use git status to see deleted files
Write-Host "git add -A" 
Write-Host "git commit -m 'Sync and cleanup obsolete files'"
Write-Host "git push"
