<p align="right"><a href="PRIVACY.en.md">🇺🇸 English</a></p>

# Política de privacidad

Última actualización: 5 de octubre de 2026.

Telegraph Writer es una aplicación de escritorio de uso personal. No tiene servidor ni cuenta propios y su autor
no recibe ningún dato de quien la usa. Solo se comunica con los servicios que tú usas desde ella.

## Qué datos trata

- **Tus artículos:** el título, el autor y el texto en Markdown que escribes.
- **Tu access token de Telegra.ph**, que generas tú mismo y que permite publicar y editar artículos de tu cuenta.
- **Las imágenes** que eliges insertar.
- **Tus ajustes:** carpeta de borradores, idioma y tema de la interfaz.

## Dónde se guardan

En tu equipo:

- Los ajustes y el access token, en `~/.config/telegraph-writer/config.json`, con permisos de lectura solo para
  tu usuario. Al reiniciar la aplicación para cambiar el idioma o el tema, ese archivo guarda también el
  borrador en curso hasta que la aplicación vuelve a abrirse.
- Los borradores en Markdown, en `~/Telegra.ph/` o en la carpeta que elijas en Ajustes.

## Con quién se comparte

Solo con los servicios que la aplicación usa cuando tú se lo pides:

- **[Telegra.ph](https://telegra.ph/)** (`api.telegra.ph`): al publicar, actualizar, cargar o listar artículos
  se envían el access token y el contenido del artículo. Quedan sujetos a las condiciones de Telegra.ph, y los
  artículos publicados son públicos.
- **[Catbox](https://catbox.moe/)** (`catbox.moe`): al subir una imagen se envía el archivo de la imagen. Queda
  alojada en un servicio externo, fuera del control de la aplicación y sujeta a las condiciones de Catbox.

La aplicación no incluye analítica, telemetría ni publicidad.

## Cómo borrar tus datos

Elimina `~/.config/telegraph-writer/` (ajustes y access token) y la carpeta de borradores que ya no quieras.
Desinstalar la aplicación no borra esos datos por sí solo. Los artículos publicados se gestionan desde
Telegra.ph, y las imágenes subidas a Catbox, desde Catbox.

## Cambios en esta política

Si cambia, se actualizará este documento y la fecha de arriba; el historial está en el repositorio.

## Contacto

Jose Antonio Seguido Doblado · jose.antonio.seguido@gmail.com
