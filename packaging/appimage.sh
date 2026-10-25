#!/usr/bin/env bash
# Costruisce un AppImage della GUI (Fase 6.3).
# Uso: bash packaging/appimage.sh [dist/pdfbook-gui]
# Richiede: dist/pdfbook-gui prodotto da PyInstaller, curl, un Linux x86_64.
set -euo pipefail

APP_DIR="${1:-dist/pdfbook-gui}"
APPDIR="LitteraLit.AppDir"
ICON_SRC="packaging/litteralit.svg"
VERSION="${VERSION:-0.0.0}"

if [ ! -x "$APP_DIR/pdfbook-gui" ]; then
  echo "errore: $APP_DIR/pdfbook-gui non trovato (esegui prima PyInstaller)" >&2
  exit 1
fi

rm -rf "$APPDIR" LitteraLit-*.AppImage
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/litteralit" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/scalable/apps"

cp -a "$APP_DIR/." "$APPDIR/usr/lib/litteralit/"
cp "$ICON_SRC" "$APPDIR/litteralit.svg"
cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/scalable/apps/litteralit.svg"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/litteralit/pdfbook-gui" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/litteralit.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LitteraLit
Comment=Traduzione di libri PDF con conservazione del layout
Exec=litteralit
Icon=litteralit
Categories=Office;Publishing;
Terminal=false
X-AppImage-Version=${VERSION}
EOF
cp "$APPDIR/litteralit.desktop" "$APPDIR/usr/share/applications/litteralit.desktop"

# appimagetool in modalità "extract and run": nessun FUSE richiesto in CI.
curl -fsSL -o appimagetool \
  "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x appimagetool

ARCH=x86_64 ./appimagetool --appimage-extract-and-run --no-appstream "$APPDIR" \
  "LitteraLit-${VERSION}-x86_64.AppImage"

ls -lh LitteraLit-*.AppImage
