# Firma Authenticode dei binari (Fase 6.3).
#
# In CI i segreti arrivano come variabili d'ambiente:
#   WINDOWS_CERT_BASE64  → contenuto base64 del file .pfx
#   WINDOWS_CERT_PASSWORD → password del .pfx
# Se WINDOWS_CERT_BASE64 è vuota lo script esce con codice 0 e non firma nulla:
# la release resta utilizzabile (SmartScreen avviserà).
#
# Uso: pwsh packaging/sign_windows.ps1 -Files dist/pdfbook/pdfbook.exe,dist/pdfbook-gui/pdfbook-gui.exe

param(
    [Parameter(Mandatory = $true)][string[]]$Files
)

$ErrorActionPreference = "Stop"

if (-not $env:WINDOWS_CERT_BASE64) {
    Write-Host "Firma saltata: WINDOWS_CERT_BASE64 non impostata."
    exit 0
}

$pfx = Join-Path $env:RUNNER_TEMP "codesign.pfx"
[IO.File]::WriteAllBytes($pfx, [Convert]::FromBase64String($env:WINDOWS_CERT_BASE64))

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Recurse -Filter signtool.exe |
    Where-Object { $_.FullName -like "*x64*" } |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $signtool) {
    Write-Host "signtool non trovato: firma saltata."
    exit 0
}

foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        Write-Host "salto $file (non esiste)"
        continue
    }
    & $signtool sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" `
        /f $pfx /p "$env:WINDOWS_CERT_PASSWORD" $file
    if ($LASTEXITCODE -ne 0) { throw "firma fallita per $file" }
    & $signtool verify /pa $file
}

Remove-Item $pfx -Force
Write-Host "Firma completata."
