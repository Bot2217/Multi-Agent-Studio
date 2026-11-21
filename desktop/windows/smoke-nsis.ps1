# Install the NSIS package this build just produced and require the sidecar
# to serve health with the same --port / --api-port arguments Tauri uses.
# ASCII only: Windows PowerShell 5.1 reads a BOM-less script as ANSI.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Bundle = Join-Path $Root "desktop\src-tauri\target\release\bundle\nsis"
if (-not (Test-Path -LiteralPath $Bundle)) {
    throw "NSIS bundle directory is missing: $Bundle"
}
$Installer = Get-ChildItem -LiteralPath $Bundle -Filter "*.exe" |
    Where-Object { $_.Name -like "*setup*" } |
    Select-Object -First 1
if (-not $Installer) {
    throw "NSIS setup executable is missing in $Bundle"
}

# "Улей тест" — Cyrillic product folder plus a space, built from code points.
$Folder = -join @(
    [char]0x0423, [char]0x043B, [char]0x0435, [char]0x0439, " ", "test"
)
$Dest = Join-Path $env:LOCALAPPDATA $Folder
Write-Output "NSIS_INSTALLER $($Installer.FullName)"
Write-Output "NSIS_DEST $Dest"

$Start = New-Object System.Diagnostics.ProcessStartInfo
$Start.FileName = $Installer.FullName
$Start.Arguments = "/S /D=$Dest"
$Start.UseShellExecute = $false
$Process = [System.Diagnostics.Process]::Start($Start)
$Process.WaitForExit()
Write-Output "NSIS_EXIT $($Process.ExitCode)"
if ($Process.ExitCode -ne 0) {
    throw "NSIS installer exited $($Process.ExitCode)"
}

$Backend = Join-Path $Dest "ulei-backend.exe"
if (-not (Test-Path -LiteralPath $Backend)) {
    Write-Output "NSIS_LISTING"
    if (Test-Path -LiteralPath $Dest) {
        Get-ChildItem -LiteralPath $Dest | ForEach-Object { $_.FullName }
    } else {
        Write-Output "destination was not created"
    }
    throw "installed sidecar is missing: $Backend"
}

$Smoke = Join-Path $Root "desktop\smoke_sidecar.py"
python $Smoke --in-place $Backend
if ($LASTEXITCODE -ne 0) {
    throw "installed sidecar did not become healthy"
}
Write-Output "NSIS_SMOKE_OK"
