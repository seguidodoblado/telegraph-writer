# Empaquetado Debian

## Dependencias

```bash
sudo apt install dpkg-dev python3-venv lintian
```

Como `python3-pyside6` no está disponible en todas las versiones de Ubuntu/Mint, el entorno virtual del proyecto incluye PySide6 dentro del paquete.

## Construcción local

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6
./build-deb.sh
sudo apt install ../telegraph-writer_2.1.2-2_all.deb
lintian ../telegraph-writer_2.1.2-2_all.deb
```

El entorno `.venv` y la carpeta temporal `.deb-stage` están excluidos por `.gitignore`.

## GitHub Release

Usa la etiqueta y el título correspondientes a la versión indicada en `APP_VERSION` y adjunta el `.deb`.

## PPA de Launchpad

Launchpad necesita el paquete fuente, no el `.deb` binario:

```bash
debuild -S -sa
dput ppa:seguidodoblado/telegraph-writer ../telegraph-writer_2.1.0-1_source.changes
```
