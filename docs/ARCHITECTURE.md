# Arquitectura de Telegraph Writer

Este documento explica cómo está construido el programa y qué responsabilidad tiene cada parte del código.

## Resumen

Telegraph Writer es una aplicación de escritorio Python/PySide6. La interfaz se concentra en `telegraph_writer_qt.py`, que contiene:

- la ventana principal y sus controles;
- la comunicación HTTP con Telegra.ph y Catbox;
- la conversión entre Markdown y nodos de Telegra.ph;
- el guardado de configuración y borradores;
- los hilos de trabajo para no bloquear la interfaz;
- el empaquetado visual de la vista previa.

Los SVG de `icons/` son los iconos monocromáticos de la toolbar. `telegraph-writer.svg` es el icono del lanzador de escritorio.

## Configuración y constantes

Al principio del archivo se definen el nombre y la versión (`APP_NAME`, `APP_VERSION`), las URLs de las APIs y las rutas locales:

- `API_URL`: API oficial de Telegra.ph.
- `IMAGE_UPLOAD_URL`: API de Catbox para alojar imágenes.
- `CONFIG_FILE`: `~/.config/telegraph-writer/config.json`.
- `DRAFT_DIR`: carpeta inicial `~/Telegra.ph`, donde se guardan los borradores Markdown. La carpeta se puede personalizar desde **Ajustes** y se guarda como `draft_dir` en la configuración.

`load_config()` lee el JSON de configuración. Si no existe o no se puede leer, devuelve una configuración vacía. `save_config()` escribe primero un archivo temporal, lo sustituye de forma atómica y aplica permisos `600`, para proteger el access token.

## Comunicación con servicios externos

### API de Telegra.ph

`telegraph_api(method, params, path)` construye peticiones POST codificadas como `application/x-www-form-urlencoded`. Se usa para:

- `getAccountInfo`: comprobar la cuenta;
- `getPageList`: cargar artículos;
- `getPage`: cargar el contenido de un artículo;
- `createPage`: publicar un artículo nuevo;
- `editPage`: actualizar un artículo existente.

La función valida el campo `ok` de la respuesta y convierte los errores de la API en excepciones legibles.

### Imágenes con Catbox

Telegra.ph ha deshabilitado las nuevas subidas de imágenes. `upload_image()` crea manualmente una petición `multipart/form-data` para Catbox, con los campos:

- `reqtype=fileupload`;
- `fileToUpload`: archivo binario seleccionado.

Solo se aceptan JPG, JPEG, PNG y GIF. El límite local aplicado es de 200 MB. Catbox devuelve una URL pública, que se inserta en el editor como `![](URL)`.

## Conversión Markdown ↔ Telegra.ph

Telegra.ph no recibe Markdown directamente: recibe una lista de nodos JSON. El programa tiene dos direcciones de conversión.

### Markdown a nodos

`markdown_to_nodes()` recorre el texto por líneas y reconoce:

- encabezados (`#` a `######`), convertidos a `h3` o `h4` por las limitaciones del formato de Telegra.ph;
- bloques de código con triple backtick (`pre` y `code`);
- citas (`blockquote`);
- listas ordenadas y no ordenadas (`ol`, `ul`, `li`);
- separadores (`hr`);
- párrafos y saltos de línea (`p`, `br`).

`inline_to_nodes()` convierte dentro de cada bloque los enlaces, imágenes, negritas, cursivas, tachado y código inline.

### Nodos a Markdown

`node_to_markdown()` y `nodes_to_markdown()` reconstruyen un borrador legible cuando se carga un artículo remoto. Las imágenes se convierten en referencias Markdown sin texto alternativo: `![](URL)`.

### Vista previa

`nodes_to_html()` transforma los nodos en HTML. `preview()` añade una plantilla HTML, estilos básicos y el título, guarda el resultado temporalmente en `/tmp/telegraph_writer_preview.html` y lo abre en el navegador predeterminado.

## Hilos de trabajo

Las operaciones de red no deben ejecutarse en el hilo de la interfaz. `ApiWorker` ejecuta llamadas a la API de Telegra.ph en un `QThread`; `ImageUploadWorker` hace lo mismo con Catbox.

Cada trabajador expone:

- `success`: resultado de la operación;
- `failure`: mensaje de error.

La ventana conecta esas señales a métodos como `account_loaded()`, `pages_loaded()`, `article_loaded()`, `published()`, `updated()`, `image_uploaded()` y `api_error()`.

## Ventana principal

`TelegraphWriter` mantiene el estado de edición:

- `current_path`: identifica un artículo ya publicado;
- `current_url`: URL pública del artículo;
- `current_file`: borrador Markdown local;
- `draft_dir`: carpeta seleccionada para abrir y guardar borradores;
- `dirty`: indica cambios sin guardar;
- `loading_article`: evita marcar como modificados los cambios producidos al cargar datos.

### Acciones principales

- `new_article()`: limpia el editor y elimina la identidad remota.
- `open_file()`: carga Markdown y su archivo lateral `.telegraph.json`.
- `save_file()`: guarda Markdown, título, `path` y URL.
- `publish()`: llama a `createPage`, pero se detiene si `current_path` ya existe para evitar duplicados.
- `update_article()`: exige `current_path` y llama a `editPage`.
- `insert_image()`: selecciona, sube e inserta una imagen.
- `settings()`: permite guardar y probar el access token.

La toolbar usa iconos SVG de `icons/` y conserva el texto de cada acción. Los botones de publicar, actualizar y vista previa están junto al editor, donde son acciones contextuales.

## Flujo de publicación

1. El usuario escribe título y Markdown.
2. `markdown_to_nodes()` genera el contenido JSON.
3. `publish()` llama a `createPage` si no existe `current_path`.
4. La respuesta guarda `path` y `url`.
5. Un artículo ya cargado o publicado solo puede modificarse mediante `update_article()`.

Esta separación es intencionada: evita que pulsar accidentalmente **Publicar** cree una copia duplicada.

## Empaquetado Debian

La carpeta `debian/` contiene el empaquetado fuente:

- `control`: metadatos, mantenedor y dependencias de construcción;
- `changelog`: versión y cambios de Debian;
- `rules`: instrucciones de `debhelper` y `dh-virtualenv`;
- `source/format`: formato del paquete fuente;
- `.gitignore`: evita incluir el entorno virtual generado en `debian/telegraph-writer/`.

`dh-virtualenv` instala PySide6 dentro de `/opt/venvs/telegraph-writer` durante la construcción. El wrapper `/usr/bin/telegraph-writer` ejecuta la aplicación con ese Python empaquetado. El resultado es un `.deb` autónomo, sin depender de que exista `python3-pyside6` en los repositorios del sistema.

## Archivos generados que no deben versionarse

No deben entrar en Git:

- `debian/telegraph-writer/`;
- `debian/.debhelper/`;
- `debian/files`;
- `debian/*.substvars`;
- `debian/*.debhelper`;
- entornos virtuales y `__pycache__`.

El `.deb` final se publica como artefacto de una Release de GitHub o se sube mediante un paquete fuente al PPA de Launchpad; no se guarda dentro del repositorio.
