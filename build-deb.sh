#!/bin/sh
set -eu

base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
stage="$base/.deb-stage"
version=$(sed -n '1s/^[^ ]* (\([^)]*\)).*/\1/p' "$base/debian/changelog")
test -n "$version" || { echo "No se pudo leer la versión de debian/changelog" >&2; exit 1; }
package="$base/../telegraph-writer_${version}_all.deb"

rm -rf "$stage"
doc="$stage/usr/share/doc/telegraph-writer"
mkdir -p "$stage/DEBIAN" "$stage/opt/telegraph-writer" "$stage/usr/bin" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$doc"
install -m 755 "$base/telegraph_writer.py" "$stage/opt/telegraph-writer/telegraph_writer.py"
printf '%s\n' "$version" > "$stage/opt/telegraph-writer/VERSION"
install -m 644 "$base/telegraph-writer.svg" "$stage/opt/telegraph-writer/telegraph-writer.svg"
install -m 755 "$base/debian/telegraph-writer-launcher" "$stage/usr/bin/telegraph-writer"
install -m 644 "$base/debian/telegraph-writer.desktop" "$stage/usr/share/applications/telegraph-writer.desktop"
install -m 644 "$base/telegraph-writer.svg" "$stage/usr/share/icons/hicolor/scalable/apps/telegraph-writer.svg"
cat > "$doc/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: telegraph-writer
Source: https://github.com/seguidodoblado/telegraph-writer

Files: *
Copyright: 2026 seguidodoblado <jose.antonio.seguido@gmail.com>
License: GPL-3

License: GPL-3
 En los sistemas Debian el texto completo de la licencia GNU GPL versión 3
 está disponible en /usr/share/common-licenses/GPL-3.
EOF
chmod 644 "$doc/copyright"
gzip -9n -c "$base/debian/changelog" > "$doc/changelog.Debian.gz"
chmod 644 "$doc/changelog.Debian.gz"

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

# Los permisos no deben depender del umask de quien construye el paquete.
chmod 644 "$stage/DEBIAN/control" "$stage/opt/telegraph-writer/VERSION"
find "$stage" -type d -exec chmod 755 {} +
dpkg-deb --build --root-owner-group "$stage" "$package"
echo "Paquete generado: $package"
