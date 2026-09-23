#!/bin/sh
set -eu

base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
stage="$base/.deb-stage"
version=$(sed -n '1s/^[^ ]* (\([^)]*\)).*/\1/p' "$base/debian/changelog")
test -n "$version" || { echo "No se pudo leer la versión de debian/changelog" >&2; exit 1; }
package="$base/../telegraph-writer_${version}_all.deb"

rm -rf "$stage"
mkdir -p "$stage/DEBIAN" "$stage/opt/telegraph-writer" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps"
cp "$base/telegraph_writer.py" "$stage/opt/telegraph-writer/"
printf '%s\n' "$version" > "$stage/opt/telegraph-writer/VERSION"
cp "$base/telegraph-writer.svg" "$stage/opt/telegraph-writer/"
cp "$base/debian/telegraph-writer-launcher" "$stage/usr/bin/telegraph-writer"
cp "$base/debian/telegraph-writer.desktop" "$stage/usr/share/applications/"
cp "$base/telegraph-writer.svg" "$stage/usr/share/icons/hicolor/scalable/apps/"

cat > "$stage/DEBIAN/control" <<EOF
Package: telegraph-writer
Version: $version
Section: editors
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-4.0 (>= 4.10)
Maintainer: seguidodoblado <jose.antonio.seguido@gmail.com>
Description: Cliente de escritorio para Telegra.ph
 Editor Markdown para crear, publicar y actualizar artículos de Telegra.ph.
EOF

chmod 755 "$stage/usr/bin/telegraph-writer" "$stage/opt/telegraph-writer/telegraph_writer.py"
dpkg-deb --build --root-owner-group "$stage" "$package"
echo "Paquete generado: $package"
