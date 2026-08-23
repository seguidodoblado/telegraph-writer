#!/usr/bin/env python3

import json
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QSplitter,
    QListWidget, QListWidgetItem, QLineEdit, QPlainTextEdit, QLabel,
    QPushButton, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout,
    QHBoxLayout, QMessageBox, QFileDialog, QStatusBar, QSizePolicy
)

APP_NAME = "Telegraph Writer"
API_URL = "https://api.telegra.ph"
CONFIG_DIR = Path.home() / ".config" / "telegraph-writer"
CONFIG_FILE = CONFIG_DIR / "config.json"
DRAFT_DIR = Path.home() / "Telegra.ph"


def load_config():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def telegraph_api(method, params=None, path=None):
    params = params or {}
    url = f"{API_URL}/{method}" if not path else f"{API_URL}/{method}/{path}"
    data = urlencode(params).encode("utf-8")
    request = Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
    request.add_header("User-Agent", "Telegraph-Writer/2.0")
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Error desconocido de Telegra.ph"))
    return result["result"]


def inline_to_nodes(text):
    result = []
    pattern = re.compile(
        r'!\[([^\]]*)\]\(([^)\s]+)\)'
        r'|\[([^\]]+)\]\(([^)\s]+)\)'
        r'|\*\*([^*]+)\*\*|__([^_]+)__'
        r'|~~([^~]+)~~|`([^`]+)`'
        r'|\*([^*]+)\*|_([^_]+)_'
    )
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            result.append(text[position:match.start()])
        if match.group(1) is not None:
            result.append({"tag": "img", "attrs": {"src": match.group(2)}})
        elif match.group(3) is not None:
            result.append({"tag": "a", "attrs": {"href": match.group(4)}, "children": [match.group(3)]})
        elif match.group(5) or match.group(6):
            result.append({"tag": "strong", "children": [match.group(5) or match.group(6)]})
        elif match.group(7):
            result.append({"tag": "s", "children": [match.group(7)]})
        elif match.group(8):
            result.append({"tag": "code", "children": [match.group(8)]})
        elif match.group(9):
            result.append({"tag": "em", "children": [match.group(9)]})
        elif match.group(10):
            result.append({"tag": "em", "children": [match.group(10)]})
        position = match.end()
    if position < len(text):
        result.append(text[position:])
    return result or [""]


def markdown_to_nodes(markdown):
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    nodes = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            nodes.append({"tag": "pre", "children": [{"tag": "code", "children": ["\n".join(code)]}]})
            continue
        heading = re.match(r"^\s*(#{1,6})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            nodes.append({"tag": "h3" if level == 1 else "h4", "children": inline_to_nodes(heading.group(2))})
            i += 1
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            nodes.append({"tag": "blockquote", "children": [{"tag": "p", "children": inline_to_nodes(" ".join(quote))}]})
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < len(lines):
                match = re.match(r"^\s*[-*+]\s+(.+)$", lines[i])
                if not match:
                    break
                items.append({"tag": "li", "children": inline_to_nodes(match.group(1))})
                i += 1
            nodes.append({"tag": "ul", "children": items})
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < len(lines):
                match = re.match(r"^\s*\d+\.\s+(.+)$", lines[i])
                if not match:
                    break
                items.append({"tag": "li", "children": inline_to_nodes(match.group(1))})
                i += 1
            nodes.append({"tag": "ol", "children": items})
            continue
        if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line):
            nodes.append({"tag": "hr"})
            i += 1
            continue
        paragraph = [line.strip()]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                break
            if (re.match(r"^\s*#{1,6}\s+", nxt) or nxt.lstrip().startswith(">") or
                    re.match(r"^\s*[-*+]\s+", nxt) or re.match(r"^\s*\d+\.\s+", nxt) or
                    nxt.strip().startswith("```")):
                break
            paragraph.append(nxt.strip())
            i += 1
        children = []
        for n, text in enumerate(paragraph):
            children.extend(inline_to_nodes(text))
            if n < len(paragraph) - 1:
                children.append({"tag": "br"})
        nodes.append({"tag": "p", "children": children})
    return nodes


