# Flujo reproducible del proyecto

Esta guía resume cómo repetir el proceso completo desde un clon limpio.

## 1. Obtener el código

```bash
git clone https://git.launchpad.net/telegraph-writer
cd telegraph-writer
```

Para desarrollo también puede usarse el repositorio de GitHub.

## 2. Ejecutar desde el código fuente

```bash
sudo apt install python3 python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python telegraph_writer_qt.py
```

## 3. Configurar GitHub y Launchpad

```bash
git remote add origin https://github.com/seguidodoblado/telegraph-writer.git
git remote add launchpad git+ssh://seguidodoblado@git.launchpad.net/telegraph-writer
git push -u origin main
git push launchpad main
```

La rama de seguimiento de VS Code se fija con `git push -u origin main`. Los siguientes pushes de VS Code irán a GitHub; Launchpad se actualiza explícitamente con `git push launchpad main`.

## 4. Preparar el paquete Debian

En Ubuntu/Linux Mint instala:

```bash
sudo apt install devscripts debhelper dh-python dh-virtualenv \
  python3-all python3-venv lintian
```

`python3-pyside6` no está disponible en todas las versiones de Ubuntu/Mint. Por eso este proyecto usa `dh-virtualenv` para incluir PySide6 en el paquete.

Construye el paquete:

```bash
debuild -us -uc -b
```

El `.deb` aparecerá en el directorio superior:

```text
../telegraph-writer_2.1.0-1_all.deb
```

Instálalo localmente:

```bash
sudo apt install ../telegraph-writer_2.1.0-1_all.deb
```

Compruébalo:

```bash
lintian ../telegraph-writer_2.1.0-1_all.deb
```

## 5. Publicar en GitHub

Crea una Release con la etiqueta `v2.1.0`, título `Telegraph Writer 2.1.0` y adjunta el `.deb`. El repositorio contiene código y metadatos; el entorno virtual de `dh-virtualenv` no debe subirse.

## 6. Publicar en Launchpad

Launchpad no recibe el `.deb` binario para el PPA. Debe recibir un paquete fuente:

```bash
debuild -S -sa
dput ppa:seguidodoblado/telegraph-writer \
  ../telegraph-writer_2.1.0-1_source.changes
```

Launchpad construye el `.deb` para las series de Ubuntu configuradas en el PPA.

## 7. Repetir una nueva versión

1. Actualiza `APP_VERSION` en `telegraph_writer_qt.py`.
2. Cambia la versión y el texto de `debian/changelog`.
3. Actualiza el README si cambia el procedimiento de instalación.
4. Haz commit y push a GitHub.
5. Haz push a Launchpad.
6. Construye y prueba el `.deb`.
7. Crea la Release y, si procede, sube el paquete fuente al PPA.
