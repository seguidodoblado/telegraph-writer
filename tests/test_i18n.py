"""Pruebas de las traducciones (sin ventana ni red). Antes de ejecutarlas,
compila los catálogos con ./i18n-compile.sh (el .mo no se versiona).

Ejecutar desde la raíz del repositorio: python3 -m unittest discover -s tests
"""

import gettext
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import telegraph_writer as tw


class I18nTests(unittest.TestCase):
    def test_spanish_is_the_source_language_and_needs_no_catalog(self):
        self.assertEqual(tw._("Archivo"), "Archivo")
        self.assertEqual(tw.count_text(1), "1 artículo")
        self.assertEqual(tw.count_text(3), "3 artículos")

    def test_english_catalog_translates(self):
        translation = gettext.translation(tw.I18N_DOMAIN, localedir=str(tw.I18N_DIR), languages=["en"])
        self.assertEqual(translation.gettext("Archivo"), "File")
        self.assertEqual(translation.gettext("Publicar"), "Publish")
        self.assertEqual(translation.gettext("Negrita (**texto**)"), "Bold (**text**)")

    def test_english_catalog_handles_plurals(self):
        translation = gettext.translation(tw.I18N_DOMAIN, localedir=str(tw.I18N_DIR), languages=["en"])
        self.assertEqual(translation.ngettext("{count} artículo", "{count} artículos", 1), "{count} article")
        self.assertEqual(translation.ngettext("{count} artículo", "{count} artículos", 3), "{count} articles")

    def test_english_mo_file_exists(self):
        mo_path = tw.I18N_DIR / "en" / "LC_MESSAGES" / f"{tw.I18N_DOMAIN}.mo"
        self.assertTrue(mo_path.exists(), "Falta compilar po/en.po (ver po/README.md)")


if __name__ == "__main__":
    unittest.main()
