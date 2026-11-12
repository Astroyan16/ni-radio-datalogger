param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    & $Python -c "import struct, sys; assert sys.platform == 'win32' and struct.calcsize('P') == 8, 'Windows x64 requis'; assert sys.version_info[:2] == (3, 12), 'Python 3.12 requis'"
    if ($LASTEXITCODE -ne 0) { throw "Environnement de compilation incorrect." }
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dépendances incohérentes." }
    & $Python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Échec des tests." }
    $workPath = Join-Path ([System.IO.Path]::GetTempPath()) ("ni-radio-build-" + [guid]::NewGuid())
    & $Python -m PyInstaller --noconfirm --clean --workpath $workPath ni-radio-datalogger.spec
    if ($LASTEXITCODE -ne 0) { throw "Échec de PyInstaller." }
    $exePath = Join-Path $projectRoot "dist\NI-Radio-Datalogger-0.1.1-windows-x64.exe"
    $smokePath = Join-Path $projectRoot "artifacts\smoke-exe"
    $previousPlatform = $env:QT_QPA_PLATFORM
    try {
        $env:QT_QPA_PLATFORM = "windows"
        $process = Start-Process -FilePath $exePath -ArgumentList @("--smoke-test", ('"' + $smokePath + '"')) -PassThru -WindowStyle Hidden
        if (-not $process.WaitForExit(60000)) {
            Stop-Process -Id $process.Id -Force
            throw "Le contrôle de l'exécutable a dépassé 60 secondes."
        }
        if ($process.ExitCode -ne 0) { throw "Échec du contrôle de l'exécutable : $($process.ExitCode)." }
    }
    finally {
        $env:QT_QPA_PLATFORM = $previousPlatform
    }
    & $Python scripts/package_release.py
    if ($LASTEXITCODE -ne 0) { throw "Échec de la préparation de la release." }
    Write-Output "Release Windows préparée dans dist/."
}
finally {
    Pop-Location
}
