"""Pruebas de la lógica pura de telegraph_writer.py (sin ventana ni red).

Ejecutar desde la raíz del repositorio: python3 -m unittest discover -s tests
"""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import telegraph_writer as tw


class MarkdownToNodesTests(unittest.TestCase):
    def test_headings(self):
        nodes = tw.markdown_to_nodes("# Uno\n## Dos")
        self.assertEqual([node["tag"] for node in nodes], ["h3", "h4"])

    def test_consecutive_items_share_one_list(self):
        nodes = tw.markdown_to_nodes("- a\n- b\n\n- c")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["tag"], "ul")
        self.assertEqual(len(nodes[0]["children"]), 3)

    def test_ordered_list_and_kind_change(self):
        nodes = tw.markdown_to_nodes("1. a\n2. b\n- c")
        self.assertEqual([node["tag"] for node in nodes], ["ol", "ul"])

    def test_consecutive_quotes_share_one_blockquote(self):
        nodes = tw.markdown_to_nodes("> a\n> b")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(nodes[0]["children"]), 2)

    def test_code_block_is_not_interpreted(self):
        nodes = tw.markdown_to_nodes("```\n# no es titulo\n- ni lista\n```")
        self.assertEqual(nodes, [{"tag": "pre", "children": ["# no es titulo\n- ni lista"]}])

    def test_rule(self):
        self.assertEqual(tw.markdown_to_nodes("---"), [{"tag": "hr"}])

    def test_inline_formats(self):
        nodes = tw.inline_to_nodes("a **b** *c* `d` [e](http://x) ![](http://i)")
        tags = [node["tag"] for node in nodes if isinstance(node, dict)]
        self.assertEqual(tags, ["strong", "em", "code", "a", "img"])


class ContentToTextTests(unittest.TestCase):
    def test_inline_formatting_stays_in_one_line(self):
        nodes = [{"tag": "p", "children": ["Hola ", {"tag": "strong", "children": ["negrita"]}, " y ", {"tag": "a", "attrs": {"href": "https://x.y"}, "children": ["enlace"]}, "."]}]
        self.assertEqual(tw.content_to_text(nodes), "Hola **negrita** y [enlace](https://x.y).")

    def test_headings_keep_their_level(self):
        nodes = [{"tag": "h3", "children": ["A"]}, {"tag": "h4", "children": ["B"]}]
        self.assertEqual(tw.content_to_text(nodes), "# A\n## B")

    def test_blockquote_and_lists(self):
        nodes = [
            {"tag": "blockquote", "children": ["cita"]},
            {"tag": "ul", "children": [{"tag": "li", "children": ["a"]}, {"tag": "li", "children": ["b"]}]},
            {"tag": "ol", "children": [{"tag": "li", "children": ["c"]}]},
        ]
        self.assertEqual(tw.content_to_text(nodes), "> cita\n- a\n- b\n1. c")

    def test_figure_with_image(self):
        nodes = [{"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "/file/a.jpg"}}]}]
        self.assertEqual(tw.content_to_text(nodes), "![](/file/a.jpg)")

    def test_round_trip_preserves_structure(self):
        markdown = "# Titulo\n## Sub\nTexto con **negrita**, *cursiva* y [enlace](http://x).\n> cita\n- a\n- b\n1. uno\n---\n```\ncodigo\n```\n![](http://i/a.png)"
        nodes = tw.markdown_to_nodes(markdown)
        self.assertEqual(tw.content_to_text(nodes), markdown)
        self.assertEqual(tw.markdown_to_nodes(tw.content_to_text(nodes)), nodes)


class ThemeVariantTests(unittest.TestCase):
    def test_mint_dark_keeps_accent(self):
        self.assertEqual(tw.theme_variant("Mint-Y-Orange", True), "Mint-Y-Dark-Orange")
        self.assertEqual(tw.theme_variant("Mint-Y", True), "Mint-Y-Dark")

    def test_mint_light_strips_dark(self):
        self.assertEqual(tw.theme_variant("Mint-Y-Dark-Orange", False), "Mint-Y-Orange")
        self.assertEqual(tw.theme_variant("Mint-Y-Dark", False), "Mint-Y")

    def test_adwaita_and_yaru(self):
        self.assertEqual(tw.theme_variant("Adwaita", True), "Adwaita-dark")
        self.assertEqual(tw.theme_variant("Adwaita-dark", False), "Adwaita")
        self.assertEqual(tw.theme_variant("Yaru-blue", True), "Yaru-blue-dark")
        self.assertEqual(tw.theme_variant("Yaru-blue-dark", False), "Yaru-blue")


class PreviewTests(unittest.TestCase):
    def test_text_is_escaped_and_not_rendered(self):
        page = tw.render_preview("<T>", "**a** <b>\nlinea")
        self.assertIn("&lt;T&gt;", page)
        self.assertIn("**a** &lt;b&gt;<br>\nlinea", page)

    def test_image_url_is_escaped_once(self):
        page = tw.render_preview("t", "![x](http://i/a.png?a=1&b=2)")
        self.assertIn('src="http://i/a.png?a=1&amp;b=2"', page)
        self.assertNotIn("&amp;amp;", page)


class FetchAllPagesTests(unittest.TestCase):
    def test_paginates_until_total(self):
        answers = [
            {"total_count": 3, "pages": [{"path": "a"}, {"path": "b"}]},
            {"total_count": 3, "pages": [{"path": "c"}]},
        ]
        with mock.patch.object(tw, "telegraph_api", side_effect=answers) as api:
            pages, total = tw.fetch_all_pages("token")
        self.assertEqual([page["path"] for page in pages], ["a", "b", "c"])
        self.assertEqual(total, 3)
        self.assertEqual([call.args[1]["offset"] for call in api.call_args_list], [0, 2])

    def test_stops_on_empty_batch(self):
        with mock.patch.object(tw, "telegraph_api", return_value={"total_count": 5, "pages": []}):
            self.assertEqual(tw.fetch_all_pages("token"), ([], 5))


class WriteConfigTests(unittest.TestCase):
    def test_file_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sub" / "config.json"
            target.parent.mkdir()
            target.write_text("{}")
            os.chmod(target, 0o644)
            with mock.patch.object(tw, "CONFIG_FILE", target):
                tw.write_config({"access_token": "secreto"})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertIn("secreto", target.read_text())
            self.assertEqual([path.name for path in target.parent.iterdir()], ["config.json"])


if __name__ == "__main__":
    unittest.main()
