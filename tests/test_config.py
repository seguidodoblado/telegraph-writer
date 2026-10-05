import os
import stat
from pathlib import Path

from telegraph_writer import config


def test_the_tests_never_use_the_real_home():
    real = Path(os.path.expanduser("~")).parent / os.environ.get("USER", "")
    assert str(config.CONFIG_FILE).startswith(os.environ["HOME"])
    assert str(config.DRAFT_DIR).startswith(os.environ["HOME"])
    assert not str(config.CONFIG_FILE).startswith(str(real) + "/.config") or str(real) == os.environ["HOME"]


def use_file(monkeypatch, tmp_path: Path) -> Path:
    path = tmp_path / "telegraph-writer" / "config.json"
    monkeypatch.setattr(config, "CONFIG_FILE", path)
    return path


def test_a_missing_or_broken_file_reads_as_empty(monkeypatch, tmp_path):
    path = use_file(monkeypatch, tmp_path)
    assert config.read_config() == {}
    path.parent.mkdir()
    path.write_text("no es json")
    assert config.read_config() == {}
    path.write_text("[1, 2]")
    assert config.read_config() == {}


def test_write_then_read_keeps_the_settings_and_the_file_is_private(monkeypatch, tmp_path):
    path = use_file(monkeypatch, tmp_path)
    config.write_config({"access_token": "secreto", "draft_dir": "~/Borradores"})
    assert config.read_config() == {"access_token": "secreto", "draft_dir": "~/Borradores"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_language_and_theme_ignore_unknown_values(monkeypatch, tmp_path):
    use_file(monkeypatch, tmp_path)
    assert config.language() is None and config.dark_mode() is None
    config.write_config({"language": "en", "dark_mode": True})
    assert config.language() == "en" and config.dark_mode() is True
    config.write_config({"language": "klingon", "dark_mode": "si"})
    assert config.language() is None and config.dark_mode() is None
    config.write_config({"language": None, "dark_mode": None})           # volver a «Sistema»
    assert config.language() is None and config.dark_mode() is None
