# Solución de problemas

## GitHub rechaza un archivo grande

No subas `.deb-stage/`: contiene archivos temporales del paquete. El `.gitignore` ya lo excluye.

## Launchpad rechaza la clave SSH

Si aparece `Permission denied (publickey)`, carga la clave en el agente SSH:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/seguidodoblado
```

Si funcionaba antes y deja de hacerlo, reiniciar la sesión del sistema suele volver a cargar el agente.

## Error al subir imágenes

Telegra.ph ha deshabilitado las nuevas subidas. Telegraph Writer usa Catbox. Comprueba la extensión, el tamaño y la conexión de red.

## Advertencia al publicar

Si aparece una advertencia, el documento ya tiene un `current_path`. Usa **Actualizar** para no crear un duplicado.

## Iconos ausentes

El archivo `telegraph-writer.svg` debe estar en la raíz del proyecto para que el lanzador y el diálogo Acerca de puedan utilizarlo.

## Error con el access token

Comprueba el token desde **Ajustes** y usa **Comprobar conexión**. La configuración se guarda en `~/.config/telegraph-writer/config.json`.
