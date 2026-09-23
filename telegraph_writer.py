#!/usr/bin/env python3
"""Telegraph Writer: cliente de escritorio GTK4 para Telegra.ph."""

import sys
import os
import json
import html
import re
import tempfile
import webbrowser
import urllib.parse
import urllib.request
import mimetypes
import uuid
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

# GTK deriva el WM_CLASS de la ventana del prgname (por defecto el nombre del
# .py); se fija para que coincida con StartupWMClass del .desktop y Cinnamon
# asocie la ventana a su icono también tras reiniciar para cambiar de tema.
GLib.set_prgname("telegraph-writer")

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
PAGE_LIST_LIMIT = 200  # máximo que admite getPageList por petición
COLOR_OK = "#78d47d"
COLOR_ERROR = "#e06c75"

INLINE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*")
HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+)$")
LIST_ITEM_RE = re.compile(r"^\s*(?:([-*+])|\d+[.)])\s+(.*)$")
RULE_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")


def telegraph_api(method, params=None, path=None):
    url = f"{API_URL}/{method}" if not path else f"{API_URL}/{method}/{path}"
    request = urllib.request.Request(url, data=urllib.parse.urlencode(params or {}).encode(), method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Error desconocido de Telegra.ph"))
    return result["result"]


def fetch_all_pages(token):
    """Devuelve (artículos, total) paginando getPageList, que limita cada
    petición a PAGE_LIST_LIMIT resultados."""
    pages = []
    while True:
        batch = telegraph_api("getPageList", {"access_token": token, "offset": len(pages), "limit": PAGE_LIST_LIMIT})
        received = batch.get("pages", [])
        pages.extend(received)
        total = batch.get("total_count", len(pages))
        if not received or len(pages) >= total:
            return pages, max(total, len(pages))


def write_config(config):
    """Escribe la configuración de forma atómica y solo legible por el usuario:
    contiene el access token (y, al cambiar de tema, el borrador en curso)."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_name(CONFIG_FILE.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, CONFIG_FILE)


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
    position = 0
    for match in INLINE_RE.finditer(text):
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


def theme_variant(name, dark):
    """Deriva el nombre del tema GTK hermano (claro/oscuro) preservando el
    acento. Sigue la convención Mint-Y[-Dark]-<Acento> de Linux Mint y, para
    el resto de temas, la de Adwaita/Yaru (<tema>[-<acento>]-dark)."""
    base = re.sub(r"-dark(?=-|$)", "", name, count=1, flags=re.IGNORECASE)
    if not dark:
        return base
    parts = base.split("-", 2)
    if parts[0] == "Mint" and len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}-Dark" + (f"-{parts[2]}" if len(parts) > 2 else "")
    return base + "-dark"


def markdown_to_nodes(markdown):
    nodes = []
    current = None  # lista o cita abierta, para agrupar líneas consecutivas
    code_lines = None  # líneas del bloque de código en curso, si hay uno abierto
    for line in markdown.replace("\r\n", "\n").split("\n"):
        if line.strip().startswith("```"):
            if code_lines is None:
                code_lines = []
            else:
                nodes.append({"tag": "pre", "children": ["\n".join(code_lines)]})
                code_lines = None
            current = None
            continue
        if code_lines is not None:
            code_lines.append(line)
            continue
        if not line.strip():
            continue
        heading = HEADING_RE.match(line)
        item = LIST_ITEM_RE.match(line)
        if heading:
            nodes.append({"tag": "h3" if len(heading.group(1)) == 1 else "h4", "children": inline_to_nodes(heading.group(2))})
            current = None
        elif RULE_RE.match(line):
            nodes.append({"tag": "hr"})
            current = None
        elif line.lstrip().startswith(">"):
            if current is None or current["tag"] != "blockquote":
                current = {"tag": "blockquote", "children": []}
                nodes.append(current)
            current["children"].append({"tag": "p", "children": inline_to_nodes(line.lstrip()[1:].strip())})
        elif item:
            tag = "ul" if item.group(1) else "ol"
            if current is None or current["tag"] != tag:
                current = {"tag": tag, "children": []}
                nodes.append(current)
            current["children"].append({"tag": "li", "children": inline_to_nodes(item.group(2))})
        else:
            nodes.append({"tag": "p", "children": inline_to_nodes(line.strip())})
            current = None
    if code_lines is not None:
        nodes.append({"tag": "pre", "children": ["\n".join(code_lines)]})
    return nodes


def plain_text(nodes):
    """Texto de los nodos sin ninguna marca de formato."""
    return "".join(node if isinstance(node, str) else plain_text(node.get("children", [])) for node in nodes)


def inline_to_text(nodes):
    """Convierte nodos en línea (texto, enlaces, negritas, imágenes…) a Markdown
    sin insertar saltos de línea, para no romper los párrafos."""
    parts = []
    for node in nodes:
        if isinstance(node, str):
            parts.append(node)
            continue
        tag = node.get("tag", "")
        attrs = node.get("attrs", {})
        inner = inline_to_text(node.get("children", []))
        if tag == "img":
            parts.append(f"![]({attrs.get('src', '')})")
        elif tag == "a":
            parts.append(f"[{inner}]({attrs.get('href', '')})")
        elif tag in ("strong", "b"):
            parts.append(f"**{inner}**")
        elif tag in ("em", "i"):
            parts.append(f"*{inner}*")
        elif tag == "code":
            parts.append(f"`{inner}`")
        elif tag == "br":
            parts.append("\n")
        else:
            parts.append(inner)
    return "".join(parts)


def content_to_text(nodes):
    """Reconstruye un borrador Markdown a partir del contenido de un artículo:
    cada nodo de bloque genera una línea y el formato en línea se conserva."""
    lines = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                lines.append(node.strip())
            continue
        tag = node.get("tag", "")
        children = node.get("children", [])
        if tag == "h3":
            lines.append(f"# {inline_to_text(children)}")
        elif tag == "h4":
            lines.append(f"## {inline_to_text(children)}")
        elif tag == "blockquote":
            lines.extend(f"> {line}" for line in content_to_text(children).split("\n") if line)
        elif tag in ("ul", "ol"):
            for number, item in enumerate(children, 1):
                content = inline_to_text(item.get("children", [])) if isinstance(item, dict) else item
                lines.append(f"{number}. {content}" if tag == "ol" else f"- {content}")
        elif tag == "pre":
            lines.extend(["```", plain_text(children), "```"])
        elif tag == "hr":
            lines.append("---")
        elif tag == "figure":
            lines.append(content_to_text(children))
        else:
            text = inline_to_text([node])
            if text.strip():
                lines.append(text)
    return "\n".join(lines)


VOID_TAGS = {"br", "hr", "img"}
PREVIEW_STYLE = (
    "body{max-width:680px;margin:60px auto;padding:0 25px;font:18px Georgia,serif;line-height:1.65}"
    "h1{font:42px Arial,sans-serif}h3,h4{font-family:Arial,sans-serif;line-height:1.3}"
    "blockquote{margin:1em 0;padding-left:1em;border-left:3px solid #000}"
    "pre,code{font-family:monospace;background:#f3f3f3}pre{padding:.7em;overflow-x:auto}"
    "img{max-width:100%}hr{border:0;border-top:1px solid #ccc;margin:2em 0}"
)


def preview_url(url):
    """Rutas relativas de Telegra.ph (/file/…) se resuelven contra su dominio
    y solo se admiten enlaces http(s), como al publicar."""
    url = urllib.parse.urljoin("https://telegra.ph", url)
    return url if url.lower().startswith(("http://", "https://")) else "#"


def nodes_to_html(nodes):
    """HTML de los nodos de Telegra.ph: los mismos que se envían al publicar."""
    parts = []
    for node in nodes:
        if isinstance(node, str):
            parts.append(html.escape(node))
            continue
        tag = node.get("tag", "")
        attrs = node.get("attrs", {})
        attributes = ""
        if tag == "a":
            attributes = f' href="{html.escape(preview_url(attrs.get("href", "")), quote=True)}"'
        elif tag == "img":
            attributes = f' src="{html.escape(preview_url(attrs.get("src", "")), quote=True)}"'
        if tag in VOID_TAGS:
            parts.append(f"<{tag}{attributes}>")
        else:
            parts.append(f"<{tag}{attributes}>{nodes_to_html(node.get('children', []))}</{tag}>")
    return "".join(parts)


def render_preview(title, text):
    """HTML de la vista previa: el Markdown se convierte en los mismos nodos
    que se publican, de modo que se ve igual que en Telegra.ph."""
    title = html.escape(title)
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>{title}</title><style>{PREVIEW_STYLE}</style></head><body><h1>{title}</h1>{nodes_to_html(markdown_to_nodes(text))}</body></html>"


def count_text(count):
    return f"{count} artículo" if count == 1 else f"{count} artículos"


class TelegraphWriter(Gtk.Application):
    def __init__(self):
        # La asociación con el icono del dock se hace mediante el prgname
        # (WM_CLASS) fijado al inicio del módulo y StartupWMClass.
        super().__init__()
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if hasattr(self, "window"):
            self.window.present()
            return
        # gtk-theme-name refleja aquí el tema XSETTINGS del sistema (p. ej.
        # Mint-Y-Orange); se captura antes de tocar la propiedad para poder
        # derivar la variante oscura sin perder el acento del usuario.
        self.system_theme = Gtk.Settings.get_default().get_property("gtk-theme-name")
        self.presented = False
        self.pages = []
        self.preview_file = None
        self.clean_state = None
        self.window = Gtk.ApplicationWindow(application=app, title=APP_NAME)
        self.window.set_default_size(1250, 800)
        self.draft_dir = Path(self.read_config().get("draft_dir", str(DRAFT_DIR))).expanduser()
        self.current_file = None
        self.current_path = None
        self.current_url = None
        self.build_ui()
        self.mark_clean()
        self.restore_pending_session()
        saved_theme = self.read_config().get("dark_mode")
        if saved_theme is not None:
            self.set_theme(bool(saved_theme))
        self.load_pages()
        self.window.present()
        self.presented = True

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
        dialog.set_message("Hay cambios sin guardar.")
        dialog.set_detail("Si continúas se perderán el título y el texto actuales.")
        dialog.set_buttons(["Cancelar", "Descartar cambios"])
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
        write_config(config)

    def read_config(self):
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return config if isinstance(config, dict) else {}

    def access_token(self):
        return self.read_config().get("access_token", "")

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
        token = self.access_token()
        if not token:
            self.pages = []
            self.filter_articles(self.search)
            self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
            self.connection_label.set_text("Sin configurar")
            self.account_label.set_text("Sin configurar")
            self.article_count_label.set_text(count_text(0))
            self.statusbar.set_text("Sin configurar · abre Ajustes para introducir el access token")
            return
        try:
            self.pages, total = fetch_all_pages(token)
            self.filter_articles(self.search)
            self.statusbar.set_text(f"{count_text(total)} cargados" if total != 1 else "1 artículo cargado")
            self.connection_dot.set_markup(f'<span foreground="{COLOR_OK}">●</span>')
            self.connection_label.set_text("Conectado")
            self.article_count_label.set_text(count_text(total))
            self.account_label.set_text(self.account_name(token))
        except Exception as error:
            self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
            self.connection_label.set_text("Sin conexión")
            self.statusbar.set_text(f"Error: {error}")

    def account_name(self, token):
        try:
            account = telegraph_api("getAccountInfo", {"access_token": token, "fields": json.dumps(["short_name"])})
            return account.get("short_name") or "Cuenta de Telegra.ph"
        except Exception:
            return "Cuenta de Telegra.ph"

    def load_article(self, _listbox, row):
        page = getattr(row, "page", None)
        if page:
            self.confirm_discard(lambda: self.open_remote_article(page))

    def open_remote_article(self, page):
        try:
            article = telegraph_api("getPage", {"access_token": self.access_token(), "return_content": "true"}, page["path"])
        except Exception as error:
            self.statusbar.set_text(f"Error al cargar el artículo: {error}")
            return
        # Un artículo remoto no está asociado a ningún borrador local: si se
        # conservara current_file, Guardar sobrescribiría el borrador anterior.
        self.current_file = None
        self.current_path = article.get("path", page.get("path"))
        self.current_url = article.get("url", page.get("url"))
        self.title_entry.set_text(article.get("title", ""))
        self.editor.get_buffer().set_text(content_to_text(article.get("content", [])))
        self.mark_clean()
        self.statusbar.set_text("Artículo cargado")

    def preview(self):
        if self.preview_file:
            self.preview_file.unlink(missing_ok=True)
        with tempfile.NamedTemporaryFile("w", prefix="telegraph_writer_preview_", suffix=".html", delete=False, encoding="utf-8") as handle:
            handle.write(render_preview(self.title_entry.get_text(), self.editor_text()))
        self.preview_file = Path(handle.name)
        webbrowser.open(self.preview_file.as_uri())
        self.statusbar.set_text("Vista previa abierta en el navegador")

    def new_article(self):
        self.confirm_discard(self.reset_editor)

    def reset_editor(self):
        self.current_file = self.current_path = self.current_url = None
        self.title_entry.set_text("")
        self.editor.get_buffer().set_text("")
        self.mark_clean()
        self.statusbar.set_text("Nuevo artículo")

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
        token = self.access_token()
        if not token:
            self.statusbar.set_text("Configura el access token desde Ajustes")
            return
        try:
            page = telegraph_api("createPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"})
        except Exception as error:
            self.statusbar.set_text(f"Error al publicar: {error}")
            return
        self.current_path = page.get("path")
        self.current_url = page.get("url")
        self.mark_clean()
        if self.current_file:
            self.write_draft(self.current_file)
        self.statusbar.set_text("Artículo publicado correctamente")
        self.load_pages()

    def update_article(self):
        if not self.current_path:
            self.show_message("Este artículo todavía no está publicado.\n\nUtiliza «Publicar» para crear el artículo en Telegra.ph.")
            return
        title = self.title_entry.get_text().strip()
        if not title:
            self.show_message("Escribe un título antes de actualizar.")
            return
        token = self.access_token()
        if not token:
            self.statusbar.set_text("Configura el access token desde Ajustes")
            return
        try:
            page = telegraph_api("editPage", {"access_token": token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor_text()), ensure_ascii=False), "return_content": "false"}, self.current_path)
        except Exception as error:
            self.statusbar.set_text(f"Error al actualizar: {error}")
            return
        self.current_url = page.get("url", self.current_url)
        self.mark_clean()
        if self.current_file:
            self.write_draft(self.current_file)
        self.statusbar.set_text("Artículo actualizado correctamente")
        self.load_pages()

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
            self.write_draft(self.current_file)
            return
        try:
            self.draft_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.show_message(f"No se pudo crear la carpeta de borradores.\n\n{error}\n\nElige otra en Ajustes → Elegir…")
            return
        dialog = Gtk.FileDialog(title="Guardar Markdown", initial_name="articulo.md")
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
            self.show_message(f"No se pudo guardar el borrador.\n\n{error}")
            return False
        self.mark_clean()
        self.statusbar.set_text(f"Guardado: {path.name}")
        return True

    def open_file(self):
        dialog = Gtk.FileDialog(title="Abrir Markdown")
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
            self.show_message(f"No se pudo abrir el borrador.\n\n{error}")
            return
        if not isinstance(metadata, dict):
            metadata = {}
        self.current_file = str(path)
        self.current_path = metadata.get("path")
        self.current_url = metadata.get("url")
        self.title_entry.set_text(metadata.get("title", path.stem))
        self.editor.get_buffer().set_text(text)
        self.mark_clean()
        self.statusbar.set_text(f"Abierto: {path.name}")

    def settings(self):
        dialog = Gtk.Dialog(transient_for=self.window, modal=True)
        dialog.set_title("Ajustes")
        dialog.set_default_size(520, 180)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16); box.set_margin_end(16); box.set_margin_top(16); box.set_margin_bottom(16)
        entry = Gtk.Entry(); entry.set_placeholder_text("Access token de Telegra.ph")
        entry.set_text(self.access_token()); box.append(entry)
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
                feedback.set_text("Introduce un access token.")
                return
            try:
                account = telegraph_api("getAccountInfo", {"access_token": token, "fields": json.dumps(["short_name", "page_count"])})
                feedback.set_text(f"Conectado: {account.get('short_name', '')} · {count_text(account.get('page_count', 0))}")
            except Exception as error:
                feedback.set_text(f"Error: {error}")
        test.connect("clicked", test_connection)

        def save_config(*_):
            config = self.read_config()
            config["access_token"] = entry.get_text().strip()
            config["draft_dir"] = draft_entry.get_text().strip() or str(DRAFT_DIR)
            try:
                write_config(config)
            except OSError as error:
                feedback.set_text(f"No se pudo guardar la configuración: {error}")
                return
            self.draft_dir = Path(config["draft_dir"]).expanduser()
            dialog.close()
            self.load_pages()
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
        paned.set_end_child(self.build_editor())
        root.append(paned)

        self.statusbar = Gtk.Label(label="", xalign=1)
        self.statusbar.set_margin_start(12)
        self.statusbar.set_margin_end(12)
        self.statusbar.set_margin_top(4)
        self.statusbar.set_margin_bottom(4)
        root.append(self.statusbar)

    def build_menubar(self):
        bar = Gtk.Box(spacing=12)
        bar.set_margin_start(12); bar.set_margin_end(12)
        bar.set_margin_top(5); bar.set_margin_bottom(5)
        menus = (
            ("Archivo", "document-properties", (
                ("Nuevo", "document-new", self.new_article),
                ("Abrir", "document-open", self.open_file),
                ("Guardar", "document-save", self.save_file),
            )),
            ("Telegra.ph", "applications-internet", (
                ("Publicar", "document-send", self.publish),
                ("Actualizar", "view-refresh", self.update_article),
                ("Abrir artículo en navegador", "web-browser", self.open_in_browser),
            )),
            ("Tema", "preferences-desktop-theme", (
                ("Claro", "weather-clear", lambda: self.set_theme(False)),
                ("Oscuro", "weather-clear-night", lambda: self.set_theme(True)),
            )),
            ("Ayuda", "help-browser", (
                ("Acerca de", "help-about", self.about),
            )),
        )
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
            ("Nuevo", "document-new", self.new_article),
            ("Abrir", "document-open", self.open_file),
            ("Guardar", "document-save", self.save_file),
            ("Insertar imagen", "insert-image", self.insert_image),
            ("Ajustes", "preferences-system", self.settings),
        )
        for label, icon_name, callback in buttons:
            button = Gtk.Button()
            button.set_tooltip_text(label)
            content = Gtk.Box(spacing=6)
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(16)
            content.append(icon)
            content.append(Gtk.Label(label=label))
            button.set_child(content)
            button.connect("clicked", lambda _, fn=callback: fn())
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
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True); scroll.set_child(listbox)
        listbox.connect("row-activated", self.load_article)
        box.append(scroll)
        account = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        connection = Gtk.Box(spacing=5)
        self.connection_dot = Gtk.Label()
        self.connection_dot.set_markup(f'<span foreground="{COLOR_ERROR}">●</span>')
        self.connection_label = Gtk.Label(label="Sin configurar", xalign=0)
        connection.append(self.connection_dot); connection.append(self.connection_label)
        account.append(connection)
        self.account_label = Gtk.Label(label="Sin configurar", xalign=0)
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
        for label, callback in (("Vista previa", self.preview), ("Publicar", self.publish), ("Actualizar", self.update_article)):
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _, fn=callback: fn())
            actions.append(button)
        box.append(actions)
        return box

    def set_theme(self, dark):
        # Cambiar gtk-theme-name en caliente no repinta una ventana ya
        # presentada en Cinnamon/Mint (solo surte efecto antes del primer
        # present()), así que si la app ya está en marcha se reinicia el
        # proceso tras persistir la preferencia y el borrador en curso.
        Gtk.Settings.get_default().set_property("gtk-theme-name", theme_variant(self.system_theme, dark))
        config = self.read_config()
        config["dark_mode"] = dark
        if self.presented:
            config["_pending_session"] = self.collect_session_state()
            write_config(config)
            # Instalado, el lanzador hace "exec -a telegraph-writer python3 ...",
            # así que sys.executable apunta al propio script /usr/bin/telegraph-writer;
            # reejecutarlo le pasaría la ruta del .py como argumento y
            # Gtk.Application.run() saldría con "can not open files". Se usa el
            # intérprete real y se conserva argv[0] para el icono del dock.
            os.execve("/proc/self/exe", [sys.orig_argv[0], os.path.abspath(__file__)], os.environ)
        write_config(config)
        self.statusbar.set_text("Tema oscuro aplicado" if dark else "Tema claro aplicado")

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
