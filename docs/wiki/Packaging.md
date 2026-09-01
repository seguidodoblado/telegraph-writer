# Empaquetado Debian

## Dependencias

```bash
sudo apt install dpkg-dev lintian
```

El paquete utiliza las dependencias GTK4/PyGObject proporcionadas por el sistema y no incluye un entorno virtual.

## Construcción local

```bash
./build-deb.sh
sudo apt install ../telegraph-writer_2.2.0-1_all.deb
lintian ../telegraph-writer_2.2.0-1_all.deb
```

El entorno `.venv` y la carpeta temporal `.deb-stage` están excluidos por `.gitignore`.

## GitHub Release

La versión se obtiene automáticamente de la primera entrada de `debian/changelog`; no hay que editar una constante de versión.

## PPA de Launchpad

Launchpad necesita el paquete fuente, no el `.deb` binario:

```bash
debuild -S -sa
dput ppa:seguidodoblado/telegraph-writer ../telegraph-writer_2.1.0-1_source.changes
```
