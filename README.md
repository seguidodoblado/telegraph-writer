# Telegraph Writer

Aplicación de escritorio para crear, editar y publicar artículos en [Telegra.ph](https://telegra.ph/). Incluye un editor Markdown sencillo, gestión de borradores locales y una interfaz gráfica basada en Qt.

## Características

- Crear y publicar artículos nuevos en Telegra.ph.
- Editar y actualizar artículos ya publicados.
- Consultar y abrir los artículos de una cuenta.
- Escribir usando Markdown y revisar el resultado en el navegador.
- Guardar borradores localmente en archivos Markdown.
- Elegir entre modo claro y modo oscuro.
- Atajos de teclado para las operaciones habituales.

## Requisitos

- Linux con Python 3.10 o posterior.
- `python3-venv` para crear el entorno virtual.
- Una cuenta de Telegra.ph y su access token.

La dependencia de Python, [PySide6](https://pypi.org/project/PySide6/), se instala automáticamente durante la instalación.

## Instalación recomendada

El instalador prepara la aplicación, crea un entorno virtual e instala un lanzador de escritorio:

```bash
git clone https://github.com/seguidodoblado/telegraph-writer.git
cd telegraph-writer
./install.sh
```

El instalador puede solicitar la contraseña de `sudo` para instalar la aplicación en `/opt/telegraph-writer`. Debe ejecutarse con un usuario normal, no como `root`.

Después de la instalación, abre **Telegraph Writer** desde el menú de aplicaciones. También puedes ejecutarlo directamente:

```bash
/home/USUARIO/.venvs/telegraph-writer/bin/python \
  /opt/telegraph-writer/telegraph_writer_qt.py
```

Sustituye `USUARIO` por el nombre de tu usuario del sistema.

## Instalación manual

Si prefieres no utilizar el instalador:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python telegraph_writer_qt.py
```

## Configuración

1. Abre **Ajustes**.
2. Introduce el access token de tu cuenta de Telegra.ph.
3. Guarda la configuración.

El token se almacena localmente en `~/.config/telegraph-writer/config.json` y no se incluye en los artículos guardados ni en el repositorio.

## Flujo de trabajo

- Usa **Nuevo** para empezar un artículo.
- Usa **Guardar** para conservar una copia local en Markdown.
- Usa **Publicar** cuando el artículo todavía no exista en Telegra.ph.
- Usa **Actualizar** para aplicar cambios a un artículo ya publicado.
- Si se intenta publicar un artículo ya existente, la aplicación lo bloquea para evitar crear un duplicado.
- **Vista previa** abre una representación del artículo en el navegador.

## Seguridad

El access token permite modificar los artículos de la cuenta. No lo compartas ni subas `~/.config/telegraph-writer/config.json` a un repositorio.

## Actualización

Si instalaste la aplicación con `install.sh`, vuelve a ejecutar el instalador desde una copia actualizada del repositorio. Para actualizar manualmente:

```bash
cd /opt/telegraph-writer
sudo git pull --ff-only
```

## Licencia

Consulta el archivo [`LICENSE`](LICENSE) incluido en el repositorio.
