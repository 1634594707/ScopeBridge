param(
  [switch]$SkipBrowserInstall,
  [string]$BrowserChannel = ""
)

$ErrorActionPreference = "Stop"
$Project = "scopebridge-verify"
$ComposeFile = Join-Path $PSScriptRoot "docker-compose.verify.yml"
$Repo = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Repo "backend"
$Frontend = Join-Path $Repo "frontend"

# Process-local overrides only. The repository `.env` is never written or edited.
$env:DATABASE_URL = "postgresql+psycopg://scopebridge:verify-password@127.0.0.1:55434/scopebridge_verify"
$env:E2E_DATABASE_URL = $env:DATABASE_URL
$env:APP_BASE_URL = "http://127.0.0.1:4173"
$env:SESSION_SECRET = "e2e-only-session-secret-32-characters"
$env:SELLER_EMAIL = "seller@verify.local"
$env:SELLER_PASSWORD = "verify-seller-password"
$env:CLIENT_EMAIL = "client@verify.local"
$env:CLIENT_PASSWORD = "verify-client-password"
$env:E2E_SELLER_EMAIL = $env:SELLER_EMAIL
$env:E2E_SELLER_PASSWORD = $env:SELLER_PASSWORD
$env:E2E_CLIENT_EMAIL = $env:CLIENT_EMAIL
$env:E2E_CLIENT_PASSWORD = $env:CLIENT_PASSWORD

# The smoke deliberately runs with both integrations unconfigured.
$env:MODEL_API_KEY = ""
$env:MODEL_NAME = ""
$env:MODEL_BASE_URL = ""
$env:PAYPAL_CLIENT_ID = ""
$env:PAYPAL_CLIENT_SECRET = ""

if ($BrowserChannel -ne "") {
  $env:E2E_BROWSER_CHANNEL = $BrowserChannel
}

function Invoke-Step {
  param(
    [string]$Name,
    [string]$WorkDir,
    [scriptblock]$Action
  )
  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  Push-Location $WorkDir
  try {
    & $Action
    if ($LASTEXITCODE -ne 0) {
      throw "$Name failed with exit code $LASTEXITCODE"
    }
  }
  finally {
    Pop-Location
  }
}

function Wait-ForDatabase {
  Write-Host ""
  Write-Host "==> database readiness probe (pg_isready)" -ForegroundColor Cyan
  for ($attempt = 1; $attempt -le 60; $attempt++) {
    & docker compose -f $ComposeFile -p $Project exec -T db pg_isready -U scopebridge -d scopebridge_verify *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "OK database ready" -ForegroundColor Green
      return
    }
    Start-Sleep -Seconds 2
  }
  & docker compose -f $ComposeFile -p $Project logs --tail 30 db
  throw "database did not become ready within 120 seconds"
}

try {
  Invoke-Step "database start (isolated volume, port 55434)" $Repo {
    & docker compose -f $ComposeFile -p $Project up -d
  }
  Wait-ForDatabase

  Invoke-Step "uv sync" $Backend { & uv sync }
  Invoke-Step "alembic upgrade head" $Backend { & uv run alembic upgrade head }
  Invoke-Step "seed verify accounts" $Backend { & uv run python -m app.seed }

  Invoke-Step "pnpm install" $Frontend { & pnpm install --frozen-lockfile }
  if ((-not $SkipBrowserInstall) -and ($BrowserChannel -eq "")) {
    Invoke-Step "playwright install chromium" $Frontend { & pnpm exec playwright install chromium }
  }

  Invoke-Step "playwright smoke" $Frontend { & pnpm test:e2e }

  Write-Host ""
  Write-Host "Smoke passed." -ForegroundColor Green
  Write-Host "Isolated stack: project=$Project, port=55434, database=scopebridge_verify"
  Write-Host "HTML report: frontend/e2e-report/index.html"
  exit 0
}
catch {
  Write-Host ""
  Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "The isolated stack and its volume were left in place; nothing was deleted." -ForegroundColor Yellow
  exit 1
}
