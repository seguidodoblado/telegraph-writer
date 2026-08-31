# Instalación

## Paquete `.deb` desde GitHub

Debido a problemas de disponibilidad de PySide6 en los repositorios usados por Launchpad, el PPA no se utiliza para distribuir esta aplicación. Descarga el paquete desde [Releases](https://github.com/seguidodoblado/telegraph-writer/releases):

```bash
sudo apt install ./telegraph-writer_2.1.2-1_all.deb
```

El paquete incluye PySide6 en un entorno virtual privado y crea el lanzador de escritorio.

## Código fuente

```bash
git clone https://git.launchpad.net/telegraph-writer
cd telegraph-writer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install PySide6
python telegraph_writer_qt.py
```

Configura el access token desde **Ajustes**. Desde ese mismo diálogo también puedes elegir la carpeta donde se guardan los borradores locales. La ubicación predeterminada es `~/Telegra.ph`.

El access token y la carpeta seleccionada se guardan en `~/.config/telegraph-writer/config.json`.
