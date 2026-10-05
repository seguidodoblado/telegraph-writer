import os


def main() -> None:
    from . import config, i18n

    # El idioma de Ajustes manda; con «Sistema» se recupera el $LANGUAGE original
    # (los reinicios lo heredan, así que se guarda aparte la primera vez).
    original = os.environ.setdefault("TELEGRAPH_WRITER_SYSTEM_LANGUAGE", os.environ.get("LANGUAGE", ""))
    chosen = config.language() or original
    if chosen:
        os.environ["LANGUAGE"] = chosen
    else:
        os.environ.pop("LANGUAGE", None)
    i18n.install()
    from .ui.gui import run_gui
    raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
