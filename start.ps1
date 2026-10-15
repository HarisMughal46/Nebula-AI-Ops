# Launches Nebula AI Ops backend (:8010) and frontend (:3010) as hidden processes.
$root = $PSScriptRoot
$be = Start-Process -WindowStyle Hidden -PassThru -FilePath "uv" `
  -ArgumentList "run","uvicorn","app.main:app","--host","127.0.0.1","--port","8010" `
  -WorkingDirectory "$root\backend" `
  -RedirectStandardOutput "$env:TEMP\nebula-backend.log" -RedirectStandardError "$env:TEMP\nebula-backend.err.log"
if (-not (Test-Path "$root\frontend\.next\BUILD_ID")) {
  Push-Location "$root\frontend"; npm run build; Pop-Location
}
$fe = Start-Process -WindowStyle Hidden -PassThru -FilePath "cmd.exe" `
  -ArgumentList "/c","npm run start" -WorkingDirectory "$root\frontend" `
  -RedirectStandardOutput "$env:TEMP\nebula-frontend.log" -RedirectStandardError "$env:TEMP\nebula-frontend.err.log"
Write-Host "Backend PID $($be.Id) -> http://127.0.0.1:8010"
Write-Host "Frontend PID $($fe.Id) -> http://localhost:3010"
