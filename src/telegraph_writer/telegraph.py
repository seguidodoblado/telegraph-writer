"""API de Telegra.ph y subida de imágenes a Catbox."""
import json
import mimetypes
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .i18n import _

API_URL = "https://api.telegra.ph"
IMAGE_UPLOAD_URL = "https://catbox.moe/user/api.php"
PAGE_LIST_LIMIT = 200  # máximo que admite getPageList por petición


def telegraph_api(method, params=None, path=None):
    url = f"{API_URL}/{method}" if not path else f"{API_URL}/{method}/{path}"
    request = urllib.request.Request(url, data=urllib.parse.urlencode(params or {}).encode(), method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", _("Error desconocido de Telegra.ph")))
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


def upload_image(filename):
    """Sube una imagen a Catbox y devuelve su URL pública."""
    file_path = Path(filename)
    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif"}:
        raise RuntimeError(_("Solo se admiten imágenes JPG, JPEG, PNG o GIF."))
    if file_path.stat().st_size > 200 * 1024 * 1024:
        raise RuntimeError(_("La imagen supera el límite de 200 MB."))
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
        body = result or _("respuesta vacía")
        raise RuntimeError(_("Catbox rechazó la imagen: {body}").format(body=body))
    return result
