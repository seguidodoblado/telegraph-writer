#!/usr/bin/env python3
"""Ventana GTK4 de Telegraph Writer (primera fase de la migración)."""

import sys
import json
import html
import re
import webbrowser
import urllib.parse
import urllib.request
import mimetypes
import uuid
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

APP_ID = "com.seguidodoblado.TelegraphWriter"
APP_NAME = "Telegraph Writer"
CHANGELOG_FILE = Path(__file__).resolve().parent / "debian" / "changelog"
try:
    VERSION_FILE = Path(__file__).resolve().parent / "VERSION"
    APP_VERSION = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else re.search(r"\(([^)]+)\)", CHANGELOG_FILE.read_text(encoding="utf-8")).group(1)
except (FileNotFoundError, AttributeError):
    APP_VERSION = "0.0.0"
CONFIG_FILE = Path.home() / ".config" / "telegraph-writer" / "config.json"
DRAFT_DIR = Path.home() / "Telegra.ph"
API_URL = "https://api.telegra.ph"
IMAGE_UPLOAD_URL = "https://catbox.moe/user/api.php"


def telegraph_api(method, params=None, path=None):
    url = f"{API_URL}/{method}" if not path else f"{API_URL}/{method}/{path}"
    request = urllib.request.Request(url, data=urllib.parse.urlencode(params or {}).encode(), method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Error desconocido de Telegra.ph"))
    return result["result"]


def upload_image(filename):
    """Sube una imagen a Catbox y devuelve su URL pública."""
    file_path = Path(filename)
    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif"}:
        raise RuntimeError("Solo se admiten imágenes JPG, JPEG, PNG o GIF.")
    if file_path.stat().st_size > 200 * 1024 * 1024:
        raise RuntimeError("La imagen supera el límite de 200 MB.")
    boundary = f"----TelegraphWriter{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"reqtype\"\r\n\r\n"
        f"fileupload\r\n--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"fileToUpload\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(IMAGE_UPLOAD_URL, data=body, method="POST")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    request.add_header("User-Agent", "Telegraph-Writer")
    with urllib.request.urlopen(request, timeout=60) as response:
        result = response.read().decode().strip()
    if not result.startswith(("http://", "https://")):
        raise RuntimeError(f"Catbox rechazó la imagen: {result or 'respuesta vacía'}")
    return result


def inline_to_nodes(text):
    result = []
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*")
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            result.append(text[position:match.start()])
        if match.group(1) is not None:
            result.append({"tag": "img", "attrs": {"src": match.group(2)}})
        elif match.group(3) is not None:
            result.append({"tag": "a", "attrs": {"href": match.group(4)}, "children": [match.group(3)]})
        elif match.group(5) is not None:
            result.append({"tag": "strong", "children": [match.group(5)]})
        elif match.group(6) is not None:
            result.append({"tag": "code", "children": [match.group(6)]})
        else:
            result.append({"tag": "em", "children": [match.group(7)]})
        position = match.end()
    if position < len(text):
        result.append(text[position:])
    return result or [""]


def markdown_to_nodes(markdown):
    nodes = []
    for line in markdown.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        heading = re.match(r"^\s*(#{1,6})\s+(.+)$", line)
        if heading:
            nodes.append({"tag": "h3" if len(heading.group(1)) == 1 else "h4", "children": inline_to_nodes(heading.group(2))})
        elif line.lstrip().startswith(">"):
            nodes.append({"tag": "blockquote", "children": [{"tag": "p", "children": inline_to_nodes(line.lstrip()[1:].strip())}]})
        elif re.match(r"^\s*[-*+]\s+", line):
            nodes.append({"tag": "ul", "children": [{"tag": "li", "children": inline_to_nodes(re.sub(r"^\s*[-*+]\s+", "", line))}]})
        else:
            nodes.append({"tag": "p", "children": inline_to_nodes(line.strip())})
    return nodes


class TelegraphWriter(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if hasattr(self, "window"):
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=app, title=APP_NAME)
        self.window.set_default_size(1250, 800)
        self.window.set_resizable(True)
        self.draft_dir = Path(self.read_config().get("draft_dir", str(DRAFT_DIR))).expanduser()
        self.current_file = None
        self.current_path = None
        self.current_url = None
        self.build_ui()
        self.add_actions()
        saved_theme = self.read_config().get("dark_mode")
        if saved_theme is not None:
            self.set_theme(bool(saved_theme))
        self.load_pages()
        self.window.present()

    def add_actions(self):
        callbacks = {
            "settings": self.settings,
            "new": self.new_article,
            "open": self.open_file,
            "save": self.save_file,
            "publish": self.publish,
            "update": self.update_article,
            "open-browser": self.open_in_browser,
            "preview": self.preview,
            "light": lambda: self.set_theme(False),
            "dark": lambda: self.set_theme(True),
            "about": self.about,
        }
        for name, callback in callbacks.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_args, cb=callback: cb())
            self.add_action(action)

    def read_config(self):
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def show_message(self, text, title=APP_NAME):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, text=text, buttons=Gtk.ButtonsType.OK)
        dialog.set_title(title)
        # GTK4 ya no expone set_message_type(); el icono se añade al área
        # del mensaje para conservar la indicación visual de advertencia.
        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning")
        warning_icon.set_pixel_size(40)
        message_area = dialog.get_message_area()
        message_area.prepend(warning_icon)
        dialog.connect("response", lambda dialog, _response: dialog.close())
        dialog.present()

    def load_pages(self):
        token = self.read_config().get("access_token", "")
        if not token:
            self.statusbar.set_text("Sin configurar · abre Ajustes para introducir el access token")
            return
        try:
            params = urllib.parse.urlencode({"access_token": token, "limit": 200}).encode()
            request = urllib.request.Request("https://api.telegra.ph/getPageList", data=params, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not result.get("ok"):
                raise RuntimeError(result.get("error", "Error de Telegra.ph"))
            self.pages = result["result"].get("pages", [])
            self.filter_articles(self.search)
            self.statusbar.set_text(f"{len(result['result'].get('pages', []))} artículos cargados")
            self.connection_dot.set_markup('<span foreground="#78d47d">●</span>')
            self.connection_label.set_text("Conectado")
            self.article_count_label.set_text(f"{len(result['result'].get('pages', []))} artículos")
        except Exception as error:
            self.connection_dot.set_markup('<span foreground="#e06c75">●</span>')
            self.connection_label.set_text("Sin conexión")
            self.statusbar.set_text(f"Error: {error}")

    def load_article(self, _listbox, row):
        page = row.page
        if not page:
            return
        try:
            token = self.read_config().get("access_token", "")
            params = urllib.parse.urlencode({"access_token": token, "return_content": "true"}).encode()
            request = urllib.request.Request(f"https://api.telegra.ph/getPage/{page['path']}", data=params, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            article = result["result"]
            self.current_path = article.get("path", page.get("path"))
            self.current_url = article.get("url", page.get("url"))
            self.title_entry.set_text(article.get("title", ""))
            self.editor.get_buffer().set_text(self.content_to_text(article.get("content", [])))
            self.statusbar.set_text("Artículo cargado")
        except Exception as error:
            self.statusbar.set_text(f"Error al cargar el artículo: {error}")

    def content_to_text(self, nodes):
        parts = []
        for node in nodes:
            if isinstance(node, str):
                parts.append(node)
                continue
            tag = node.get("tag", "")
            children = self.content_to_text(node.get("children", []))
            if tag == "img":
                parts.append(f"![]({node.get('attrs', {}).get('src', '')})")
            elif tag in ("h3", "h4"):
                parts.append(f"# {children}")
            elif tag == "br":
                parts.append("\n")
            elif tag == "li":
                parts.append(f"- {children}")
            else:
                parts.append(children)
        return "\n".join(parts)

    def preview(self):
        title = html.escape(self.title_entry.get_text())
        start, end = self.editor.get_buffer().get_bounds()
        text = self.editor.get_buffer().get_text(start, end, False)
        body = html.escape(text).replace("\n", "<br>\n")
        body = re.sub(
            r"!\[([^\]]*)\]\(([^)\s]+)\)",
            lambda match: f'<img src="{html.escape(match.group(2), quote=True)}" alt="{html.escape(match.group(1), quote=True)}" style="max-width:100%;">',
            body,
        )
        filename = Path("/tmp") / "telegraph_writer_preview.html"
        filename.write_text(f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>{title}</title><style>body{{max-width:680px;margin:60px auto;padding:0 25px;font:18px Georgia,serif;line-height:1.65}}h1{{font:42px Arial,sans-serif}}</style></head><body><h1>{title}</h1><p>{body}</p></body></html>", encoding="utf-8")
        webbrowser.open(filename.as_uri())
        self.statusbar.set_text("Vista previa abierta en el navegador")

    def new_article(self):
        self.current_file = self.current_path = self.current_url = None
        self.title_entry.set_text("")
        self.editor.get_buffer().set_text("")
        self.statusbar.set_text("Nuevo artículo")

    def editor_text(self):
        start, end = self.editor.get_buffer().get_bounds()
        return self.editor.get_buffer().get_text(start, end, False)

    def publish(self):
        # Un artículo cargado desde Telegra.ph no debe volver a publicarse:
        # eso crearía un duplicado aunque por alguna razón falte el path.
        if self.current_path or self.current_url:
            self.show_message("Este artículo ya existe en Telegra.ph.\n\nUtiliza «Actualizar» para aplicar los cambios sin crear un duplicado.")
            return
        title = self.title_entry.get_text().strip()
        if not title:
            self.show_message("Escribe un título antes de publicar.")
            return
        token = self.read_config().get("access_token", "")
        if not token:
            self.statusbar.set_text("Configura el access token desde Ajustes")
            return
        try:
            page = telegraph_api("createPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"})
            self.current_path = page.get("path"); self.current_url = page.get("url")
            if self.current_file: self.write_draft(self.current_file)
            self.statusbar.set_text("Artículo publicado correctamente")
            self.load_pages()
        except Exception as error:
            self.statusbar.set_text(f"Error al publicar: {error}")

    def update_article(self):
        if not self.current_path:
            self.show_message("Este artículo todavía no está publicado.\n\nUtiliza «Publicar» para crear el artículo en Telegra.ph.")
            return
        title = self.title_entry.get_text().strip(); token = self.read_config().get("access_token", "")
        if not title or not token: return
        try:
            page = telegraph_api("editPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"}, self.current_path)
            self.current_url = page.get("url", self.current_url)
            if self.current_file: self.write_draft(self.current_file)
            self.statusbar.set_text("Artículo actualizado correctamente"); self.load_pages()
        except Exception as error:
            self.statusbar.set_text(f"Error al actualizar: {error}")

    def open_in_browser(self):
        if not self.current_url:
            self.statusbar.set_text("El artículo todavía no tiene una URL pública")
            return
        webbrowser.open(self.current_url)

    def insert_image(self):
        dialog = Gtk.FileDialog(title="Seleccionar imagen")
        dialog.set_initial_folder(Gio.File.new_for_path(str(Path.home())))
        dialog.open(self.window, None, self.image_selected)

    def image_selected(self, dialog, result):
        try:
            file_path = dialog.open_finish(result).get_path()
        except GLib.Error:
            return
        self.statusbar.set_text("Subiendo imagen…")
        try:
            url = upload_image(file_path)
            buffer = self.editor.get_buffer()
            buffer.insert_at_cursor(f"![]({url})")
            self.statusbar.set_text("Imagen subida correctamente")
        except Exception as error:
            self.show_message(f"No se pudo subir la imagen.\n\n{error}", "Error al insertar imagen")
            self.statusbar.set_text("Error al subir la imagen")

    def save_file(self):
        if self.current_file:
            self.write_draft(self.current_file); return
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        dialog = Gtk.FileDialog(title="Guardar Markdown", initial_name="articulo.md")
        dialog.set_initial_folder(Gio.File.new_for_path(str(self.draft_dir)))
        dialog.save(self.window, None, self.draft_saved)

    def draft_saved(self, dialog, result):
        try:
            self.current_file = dialog.save_finish(result).get_path()
            self.write_draft(self.current_file)
        except GLib.Error:
            pass

    def write_draft(self, filename):
        path = Path(filename)
        start, end = self.editor.get_buffer().get_bounds()
        path.write_text(self.editor.get_buffer().get_text(start, end, False), encoding="utf-8")
        path.with_suffix(".telegraph.json").write_text(json.dumps({"title": self.title_entry.get_text(), "path": self.current_path, "url": self.current_url}, ensure_ascii=False, indent=2), encoding="utf-8")
        self.statusbar.set_text(f"Guardado: {path.name}")

    def open_file(self):
        dialog = Gtk.FileDialog(title="Abrir Markdown")
        dialog.set_initial_folder(Gio.File.new_for_path(str(self.draft_dir)))
        dialog.open(self.window, None, self.file_opened)

    def file_opened(self, dialog, result):
        try:
            path = Path(dialog.open_finish(result).get_path())
            metadata_file = path.with_suffix(".telegraph.json")
            metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}
            self.current_file = str(path); self.current_path = metadata.get("path"); self.current_url = metadata.get("url")
            self.title_entry.set_text(metadata.get("title", path.stem))
            self.editor.get_buffer().set_text(path.read_text(encoding="utf-8"))
            self.statusbar.set_text(f"Abierto: {path.name}")
        except (GLib.Error, OSError, json.JSONDecodeError):
            pass

    def settings(self):
        dialog = Gtk.Dialog(transient_for=self.window, modal=True)
        dialog.set_title("Ajustes")
        dialog.set_default_size(520, 180)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16); box.set_margin_end(16); box.set_margin_top(16); box.set_margin_bottom(16)
        entry = Gtk.Entry(); entry.set_placeholder_text("Access token de Telegra.ph")
        entry.set_text(self.read_config().get("access_token", "")); box.append(entry)
        draft_entry = Gtk.Entry(); draft_entry.set_text(str(self.draft_dir)); draft_entry.set_hexpand(True)
        draft_row = Gtk.Box(spacing=8); draft_row.append(Gtk.Label(label="Borradores:", xalign=0)); draft_row.append(draft_entry)
        choose = Gtk.Button(label="Elegir…"); draft_row.append(choose); box.append(draft_row)
        feedback = Gtk.Label(xalign=0)
        box.append(feedback)
        buttons = Gtk.Box(spacing=8); buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancelar"); save = Gtk.Button(label="Guardar")
        test = Gtk.Button(label="Comprobar conexión")
        buttons.append(test); buttons.append(cancel); buttons.append(save); box.append(buttons); dialog.set_child(box)
        cancel.connect("clicked", lambda *_: dialog.close())
        def choose_folder(*_):
            chooser = Gtk.FileDialog(title="Elegir carpeta de borradores")
            chooser.select_folder(self.window, None, lambda d, result: self.folder_selected(d, result, draft_entry))
        choose.connect("clicked", choose_folder)
        def test_connection(*_):
            token = entry.get_text().strip()
            if not token:
                feedback.set_text("Introduce un access token."); return
            try:
                params = urllib.parse.urlencode({"access_token": token, "fields": json.dumps(["short_name", "page_count"])}).encode()
                request = urllib.request.Request("https://api.telegra.ph/getAccountInfo", data=params, method="POST")
                with urllib.request.urlopen(request, timeout=30) as response: result = json.loads(response.read().decode("utf-8"))
                if not result.get("ok"): raise RuntimeError(result.get("error", "Error de Telegra.ph"))
                account = result["result"]
                feedback.set_text(f"Conectado: {account.get('short_name', '')} · {account.get('page_count', 0)} artículos")
            except Exception as error:
                feedback.set_text(f"Error: {error}")
        test.connect("clicked", test_connection)
        def save_config(*_):
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            config = self.read_config()
            config["access_token"] = entry.get_text().strip()
            config["draft_dir"] = draft_entry.get_text().strip() or str(DRAFT_DIR)
            self.draft_dir = Path(config["draft_dir"]).expanduser()
            CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            dialog.close(); self.load_pages()
        save.connect("clicked", save_config); dialog.present()

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
        paned.set_end_child(self.build_editor())
        root.append(paned)

        self.statusbar = Gtk.Label(label="0 palabras · 0 caracteres", xalign=1)
        self.statusbar.set_margin_start(12)
        self.statusbar.set_margin_end(12)
        self.statusbar.set_margin_top(4)
        self.statusbar.set_margin_bottom(4)
        root.append(self.statusbar)

    def build_menubar(self):
        bar = Gtk.Box(spacing=12)
        bar.set_margin_start(12); bar.set_margin_end(12)
        bar.set_margin_top(5); bar.set_margin_bottom(5)
        menus = (("Archivo", "document-properties", (("Nuevo", "document-new", self.new_article), ("Abrir", "document-open", self.open_file), ("Guardar", "document-save", self.save_file))), ("Telegra.ph", "applications-internet", (("Publicar", "document-send", self.publish), ("Actualizar", "view-refresh", self.update_article), ("Abrir artículo en navegador", "web-browser", self.open_in_browser))), ("Tema", "preferences-desktop-theme", (("Claro", "weather-clear", lambda: self.set_theme(False)), ("Oscuro", "weather-clear-night", lambda: self.set_theme(True)))), ("Ayuda", "help-browser", (("Acerca de", "help-about", self.about),)))
        for label, icon_name, items in menus:
            button = Gtk.MenuButton()
            content = Gtk.Box(spacing=6)
            content.append(Gtk.Image.new_from_icon_name(icon_name))
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
            content.append(Gtk.Image.new_from_icon_name(icon_name))
            content.append(Gtk.Label(label=label, xalign=0))
            item.set_child(content); item.set_halign(Gtk.Align.FILL)
            item.connect("clicked", lambda _, fn=callback: (popover.popdown(), fn()))
            box.append(item)
        popover.set_child(box); button.set_popover(popover)

    def build_toolbar(self):
        bar = Gtk.Box(spacing=6)
        bar.set_margin_start(8); bar.set_margin_end(8)
        bar.set_margin_bottom(6)
        buttons = (
            ("Nuevo", "document-new"),
            ("Abrir", "document-open"),
            ("Guardar", "document-save"),
            ("Insertar imagen", "insert-image"),
            ("Ajustes", "preferences-system"),
        )
        for label, icon_name in buttons:
            button = Gtk.Button()
            button.set_tooltip_text(label)
            content = Gtk.Box(spacing=6)
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(16)
            content.append(icon)
            content.append(Gtk.Label(label=label))
            button.set_child(content)
            if label == "Ajustes":
                button.connect("clicked", lambda *_: self.settings())
            elif label == "Nuevo":
                button.connect("clicked", lambda *_: self.new_article())
            elif label == "Abrir":
                button.connect("clicked", lambda *_: self.open_file())
            elif label == "Guardar":
                button.connect("clicked", lambda *_: self.save_file())
            elif label == "Insertar imagen":
                button.connect("clicked", lambda *_: self.insert_image())
            bar.append(button)
        return bar

    def build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(12); box.set_margin_end(8); box.set_margin_top(12); box.set_margin_bottom(12)
        box.append(Gtk.Label(label="MIS ARTÍCULOS", xalign=0))
        self.search = Gtk.SearchEntry(placeholder_text="Buscar artículos…")
        self.search.connect("search-changed", self.filter_articles)
        box.append(self.search)
        listbox = Gtk.ListBox()
        self.article_list = listbox
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for title, views in (("Prueba 2", 2), ("Testing", 10), ("Prueba", 17)):
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=f"{title}\n{views} vistas", xalign=0))
            listbox.append(row)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True); scroll.set_child(listbox)
        listbox.connect("row-activated", self.load_article)
        box.append(scroll)
        account = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        connection = Gtk.Box(spacing=5)
        self.connection_dot = Gtk.Label()
        self.connection_dot.set_markup('<span foreground="#e06c75">●</span>')
        self.connection_label = Gtk.Label(label="Sin configurar", xalign=0)
        connection.append(self.connection_dot); connection.append(self.connection_label)
        account.append(connection)
        account.append(Gtk.Label(label="seguidodoblado", xalign=0))
        self.article_count_label = Gtk.Label(label="0 artículos", xalign=0)
        account.append(self.article_count_label)
        box.append(account)
        return box

    def filter_articles(self, search):
        query = search.get_text().strip().lower()
        while (row := self.article_list.get_row_at_index(0)) is not None:
            self.article_list.remove(row)
        for page in getattr(self, "pages", []):
            if query and query not in page.get("title", "").lower():
                continue
            row = Gtk.ListBoxRow()
            row.page = page
            row.set_child(Gtk.Label(label=f"{page.get('title', '(sin título)')}\n{page.get('views', 0)} vistas", xalign=0))
            self.article_list.append(row)

    def build_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(8); box.set_margin_end(12); box.set_margin_top(12); box.set_margin_bottom(12)
        self.title_entry = Gtk.Entry(placeholder_text="Título del artículo")
        box.append(self.title_entry)
        editor = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.editor = editor
        editor.set_vexpand(True); editor.set_top_margin(8); editor.set_left_margin(8)
        scroll = Gtk.ScrolledWindow(); scroll.set_child(editor); scroll.set_vexpand(True)
        box.append(scroll)
        actions = Gtk.Box(spacing=8); actions.set_halign(Gtk.Align.END)
        for label in ("Vista previa", "Publicar", "Actualizar"):
            button = Gtk.Button(label=label)
            if label == "Vista previa":
                button.connect("clicked", lambda *_: self.preview())
            elif label == "Publicar":
                button.connect("clicked", lambda *_: self.publish())
            elif label == "Actualizar":
                button.connect("clicked", lambda *_: self.update_article())
            actions.append(button)
        box.append(actions)
        return box

    def file_menu(self):
        return self.menu_with_icons((("Nuevo", "app.new", "document-new-symbolic"), ("Abrir", "app.open", "document-open-symbolic"), ("Guardar", "app.save", "document-save-symbolic")))
    def telegraph_menu(self):
        return self.menu_with_icons((("Publicar", "app.publish", "document-send-symbolic"), ("Actualizar", "app.update", "view-refresh-symbolic"), ("Abrir artículo en navegador", "app.open-browser", "web-browser-symbolic")))
    def view_menu(self):
        return self.menu_with_icons((("Claro", "app.light", "weather-clear-symbolic"), ("Oscuro", "app.dark", "weather-clear-night-symbolic")))

    def set_theme(self, dark):
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-theme-name", "Adwaita-dark" if dark else "Adwaita")
        config = self.read_config()
        config["dark_mode"] = dark
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config), encoding="utf-8")
        self.statusbar.set_text("Tema oscuro aplicado" if dark else "Tema claro aplicado")
    def help_menu(self):
        return self.menu_with_icons((("Acerca de", "app.about", "help-about-symbolic"),))

    def menu_with_icons(self, items):
        menu = Gio.Menu()
        for label, action, icon_name in items:
            item = Gio.MenuItem.new(label, action)
            item.set_attribute_value("icon", GLib.Variant("s", icon_name))
            menu.append_item(item)
        return menu

    def about(self):
        dialog = Gtk.Dialog(transient_for=self.window, modal=True)
        dialog.set_title(f"Acerca de {APP_NAME}")
        dialog.set_default_size(380, 500)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(24); box.set_margin_end(24); box.set_margin_top(24); box.set_margin_bottom(18)
        icon_path = Path(__file__).resolve().parent / "telegraph-writer.svg"
        icon = Gtk.Image.new_from_file(str(icon_path)); icon.set_pixel_size(112); icon.set_halign(Gtk.Align.CENTER); box.append(icon)
        title = Gtk.Label(); title.set_markup(f"<big><b>{APP_NAME}</b></big>"); box.append(title)
        details = Gtk.Label()
        details.set_markup(
            f"Versión {APP_VERSION}\n\n"
            "Cliente de escritorio para Telegra.ph.\n\n"
            "<b>Desarrollador:</b>\n"
            "seguidodoblado\n"
            "jose.antonio.seguido@gmail.com\n\n"
            "<b>Dependencia:</b>\n"
            "PyGObject · GTK4"
        )
        details.set_justify(Gtk.Justification.CENTER)
        details.set_wrap(True)
        box.append(details)
        close = Gtk.Button(label="Cerrar"); close.set_halign(Gtk.Align.END); close.connect("clicked", lambda *_: dialog.close()); box.append(close)
        dialog.set_child(box); dialog.present()


if __name__ == "__main__":
    sys.exit(TelegraphWriter().run(sys.argv))
