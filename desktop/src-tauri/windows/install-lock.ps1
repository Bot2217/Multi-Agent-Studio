# Release only this installation's ulei.exe and ulei-backend.exe before NSIS
# replaces them. Other Python processes, and files under this folder such as
# ollama\, are left alone. Settings live in %APPDATA%\ulei and are not touched.
# Exit 0 when those two executables can be replaced. Exit 2 when a file is
# still locked after a bounded wait.

param(
    [string]$InstallDir,
    [int]$WaitSeconds = 8,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
$UleiNames = @("ulei.exe", "ulei-backend.exe")

function Get-NormalizedPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }
    try {
        return [IO.Path]::GetFullPath($Path).TrimEnd("\")
    } catch {
        return $Path.TrimEnd("\")
    }
}

function Get-UleiInstallTargets([string]$Root) {
    $rootPath = Get-NormalizedPath $Root
    $wanted = foreach ($name in $UleiNames) {
        Get-NormalizedPath (Join-Path $rootPath $name)
    }
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and ($wanted -contains (Get-NormalizedPath $_.ExecutablePath))
    }
}

function Get-DescendantPids([int[]]$RootPids) {
    $all = @(Get-CimInstance Win32_Process)
    $found = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    foreach ($pidValue in $RootPids) { $queue.Enqueue([int]$pidValue) }
    $depth = 0
    while ($queue.Count -gt 0 -and $depth -lt 6) {
        $count = $queue.Count
        for ($i = 0; $i -lt $count; $i++) {
            $current = $queue.Dequeue()
            foreach ($proc in $all) {
                if ([int]$proc.ParentProcessId -eq $current -and -not $found.Contains([int]$proc.ProcessId)) {
                    $found.Add([int]$proc.ProcessId) | Out-Null
                    $queue.Enqueue([int]$proc.ProcessId)
                }
            }
        }
        $depth++
    }
    return @($found)
}

function Stop-OneProcess([int]$ProcessId, [switch]$Force) {
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $proc) { return }
    if (-not $Force) {
        try { [void]$proc.CloseMainWindow() } catch { }
        return
    }
    try { Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue } catch { }
}

function Test-FileReplaceable([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    $item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($item -and $item.IsReadOnly) {
        try { $item.IsReadOnly = $false } catch { }
    }
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        $stream.Dispose()
        return $true
    } catch {
        return $false
    }
}

function Invoke-UleiInstallLock([string]$Root, [int]$TimeoutSeconds) {
    $rootPath = Get-NormalizedPath $Root
    if (-not $rootPath) { return 0 }
    $targets = @(Get-UleiInstallTargets $rootPath)
    foreach ($proc in $targets) {
        if ((Split-Path -Leaf $proc.ExecutablePath) -eq "ulei.exe") {
            Stop-OneProcess -ProcessId $proc.ProcessId
        }
    }
    $deadline = (Get-Date).AddSeconds(3)
    do {
        $targets = @(Get-UleiInstallTargets $rootPath)
        if ($targets.Count -eq 0) { break }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)

    $targets = @(Get-UleiInstallTargets $rootPath)
    if ($targets.Count -gt 0) {
        $roots = @($targets | ForEach-Object { [int]$_.ProcessId })
        $children = @(Get-DescendantPids $roots)
        foreach ($child in $children) { Stop-OneProcess -ProcessId $child -Force }
        foreach ($rootPid in $roots) { Stop-OneProcess -ProcessId $rootPid -Force }
    }

    $paths = foreach ($name in $UleiNames) { Join-Path $rootPath $name }
    $deadline = (Get-Date).AddSeconds([Math]::Max(1, $TimeoutSeconds))
    do {
        $blocked = @($paths | Where-Object { -not (Test-FileReplaceable $_) })
        if ($blocked.Count -eq 0) {
            [Console]::Out.WriteLine("ULEI_INSTALL_LOCK_OK")
            return 0
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    foreach ($blockedPath in $blocked) {
        [Console]::Out.WriteLine("ULEI_INSTALL_LOCK_BUSY $blockedPath")
    }
    return 2
}

function Invoke-UleiInstallLockSelfTest {
    $root = Join-Path $env:TEMP ("ulei-install-lock-" + [guid]::NewGuid().ToString("n"))
    # The real installer uses the Cyrillic product folder. Keep this file ASCII.
    $leaf = -join @(0x0423, 0x043B, 0x0435, 0x0439 | ForEach-Object { [char]$_ })
    $install = Join-Path $root $leaf
    New-Item -ItemType Directory -Force -Path $install | Out-Null
    $backend = Join-Path $install "ulei-backend.exe"
    Copy-Item -LiteralPath $env:ComSpec -Destination $backend -Force
    $decoy = Start-Process -FilePath $env:ComSpec -ArgumentList "/d", "/c", "ping -n 40 127.0.0.1 > nul" -WindowStyle Hidden -PassThru
    $locked = Start-Process -FilePath $backend -ArgumentList "/d", "/c", "ping -n 40 127.0.0.1 > nul" -WindowStyle Hidden -PassThru
    try {
        $seen = $false
        foreach ($try in 1..20) {
            $hit = @(Get-UleiInstallTargets $install | ForEach-Object { [int]$_.ProcessId })
            if ($hit -contains $locked.Id) { $seen = $true; break }
            Start-Sleep -Milliseconds 200
        }
        if (-not $seen) { throw "WINDOWS_EXEC: copied ulei-backend.exe was not visible to the process query" }
        $code = Invoke-UleiInstallLock -Root $install -TimeoutSeconds 8
        if ($code -ne 0) { throw "WINDOWS_EXEC: expected to unlock this install, got $code" }
        if (Get-Process -Id $locked.Id -ErrorAction SilentlyContinue) {
            throw "WINDOWS_EXEC: sidecar process was not stopped"
        }
        if (-not (Get-Process -Id $decoy.Id -ErrorAction SilentlyContinue)) {
            throw "WINDOWS_EXEC: a process outside this install was stopped"
        }
        if (-not (Test-FileReplaceable $backend)) { throw "WINDOWS_EXEC: ulei-backend.exe is still not replaceable" }

        $locker = Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -PassThru -ArgumentList @(
            "-NoProfile", "-Command",
            "`$s = [IO.File]::Open('$backend', 'Open', 'Read', 'None'); Start-Sleep -Seconds 30; `$s.Dispose()"
        )
        try {
            Start-Sleep -Milliseconds 500
            $busy = Invoke-UleiInstallLock -Root $install -TimeoutSeconds 2
            if ($busy -ne 2) { throw "WINDOWS_EXEC: a foreign lock should abort with code 2, got $busy" }
            if (-not (Get-Process -Id $locker.Id -ErrorAction SilentlyContinue)) {
                throw "WINDOWS_EXEC: the foreign lock process was killed"
            }
        } finally {
            Stop-Process -Id $locker.Id -Force -ErrorAction SilentlyContinue
        }
        [Console]::Out.WriteLine("ULEI_INSTALL_LOCK_WINDOWS_OK $install")
        return 0
    } finally {
        if ($decoy -and (Get-Process -Id $decoy.Id -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $decoy.Id -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($SelfTest) {
    $result = Invoke-UleiInstallLockSelfTest
    exit $result
}

if (-not $InstallDir) {
    Write-Error "InstallDir is required"
    exit 2
}
$code = Invoke-UleiInstallLock -Root $InstallDir -TimeoutSeconds $WaitSeconds
exit $code
