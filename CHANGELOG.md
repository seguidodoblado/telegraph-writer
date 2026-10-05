# Changelog

## [Unreleased]

### Añadido
- **Tema Sistema / Claro / Oscuro** en el menú Tema (antes solo Claro y Oscuro; se guarda en `config.json` y se aplica reiniciando, conservando el borrador sin guardar). «Oscuro» y «Claro» eligen el tema GTK hermano del que tenga el sistema, conservando el acento (`Mint-Y-Aqua` ↔ `Mint-Y-Dark-Aqua`)
- **Selector de idioma** en Ajustes (Sistema, Español o English; reinicia la aplicación). Con «Sistema» se usa el idioma del escritorio o `$LANGUAGE`
- `ruff`, `pytest` (51 pruebas: Markdown, vista previa, API de Telegra.ph, ajustes, traducciones y tema) e integración continua (`ci.yml`: ruff, pytest y `.deb` con lintian) y despliegue (`cd.yml`: al subir una etiqueta `vX.Y.Z` ejecuta el CI y, solo si pasa, deja la release en borrador con el mismo `.deb` que construyó el CI)
- Páginas de manual en inglés y español, `PRIVACY.md` y `PRIVACY.en.md`, y versión en inglés de `CONTRIBUTING`, `SECURITY` y `SUPPORT`, con selector de idioma; `CHANGELOG.md`

### Cambiado
- El código pasa de un único `telegraph_writer.py` a `src/telegraph_writer/` (`markdown`, `preview`, `telegraph`, `config`, `i18n`) con la interfaz en su propio paquete `ui/`
- La licencia pasa a **GPL-3.0 o posterior** (antes, solo versión 3): `debian/copyright` (GPL-3+), `pyproject.toml`, README y «Acerca de», que usa la licencia predefinida de GTK
- Empaquetado conforme a Debian: la aplicación se instala en `/usr/share/telegraph-writer`, con `debian/control`, `copyright`, `postinst`, `rules`, `md5sums` y permisos fijos; el `.deb` pasa lintian sin errores
- El identificador de la aplicación (`Gtk.Application`) pasa a `io.github.seguidodoblado.TelegraphWriter`, con la forma que exige Flathub; no cambia ningún dato guardado
- Los botones y el menú usan iconos del sistema: simbólicos en el tema oscuro y de color en el claro

## [2.7.0] - 2026-10-02

### Añadido
- Traducciones con `gettext` (español como idioma fuente y catálogo en inglés): la barra de formato, los menús, los diálogos y los mensajes de estado son traducibles

## [2.6.0] - 2026-10-01

### Añadido
- Barra de formato Markdown sobre el editor (negrita, cursiva, tachado, subrayado, encabezado, listas, cita, código y enlace), portada de Bloguero

## [2.5.1] - 2026-09-27

### Cambiado
- «Acerca de» usa la ventana estándar de GNOME, como Comic Identify

## [2.5.0] - 2026-09-27

### Añadido
- La vista previa se abre en un panel lateral WebKit que se actualiza mientras escribes

### Cambiado
- Los botones Publicar y Actualizar son de color, y Actualizar queda desactivado hasta que el artículo esté publicado

## [2.4.3] - 2026-09-27

### Corregido
- Al cargar un artículo de Telegra.ph, los bloques se separan con una línea en blanco en el editor

## [2.4.2] - 2026-09-26

### Cambiado
- El tema oscuro usa iconos simbólicos monocromos (el claro conserva los de color)

## [2.4.1] - 2026-09-23

### Corregido
- La vista previa muestra el Markdown tal como lo renderiza Telegra.ph

## [2.4.0] - 2026-09-23

### Añadido
- Listas ordenadas, bloques de código y reglas horizontales
- Paginación de la lista de artículos
- `copyright` y `changelog` en el paquete

### Cambiado
- El archivo de configuración queda privado (permisos 600)
- Se pregunta antes de descartar cambios sin guardar

### Corregido
- Pérdida de datos al actualizar artículos cargados: se conservan el formato en línea y los niveles de encabezado
- El cambio de tema reiniciaba mal la aplicación en el paquete instalado, y se conserva el icono del panel

## [2.3.2] - 2026-09-22

### Corregido
- El tema claro no volvía al cambiar de tema: la aplicación se reinicia para aplicarlo y deriva la variante clara u oscura de Mint-Y del tema del sistema, para conservar el acento en ambos modos

### Cambiado
- Se elimina código muerto de la interfaz, se centralizan las llamadas a la API y se unifica la versión

## [2.3.1] - 2026-09-22

### Corregido
- Se deja de forzar el tema Adwaita al cambiar de tema: se respeta el acento del tema GTK del sistema

## [2.3.0] - 2026-09-01

### Cambiado
- Migración a GTK 4 y PyGObject

## [2.2.0] - 2026-08-31

### Cambiado
- Estilo gráfico rediseñado con un enfoque más nativo

## [2.1.2] - 2026-08-24

### Corregido
- El lanzador de la aplicación se instala en la ruta ejecutable correcta
- Icono de ajustes
