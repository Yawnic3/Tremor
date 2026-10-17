$ErrorActionPreference = 'Stop'
$python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
foreach ($module in @('pytest', 'ruff', 'mypy')) {
    if ($module -eq 'pytest') { & $python -m pytest -q }
    elseif ($module -eq 'ruff') { & $python -m ruff check backend }
    else { & $python -m mypy backend }
    if ($LASTEXITCODE -ne 0) { throw "$module failed" }
}
foreach ($task in @('test', 'lint', 'build')) {
    npm run $task
    if ($LASTEXITCODE -ne 0) { throw "$task failed" }
}
