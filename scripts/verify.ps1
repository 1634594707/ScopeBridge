param(
  [switch]$KeepRunning = $true
)

$ErrorActionPreference = "Stop"
$Project = "scopebridge-verify"
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.verify.yml"
$Repo = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Repo "backend"
$Frontend = Join-Path $Repo "frontend"

# Everything below is a process-local override. The repository `.env` is never written.
$env:DATABASE_URL = "postgresql+psycopg://scopebridge:verify-password@127.0.0.1:55434/scopebridge_verify"
$env:APP_BASE_URL = "http://127.0.0.1:4173"
$env:SESSION_SECRET = "verify-only-session-secret-32-characters"
$env:SELLER_EMAIL = "seller@verify.local"
$env:SELLER_PASSWORD = "verify-seller-password"
$env:CLIENT_EMAIL = "client@verify.local"
$env:CLIENT_PASSWORD = "verify-client-password"
$env:MODEL_API_KEY = "test-model-key"
$env:MODEL_NAME = "test-model"
$env:PAYPAL_CLIENT_ID = "test-client-id"
$env:PAYPAL_CLIENT_SECRET = "test-client-secret"
$env:PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"

$script:results = @()

function Invoke-Step {
  param(
    [string]$Name,
    [string]$WorkDir,
    [scriptblock]$Action
  )
  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  Push-Location $WorkDir
  try {
    & $Action
    if ($LASTEXITCODE -ne 0) {
      throw "$Name failed with exit code $LASTEXITCODE"
    }
  }
  finally {
    Pop-Location
    $watch.Stop()
  }
  $seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1)
  $script:results += [pscustomobject]@{ Step = $Name; Seconds = $seconds }
  Write-Host "OK $Name (${seconds}s)" -ForegroundColor Green
}

function Wait-ForDatabase {
  Write-Host ""
  Write-Host "==> database readiness probe (pg_isready, not sleep)" -ForegroundColor Cyan
  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  $ready = $false
  for ($attempt = 1; $attempt -le 60; $attempt++) {
    & docker compose -f $ComposeFile -p $Project exec -T db pg_isready -U scopebridge -d scopebridge_verify *> $null
    if ($LASTEXITCODE -eq 0) {
      $ready = $true
      break
    }
    Start-Sleep -Seconds 2
  }
  $watch.Stop()
  if (-not $ready) {
    & docker compose -f $ComposeFile -p $Project logs --tail 30 db
    throw "database did not become ready within 120 seconds"
  }
  $seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1)
  $script:results += [pscustomobject]@{ Step = "database readiness"; Seconds = $seconds }
  Write-Host "OK database readiness (${seconds}s)" -ForegroundColor Green
}

function Print-Summary {
  Write-Host ""
  Write-Host "Timing summary" -ForegroundColor Cyan
  foreach ($row in $script:results) {
    Write-Host ("  {0,-28} {1,8}s" -f $row.Step, $row.Seconds)
  }
  $total = ($script:results | Measure-Object -Property Seconds -Sum).Sum
  Write-Host ("  {0,-28} {1,8}s" -f "total", [math]::Round($total, 1)) -ForegroundColor Green
}

try {
  Invoke-Step "database start" $Repo {
    & docker compose -f $ComposeFile -p $Project up -d
  }
  Wait-ForDatabase

  Invoke-Step "uv sync" $Backend {
    & uv sync
  }
  Invoke-Step "alembic upgrade head" $Backend {
    & uv run alembic upgrade head
  }
  Invoke-Step "seed demo data" $Backend {
    & uv run python -m app.seed
  }
  Invoke-Step "pytest" $Backend {
    & uv run pytest -q
  }
  Invoke-Step "ruff" $Backend {
    & uv run ruff check .
  }
  Invoke-Step "pnpm install" $Frontend {
    & pnpm install --frozen-lockfile
  }
  Invoke-Step "tsc -b" $Frontend {
    & pnpm exec tsc -b
  }
  Invoke-Step "vite build" $Frontend {
    & pnpm exec vite build
  }

  Print-Summary
  Write-Host ""
  Write-Host "All verification steps passed." -ForegroundColor Green
  Write-Host "Isolated stack: project=$Project, port=55434, database=scopebridge_verify"
  Write-Host "Volume is project-scoped and separate from the demo volume."
  Write-Host "Stop it without deleting data:"
  Write-Host "  docker compose -f `"$ComposeFile`" -p $Project stop"
  if (-not $KeepRunning) {
    Write-Host "KeepRunning=false requested; leaving the stack running anyway (no data deletion)."
  }
  exit 0
}
catch {
  Write-Host ""
  Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
  if ($script:results.Count -gt 0) {
    Print-Summary
  }
  Write-Host "The isolated stack and its volume were left in place; nothing was deleted." -ForegroundColor Yellow
  exit 1
}
