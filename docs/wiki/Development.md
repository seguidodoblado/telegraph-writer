# Desarrollo y arquitectura

La aplicación está concentrada en `telegraph_writer.py` y utiliza Python 3, PyGObject y GTK4.

## Componentes

- Configuración: `load_config()` y `save_config()`.
- API Telegra.ph: `telegraph_api()`.
- Imágenes: `upload_image()` mediante Catbox.
- Markdown: `inline_to_nodes()`, `markdown_to_nodes()`, `node_to_markdown()`.
- Vista previa: `nodes_to_html()` y `preview()`.
- Interfaz: `TelegraphWriter`, diálogos GTK4 e iconos SVG.

La explicación extensa está en `docs/ARCHITECTURE.md`.
