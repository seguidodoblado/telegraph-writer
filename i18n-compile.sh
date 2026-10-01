#!/bin/sh
# Compila po/*.po a los .mo que carga telegraph_writer.py
# (i18n/<idioma>/LC_MESSAGES/). El idioma fuente (es) no necesita catálogo:
# gettext ya devuelve el msgid tal cual. Portado de Bloguero (i18n-compile.sh).
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
domain=telegraph-writer

command -v msgfmt >/dev/null 2>&1 || { echo "Falta msgfmt (instala gettext)." >&2; exit 1; }

for po in "$base"/po/*.po; do
    [ -e "$po" ] || continue
    lang=$(basename "$po" .po)
    out_dir="$base/i18n/$lang/LC_MESSAGES"
    mkdir -p "$out_dir"
    msgfmt --check "$po" -o "$out_dir/$domain.mo"
    echo "Compilado $po -> $out_dir/$domain.mo"
done
