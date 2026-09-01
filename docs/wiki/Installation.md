# Instalación

## Paquete `.deb` desde GitHub

Descarga el paquete desde [Releases](https://github.com/seguidodoblado/telegraph-writer/releases):

```bash
sudo apt install ./telegraph-writer_2.1.2-1_all.deb
```

El paquete utiliza Python 3 y GTK4/PyGObject del sistema y crea el lanzador de escritorio.

## Código fuente

```bash
git clone https://git.launchpad.net/telegraph-writer
cd telegraph-writer
sudo apt install python3 python3-gi gir1.2-gtk-4.0
python3 telegraph_writer_gtk.py
```

Configura el access token desde **Ajustes**. Desde ese mismo diálogo también puedes elegir la carpeta donde se guardan los borradores locales. La ubicación predeterminada es `~/Telegra.ph`.

El access token y la carpeta seleccionada se guardan en `~/.config/telegraph-writer/config.json`.
