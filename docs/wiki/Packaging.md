# Empaquetado Debian

## Dependencias

```bash
sudo apt install devscripts debhelper dh-python dh-virtualenv python3-all python3-venv lintian
```

Como `python3-pyside6` no está disponible en todas las versiones de Ubuntu/Mint, `dh-virtualenv` instala PySide6 desde `requirements.txt` dentro del paquete.

## Construcción local

```bash
debuild -us -uc -b
sudo apt install ../telegraph-writer_2.1.0-1_all.deb
lintian ../telegraph-writer_2.1.0-1_all.deb
```

Los artefactos generados de `debian/` están excluidos por `.gitignore`.

## GitHub Release

Usa la etiqueta `v2.1.0`, el título `Telegraph Writer 2.1.0` y adjunta el `.deb`.

## PPA de Launchpad

Launchpad necesita el paquete fuente, no el `.deb` binario:

```bash
debuild -S -sa
dput ppa:seguidodoblado/telegraph-writer ../telegraph-writer_2.1.0-1_source.changes
```