def node_to_markdown(node):
    if isinstance(node, str):
        return node
    tag = node.get("tag", "")
    children = node.get("children", [])
    attrs = node.get("attrs", {})
    if tag == "p": return "".join(node_to_markdown(x) for x in children)
    if tag == "h3": return "# " + "".join(node_to_markdown(x) for x in children)
    if tag == "h4": return "## " + "".join(node_to_markdown(x) for x in children)
    if tag == "blockquote":
        text = "".join(node_to_markdown(x) for x in children)
        return "\n".join("> " + line for line in text.splitlines())
    if tag == "ul": return "\n".join("- " + node_to_markdown(x) for x in children)
    if tag == "ol": return "\n".join(f"{n + 1}. " + node_to_markdown(x) for n, x in enumerate(children))
    if tag == "li": return "".join(node_to_markdown(x) for x in children)
    if tag == "pre": return "```\n" + "".join(node_to_markdown(x) for x in children) + "\n```"
    if tag == "code": return "`" + "".join(node_to_markdown(x) for x in children) + "`"
    if tag == "strong": return "**" + "".join(node_to_markdown(x) for x in children) + "**"
    if tag == "em": return "*" + "".join(node_to_markdown(x) for x in children) + "*"
    if tag == "s": return "~~" + "".join(node_to_markdown(x) for x in children) + "~~"
    if tag == "a": return "[" + "".join(node_to_markdown(x) for x in children) + "](" + attrs.get("href", "") + ")"
    if tag == "img": return "![](" + attrs.get("src", "") + ")"
    if tag == "br": return "\n"
    if tag == "hr": return "---"
    return "".join(node_to_markdown(x) for x in children)


def nodes_to_markdown(nodes):
    parts = []
    for node in nodes:
        text = node_to_markdown(node)
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


class ApiWorker(QThread):
    success = Signal(object)
    failure = Signal(str)
    def __init__(self, method, params=None, path=None):
        super().__init__()
        self.method = method
        self.params = params
        self.path = path
    def run(self):
        try:
            self.success.emit(telegraph_api(self.method, self.params, self.path))
        except Exception as error:
            self.failure.emit(str(error))


class SettingsDialog(QDialog):
    def __init__(self, parent, token):
        super().__init__(parent)
        self.setWindowTitle("Ajustes — Telegraph Writer")
        self.resize(560, 230)
        self.token_entry = QLineEdit()
        self.token_entry.setText(token)
        self.token_entry.setEchoMode(QLineEdit.Password)
        self.test_button = QPushButton("Comprobar conexión")
        self.test_button.clicked.connect(self.check_connection)
        self.status = QLabel("")
        form = QFormLayout()
        form.addRow("Access token:", self.token_entry)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.test_button)
        layout.addWidget(self.status)
        layout.addWidget(buttons)
    def check_connection(self):
        token = self.token_entry.text().strip()
        if not token:
            self.status.setText("Introduce un access token.")
            return
        self.status.setText("Comprobando...")
        self.worker = ApiWorker("getAccountInfo", {
            "access_token": token,
            "fields": json.dumps(["short_name", "author_name", "author_url", "page_count"])
        })
        self.worker.success.connect(self.connection_ok)
        self.worker.failure.connect(self.connection_error)
        self.worker.start()
    def connection_ok(self, account):
        self.status.setText(f"✓ Conectado: {account.get('short_name', '')} · {account.get('page_count', 0)} artículos")
    def connection_error(self, error):
        self.status.setText("✗ " + error)
    def token(self):
        return self.token_entry.text().strip()


