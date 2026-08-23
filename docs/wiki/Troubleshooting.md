# Solución de problemas

## GitHub rechaza un archivo grande

No subas `debian/telegraph-writer/`: contiene el entorno virtual generado por `dh-virtualenv`. El `.gitignore` ya lo excluye.

## Error al subir imágenes

Telegra.ph ha deshabilitado las nuevas subidas. Telegraph Writer usa Catbox. Comprueba la extensión, el tamaño y la conexión de red.

## Advertencia al publicar

Si aparece una advertencia, el documento ya tiene un `current_path`. Usa **Actualizar** para no crear un duplicado.

## Iconos ausentes

La carpeta `icons/` debe estar junto a `telegraph_writer_qt.py` y debe incluirse en el paquete.

## Error con el access token

Comprueba el token desde **Ajustes** y usa **Comprobar conexión**. La configuración se guarda en `~/.config/telegraph-writer/config.json`.

