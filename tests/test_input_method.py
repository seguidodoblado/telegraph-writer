import importlib

import telegraph_writer


def test_ibus_se_cambia_a_simple(monkeypatch):
    monkeypatch.setenv("GTK_IM_MODULE", "ibus")
    importlib.reload(telegraph_writer)
    assert telegraph_writer._os.environ["GTK_IM_MODULE"] == "simple"


def test_otros_valores_no_cambian(monkeypatch):
    monkeypatch.setenv("GTK_IM_MODULE", "fcitx")
    importlib.reload(telegraph_writer)
    assert telegraph_writer._os.environ["GTK_IM_MODULE"] == "fcitx"


def test_sin_variable_no_se_crea(monkeypatch):
    monkeypatch.delenv("GTK_IM_MODULE", raising=False)
    importlib.reload(telegraph_writer)
    assert "GTK_IM_MODULE" not in telegraph_writer._os.environ
