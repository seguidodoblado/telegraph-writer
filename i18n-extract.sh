#!/bin/sh
# Regenera po/telegraph-writer.pot a partir de telegraph_writer.py (strings
# envueltos en _() o ngettext()) y actualiza las traducciones existentes
# (po/*.po) con las cadenas nuevas. Ejecutar a mano cada vez que se añade o
# cambia un texto de la interfaz. Portado de Bloguero (i18n-extract.sh).
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
domain=telegraph-writer

command -v xgettext >/dev/null 2>&1 || { echo "Falta xgettext (instala gettext)." >&2; exit 1; }
command -v msgmerge >/dev/null 2>&1 || { echo "Falta msgmerge (instala gettext)." >&2; exit 1; }

version=$(sed -n '1s/^[^ ]* (\([^)-]*\).*/\1/p' "$base/debian/changelog")

xgettext \
    --language=Python \
    --keyword=_ --keyword=ngettext:1,2 \
    --from-code=UTF-8 \
    --package-name="$domain" \
    --package-version="$version" \
    --msgid-bugs-address=jose.antonio.seguido@gmail.com \
    --output="$base/po/$domain.pot" \
    "$base/telegraph_writer.py"
echo "Plantilla actualizada: po/$domain.pot"

for po in "$base"/po/*.po; do
    [ -e "$po" ] || continue
    msgmerge --update --backup=off "$po" "$base/po/$domain.pot"
    echo "Actualizado $po (revisa las cadenas marcadas como fuzzy o nuevas)"
done
