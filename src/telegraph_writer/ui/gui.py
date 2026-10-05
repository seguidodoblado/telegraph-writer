"""Interfaz GTK 4: ventana principal, lista de artículos, editor, vista previa y diálogos."""
import json
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from .. import __version__
from ..config import (
    DRAFT_DIR,
    dark_mode,
    language,
    read_config,
    write_config,
)
from ..i18n import _, ngettext
from ..markdown import content_to_text, markdown_to_nodes
from ..preview import preview_update_script, render_preview
from ..telegraph import fetch_all_pages, telegraph_api, upload_image
from .theming import icon_choice, is_dark_theme, theme_variant
from .toolbar import build_markdown_toolbar

# GTK deriva el WM_CLASS de la ventana del prgname; se fija para que coincida con StartupWMClass del .desktop
# y Cinnamon asocie la ventana a su icono también tras reiniciar para cambiar de tema o de idioma.
GLib.set_prgname("telegraph-writer")

APP_NAME = "Telegraph Writer"
AUTHOR = "Jose Antonio Seguido Doblado"
AUTHOR_EMAIL = "jose.antonio.seguido@gmail.com"
REPO_URL = "https://github.com/seguidodoblado/telegraph-writer"
APPLICATION_ID = "io.github.seguidodoblado.TelegraphWriter"
LOGO = Path(__file__).resolve().parents[3] / "telegraph-writer.svg"   # solo al ejecutar desde el repositorio
LANGUAGE_CODES = [None, "es", "en"]
COLOR_OK = "#78d47d"
COLOR_ERROR = "#e06c75"

PREVIEW_CSP = "default-src 'none'; img-src http: https:; style-src 'unsafe-inline'"


# Publicar en verde y Actualizar en azul (paleta de joseflix-request, algo más
# oscura para que el texto blanco mantenga contraste); Vista previa es neutra.
ACTION_CSS = (
    "button.publish-action{background-image:none;background-color:#1e8a58;color:#fff;}"
    "button.publish-action:hover{background-color:#23a066;}"
    "button.update-action{background-image:none;background-color:#1c71d8;color:#fff;}"
    "button.update-action:hover{background-color:#3584e4;}"
    "button.publish-action:disabled,button.update-action:disabled{opacity:.45;}"
)

def webkit_available():
    """WebKitGTK 6.0 instalado (se comprueba sin cargarlo)."""
    return "6.0" in gi.Repository.get_default().enumerate_versions("WebKit")


def count_text(count):
    return ngettext("{count} artículo", "{count} artículos", count).format(count=count)


def run_gui():
    return TelegraphWriter().run(sys.argv)


