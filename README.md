# Telegraph Writer

Cliente de escritorio para [Telegra.ph](https://telegra.ph/), pensado para Linux Mint y otros escritorios Linux.

## Características

- Publicar artículos en Telegra.ph.
- Editar y actualizar artículos ya publicados.
- Cargar la lista de artículos de la cuenta.
- Editor Markdown sencillo.
- Vista previa en el navegador.
- Guardado local de borradores en Markdown.
- Modo oscuro y claro.
- Fuente Ubuntu Sans.
- Access token guardado en `~/.config/telegraph-writer/config.json` con permisos 600.

## Requisitos

- Python 3.10 o posterior recomendado.
- PySide6.
- Una cuenta de Telegra.ph con access token.

## Instalación en Linux Mint

```bash
python3 -m venv ~/.venvs/telegraph-writer
source ~/.venvs/telegraph-writer/bin/activate
pip install -r requirements.txt
```

Después ejecuta:

```bash
python telegraph_writer_qt.py
```

## Configuración

La primera vez, abre **Ajustes** e introduce tu access token de Telegra.ph. El token se guarda localmente y no forma parte del repositorio.

## Lanzador de escritorio

El proyecto incluye `telegraph-writer.desktop`, preparado para la instalación que hemos utilizado en Linux Mint (`~/Escritorio` y `~/.venvs/telegraph-writer`). Si clonas el proyecto en otra ubicación, adapta la línea `Exec` del lanzador.

El icono está en `telegraph-writer.svg`.

## Seguridad

**No subas nunca `~/.config/telegraph-writer/config.json` al repositorio.** El access token da acceso de edición a tus artículos de Telegra.ph.

## Licencia

Consulta `LICENSE`, incluida en este repositorio.
