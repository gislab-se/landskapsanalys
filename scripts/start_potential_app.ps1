param(
    [int]$Port = 8501,
    [switch]$AutoPort,
    [switch]$CheckOnly,
    [string]$Python = "python",
    [string]$EntryPoint = "streamlit_app.py"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$entryPath = Join-Path $repoRoot $EntryPoint

function Test-PortInUse {
    param([int]$PortToCheck)

    $pattern = [regex]::Escape(":$PortToCheck") + "\s"
    $matches = @(netstat -ano | Select-String -Pattern $pattern)
    return $matches.Count -gt 0
}

function Get-WorkingPython {
    param([string]$RequestedPython)

    $candidates = @($RequestedPython, "py", "python3", "python") | Where-Object { $_ } | Select-Object -Unique
    foreach ($candidate in $candidates) {
        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
            # Try the next common Windows/Python launcher command.
        }
    }

    throw "Could not find a working Python. Pass -Python with the full path to python.exe."
}

if (-not (Test-Path $entryPath)) {
    throw "Streamlit entrypoint not found: $entryPath"
}

$selectedPort = $Port
if ($AutoPort) {
    $selectedPort = 8501..8520 | Where-Object { -not (Test-PortInUse -PortToCheck $_) } | Select-Object -First 1
    if (-not $selectedPort) {
        throw "No free Streamlit port found in 8501-8520."
    }
} elseif (Test-PortInUse -PortToCheck $selectedPort) {
    throw "Port $selectedPort is already in use. Re-run with -AutoPort or pass -Port <number>."
}

$pythonCommand = Get-WorkingPython -RequestedPython $Python
& $pythonCommand -m streamlit --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Streamlit is not installed for $pythonCommand. Run: $pythonCommand -m pip install -r requirements.txt"
}

Set-Location $repoRoot
Write-Host "Starting Streamlit: http://localhost:$selectedPort"
if ($CheckOnly) {
    Write-Host "Check only: $pythonCommand -m streamlit run $entryPath --server.port $selectedPort"
    exit 0
}

& $pythonCommand -m streamlit run $entryPath --server.port $selectedPort
exit $LASTEXITCODE
