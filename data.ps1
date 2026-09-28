[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TyperArguments
)

$ErrorActionPreference = "Stop"
$PythonExecutable = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
$ExitCode = 0

Push-Location $PSScriptRoot
try {
    & $PythonExecutable -m tools.data_pipeline.compose_runner @TyperArguments
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $ExitCode
