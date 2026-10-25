#!/usr/bin/env bash
# Firma e notarizzazione macOS (Fase 6.3).
#
# Segreti attesi (GitHub Actions):
#   APPLE_CERT_P12_BASE64     → certificato "Developer ID Application" in base64
#   APPLE_CERT_PASSWORD       → password del .p12
#   APPLE_TEAM_ID             → team id Apple
#   APPLE_ID                  → email Apple ID
#   APPLE_APP_PASSWORD        → app-specific password
#
# Senza certificato lo script esce 0 e non firma: la release resta utilizzabile
# (Gatekeeper chiederà di autorizzare l'app).
set -euo pipefail

if [ -z "${APPLE_CERT_P12_BASE64:-}" ]; then
  echo "Firma macOS saltata: APPLE_CERT_P12_BASE64 non impostata."
  exit 0
fi

KEYCHAIN="$RUNNER_TEMP/signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -hex 16)"
echo "$APPLE_CERT_P12_BASE64" | base64 --decode > "$RUNNER_TEMP/cert.p12"

security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security set-keychain-settings -lut 21600 "$KEYCHAIN"
security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN"
security import "$RUNNER_TEMP/cert.p12" -k "$KEYCHAIN" -P "$APPLE_CERT_PASSWORD" \
  -T /usr/bin/codesign -T /usr/bin/security
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN" >/dev/null
identity="$(security find-identity -v -p codesigning "$KEYCHAIN" | awk '/Developer ID Application/ {print $2; exit}')"
if [ -z "$identity" ]; then
  echo "nessuna identità Developer ID trovata nel certificato" >&2
  exit 1
fi

for app in dist/pdfbook dist/pdfbook-gui; do
  [ -d "$app" ] || continue
  # --deep firma anche i binari annidati; --options runtime abilita l'hardened runtime.
  codesign --force --deep --options runtime --timestamp \
    --sign "$identity" --keychain "$KEYCHAIN" "$app"/* 2>/dev/null || \
    codesign --force --deep --options runtime --timestamp \
      --sign "$identity" --keychain "$KEYCHAIN" "$app"
done

ARCHIVE="LitteraLit-macOS.tar.gz"
if [ -f "$ARCHIVE" ]; then
  xcrun notarytool submit "$ARCHIVE" \
    --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" --wait
  xcrun stapler staple dist/pdfbook-gui 2>/dev/null || true
  # La notarizzazione vale sull'archivio: si ricrea dopo la staple, se possibile.
  tar -czf "$ARCHIVE" -C dist pdfbook pdfbook-gui
fi

security delete-keychain "$KEYCHAIN" || true
echo "Firma/notarizzazione macOS completata."
