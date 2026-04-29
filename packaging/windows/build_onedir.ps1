param(
    [string]$Python = "py -3.12",
    [string]$VenvPath = ".venv-fleet-package"
)

$ErrorActionPreference = "Stop"
$StandaloneRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$MonorepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")
if (Test-Path (Join-Path $StandaloneRoot "app.py")) {
    $RepoRoot = $StandaloneRoot
    $AppRoot = $StandaloneRoot
}
elseif (Test-Path (Join-Path $MonorepoRoot "products\apps\fleet_manager\app.py")) {
    $RepoRoot = $MonorepoRoot
    $AppRoot = Join-Path $RepoRoot "products\apps\fleet_manager"
}
else {
    throw "Could not find Fleet Manager app root from $PSScriptRoot"
}
$SpecPath = Join-Path $AppRoot "packaging\pyinstaller\fleet_manager_onedir.spec"
$VenvFullPath = Join-Path $AppRoot $VenvPath
$DistPath = Join-Path $AppRoot "dist"
$BuildPath = Join-Path $AppRoot "build"

Set-Location $AppRoot

if (-not (Test-Path $VenvFullPath)) {
    Invoke-Expression "$Python -m venv `"$VenvFullPath`""
}

$PythonExe = Join-Path $VenvFullPath "Scripts\python.exe"
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $AppRoot "requirements.txt") -r (Join-Path $AppRoot "requirements-packaging.txt")
& $PythonExe -m PyInstaller --clean --noconfirm --distpath $DistPath --workpath $BuildPath $SpecPath

Write-Host ""
Write-Host "Built onedir package:"
Write-Host "  $DistPath\SolarExpanseFleetManager"
