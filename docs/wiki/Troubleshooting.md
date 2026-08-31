# Solución de problemas

## GitHub rechaza un archivo grande

No subas `.venv/` ni `.deb-stage/`: contienen el entorno virtual y los archivos temporales del paquete. El `.gitignore` ya los excluye.

## Error al subir imágenes

Telegra.ph ha deshabilitado las nuevas subidas. Telegraph Writer usa Catbox. Comprueba la extensión, el tamaño y la conexión de red.

## Advertencia al publicar

Si aparece una advertencia, el documento ya tiene un `current_path`. Usa **Actualizar** para no crear un duplicado.

## Iconos ausentes

El archivo `telegraph-writer.svg` debe estar en la raíz del proyecto para que el lanzador y el diálogo Acerca de puedan utilizarlo.

## Error con el access token

Comprueba el token desde **Ajustes** y usa **Comprobar conexión**. La configuración se guarda en `~/.config/telegraph-writer/config.json`.