class TelegraphWriter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.token = self.config.get("access_token", "")
        self.dark_mode = self.config.get("dark_mode", True)
        self.pages = []
        self.filtered_pages = []
        self.current_path = None
        self.current_url = None
        self.current_file = None
        self.dirty = False
        self.loading_article = False
        self.setWindowTitle(APP_NAME)
        self.resize(1250, 800)
        self.setup_font()
        self.build_ui()
        self.apply_theme()
        self.load_pages()

    def setup_font(self):
        QApplication.instance().setFont(QFont("Ubuntu Sans", 10))

    def build_ui(self):
        self.create_actions()
        self.create_toolbar()
        self.create_menu()
        self.create_main_area()
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.stats_label = QLabel("0 palabras · 0 caracteres")
        self.status.addPermanentWidget(self.stats_label)
        self.status.showMessage("Listo")

    def create_actions(self):
        self.new_action = QAction("Nuevo", self); self.new_action.setShortcut(QKeySequence.New); self.new_action.triggered.connect(self.new_article)
        self.open_action = QAction("Abrir", self); self.open_action.setShortcut(QKeySequence.Open); self.open_action.triggered.connect(self.open_file)
        self.save_action = QAction("Guardar", self); self.save_action.setShortcut(QKeySequence.Save); self.save_action.triggered.connect(self.save_file)
        self.publish_action = QAction("Publicar", self); self.publish_action.setShortcut("Ctrl+P"); self.publish_action.triggered.connect(self.publish)
        self.update_action = QAction("Actualizar", self); self.update_action.triggered.connect(self.update_article)
        self.preview_action = QAction("Vista previa", self); self.preview_action.triggered.connect(self.preview)
        self.settings_action = QAction("Ajustes", self); self.settings_action.triggered.connect(self.settings)
        self.theme_action = QAction("Cambiar tema", self); self.theme_action.triggered.connect(self.toggle_theme)
        self.refresh_action = QAction("Actualizar lista", self); self.refresh_action.setShortcut("F5"); self.refresh_action.triggered.connect(self.load_pages)

    def create_toolbar(self):
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.settings_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent; border: none;")
        toolbar.addWidget(spacer)
        self.theme_button = QPushButton()
        self.theme_button.setFixedSize(42, 32)
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.setToolTip("Cambiar entre modo claro y oscuro")
        self.theme_button.clicked.connect(self.toggle_theme)
        toolbar.addWidget(self.theme_button)
        self.update_theme_button()

    def create_menu(self):
        file_menu = self.menuBar().addMenu("Archivo")
        file_menu.addAction(self.new_action); file_menu.addAction(self.open_action); file_menu.addAction(self.save_action)
        file_menu.addSeparator(); file_menu.addAction("Salir", self.close)
        telegraph_menu = self.menuBar().addMenu("Telegra.ph")
        telegraph_menu.addAction(self.publish_action); telegraph_menu.addAction(self.update_action); telegraph_menu.addAction(self.refresh_action)
        telegraph_menu.addSeparator(); telegraph_menu.addAction("Abrir artículo en navegador", self.open_current_url)
        view_menu = self.menuBar().addMenu("Vista")
        view_menu.addAction(self.preview_action); view_menu.addAction(self.theme_action)
        help_menu = self.menuBar().addMenu("Ayuda")
        help_menu.addAction("Acerca de", self.about)

    def create_main_area(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        self.setCentralWidget(splitter)
        left = QWidget(); left_layout = QVBoxLayout(left); left_layout.setContentsMargins(12, 12, 8, 12)
        title = QLabel("MIS ARTÍCULOS"); title.setObjectName("sectionTitle"); left_layout.addWidget(title)
        self.search = QLineEdit(); self.search.setPlaceholderText("Buscar artículos…"); self.search.textChanged.connect(self.filter_pages); left_layout.addWidget(self.search)
        self.page_list = QListWidget(); self.page_list.itemDoubleClicked.connect(self.load_selected_page); self.page_list.itemClicked.connect(self.load_selected_page); left_layout.addWidget(self.page_list, 1)
        self.account_label = QLabel("Sin conectar"); self.account_label.setObjectName("accountLabel"); left_layout.addWidget(self.account_label)
        splitter.addWidget(left)
        editor_panel = QWidget(); editor_layout = QVBoxLayout(editor_panel); editor_layout.setContentsMargins(10, 10, 12, 10)
        self.title_edit = QLineEdit(); self.title_edit.setPlaceholderText("Título del artículo"); self.title_edit.setObjectName("titleEdit"); self.title_edit.textChanged.connect(self.mark_dirty); editor_layout.addWidget(self.title_edit)
        self.editor = QPlainTextEdit(); self.editor.setPlaceholderText("Empieza a escribir tu artículo…\n\nPuedes utilizar Markdown."); self.editor.setTabStopDistance(32); self.editor.textChanged.connect(self.editor_changed); editor_layout.addWidget(self.editor, 1)
        bottom = QHBoxLayout(); self.document_status = QLabel("Nuevo artículo"); bottom.addWidget(self.document_status); bottom.addStretch()
        preview_button = QPushButton("Vista previa"); preview_button.clicked.connect(self.preview); bottom.addWidget(preview_button)
        publish_button = QPushButton("Publicar"); publish_button.setObjectName("primaryButton"); publish_button.clicked.connect(self.publish); bottom.addWidget(publish_button)
        update_button = QPushButton("Actualizar"); update_button.clicked.connect(self.update_article); bottom.addWidget(update_button)
        editor_layout.addLayout(bottom); splitter.addWidget(editor_panel); splitter.setSizes([310, 900])

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background:#181a1b; }
                QWidget { background:#181a1b; color:#eeeeee; }
                QToolBar { background:#202324; border:none; border-bottom:1px solid #34383b; spacing:4px; padding:5px; }
                QToolButton { padding:7px 12px; border-radius:6px; }
                QToolButton:hover { background:#303537; } QToolButton:pressed { background:#3a4145; }
                QMenuBar { background:#202324; color:#eeeeee; } QMenuBar::item:selected { background:#303537; }
                QMenu { background:#242728; color:#eeeeee; border:1px solid #3b4043; } QMenu::item:selected { background:#315a78; }
                QLineEdit,QPlainTextEdit { background:#151718; color:#eeeeee; border:1px solid #34383b; border-radius:6px; selection-background-color:#315a78; }
                QLineEdit:focus,QPlainTextEdit:focus { border:1px solid #5b9bd5; }
                #titleEdit { font-size:24px; padding:8px 12px; border:none; border-bottom:1px solid #34383b; border-radius:0; }
                QListWidget { background:#202324; border:none; border-radius:6px; outline:none; }
                QListWidget::item { padding:10px; border-radius:5px; } QListWidget::item:hover { background:#2c3032; }
                QListWidget::item:selected { background:#315a78; color:white; }
                #sectionTitle { font-size:12px; font-weight:bold; color:#b8bec2; }
                #accountLabel { color:#7bd88f; padding:8px 2px; }
                QStatusBar { background:#202324; color:#9da4a8; border-top:1px solid #34383b; }
                QPushButton { background:#2a2e30; color:#eeeeee; border:1px solid #41474a; border-radius:6px; padding:8px 15px; }
                QPushButton:hover { background:#353a3d; } QPushButton:pressed { background:#41484c; }
                #primaryButton { background:#315a78; border-color:#4a789b; } #primaryButton:hover { background:#3b6b8d; }
                QScrollBar:vertical { background:#181a1b; width:12px; } QScrollBar::handle:vertical { background:#444b4f; border-radius:6px; min-height:30px; }
                #themeButton { background:#2a2e30; border:1px solid #41474a; border-radius:6px; font-size:17px; padding:0; }
                #themeButton:hover { background:#353a3d; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background:#f5f5f5; }
                QWidget { background:#f5f5f5; color:#202124; }
                QToolBar { background:#ffffff; border:none; border-bottom:1px solid #dddddd; spacing:4px; padding:5px; }
                QToolButton { padding:7px 12px; border-radius:6px; } QToolButton:hover { background:#eeeeee; } QToolButton:pressed { background:#e3e3e3; }
                QMenuBar { background:#ffffff; color:#202124; } QMenuBar::item:selected { background:#eeeeee; }
                QMenu { background:#ffffff; color:#202124; border:1px solid #dddddd; } QMenu::item:selected { background:#dcecff; }
                QLineEdit,QPlainTextEdit { background:#ffffff; color:#202124; border:1px solid #d5d5d5; border-radius:6px; selection-background-color:#bcd7f0; }
                QLineEdit:focus,QPlainTextEdit:focus { border:1px solid #6aa5d8; }
                #titleEdit { font-size:24px; padding:8px 12px; border:none; border-bottom:1px solid #dddddd; border-radius:0; }
                QListWidget { background:#ffffff; border:1px solid #dddddd; border-radius:6px; outline:none; }
                QListWidget::item { padding:10px; border-radius:5px; } QListWidget::item:hover { background:#eeeeee; }
                QListWidget::item:selected { background:#dcecff; color:#202124; }
                #sectionTitle { font-size:12px; font-weight:bold; color:#555555; } #accountLabel { color:#287a3d; padding:8px 2px; }
                QStatusBar { background:#ffffff; color:#666666; border-top:1px solid #dddddd; }
                QPushButton { background:#ffffff; color:#202124; border:1px solid #cccccc; border-radius:6px; padding:8px 15px; }
                QPushButton:hover { background:#eeeeee; } QPushButton:pressed { background:#e2e2e2; }
                #primaryButton { background:#1976d2; color:white; border-color:#1976d2; } #primaryButton:hover { background:#2b82d0; }
                #themeButton { background:#ffffff; border:1px solid #cccccc; border-radius:6px; font-size:17px; padding:0; } #themeButton:hover { background:#eeeeee; }
            """)
        if hasattr(self, "theme_button"):
            self.theme_button.setObjectName("themeButton")
            self.theme_button.style().unpolish(self.theme_button)
            self.theme_button.style().polish(self.theme_button)

    def update_theme_button(self):
        if not hasattr(self, "theme_button"):
            return
        if self.dark_mode:
            self.theme_button.setText("☀")
            self.theme_button.setToolTip("Cambiar a modo claro")
        else:
            self.theme_button.setText("☾")
            self.theme_button.setToolTip("Cambiar a modo oscuro")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.config["dark_mode"] = self.dark_mode
        save_config(self.config)
        self.apply_theme()
        self.update_theme_button()

    def load_pages(self):
        if not self.token:
            self.account_label.setText("Sin configurar")
            return
        self.status.showMessage("Comprobando cuenta…")
        self.worker = ApiWorker("getAccountInfo", {"access_token": self.token, "fields": json.dumps(["short_name", "author_name", "author_url", "page_count"])})
        self.worker.success.connect(self.account_loaded); self.worker.failure.connect(self.api_error); self.worker.start()

    def account_loaded(self, account):
        self.account_label.setText(f"● Conectado\n{account.get('short_name', '')}\n{account.get('page_count', 0)} artículos")
        self.worker = ApiWorker("getPageList", {"access_token": self.token, "limit": 200})
        self.worker.success.connect(self.pages_loaded); self.worker.failure.connect(self.api_error); self.worker.start()

    def pages_loaded(self, result):
        self.pages = result.get("pages", [])
        self.filter_pages()
        self.status.showMessage(f"{len(self.pages)} artículos cargados")

    def filter_pages(self):
        query = self.search.text().strip().lower()
        self.page_list.clear(); self.filtered_pages = []
        for page in self.pages:
            title = page.get("title", "(sin título)")
            if query and query not in title.lower():
                continue
            self.filtered_pages.append(page)
            item = QListWidgetItem(f"{title}\n{page.get('views', 0)} vistas")
            item.setData(Qt.UserRole, page)
            self.page_list.addItem(item)

    def load_selected_page(self, item):
        page = item.data(Qt.UserRole)
        if not page:
            return
        self.status.showMessage("Cargando artículo…")
        self.worker = ApiWorker("getPage", {"return_content": "true"}, page.get("path"))
        self.worker.success.connect(self.article_loaded); self.worker.failure.connect(self.api_error); self.worker.start()

    def article_loaded(self, page):
        self.loading_article = True
        self.current_path = page.get("path"); self.current_url = page.get("url"); self.current_file = None
        self.title_edit.setText(page.get("title", "")); self.editor.setPlainText(nodes_to_markdown(page.get("content", [])))
        self.loading_article = False; self.dirty = False; self.update_stats()
        self.document_status.setText("Artículo publicado"); self.status.showMessage("Artículo cargado")

    def editor_changed(self):
        if self.loading_article: return
        self.dirty = True; self.document_status.setText("● Cambios sin guardar"); self.update_stats()

    def mark_dirty(self):
        if self.loading_article: return
        self.dirty = True; self.document_status.setText("● Cambios sin guardar")

    def update_stats(self):
        text = self.editor.toPlainText(); self.stats_label.setText(f"{len(text.split()):,} palabras · {len(text):,} caracteres")

    def new_article(self):
        if not self.confirm_discard(): return
        self.loading_article = True; self.title_edit.clear(); self.editor.clear()
        self.current_path = None; self.current_url = None; self.current_file = None; self.loading_article = False; self.dirty = False
        self.document_status.setText("Nuevo artículo"); self.status.showMessage("Nuevo artículo"); self.title_edit.setFocus(); self.update_stats()

    def save_file(self):
        if not self.current_file:
            DRAFT_DIR.mkdir(parents=True, exist_ok=True)
            filename, _ = QFileDialog.getSaveFileName(self, "Guardar Markdown", str(DRAFT_DIR / "articulo.md"), "Markdown (*.md);;Todos los archivos (*)")
            if not filename: return False
            self.current_file = Path(filename)
        DRAFT_DIR.mkdir(parents=True, exist_ok=True)
        self.current_file.write_text(self.editor.toPlainText(), encoding="utf-8")
        metadata = {"title": self.title_edit.text(), "path": self.current_path, "url": self.current_url}
        self.current_file.with_suffix(".telegraph.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self.dirty = False; self.document_status.setText("Guardado"); self.status.showMessage("Guardado localmente"); return True

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Abrir Markdown", str(DRAFT_DIR), "Markdown (*.md);;Todos los archivos (*)")
        if not filename: return
        path = Path(filename); self.current_file = path; self.editor.setPlainText(path.read_text(encoding="utf-8"))
        metadata_file = path.with_suffix(".telegraph.json")
        if metadata_file.exists():
            try: metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception: metadata = {}
            self.title_edit.setText(metadata.get("title", path.stem)); self.current_path = metadata.get("path"); self.current_url = metadata.get("url")
        else:
            self.title_edit.setText(path.stem); self.current_path = None; self.current_url = None
        self.dirty = False; self.document_status.setText("Documento local"); self.update_stats(); self.status.showMessage(f"Abierto: {path.name}")

    def publish(self):
        if self.current_path:
            QMessageBox.warning(
                self,
                APP_NAME,
                "Este documento ya está publicado en Telegra.ph.\n\n"
                "Utiliza «Actualizar» para aplicar las modificaciones "
                "sin crear un artículo duplicado."
            )
            return
        if not self.token:
            self.settings()
            if not self.token: return
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, APP_NAME, "Escribe un título."); self.title_edit.setFocus(); return
        params = {"access_token": self.token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor.toPlainText()), ensure_ascii=False), "return_content": "false"}
        self.status.showMessage("Publicando…")
        self.worker = ApiWorker("createPage", params); self.worker.success.connect(self.published); self.worker.failure.connect(self.api_error); self.worker.start()

    def published(self, page):
        self.current_path = page.get("path"); self.current_url = page.get("url"); self.dirty = False; self.document_status.setText("Publicado"); self.status.showMessage("Artículo publicado"); self.load_pages()
        if self.current_url and QMessageBox.question(self, APP_NAME, f"Artículo publicado correctamente.\n\n{self.current_url}\n\n¿Quieres abrirlo en el navegador?") == QMessageBox.Yes:
            webbrowser.open(self.current_url)

    def update_article(self):
        if not self.token:
            self.settings()
            if not self.token: return
        if not self.current_path:
            QMessageBox.information(self, APP_NAME, "Este documento todavía no está vinculado a un artículo de Telegra.ph.\n\nUtiliza «Publicar»."); return
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, APP_NAME, "El artículo necesita un título."); return
        params = {"access_token": self.token, "title": title, "content": json.dumps(markdown_to_nodes(self.editor.toPlainText()), ensure_ascii=False), "return_content": "false"}
        self.status.showMessage("Actualizando…")
        self.worker = ApiWorker("editPage", params, self.current_path); self.worker.success.connect(self.updated); self.worker.failure.connect(self.api_error); self.worker.start()

    def updated(self, page):
        self.current_path = page.get("path", self.current_path); self.current_url = page.get("url", self.current_url); self.dirty = False; self.document_status.setText("Publicado · actualizado"); self.load_pages(); self.status.showMessage("Artículo actualizado correctamente")

    def preview(self):
        title = self.title_edit.text(); html = f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>{html_escape(title)}</title><style>body{{max-width:680px;margin:60px auto;padding:0 25px;font-family:Georgia,serif;font-size:18px;line-height:1.65;color:#222}}h1{{font-family:Arial,sans-serif;font-size:42px;line-height:1.1}}h3,h4{{font-family:Arial,sans-serif}}img{{max-width:100%}}pre{{background:#f0f0f0;padding:15px;overflow-x:auto}}blockquote{{border-left:4px solid #aaa;padding-left:16px;color:#666}}a{{color:#1683d8}}</style></head><body><h1>{html_escape(title)}</h1>{nodes_to_html(markdown_to_nodes(self.editor.toPlainText()))}</body></html>'''
        filename = Path("/tmp") / "telegraph_writer_preview.html"; filename.write_text(html, encoding="utf-8"); webbrowser.open(filename.as_uri())

    def settings(self):
        dialog = SettingsDialog(self, self.token)
        if dialog.exec() == QDialog.Accepted:
            token = dialog.token()
            if token:
                self.token = token; self.config["access_token"] = token; save_config(self.config); self.load_pages()

    def open_current_url(self):
        if self.current_url: webbrowser.open(self.current_url)
        else: QMessageBox.information(self, APP_NAME, "El documento todavía no tiene una URL de Telegra.ph.")

    def api_error(self, error):
        self.status.showMessage("Error"); QMessageBox.critical(self, APP_NAME, error)

    def confirm_discard(self):
        if not self.dirty: return True
        answer = QMessageBox.question(self, APP_NAME, "Hay cambios sin guardar.\n\n¿Quieres guardarlos antes de continuar?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Save: return self.save_file()
        if answer == QMessageBox.Discard: return True
        return False

    def closeEvent(self, event):
        if self.confirm_discard(): event.accept()
        else: event.ignore()

    def about(self):
        QMessageBox.about(self, APP_NAME, "<h2>Telegraph Writer</h2><p>Cliente de escritorio para Telegra.ph.</p><p>Versión 2.0 · Qt / PySide6</p>")


def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def nodes_to_html(nodes):
    def convert(node):
        if isinstance(node, str): return html_escape(node).replace("\n", "<br>\n")
        tag = node.get("tag", "span"); attrs = ""
        for key, value in node.get("attrs", {}).items(): attrs += f' {key}="{html_escape(str(value))}"'
        children = "".join(convert(child) for child in node.get("children", []))
        return f"<{tag}{attrs}>{children}</{tag}>"
    return "".join(convert(node) for node in nodes)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("TelegraphWriter")
    window = TelegraphWriter(); window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
