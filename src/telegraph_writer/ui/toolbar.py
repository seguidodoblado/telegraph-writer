"""Barra de formato Markdown para el editor (portada de Bloguero y ampliada con tachado y subrayado)."""
import re

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..i18n import _

_TOOLBAR_NUMBERED_RE = re.compile(r"^\d+\. ")
_TOOLBAR_HEADING_RE = re.compile(r"^(#{1,6}) (.*)$")
_TOOLBAR_MAX_HEADING_LEVEL = 2


def build_markdown_toolbar(text_view):
    """Crea una barra de botones de formato Markdown para `text_view`."""
    toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    toolbar.add_css_class("toolbar")

    # Cada entrada: (icon_name simbólico | None, texto si no hay icono,
    # tooltip, acción). Los iconos ya son simbólicos, así que no pasan por
    # icon_variant(): se ven igual en los dos temas, como el resto de
    # controles «en línea» de GNOME.
    buttons = [
        ("format-text-bold-symbolic", None, _("Negrita (**texto**)"), lambda: _toolbar_wrap_selection(text_view, "**", "**")),
        ("format-text-italic-symbolic", None, _("Cursiva (*texto*)"), lambda: _toolbar_wrap_selection(text_view, "*", "*")),
        ("format-text-strikethrough-symbolic", None, _("Tachado (~~texto~~)"), lambda: _toolbar_wrap_selection(text_view, "~~", "~~")),
        ("format-text-underline-symbolic", None, _("Subrayado (__texto__)"), lambda: _toolbar_wrap_selection(text_view, "__", "__")),
        (None, "H", _("Título: alterna H1 (#), H2 (##) y texto normal"), lambda: _toolbar_cycle_heading(text_view)),
        ("view-list-bullet-symbolic", None, _("Lista con viñetas"), lambda: _toolbar_toggle_line_prefix(text_view, "- ")),
        ("view-list-ordered-symbolic", None, _("Lista numerada"), lambda: _toolbar_apply_numbered_list(text_view)),
        ("format-indent-more-symbolic", None, _("Cita (> texto)"), lambda: _toolbar_toggle_line_prefix(text_view, "> ")),
        (None, "<>", _("Código (`texto`)"), lambda: _toolbar_wrap_selection(text_view, "`", "`")),
        ("insert-link-symbolic", None, _("Enlace ([texto](url))"), lambda: _toolbar_apply_link(text_view)),
    ]

    for icon_name, label, tooltip, action in buttons:
        button = Gtk.Button(icon_name=icon_name) if icon_name else Gtk.Button(label=label)
        button.add_css_class("flat")
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _btn, fn=action: fn())
        toolbar.append(button)

    return toolbar


def _toolbar_wrap_selection(text_view, prefix, suffix):
    buffer = text_view.get_buffer()
    bounds = buffer.get_selection_bounds()

    buffer.begin_user_action()
    if bounds:
        start, end = bounds
        start_off, end_off = start.get_offset(), end.get_offset()
        selected = buffer.get_text(start, end, True)
        buffer.delete(buffer.get_iter_at_offset(start_off), buffer.get_iter_at_offset(end_off))
        buffer.insert(buffer.get_iter_at_offset(start_off), f"{prefix}{selected}{suffix}")
        cursor_offset = start_off + len(prefix) + len(selected) + len(suffix)
    else:
        offset = buffer.get_iter_at_mark(buffer.get_insert()).get_offset()
        buffer.insert(buffer.get_iter_at_offset(offset), f"{prefix}{suffix}")
        cursor_offset = offset + len(prefix)
    buffer.end_user_action()

    buffer.place_cursor(buffer.get_iter_at_offset(cursor_offset))
    text_view.grab_focus()


def _toolbar_selected_or_cursor_lines(text_view):
    """Devuelve (offset_inicio, offset_fin) de las líneas completas afectadas."""
    buffer = text_view.get_buffer()
    bounds = buffer.get_selection_bounds()
    if bounds:
        start, end = bounds
    else:
        it = buffer.get_iter_at_mark(buffer.get_insert())
        start, end = it.copy(), it.copy()

    start_it = buffer.get_iter_at_offset(start.get_offset())
    start_it.set_line_offset(0)
    end_it = buffer.get_iter_at_offset(end.get_offset())
    if not end_it.ends_line():
        end_it.forward_to_line_end()
    return start_it.get_offset(), end_it.get_offset()


