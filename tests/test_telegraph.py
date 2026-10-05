import io
import json
from pathlib import Path
from unittest import mock

import pytest

from telegraph_writer import telegraph


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def answer(payload) -> Response:
    return Response(json.dumps(payload).encode() if not isinstance(payload, bytes) else payload)


def test_api_returns_the_result_and_posts_form_encoded_data():
    seen = {}

    def fake(request, timeout=0):
        seen["url"], seen["body"], seen["method"] = request.full_url, request.data, request.get_method()
        return answer({"ok": True, "result": {"short_name": "Ana"}})

    with mock.patch("urllib.request.urlopen", fake):
        result = telegraph.telegraph_api("getAccountInfo", {"access_token": "t", "fields": '["short_name"]'})
    assert result == {"short_name": "Ana"}
    assert seen["url"] == "https://api.telegra.ph/getAccountInfo" and seen["method"] == "POST"
    assert b"access_token=t" in seen["body"]


def test_api_with_a_path_appends_it_to_the_method():
    seen = {}

    def fake(request, timeout=0):
        seen["url"] = request.full_url
        return answer({"ok": True, "result": {}})

    with mock.patch("urllib.request.urlopen", fake):
        telegraph.telegraph_api("getPage", {}, "mi-articulo-10-05")
    assert seen["url"] == "https://api.telegra.ph/getPage/mi-articulo-10-05"


def test_api_error_becomes_a_runtime_error_with_the_message_of_telegraph():
    with mock.patch("urllib.request.urlopen", lambda request, timeout=0: answer({"ok": False, "error": "ACCESS_TOKEN_INVALID"})), pytest.raises(RuntimeError, match="ACCESS_TOKEN_INVALID"):
        telegraph.telegraph_api("getAccountInfo", {})


def test_api_error_without_message_has_a_default_one():
    with mock.patch("urllib.request.urlopen", lambda request, timeout=0: answer({"ok": False})), pytest.raises(RuntimeError, match="Error desconocido"):
        telegraph.telegraph_api("getAccountInfo", {})


def test_upload_rejects_other_extensions(tmp_path: Path):
    path = tmp_path / "foto.webp"
    path.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="JPG, JPEG, PNG o GIF"):
        telegraph.upload_image(str(path))


def test_upload_rejects_images_over_200_mb(tmp_path: Path):
    path = tmp_path / "grande.png"
    path.write_bytes(b"x")
    fake_stat = mock.Mock(st_size=201 * 1024 * 1024)
    with mock.patch.object(Path, "stat", return_value=fake_stat), pytest.raises(RuntimeError, match="200 MB"):
        telegraph.upload_image(str(path))


def test_upload_sends_a_multipart_form_and_returns_the_url(tmp_path: Path):
    path = tmp_path / "foto.PNG"
    path.write_bytes(b"\x89PNG-datos")
    seen = {}

    def fake(request, timeout=0):
        seen["url"], seen["body"], seen["type"] = request.full_url, request.data, request.get_header("Content-type")
        return answer(b"https://files.catbox.moe/abc.png\n")

    with mock.patch("urllib.request.urlopen", fake):
        url = telegraph.upload_image(str(path))
    assert url == "https://files.catbox.moe/abc.png"
    assert seen["url"] == telegraph.IMAGE_UPLOAD_URL and seen["type"].startswith("multipart/form-data; boundary=")
    assert b'name="reqtype"' in seen["body"] and b"fileupload" in seen["body"] and b"\x89PNG-datos" in seen["body"]


def test_upload_rejects_a_response_that_is_not_a_url(tmp_path: Path):
    path = tmp_path / "foto.jpg"
    path.write_bytes(b"x")
    with mock.patch("urllib.request.urlopen", lambda request, timeout=0: answer(b"Error: algo")), pytest.raises(RuntimeError, match="Catbox rechazó la imagen: Error: algo"):
        telegraph.upload_image(str(path))
