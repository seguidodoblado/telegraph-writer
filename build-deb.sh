#!/bin/sh
set -eu

base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
stage="$base/.deb-stage"
version=$(dpkg-parsechangelog -S Version)
package="$base/../telegraph-writer_${version}_all.deb"

test -x "$base/.venv/bin/python" || {
    echo "Falta .venv. Ejecuta: python3 -m venv .venv && .venv/bin/pip install PySide6" >&2
    exit 1
}

rm -rf "$stage"
mkdir -p "$stage/DEBIAN" "$stage/opt/venvs/telegraph-writer" "$stage/usr/share/telegraph-writer" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps"
cp -a "$base/.venv/." "$stage/opt/venvs/telegraph-writer/"
cp "$base/telegraph_writer_qt.py" "$stage/usr/share/telegraph-writer/"
cp "$base/telegraph-writer.svg" "$stage/usr/share/telegraph-writer/"
cp "$base/debian/telegraph-writer-launcher" "$stage/usr/bin/telegraph-writer"
cp "$base/debian/telegraph-writer.desktop" "$stage/usr/share/applications/"
cp "$base/telegraph-writer.svg" "$stage/usr/share/icons/hicolor/scalable/apps/"

cat > "$stage/DEBIAN/control" <<EOF
Package: telegraph-writer
Version: $version
Section: editors
Priority: optional
Architecture: all
Depends: python3
Maintainer: seguidodoblado <jose.antonio.seguido@gmail.com>
Description: Cliente de escritorio para Telegra.ph
 Editor Markdown para crear, publicar y actualizar artículos de Telegra.ph.
EOF

chmod 755 "$stage/usr/bin/telegraph-writer" "$stage/usr/share/telegraph-writer/telegraph_writer_qt.py"
dpkg-deb --build --root-owner-group "$stage" "$package"
echo "Paquete generado: $package"