def _toolbar_toggle_line_prefix(text_view, prefix):
    buffer = text_view.get_buffer()
    region_start, region_end = _toolbar_selected_or_cursor_lines(text_view)
    text = buffer.get_text(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end), True)
    lines = text.split("\n")

    if all((not line) or line.startswith(prefix) for line in lines):
        new_lines = [line.removeprefix(prefix) for line in lines]
    else:
        new_lines = [prefix + line if line else line for line in lines]
    new_text = "\n".join(new_lines)

    buffer.begin_user_action()
    buffer.delete(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end))
    buffer.insert(buffer.get_iter_at_offset(region_start), new_text)
    buffer.end_user_action()
    text_view.grab_focus()


def _toolbar_cycle_heading(text_view):
    """Alterna el nivel de título de las líneas afectadas: normal -> H1 -> H2 -> normal."""
    buffer = text_view.get_buffer()
    region_start, region_end = _toolbar_selected_or_cursor_lines(text_view)
    text = buffer.get_text(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end), True)
    lines = text.split("\n")

    stripped = []
    current_level = 0
    for i, line in enumerate(lines):
        match = _TOOLBAR_HEADING_RE.match(line)
        if match:
            content, level = match.group(2), len(match.group(1))
        else:
            content, level = line, 0
        if i == 0:
            current_level = level
        stripped.append(content)

    next_level = 0 if current_level >= _TOOLBAR_MAX_HEADING_LEVEL else current_level + 1
    if next_level == 0:
        new_lines = stripped
    else:
        prefix = "#" * next_level + " "
        new_lines = [prefix + content if content else content for content in stripped]
    new_text = "\n".join(new_lines)

    buffer.begin_user_action()
    buffer.delete(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end))
    buffer.insert(buffer.get_iter_at_offset(region_start), new_text)
    buffer.end_user_action()
    text_view.grab_focus()


def _toolbar_apply_numbered_list(text_view):
    buffer = text_view.get_buffer()
    region_start, region_end = _toolbar_selected_or_cursor_lines(text_view)
    text = buffer.get_text(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end), True)
    lines = text.split("\n")

    if all((not line) or _TOOLBAR_NUMBERED_RE.match(line) for line in lines):
        new_lines = [_TOOLBAR_NUMBERED_RE.sub("", line) for line in lines]
    else:
        new_lines = [f"{i + 1}. {line}" if line else line for i, line in enumerate(lines)]
    new_text = "\n".join(new_lines)

    buffer.begin_user_action()
    buffer.delete(buffer.get_iter_at_offset(region_start), buffer.get_iter_at_offset(region_end))
    buffer.insert(buffer.get_iter_at_offset(region_start), new_text)
    buffer.end_user_action()
    text_view.grab_focus()


def _toolbar_apply_link(text_view):
    buffer = text_view.get_buffer()
    bounds = buffer.get_selection_bounds()

    buffer.begin_user_action()
    if bounds:
        start, end = bounds
        start_off, end_off = start.get_offset(), end.get_offset()
        text = buffer.get_text(start, end, True)
        buffer.delete(buffer.get_iter_at_offset(start_off), buffer.get_iter_at_offset(end_off))
        buffer.insert(buffer.get_iter_at_offset(start_off), f"[{text}](url)")
        url_start = start_off + len(text) + 3
    else:
        offset = buffer.get_iter_at_mark(buffer.get_insert()).get_offset()
        placeholder = _("texto del enlace")
        buffer.insert(buffer.get_iter_at_offset(offset), f"[{placeholder}](url)")
        url_start = offset + len(placeholder) + 3
    buffer.end_user_action()

    url_end = url_start + len("url")
    buffer.select_range(buffer.get_iter_at_offset(url_start), buffer.get_iter_at_offset(url_end))
    text_view.grab_focus()
