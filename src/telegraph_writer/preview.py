"""HTML de la vista previa: los mismos nodos que se publican, con el HTML escapado y sin scripts."""
import html
import json
import urllib.parse

from .markdown import markdown_to_nodes

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


# La vista previa solo contiene HTML propio: se bloquean los scripts de la
# página y solo se permiten imágenes http(s) y los estilos en línea.
PREVIEW_CSP = "default-src 'none'; img-src http: https:; style-src 'unsafe-inline'"


def preview_body(title, text):
    """Cuerpo de la vista previa: el Markdown se convierte en los mismos nodos
    que se publican, de modo que se ve igual que en Telegra.ph."""
    return f"<h1>{html.escape(title)}</h1>{nodes_to_html(markdown_to_nodes(text))}"


def render_preview(title, text):
    """Página HTML completa de la vista previa."""
    return (
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<meta http-equiv='Content-Security-Policy' content=\"{PREVIEW_CSP}\">"
        f"<title>{html.escape(title)}</title><style>{PREVIEW_STYLE}</style></head>"
        f"<body>{preview_body(title, text)}</body></html>"
    )


def preview_update_script(title, text):
    """JavaScript que sustituye el cuerpo de una vista previa ya cargada; así
    el panel se actualiza sin perder la posición de desplazamiento."""
    return f"document.title={json.dumps(title)};document.body.innerHTML={json.dumps(preview_body(title, text))};"
