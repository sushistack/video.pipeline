<#
.SYNOPSIS
    Video Pipeline Unified Initialization Script
    
.DESCRIPTION
    1. Updates git submodules explicitly.
    2. Opens the GPT-SoVITS README for user review.
    3. Executes the main worker initialization logic (environment setup, dependencies, models).

.NOTES
    Run this script from the project root.
#>

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "   Video Pipeline: Atomic Initialization" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Submodule Update
Write-Host "`n[Step 1/3] Updating Submodules..." -ForegroundColor Green
try {
    git submodule update --init --recursive
    if ($LASTEXITCODE -ne 0) { throw "Git submodule update failed." }
    Write-Host "[+] Submodules updated successfully." -ForegroundColor Yellow
}
catch {
    Write-Error "Error updating submodules. Please check git installation."
    exit 1
}

# 2. Readme Review
$readmePath = Join-Path "worker" "vendor" "GPT-SoVITS" "README.md"
Write-Host "`n[Step 2/3] Checking Submodule Documentation..." -ForegroundColor Green
if (Test-Path $readmePath) {
    Write-Host "[*] Opening GPT-SoVITS README for your review..." -ForegroundColor Gray
    Start-Process $readmePath
    
    Write-Host "`nCurrently opening the submodule README."
    Write-Host "Please review it if needed, then..." -ForegroundColor Yellow
    Pause
} else {
    Write-Warning "Submodule README not found at $readmePath"
}

# 3. Dependency Check (uv)
Write-Host "`n[Step 3/4] Checking Dependencies..." -ForegroundColor Green

function Get-UvPath {
    $paths = @(
        "$env:USERPROFILE\.cargo\bin",
        "$env:LOCALAPPDATA\uv",
        "$env:USERPROFILE\.local\bin"
    )
    foreach ($p in $paths) {
        if (Test-Path (Join-Path $p "uv.exe")) { return $p }
    }
    return $null
}

$uvDir = Get-UvPath
if ($uvDir) {
    Write-Host "[*] Found 'uv' in: $uvDir" -ForegroundColor Gray
    $env:Path = "$uvDir;$env:Path"
}

if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Warning "'uv' package manager not found. Installing..."
    try {
        # Install uv
        irm https://astral.sh/uv/install.ps1 | iex
        
        # Check paths again
        $uvDir = Get-UvPath
        if ($uvDir) {
            Write-Host "[+] 'uv' installed to: $uvDir" -ForegroundColor Yellow
            $env:Path = "$uvDir;$env:Path"
        } else {
             Write-Error "Installed 'uv' but cannot locate executable. Please restart terminal."
             exit 1
        }
    } catch {
        Write-Error "Failed to install 'uv'. Please install manually: pip install uv"
        exit 1
    }
} else {
    Write-Host "[*] 'uv' is available." -ForegroundColor Gray
}

# 4. Execution of Worker Init
Write-Host "`n[Step 4/4] Running Python Bootstrapper..." -ForegroundColor Green
Write-Host "[*] This will handle VENV creation (uv), Dependencies, and Models." -ForegroundColor Gray

# Check if python is available
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found in PATH. Please install Python."
    exit 1
}

# Run the python init script
python worker/init.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Initialization Complete!" -ForegroundColor Cyan
    Write-Host "You can now run the pipeline or verify configuration."
} else {
    Write-Error "`n[FAILED] Bootstrapper returned error code $LASTEXITCODE"
    exit $LASTEXITCODE
}
