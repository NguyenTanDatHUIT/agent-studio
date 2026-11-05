param(
    [string]$Config,
    [switch]$Demo,
    [switch]$MonitorOnly,
    [int]$Port = 8765,
    [string]$Python
)

$ErrorActionPreference = 'Stop'
if ($Config -and $Demo) { throw 'Choose -Config or -Demo, not both.' }
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be 1..65535.' }
if ($Config) { $Config = (Resolve-Path -LiteralPath $Config).Path }
$pythonPrefix = @()
if (-not $Python) {
    foreach ($candidate in @('.venv\Scripts\python.exe', '.runtime\python\python.exe')) {
        $candidatePath = Join-Path $PSScriptRoot $candidate
        if (Test-Path -LiteralPath $candidatePath -PathType Leaf) { $Python = $candidatePath; break }
    }
}
if (-not $Python) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) { $Python = $pythonCommand.Source }
    else {
        $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyCommand) { $Python = $pyCommand.Source; $pythonPrefix = @('-3') }
    }
}
if (-not $Python) { throw 'Python 3.11+ is required. Install Python or pass -Python C:\Path\python.exe.' }
$orchestratorArgs = @('-m', 'agent_orchestrator')
if ($Config) { $orchestratorArgs += @('--config', $Config) }
$orchestratorArgs += @('web', '--port', "$Port")
if ($Config -and -not $MonitorOnly) { $orchestratorArgs += '--run-workers' }
if (-not $Config) {
    $orchestratorArgs += '--demo'
    Write-Host 'OFFLINE DEMO: disposable workspace; no model calls. Use -Config for a real project.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python @pythonPrefix @orchestratorArgs
    exit $LASTEXITCODE
} finally { Pop-Location }
