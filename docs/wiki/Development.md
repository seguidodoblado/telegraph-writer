# Desarrollo y arquitectura

La aplicación está concentrada en `telegraph_writer_qt.py` y utiliza Python 3 y PySide6.

## Componentes

- Configuración: `load_config()` y `save_config()`.
- API Telegra.ph: `telegraph_api()`.
- Imágenes: `upload_image()` mediante Catbox.
- Markdown: `inline_to_nodes()`, `markdown_to_nodes()`, `node_to_markdown()`.
- Vista previa: `nodes_to_html()` y `preview()`.
- Red asíncrona: `ApiWorker` e `ImageUploadWorker`.
- Interfaz: `TelegraphWriter`, `SettingsDialog` e iconos SVG.

La explicación extensa está en `docs/ARCHITECTURE.md`.

