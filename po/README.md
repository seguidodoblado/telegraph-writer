# Traducciones (i18n)

El idioma fuente del código es **español**: los textos de la interfaz se
escriben directamente en español dentro de `telegraph_writer.py`
(`_("Conectar con…")`), y no hace falta ningún catálogo `es.po` — si no hay
traducción cargada, `gettext` devuelve el texto tal cual.

## Añadir o cambiar un texto de la interfaz

1. Envuelve el texto en `_(...)` (o en `ngettext(singular, plural, n)` si
   depende de una cantidad), ambas definidas en el propio `telegraph_writer.py`.
2. **No** metas la llamada a `_()` dentro de una f-string (`f"...{_('texto')}..."`)
   ni le pases una variable: `xgettext` solo detecta una cadena literal como
   argumento directo. Saca el texto a una plantilla y usa `.format()`:
   ```python
   # mal — xgettext no ve "Texto":
   mensaje = f"Hola {_('Texto')}"
   # bien:
   mensaje = _("Hola {nombre}").format(nombre=texto)
   ```
3. Si el texto es una **constante de módulo** (asignada fuera de cualquier
   función), no la envuelvas ahí: ese código se ejecuta al importar el
   archivo, antes de que `install_i18n()` fije el idioma, así que quedaría
   congelado en español para siempre. Mueve el texto dentro de la función o
   el método donde se usa (ver `LICENSE_TEXT` dentro de `about()` como
   ejemplo ya resuelto así).
4. Ejecuta `./i18n-extract.sh` desde la raíz del proyecto. Regenera
   `po/telegraph-writer.pot` y actualiza `po/*.po` con las cadenas nuevas
   (quedan con `msgstr ""` o marcadas `#, fuzzy` si el texto original cambió).
5. Traduce las cadenas nuevas/fuzzy a mano en `po/en.po` (o el idioma que
   corresponda) y quita la marca `#, fuzzy` una vez revisadas.
6. Ejecuta `./i18n-compile.sh` para generar los `.mo` y probarlo en la app:
   ```sh
   LANGUAGE=en python3 telegraph_writer.py
   ```

`build-deb.sh` ya llama a `i18n-compile.sh` automáticamente, así que no hace
falta compilar a mano antes de empaquetar. Las pruebas (`tests/test_i18n.py`)
sí lo necesitan: ejecuta `./i18n-compile.sh` antes de
`python3 -m unittest discover -s tests` si acabas de clonar el repositorio.

## Añadir un idioma nuevo

```sh
msginit --input=po/telegraph-writer.pot --locale=<código> --output=po/<código>.po
```

Traduce `po/<código>.po` y compílalo con `./i18n-compile.sh` — detecta
cualquier `po/*.po` automáticamente, no hace falta tocar el script.

## Dónde vive cada cosa

- `po/*.po`, `po/telegraph-writer.pot` — fuente de las traducciones,
  versionado en git.
- `i18n/<idioma>/LC_MESSAGES/telegraph-writer.mo` — catálogo compilado,
  **no** se versiona (está en `.gitignore`), se genera con `i18n-compile.sh`.
- `install_i18n()`, `_()` y `ngettext()`, al principio de `telegraph_writer.py`
  — se llama una sola vez, en `if __name__ == "__main__":`, antes de
  construir la ventana.

Patrón e infraestructura (`install_i18n()`, los dos scripts `.sh` y este
mismo README) portados de [Bloguero](https://github.com/seguidodoblado/bloguero),
adaptados a que aquí todo vive en un único archivo en vez de un paquete.
