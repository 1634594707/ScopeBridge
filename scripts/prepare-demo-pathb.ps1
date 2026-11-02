$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Repo "backend"
$PathbDb = "scopebridge_pathb"

Push-Location $Backend
try {
  Write-Host "==> create/reuse isolated database $PathbDb" -ForegroundColor Cyan
  $pathbUrl = (& uv run python ../scripts/create_pathb_db.py).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($pathbUrl)) {
    throw "could not create the isolated Path B database"
  }

  # Process-local only; .env is never written.
  $env:DATABASE_URL = $pathbUrl

  Write-Host "==> alembic upgrade head on $PathbDb" -ForegroundColor Cyan
  & uv run alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw "alembic failed on $PathbDb" }

  Write-Host "==> seed Path B confirmed quote" -ForegroundColor Cyan
  & uv run python -m app.seed --pathb
  if ($LASTEXITCODE -ne 0) { throw "Path B seed failed" }

  Write-Host ""
  Write-Host "Path B database is ready: $PathbDb" -ForegroundColor Green
  Write-Host "The demo database and its recorded sandbox snapshot were not modified."
  Write-Host ""
  Write-Host "To run the API against Path B without editing .env, use a new terminal:"
  Write-Host @'
  $line = Get-Content .env | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
  $env:DATABASE_URL = ($line -replace '/scopebridge', '/scopebridge_pathb')
  cd backend
  uv run uvicorn app.main:app --port 8000
'@
  Write-Host ""
  Write-Host "Then start the frontend/preview as usual and sign in with CLIENT_EMAIL / CLIENT_PASSWORD."
  Write-Host "For Path A recording, use the normal .env DATABASE_URL (the demo database)."
}
finally {
  Pop-Location
}