class TelegraphWriter(Gtk.Application):
    def __init__(self):
        # La asociación con el icono del dock se hace mediante el prgname
        # (WM_CLASS) fijado al inicio del módulo y StartupWMClass.
        super().__init__(application_id=APPLICATION_ID)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if hasattr(self, "window"):
            self.window.present()
            return
        # gtk-theme-name refleja aquí el tema XSETTINGS del sistema (p. ej.
        # Mint-Y-Orange); se captura antes de tocar la propiedad para poder
        # derivar la variante oscura sin perder el acento del usuario.
        self.system_theme = Gtk.Settings.get_default().get_property("gtk-theme-name")
        # Los iconos se eligen al construir la interfaz, así que el modo oscuro
        # (preferencia guardada o, si no hay, el del sistema) se decide antes.
        saved_theme = dark_mode()
        self.dark = saved_theme if saved_theme is not None else is_dark_theme(self.system_theme)
        if saved_theme is not None:   # antes de presentar la ventana: en caliente Cinnamon no repinta
            Gtk.Settings.get_default().set_property("gtk-theme-name", theme_variant(self.system_theme, saved_theme))
        self.pages = []
        self.preview_file = None
        self.preview_view = None  # WebView del panel: se crea al abrirlo por primera vez
        self.preview_visible = False
        self.preview_ready = False
        self.preview_timer = None
        self.clean_state = None
        self.window = Gtk.ApplicationWindow(application=app, title=APP_NAME)
        self.window.set_default_size(1250, 800)
        self.draft_dir = Path(self.read_config().get("draft_dir", str(DRAFT_DIR))).expanduser()
        self.current_file = None
        self.current_path = None
        self.current_url = None
        css = Gtk.CssProvider()
        css.load_from_string(ACTION_CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.build_ui()
        self.mark_clean()
        self.restore_pending_session()
        self.update_action_buttons()
        self.load_pages()
        self.window.present()

    def editor_text(self):
        start, end = self.editor.get_buffer().get_bounds()
        return self.editor.get_buffer().get_text(start, end, False)

    def editor_state(self):
        return (self.title_entry.get_text(), self.editor_text())

    def mark_clean(self):
        """Toma el contenido actual como la última versión guardada o publicada."""
        self.clean_state = self.editor_state()

    def is_dirty(self):
        return self.editor_state() != self.clean_state

    def confirm_discard(self, action):
        """Ejecuta action, pidiendo confirmación si hay cambios sin guardar."""
        if not self.is_dirty():
            action()
            return
        dialog = Gtk.AlertDialog()
        dialog.set_message(_("Hay cambios sin guardar."))
        dialog.set_detail(_("Si continúas se perderán el título y el texto actuales."))
        dialog.set_buttons([_("Cancelar"), _("Descartar cambios")])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)

        def on_response(dialog, result):
            try:
                choice = dialog.choose_finish(result)
            except GLib.Error:
                return
            if choice == 1:
                action()

        dialog.choose(self.window, None, on_response)

    def collect_session_state(self):
        title, text = self.editor_state()
        return {
            "title": title,
            "text": text,
            "dirty": self.is_dirty(),
            "current_file": self.current_file,
            "current_path": self.current_path,
            "current_url": self.current_url,
            "preview": self.preview_visible,
        }

    def restore_pending_session(self):
        # Al reiniciar el proceso para aplicar el tema (ver set_theme), el
        # borrador sin guardar se guarda temporalmente en config.json para no
        # perderlo; aquí se recupera y se limpia la entrada.
        config = self.read_config()
        pending = config.pop("_pending_session", None)
        if not pending:
            return
        self.title_entry.set_text(pending.get("title", ""))
        self.editor.get_buffer().set_text(pending.get("text", ""))
        self.current_file = pending.get("current_file")
        self.current_path = pending.get("current_path")
        self.current_url = pending.get("current_url")
        if not pending.get("dirty", True):
            self.mark_clean()
        if pending.get("preview"):
            self.preview_button.set_active(True)
        write_config(config)

    def read_config(self):
        return read_config()

    def access_token(self):
        return self.read_config().get("access_token", "")

    def show_message(self, text, title=APP_NAME):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, text=text, buttons=Gtk.ButtonsType.OK)
        dialog.set_title(title)
        # GTK4 ya no expone set_message_type(); el icono se añade al área
        # del mensaje para conservar la indicación visual de advertencia.
        warning_icon = self.icon("dialog-warning")
        warning_icon.set_pixel_size(40)
        message_area = dialog.get_message_area()
        message_area.prepend(warning_icon)
        dialog.connect("response", lambda dialog, _response: dialog.close())
        dialog.present()

    def load_pages(self):
        token = self.access_token()
        if not token:
            self.pages = []
            self.filter_articles(self.search)
            self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
            self.connection_label.set_text(_("Sin configurar"))
            self.account_label.set_text(_("Sin configurar"))
            self.article_count_label.set_text(count_text(0))
            self.statusbar.set_text(_("Sin configurar · abre Ajustes para introducir el access token"))
            return
        try:
            self.pages, total = fetch_all_pages(token)
            self.filter_articles(self.search)
            loaded = ngettext("{count} artículo cargado", "{count} artículos cargados", total).format(count=total)
            self.statusbar.set_text(loaded)
            self.connection_dot.set_markup(f'<span foreground="{COLOR_OK}">●</span>')
            self.connection_label.set_text(_("Conectado"))
            self.article_count_label.set_text(count_text(total))
            self.account_label.set_text(self.account_name(token))
        except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
            self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
            self.connection_label.set_text(_("Sin conexión"))
            self.statusbar.set_text(_("Error: {error}").format(error=error))

    def account_name(self, token):
        try:
            account = telegraph_api("getAccountInfo", {"access_token": token, "fields": json.dumps(["short_name"])})
            return account.get("short_name") or _("Cuenta de Telegra.ph")
        except Exception:  # noqa: BLE001 - es un dato accesorio: se sigue con un valor por defecto
            return _("Cuenta de Telegra.ph")

    def load_article(self, _listbox, row):
        page = getattr(row, "page", None)
        if page:
            self.confirm_discard(lambda: self.open_remote_article(page))

    def open_remote_article(self, page):
        try:
            article = telegraph_api("getPage", {"access_token": self.access_token(), "return_content": "true"}, page["path"])
        except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
            self.statusbar.set_text(_("Error al cargar el artículo: {error}").format(error=error))
            return
        # Un artículo remoto no está asociado a ningún borrador local: si se
        # conservara current_file, Guardar sobrescribiría el borrador anterior.
        self.current_file = None
        self.current_path = article.get("path", page.get("path"))
        self.current_url = article.get("url", page.get("url"))
        self.title_entry.set_text(article.get("title", ""))
        self.editor.get_buffer().set_text(content_to_text(article.get("content", [])))
        self.mark_clean()
        self.update_action_buttons()
        self.statusbar.set_text(_("Artículo cargado"))

    def preview_in_browser(self):
        if self.preview_file:
            self.preview_file.unlink(missing_ok=True)
        with tempfile.NamedTemporaryFile("w", prefix="telegraph_writer_preview_", suffix=".html", delete=False, encoding="utf-8") as handle:
            handle.write(render_preview(self.title_entry.get_text(), self.editor_text()))
        self.preview_file = Path(handle.name)
        webbrowser.open(self.preview_file.as_uri())
        self.statusbar.set_text(_("Vista previa abierta en el navegador"))

    def create_preview_view(self):
        """Crea el WebView del panel (WebKit consume memoria, así que solo se
        carga al abrir la vista previa por primera vez). Devuelve False si
        WebKit no se puede cargar."""
        try:
            gi.require_version("WebKit", "6.0")
            from gi.repository import WebKit
        except (ValueError, ImportError):
            return False
        self.WebKit = WebKit
        # Sesión efímera: la vista previa no guarda cookies ni caché en disco.
        self.preview_view = WebKit.WebView(network_session=WebKit.NetworkSession.new_ephemeral(), hexpand=True, vexpand=True)
        self.preview_view.connect("decide-policy", self.on_preview_policy)
        self.preview_view.connect("load-changed", lambda _view, event: setattr(self, "preview_ready", True) if event == WebKit.LoadEvent.FINISHED else None)
        frame = Gtk.Frame(child=self.preview_view)
        frame.set_margin_start(8); frame.set_margin_end(12); frame.set_margin_top(12); frame.set_margin_bottom(12)
        self.preview_frame = frame
        return True

    def on_preview_policy(self, _view, decision, decision_type):
        # Los enlaces de la vista previa se abren en el navegador; el panel
        # solo muestra el artículo.
        if decision_type == self.WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            action = decision.get_navigation_action()
            if action.get_navigation_type() == self.WebKit.NavigationType.LINK_CLICKED:
                webbrowser.open(action.get_request().get_uri())
                decision.ignore()
                return True
        return False

    def set_preview_visible(self, visible):
        if visible == self.preview_visible:
            return
        if visible:
            if self.preview_view is None and not self.create_preview_view():
                self.preview_button.set_active(False)
                self.preview_in_browser()
                return
            self.preview_paned.set_end_child(self.preview_frame)
            self.preview_paned.set_position(max(320, (self.preview_paned.get_width() or 940) // 2))
            self.preview_visible = True
            self.preview_ready = False
            self.refresh_preview()
        else:
            self.preview_visible = False
            if self.preview_timer:
                GLib.source_remove(self.preview_timer)
                self.preview_timer = None
            self.preview_paned.set_end_child(None)

    def refresh_preview(self):
        if not self.preview_visible:
            return
        title, text = self.editor_state()
        if self.preview_ready:
            self.preview_view.evaluate_javascript(preview_update_script(title, text), -1, None, None, None, None, None)
        else:
            self.preview_view.load_html(render_preview(title, text), "https://telegra.ph/")

    def schedule_preview(self):
        """Refresca el panel poco después de la última pulsación de tecla."""
        if not self.preview_visible:
            return
        if self.preview_timer:
            GLib.source_remove(self.preview_timer)
        self.preview_timer = GLib.timeout_add(250, self.run_preview_refresh)

    def run_preview_refresh(self):
        self.preview_timer = None
        self.refresh_preview()
        return False

    def update_action_buttons(self):
        """Actualizar solo tiene sentido con un artículo ya publicado."""
        published = bool(self.current_path)
        self.update_button.set_sensitive(published)
        tooltip = _("Aplica los cambios al artículo publicado") if published else _("Publica primero el artículo para poder actualizarlo")
        self.update_button.set_tooltip_text(tooltip)

    def new_article(self):
        self.confirm_discard(self.reset_editor)

    def reset_editor(self):
        self.current_file = self.current_path = self.current_url = None
        self.title_entry.set_text("")
        self.editor.get_buffer().set_text("")
        self.mark_clean()
        self.update_action_buttons()
        self.statusbar.set_text(_("Nuevo artículo"))

    def publish(self):
        # Un artículo cargado desde Telegra.ph no debe volver a publicarse:
        # eso crearía un duplicado aunque por alguna razón falte el path.
        if self.current_path or self.current_url:
            self.show_message(_("Este artículo ya existe en Telegra.ph.\n\nUtiliza «Actualizar» para aplicar los cambios sin crear un duplicado."))
            return
        title = self.title_entry.get_text().strip()
        if not title:
            self.show_message(_("Escribe un título antes de publicar."))
            return
        token = self.access_token()
        if not token:
            self.statusbar.set_text(_("Configura el access token desde Ajustes"))
            return
        try:
            page = telegraph_api("createPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"})
        except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
            self.statusbar.set_text(_("Error al publicar: {error}").format(error=error))
            return
        self.current_path = page.get("path")
        self.current_url = page.get("url")
        self.mark_clean()
        self.update_action_buttons()
        if self.current_file:
            self.write_draft(self.current_file)
        self.statusbar.set_text(_("Artículo publicado correctamente"))
        self.load_pages()

    def update_article(self):
        if not self.current_path:
            self.show_message(_("Este artículo todavía no está publicado.\n\nUtiliza «Publicar» para crear el artículo en Telegra.ph."))
            return
        title = self.title_entry.get_text().strip()
        if not title:
            self.show_message(_("Escribe un título antes de actualizar."))
            return
        token = self.access_token()
        if not token:
            self.statusbar.set_text(_("Configura el access token desde Ajustes"))
            return
        try:
            page = telegraph_api("editPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"}, self.current_path)
        except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
            self.statusbar.set_text(_("Error al actualizar: {error}").format(error=error))
            return
        self.current_url = page.get("url", self.current_url)
        self.mark_clean()
        if self.current_file:
            self.write_draft(self.current_file)
        self.statusbar.set_text(_("Artículo actualizado correctamente"))
        self.load_pages()

    def open_in_browser(self):
        if not self.current_url:
            self.statusbar.set_text(_("El artículo todavía no tiene una URL pública"))
            return
        webbrowser.open(self.current_url)

    def insert_image(self):
        dialog = Gtk.FileDialog(title=_("Seleccionar imagen"))
        dialog.set_initial_folder(Gio.File.new_for_path(str(Path.home())))
        dialog.open(self.window, None, self.image_selected)

    def image_selected(self, dialog, result):
        try:
            file_path = dialog.open_finish(result).get_path()
        except GLib.Error:
            return
        self.statusbar.set_text(_("Subiendo imagen…"))
        try:
            url = upload_image(file_path)
            buffer = self.editor.get_buffer()
            buffer.insert_at_cursor(f"![]({url})")
            self.statusbar.set_text(_("Imagen subida correctamente"))
        except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
            message = _("No se pudo subir la imagen.\n\n{error}").format(error=error)
            self.show_message(message, _("Error al insertar imagen"))
            self.statusbar.set_text(_("Error al subir la imagen"))

    def save_file(self):
        if self.current_file:
            self.write_draft(self.current_file)
            return
        try:
            self.draft_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            message = _("No se pudo crear la carpeta de borradores.\n\n{error}\n\nElige otra en Ajustes → Elegir…").format(error=error)
            self.show_message(message)
            return
        dialog = Gtk.FileDialog(title=_("Guardar Markdown"), initial_name="articulo.md")
        dialog.set_initial_folder(Gio.File.new_for_path(str(self.draft_dir)))
        dialog.save(self.window, None, self.draft_saved)

    def draft_saved(self, dialog, result):
        try:
            filename = dialog.save_finish(result).get_path()
        except GLib.Error:
            return
        if self.write_draft(filename):
            self.current_file = filename

    def write_draft(self, filename):
        path = Path(filename)
        metadata = {"title": self.title_entry.get_text(), "path": self.current_path, "url": self.current_url}
        try:
            path.write_text(self.editor_text(), encoding="utf-8")
            path.with_suffix(".telegraph.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as error:
            self.show_message(_("No se pudo guardar el borrador.\n\n{error}").format(error=error))
            return False
        self.mark_clean()
        self.statusbar.set_text(_("Guardado: {name}").format(name=path.name))
        return True

    def open_file(self):
        dialog = Gtk.FileDialog(title=_("Abrir Markdown"))
        dialog.set_initial_folder(Gio.File.new_for_path(str(self.draft_dir)))
        dialog.open(self.window, None, self.file_opened)

    def file_opened(self, dialog, result):
        try:
            path = Path(dialog.open_finish(result).get_path())
        except GLib.Error:
            return
        self.confirm_discard(lambda: self.load_draft(path))

    def load_draft(self, path):
        metadata_file = path.with_suffix(".telegraph.json")
        try:
            text = path.read_text(encoding="utf-8")
            metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.show_message(_("No se pudo abrir el borrador.\n\n{error}").format(error=error))
            return
        if not isinstance(metadata, dict):
            metadata = {}
        self.current_file = str(path)
        self.current_path = metadata.get("path")
        self.current_url = metadata.get("url")
        self.title_entry.set_text(metadata.get("title", path.stem))
        self.editor.get_buffer().set_text(text)
        self.mark_clean()
        self.update_action_buttons()
        self.statusbar.set_text(_("Abierto: {name}").format(name=path.name))

    def settings(self):
        dialog = Gtk.Dialog(transient_for=self.window, modal=True)
        dialog.set_title(_("Ajustes"))
        dialog.set_default_size(560, 240)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16); box.set_margin_end(16); box.set_margin_top(16); box.set_margin_bottom(16)
        entry = Gtk.Entry(); entry.set_placeholder_text(_("Access token de Telegra.ph"))
        entry.set_text(self.access_token()); box.append(entry)
        draft_entry = Gtk.Entry(); draft_entry.set_text(str(self.draft_dir)); draft_entry.set_hexpand(True)
        draft_row = Gtk.Box(spacing=8); draft_row.append(Gtk.Label(label=_("Borradores:"), xalign=0)); draft_row.append(draft_entry)
        choose = Gtk.Button(label=_("Elegir…")); draft_row.append(choose); box.append(draft_row)
        # Los nombres de idioma no se traducen: «English» se ve igual con la app en español, y viceversa
        language_drop = Gtk.DropDown.new_from_strings([_("Sistema"), "Español", "English"])
        language_drop.set_selected(LANGUAGE_CODES.index(language()))
        language_row = Gtk.Box(spacing=8); language_row.append(Gtk.Label(label=_("Idioma:"), xalign=0)); language_row.append(language_drop)
        language_row.append(Gtk.Label(label=_("Se aplica reiniciando la aplicación."), xalign=0, css_classes=["dim-label"])); box.append(language_row)
        feedback = Gtk.Label(xalign=0)
        box.append(feedback)
        buttons = Gtk.Box(spacing=8); buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label=_("Cancelar")); save = Gtk.Button(label=_("Guardar"))
        test = Gtk.Button(label=_("Comprobar conexión"))
        buttons.append(test); buttons.append(cancel); buttons.append(save); box.append(buttons); dialog.set_child(box)
        cancel.connect("clicked", lambda *_args: dialog.close())

        def choose_folder(*_args):
            chooser = Gtk.FileDialog(title=_("Elegir carpeta de borradores"))
            chooser.select_folder(self.window, None, lambda d, result: self.folder_selected(d, result, draft_entry))
        choose.connect("clicked", choose_folder)

        def test_connection(*_args):
            token = entry.get_text().strip()
            if not token:
                feedback.set_text(_("Introduce un access token."))
                return
            try:
                account = telegraph_api("getAccountInfo", {"access_token": token, "fields": json.dumps(["short_name", "page_count"])})
                feedback.set_text(_("Conectado: {name} · {count}").format(name=account.get("short_name", ""), count=count_text(account.get("page_count", 0))))
            except Exception as error:  # noqa: BLE001 - el motivo se muestra al usuario, no debe cerrar la app
                feedback.set_text(_("Error: {error}").format(error=error))
        test.connect("clicked", test_connection)

        def save_config(*_args):
            config = self.read_config()
            config["access_token"] = entry.get_text().strip()
            config["draft_dir"] = draft_entry.get_text().strip() or str(DRAFT_DIR)
            chosen_language = LANGUAGE_CODES[language_drop.get_selected()]
            language_changed = chosen_language != language()
            config["language"] = chosen_language
            try:
                write_config(config)
            except OSError as error:
                feedback.set_text(_("No se pudo guardar la configuración: {error}").format(error=error))
                return
            self.draft_dir = Path(config["draft_dir"]).expanduser()
            dialog.close()
            self.load_pages()
            if language_changed:
                self.restart()
        save.connect("clicked", save_config)
        dialog.present()

    def folder_selected(self, _dialog, result, entry):
        try:
            folder = _dialog.select_folder_finish(result)
            entry.set_text(folder.get_path())
        except GLib.Error:
            pass

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.set_child(root)
        root.append(self.build_menubar())
        root.append(self.build_toolbar())

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_wide_handle(True)
        paned.set_position(310)
        paned.set_vexpand(True)
        paned.set_start_child(self.build_sidebar())
        # El panel de vista previa se añade como hijo final de este Paned solo
        # mientras está abierto; cerrado, el editor ocupa todo el ancho.
        self.preview_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.preview_paned.set_wide_handle(True)
        self.preview_paned.set_start_child(self.build_editor())
        self.preview_paned.set_resize_end_child(True)
        paned.set_end_child(self.preview_paned)
        root.append(paned)

        self.statusbar = Gtk.Label(label="", xalign=1)
        self.statusbar.set_margin_start(12)
        self.statusbar.set_margin_end(12)
        self.statusbar.set_margin_top(4)
        self.statusbar.set_margin_bottom(4)
        root.append(self.statusbar)

    def icon(self, names):
        """Icono del tema: simbólico en el modo oscuro y de color en el claro (ver theming.icon_choice)."""
        names = (names,) if isinstance(names, str) else names
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        return Gtk.Image.new_from_icon_name(icon_choice(names, self.dark, theme.has_icon))

    def build_menubar(self):
        bar = Gtk.Box(spacing=12)
        bar.set_margin_start(12); bar.set_margin_end(12)
        bar.set_margin_top(5); bar.set_margin_bottom(5)
        menus = (
            (_("Archivo"), "document-properties", (
                (_("Nuevo"), "document-new", self.new_article),
                (_("Abrir"), "document-open", self.open_file),
                (_("Guardar"), "document-save", self.save_file),
            )),
            ("Telegra.ph", "applications-internet", (
                (_("Publicar"), "document-send", self.publish),
                (_("Actualizar"), "view-refresh", self.update_article),
                (_("Abrir artículo en navegador"), "web-browser", self.open_in_browser),
            )),
            (_("Tema"), "preferences-desktop-theme", (
                (_("Sistema"), "preferences-desktop-theme", lambda: self.set_theme(None)),
                (_("Claro"), "weather-clear", lambda: self.set_theme(False)),
                (_("Oscuro"), "weather-clear-night", lambda: self.set_theme(True)),
            )),
            (_("Ayuda"), "help-browser", (
                (_("Acerca de"), "help-about", self.about),
            )),
        )
        for label, icon_name, items in menus:
            button = Gtk.MenuButton()
            content = Gtk.Box(spacing=6)
            content.append(self.icon(icon_name))
            content.append(Gtk.Label(label=label))
            button.set_child(content)
            self.menu_popover(button, items)
            bar.append(button)
        return bar

    def menu_popover(self, button, items):
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_start(6); box.set_margin_end(6); box.set_margin_top(6); box.set_margin_bottom(6)
        for label, icon_name, callback in items:
            item = Gtk.Button()
            content = Gtk.Box(spacing=8)
            content.append(self.icon(icon_name))
            content.append(Gtk.Label(label=label, xalign=0))
            item.set_child(content); item.set_halign(Gtk.Align.FILL)
            item.connect("clicked", lambda _btn, fn=callback: (popover.popdown(), fn()))
            box.append(item)
        popover.set_child(box); button.set_popover(popover)

    def build_toolbar(self):
        bar = Gtk.Box(spacing=6)
        bar.set_margin_start(8); bar.set_margin_end(8)
        bar.set_margin_bottom(6)
        buttons = (
            (_("Nuevo"), "document-new", self.new_article),
            (_("Abrir"), "document-open", self.open_file),
            (_("Guardar"), "document-save", self.save_file),
            (_("Insertar imagen"), "insert-image", self.insert_image),
            (_("Ajustes"), "preferences-system", self.settings),
        )
        for label, icon_name, callback in buttons:
            button = Gtk.Button()
            button.set_tooltip_text(label)
            content = Gtk.Box(spacing=6)
            icon = self.icon(icon_name)
            icon.set_pixel_size(16)
            content.append(icon)
            content.append(Gtk.Label(label=label))
            button.set_child(content)
            button.connect("clicked", lambda _btn, fn=callback: fn())
            bar.append(button)
        return bar

    def build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(8); box.set_margin_top(12); box.set_margin_bottom(12)
        box.append(Gtk.Label(label=_("MIS ARTÍCULOS"), xalign=0))
        self.search = Gtk.SearchEntry(placeholder_text=_("Buscar artículos…"))
        self.search.connect("search-changed", self.filter_articles)
        box.append(self.search)
        listbox = Gtk.ListBox()
        self.article_list = listbox
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True); scroll.set_child(listbox)
        listbox.connect("row-activated", self.load_article)
        box.append(scroll)
        account = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        connection = Gtk.Box(spacing=5)
        self.connection_dot = Gtk.Label()
        self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
        self.connection_label = Gtk.Label(label=_("Sin configurar"), xalign=0)
        connection.append(self.connection_dot); connection.append(self.connection_label)
        account.append(connection)
        self.account_label = Gtk.Label(label=_("Sin configurar"), xalign=0)
        account.append(self.account_label)
        self.article_count_label = Gtk.Label(label=count_text(0), xalign=0)
        account.append(self.article_count_label)
        box.append(account)
        return box

    def filter_articles(self, search):
        query = search.get_text().strip().lower()
        while (row := self.article_list.get_row_at_index(0)) is not None:
            self.article_list.remove(row)
        for page in self.pages:
            if query and query not in page.get("title", "").lower():
                continue
            row = Gtk.ListBoxRow()
            row.page = page
            title = page.get("title") or _("(sin título)")
            views = page.get("views", 0)
            views_text = ngettext("{views} vista", "{views} vistas", views).format(views=views)
            row.set_child(Gtk.Label(label=f"{title}\n{views_text}", xalign=0))
            self.article_list.append(row)

    def build_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(8); box.set_margin_end(12); box.set_margin_top(12); box.set_margin_bottom(12)
        self.title_entry = Gtk.Entry(placeholder_text=_("Título del artículo"))
        self.title_entry.connect("changed", lambda _entry: self.schedule_preview())
        box.append(self.title_entry)
        editor = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.editor = editor
        editor.get_buffer().connect("changed", lambda _buf: self.schedule_preview())
        editor.set_vexpand(True); editor.set_top_margin(8); editor.set_left_margin(8)
        box.append(build_markdown_toolbar(editor))
        scroll = Gtk.ScrolledWindow(); scroll.set_child(editor); scroll.set_vexpand(True)
        box.append(scroll)
        actions = Gtk.Box(spacing=8); actions.set_halign(Gtk.Align.END)
        if webkit_available():
            self.preview_button = Gtk.ToggleButton(label=_("Vista previa"))
            self.preview_button.set_tooltip_text(_("Muestra u oculta la vista previa junto al editor"))
            self.preview_button.connect("toggled", lambda button: self.set_preview_visible(button.get_active()))
        else:
            self.preview_button = Gtk.Button(label=_("Vista previa"))
            self.preview_button.set_tooltip_text(_("Abre la vista previa en el navegador"))
            self.preview_button.connect("clicked", lambda _btn: self.preview_in_browser())
        publish_button = Gtk.Button(label=_("Publicar"))
        publish_button.add_css_class("publish-action")
        publish_button.connect("clicked", lambda _btn: self.publish())
        self.update_button = Gtk.Button(label=_("Actualizar"))
        self.update_button.add_css_class("update-action")
        self.update_button.connect("clicked", lambda _btn: self.update_article())
        for button in (self.preview_button, publish_button, self.update_button):
            actions.append(button)
        box.append(actions)
        return box

    def restart(self):
        """Relanza la aplicación con un proceso nuevo, conservando el borrador en curso (se guarda en config.json)."""
        config = self.read_config()
        config["_pending_session"] = self.collect_session_state()
        write_config(config)
        # Un exec en el sitio conservaría los descriptores abiertos (y con ellos el registro D-Bus de esta
        # instancia): el proceso nuevo se vería como secundario y se cerraría sin ventana. El ejecutable se
        # toma de /proc/self/exe, no de sys.executable, porque el lanzador instalado usa «exec -a».
        subprocess.Popen(["/proc/self/exe", "-m", "telegraph_writer"], start_new_session=True)
        self.quit()

    def set_theme(self, dark):
        """Guarda el tema (True oscuro, False claro, None el del sistema) y reinicia: cambiar gtk-theme-name con la
        ventana ya presentada no repinta en Cinnamon/Mint, así que el tema se aplica al arrancar."""
        config = self.read_config()
        config["dark_mode"] = dark
        write_config(config)
        self.restart()

    def about(self):
        about = Gtk.AboutDialog(
            transient_for=self.window, modal=True, program_name=APP_NAME, version=__version__,
            authors=[f"{AUTHOR} <{AUTHOR_EMAIL}>"], copyright=f"© 2026 {AUTHOR}",
            comments=_("Cliente de escritorio para Telegra.ph: editor Markdown para crear, publicar y actualizar artículos."),
            website=REPO_URL, website_label=REPO_URL.removeprefix("https://"),
            license_type=Gtk.License.GPL_3_0, translator_credits=_("translator-credits"))
        # Instalado, el icono está en el tema (hicolor); desde el código fuente se carga el SVG del repositorio.
        if Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).has_icon("telegraph-writer"):
            about.set_logo_icon_name("telegraph-writer")
        elif LOGO.exists():
            about.set_logo(Gdk.Texture.new_from_filename(str(LOGO)))
        about.add_credit_section(_("Servicios de terceros"), [
            "Telegra.ph https://telegra.ph/",
            _("Catbox (subida de imágenes) https://catbox.moe/")])
        about.present()
