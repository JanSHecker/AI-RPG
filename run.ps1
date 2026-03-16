param(
    [switch]$Cli,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$backendSrc = Join-Path $backendRoot "src"
$pythonCandidates = @(
    (Join-Path $backendRoot ".venv-win\Scripts\python.exe"),
    (Join-Path $repoRoot ".venv-win\Scripts\python.exe")
)
$pythonExe = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$envFiles = @(
    (Join-Path $repoRoot ".env"),
    (Join-Path $backendRoot ".env")
)

if (-not (Test-Path $pythonExe)) {
    throw "Missing Python environment in $backendRoot or $repoRoot. Install the project first."
}

foreach ($envFile in $envFiles) {
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith("#")) {
                return
            }

            $parts = $line -split "=", 2
            if ($parts.Count -ne 2) {
                return
            }

            $name = $parts[0].Trim()
            $value = $parts[1]
            if (
                $value.Length -ge 2 -and (
                    ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                    ($value.StartsWith("'") -and $value.EndsWith("'"))
                )
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$pathSeparator = [System.IO.Path]::PathSeparator
$existingPythonPath = [System.Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$pythonPath = if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
    $backendSrc
}
else {
    "$backendSrc$pathSeparator$existingPythonPath"
}
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", $pythonPath, "Process")

$moduleName = if ($Cli) { "ai_rpg.cli.main" } else { "ai_rpg.web.main" }

Push-Location $backendRoot
try {
    & $pythonExe -m $moduleName @AppArgs
}
finally {
    Pop-Location
}
