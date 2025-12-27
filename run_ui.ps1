$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$VenvPython = "$ScriptDir\worker\.venv\Scripts\python.exe"
$ReflexExe = "$ScriptDir\worker\.venv\Scripts\reflex.exe"
$UiDir = "$ScriptDir\ui_reflex"

# Set Encoding to UTF-8 to avoid Unicode errors
$env:PYTHONUTF8 = "1"

# Check if Virtual Environment exists
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found. Please run .\init.ps1 first to set up the environment."
}

# Add Worker Directory to PYTHONPATH so Reflex can import worker modules
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

# Run Reflex
Write-Host "[*] Starting Reflex UI from $UiDir..."
Push-Location $UiDir
try {
    & $ReflexExe run
} finally {
    Pop-Location
}
