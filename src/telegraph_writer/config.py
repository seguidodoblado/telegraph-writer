"""Rutas y ajustes del usuario: ~/.config/telegraph-writer/config.json y la carpeta de borradores."""
import json
import os
from pathlib import Path

LANGUAGES = ("es", "en")   # idiomas que se pueden elegir en Ajustes (None: el del sistema)
CONFIG_FILE = Path.home() / ".config" / "telegraph-writer" / "config.json"
DRAFT_DIR = Path.home() / "Telegra.ph"


def read_config():
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return config if isinstance(config, dict) else {}


def write_config(config):
    """Escribe la configuración de forma atómica y solo legible por el usuario:
    contiene el access token (y, al reiniciar para cambiar de tema o de idioma, el borrador en curso)."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_name(CONFIG_FILE.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, CONFIG_FILE)


def language():
    """El idioma elegido, o None para seguir el del sistema (un valor desconocido se ignora)."""
    value = read_config().get("language")
    return value if value in LANGUAGES else None


def dark_mode():
    """El tema elegido (True oscuro, False claro), o None para seguir el del sistema."""
    value = read_config().get("dark_mode")
    return value if isinstance(value, bool) else None
