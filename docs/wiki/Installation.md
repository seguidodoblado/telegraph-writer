# Instalación

## PPA de Launchpad

```bash
sudo add-apt-repository ppa:seguidodoblado/telegraph-writer
sudo apt update
sudo apt install telegraph-writer
```

## Paquete `.deb` desde GitHub

Descarga el paquete desde [Releases](https://github.com/seguidodoblado/telegraph-writer/releases):

```bash
sudo apt install ./telegraph-writer_2.1.0-1_all.deb
```

El paquete incluye PySide6 en un entorno virtual privado y crea el lanzador de escritorio.

## Código fuente

```bash
git clone https://git.launchpad.net/telegraph-writer
cd telegraph-writer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python telegraph_writer_qt.py
```

Configura el access token desde **Ajustes**. Se guarda en `~/.config/telegraph-writer/config.json`.

