[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "rebuild", "status", "logs", "setup")]
    [string]$Action = "status",

    [Parameter(Position = 1)]
    [ValidateSet("all", "backend", "frontend", "storybook", "datasette")]
    [string]$Service = "all"
)

$ErrorActionPreference = "Stop"
$ComposeFile = Join-Path $PSScriptRoot "compose.yaml"
$ProjectDirectory = $PSScriptRoot
$AllServices = @("backend", "frontend", "storybook", "datasette")

function Invoke-Compose {
    param([string[]]$Arguments)

    & docker compose --file $ComposeFile --project-directory $ProjectDirectory @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed with exit code $LASTEXITCODE."
    }
}

function Get-StatusRows {
    $json = & docker compose --file $ComposeFile --project-directory $ProjectDirectory ps --all --format json
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose status failed with exit code $LASTEXITCODE."
    }
    if ([string]::IsNullOrWhiteSpace(($json -join ""))) {
        return @()
    }
    try {
        return @($json | ForEach-Object { $_ | ConvertFrom-Json })
    }
    catch {
        throw "Docker Compose returned invalid status JSON."
    }
}

function Test-ServiceHealthy {
    param([string]$Name)
    $rows = @(Get-StatusRows)
    $row = @($rows | Where-Object { $_.Service -eq $Name }) | Select-Object -First 1
    return ($null -ne $row -and $row.State -eq "running" -and $row.Health -eq "healthy")
}

function Get-SelectedServices {
    if ($Service -eq "all") { return $AllServices }
    return @($Service)
}

switch ($Action) {
    "status" {
        $rows = @(Get-StatusRows)
        foreach ($name in (Get-SelectedServices)) {
            $row = @($rows | Where-Object { $_.Service -eq $name }) | Select-Object -First 1
            if ($null -eq $row) {
                Write-Output ("{0}: missing (not created yet)" -f $name)
            }
            else {
                Write-Output ("{0}: state={1}, health={2}" -f $name, $row.State, $row.Health)
            }
        }
    }
    "setup" {
        if ($Service -ne "all") { throw "The setup action only supports the 'all' target." }
        $script = @'
import os, sqlite3
p='/data/fplpatternrec.db'
if os.path.exists(p):
    c=sqlite3.connect('file:'+p+'?mode=ro', uri=True)
    try:
        if c.execute('PRAGMA quick_check').fetchone()!=('ok',):
            raise SystemExit('Existing database failed SQLite quick_check; setup refused to modify it.')
        if c.execute('SELECT name FROM sqlite_master WHERE type=?', ('table',)).fetchall()!=[]:
            raise SystemExit('Existing database contains tables; setup refused to modify it.')
    finally:
        c.close()
    print('Existing valid zero-table SQLite database verified; leaving it unchanged.')
else:
    fd=os.open(p, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o644)
    os.close(fd)
    c=sqlite3.connect(p)
    try:
        assert c.execute('PRAGMA quick_check').fetchone()==('ok',)
        assert c.execute('SELECT name FROM sqlite_master WHERE type=?', ('table',)).fetchall()==[]
    finally:
        c.close()
'@
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
        Invoke-Compose @("run", "--rm", "--no-deps", "--entrypoint", "python", "datasette", "-c", "import base64; exec(base64.b64decode('$encoded'))")
        Write-Output "Setup completed: empty SQLite database created in the fplpatternrec-sqlite volume."
    }
    "start" {
        $healthy = $true
        foreach ($name in (Get-SelectedServices)) {
            if (-not (Test-ServiceHealthy $name)) { $healthy = $false }
        }
        if ($healthy) {
            Write-Output "Selected services are already healthy; leaving them alone."
        }
        else {
            Invoke-Compose (@("up", "--detach", "--wait", "--wait-timeout", "180") + (Get-SelectedServices))
        }
    }
    "stop" { Invoke-Compose (@("stop") + (Get-SelectedServices)) }
    "restart" { Invoke-Compose (@("restart") + (Get-SelectedServices)) }
    "rebuild" { Invoke-Compose (@("up", "--detach", "--build", "--force-recreate", "--wait", "--wait-timeout", "300") + (Get-SelectedServices)) }
    "logs" { Invoke-Compose (@("logs", "--tail", "100", "--no-log-prefix") + (Get-SelectedServices)) }
}
