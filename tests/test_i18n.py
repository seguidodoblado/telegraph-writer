import gettext
import string

import pytest

from telegraph_writer import i18n
from telegraph_writer.i18n import _, ngettext

MO = i18n.LOCALE_DIR / "en" / "LC_MESSAGES" / f"{i18n.DOMAIN}.mo"
needs_catalog = pytest.mark.skipif(not MO.exists(), reason="Falta compilar po/en.po (ver po/README.md)")


def english():
    return gettext.translation(i18n.DOMAIN, localedir=str(i18n.LOCALE_DIR), languages=["en"])


def placeholders(text):
    return {name for _literal, name, _spec, _conv in string.Formatter().parse(text) if name}


def test_spanish_is_the_source_language_and_needs_no_catalog():
    assert _("Archivo") == "Archivo"
    assert ngettext("{count} artículo", "{count} artículos", 1) == "{count} artículo"
    assert ngettext("{count} artículo", "{count} artículos", 3) == "{count} artículos"


@needs_catalog
def test_english_catalog_translates():
    translation = english()
    assert translation.gettext("Archivo") == "File"
    assert translation.gettext("Publicar") == "Publish"
    assert translation.gettext("Negrita (**texto**)") == "Bold (**text**)"
    assert translation.gettext("Sistema") == "System"


@needs_catalog
def test_english_plural_forms():
    translation = english()
    assert translation.ngettext("{count} artículo", "{count} artículos", 1) == "{count} article"
    assert translation.ngettext("{count} artículo", "{count} artículos", 3) == "{count} articles"


@needs_catalog
def test_translator_credits_entry_is_filled():
    assert "@" in english().gettext("translator-credits")


@needs_catalog
def test_every_translation_keeps_the_placeholders_of_the_original():
    """Si el inglés perdiera un {nombre}, .format() fallaría en pleno uso."""
    translation = english()
    messages = [m for m in translation._catalog if isinstance(m, str) and m]
    assert messages
    for message in messages:
        assert placeholders(translation.gettext(message)) == placeholders(message), message
