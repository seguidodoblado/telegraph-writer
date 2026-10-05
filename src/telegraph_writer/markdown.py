"""Conversión entre Markdown y los nodos de Telegra.ph (y de vuelta), sin GTK ni red."""
import re

INLINE_RE = re.compile(
    r"!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`"
    r"|\*([^*]+)\*|~~([^~]+)~~|__([^_]+)__"
)
HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+)$")
LIST_ITEM_RE = re.compile(r"^\s*(?:([-*+])|\d+[.)])\s+(.*)$")
RULE_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")


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
        elif match.group(8) is not None:
            result.append({"tag": "s", "children": [match.group(8)]})
        elif match.group(9) is not None:
            result.append({"tag": "u", "children": [match.group(9)]})
        else:
            result.append({"tag": "em", "children": [match.group(7)]})
        position = match.end()
    if position < len(text):
        result.append(text[position:])
    return result or [""]


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
        elif tag == "s":
            parts.append(f"~~{inner}~~")
        elif tag == "u":
            parts.append(f"__{inner}__")
        elif tag == "br":
            parts.append("\n")
        else:
            parts.append(inner)
    return "".join(parts)


def content_to_text(nodes):
    """Reconstruye un borrador Markdown a partir del contenido de un artículo:
    cada nodo de bloque genera un bloque separado por una línea en blanco (las
    listas, citas y códigos mantienen sus líneas juntas) y el formato en línea
    se conserva. Telegra.ph no guarda las líneas en blanco del original."""
    blocks = []
    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                blocks.append(node.strip())
            continue
        tag = node.get("tag", "")
        children = node.get("children", [])
        if tag == "h3":
            blocks.append(f"# {inline_to_text(children)}")
        elif tag == "h4":
            blocks.append(f"## {inline_to_text(children)}")
        elif tag == "blockquote":
            blocks.append("\n".join(f"> {line}" for line in content_to_text(children).split("\n") if line))
        elif tag in ("ul", "ol"):
            items = []
            for number, item in enumerate(children, 1):
                content = inline_to_text(item.get("children", [])) if isinstance(item, dict) else item
                items.append(f"{number}. {content}" if tag == "ol" else f"- {content}")
            blocks.append("\n".join(items))
        elif tag == "pre":
            blocks.append("\n".join(["```", plain_text(children), "```"]))
        elif tag == "hr":
            blocks.append("---")
        elif tag == "figure":
            blocks.append(content_to_text(children))
        else:
            text = inline_to_text([node])
            if text.strip():
                blocks.append(text)
    return "\n\n".join(blocks)
