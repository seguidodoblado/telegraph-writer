"""Pruebas de la lógica sin ventana ni red: Markdown, nodos de Telegra.ph, vista previa, paginación y config.json."""

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from telegraph_writer import config, markdown, preview, telegraph


class MarkdownToNodesTests(unittest.TestCase):
    def test_headings(self):
        nodes = markdown.markdown_to_nodes("# Uno\n## Dos")
        self.assertEqual([node["tag"] for node in nodes], ["h3", "h4"])

    def test_consecutive_items_share_one_list(self):
        nodes = markdown.markdown_to_nodes("- a\n- b\n\n- c")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["tag"], "ul")
        self.assertEqual(len(nodes[0]["children"]), 3)

    def test_ordered_list_and_kind_change(self):
        nodes = markdown.markdown_to_nodes("1. a\n2. b\n- c")
        self.assertEqual([node["tag"] for node in nodes], ["ol", "ul"])

    def test_consecutive_quotes_share_one_blockquote(self):
        nodes = markdown.markdown_to_nodes("> a\n> b")
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(nodes[0]["children"]), 2)

    def test_code_block_is_not_interpreted(self):
        nodes = markdown.markdown_to_nodes("```\n# no es titulo\n- ni lista\n```")
        self.assertEqual(nodes, [{"tag": "pre", "children": ["# no es titulo\n- ni lista"]}])

    def test_rule(self):
        self.assertEqual(markdown.markdown_to_nodes("---"), [{"tag": "hr"}])

    def test_inline_formats(self):
        nodes = markdown.inline_to_nodes("a **b** *c* `d` [e](http://x) ![](http://i)")
        tags = [node["tag"] for node in nodes if isinstance(node, dict)]
        self.assertEqual(tags, ["strong", "em", "code", "a", "img"])

    def test_strikethrough_and_underline(self):
        nodes = markdown.inline_to_nodes("a ~~tachado~~ y __subrayado__")
        formatted = [node for node in nodes if isinstance(node, dict)]
        self.assertEqual([node["tag"] for node in formatted], ["s", "u"])
        self.assertEqual(formatted[0]["children"], ["tachado"])
        self.assertEqual(formatted[1]["children"], ["subrayado"])


class ContentToTextTests(unittest.TestCase):
    def test_inline_formatting_stays_in_one_line(self):
        nodes = [{"tag": "p", "children": ["Hola ", {"tag": "strong", "children": ["negrita"]}, " y ", {"tag": "a", "attrs": {"href": "https://x.y"}, "children": ["enlace"]}, "."]}]
        self.assertEqual(markdown.content_to_text(nodes), "Hola **negrita** y [enlace](https://x.y).")

    def test_headings_keep_their_level(self):
        nodes = [{"tag": "h3", "children": ["A"]}, {"tag": "h4", "children": ["B"]}]
        self.assertEqual(markdown.content_to_text(nodes), "# A\n\n## B")

    def test_blockquote_and_lists(self):
        nodes = [
            {"tag": "blockquote", "children": ["cita"]},
            {"tag": "ul", "children": [{"tag": "li", "children": ["a"]}, {"tag": "li", "children": ["b"]}]},
            {"tag": "ol", "children": [{"tag": "li", "children": ["c"]}]},
        ]
        self.assertEqual(markdown.content_to_text(nodes), "> cita\n\n- a\n- b\n\n1. c")

    def test_figure_with_image(self):
        nodes = [{"tag": "figure", "children": [{"tag": "img", "attrs": {"src": "/file/a.jpg"}}]}]
        self.assertEqual(markdown.content_to_text(nodes), "![](/file/a.jpg)")

    def test_round_trip_preserves_structure(self):
        source = "# Titulo\n\n## Sub\n\nTexto con **negrita**, *cursiva*, ~~tachado~~, __subrayado__ y [enlace](http://x).\n\n> cita\n\n- a\n- b\n\n1. uno\n\n---\n\n```\ncodigo\n```\n\n![](http://i/a.png)"
        nodes = markdown.markdown_to_nodes(source)
        self.assertEqual(markdown.content_to_text(nodes), source)
        self.assertEqual(markdown.markdown_to_nodes(markdown.content_to_text(nodes)), nodes)

    def test_strikethrough_and_underline_round_trip(self):
        nodes = [{"tag": "p", "children": ["Texto ", {"tag": "s", "children": ["tachado"]}, " y ", {"tag": "u", "children": ["subrayado"]}, "."]}]
        self.assertEqual(markdown.content_to_text(nodes), "Texto ~~tachado~~ y __subrayado__.")
        self.assertEqual(markdown.markdown_to_nodes(markdown.content_to_text(nodes)), nodes)


class PreviewPanelTests(unittest.TestCase):
    def test_full_page_wraps_the_body_and_blocks_scripts(self):
        page = preview.render_preview("T", "Hola")
        self.assertIn(preview.preview_body("T", "Hola"), page)
        self.assertIn(f"Content-Security-Policy' content=\"{preview.PREVIEW_CSP}\"", page)
        self.assertIn("default-src 'none'", preview.PREVIEW_CSP)
        self.assertNotIn("script-src", preview.PREVIEW_CSP)
        self.assertNotIn("<script", page)

    def test_update_script_replaces_body_with_escaped_json(self):
        script = preview.preview_update_script('Un "título"', "**a** <b>")
        self.assertTrue(script.startswith("document.title="))
        self.assertIn("document.body.innerHTML=", script)
        self.assertIn("&lt;b&gt;", script)
        self.assertNotIn("<b>", script)
        self.assertEqual(script.count("\n"), 0)

    def test_update_script_is_valid_javascript_string_literals(self):
        script = preview.preview_update_script("ñ\u2028", "línea\nsalto")
        title, body = script.split(";document.body.innerHTML=")
        self.assertEqual(json.loads(title[len("document.title="):]), "ñ\u2028")
        self.assertIn("línea", json.loads(body.rstrip(";")))


class BlankLineTests(unittest.TestCase):
    def test_blocks_are_separated_by_a_blank_line(self):
        nodes = markdown.markdown_to_nodes("Uno\nDos\n- a\n- b")
        self.assertEqual(markdown.content_to_text(nodes), "Uno\n\nDos\n\n- a\n- b")

    def test_extra_blank_lines_are_not_published_and_reload_is_stable(self):
        nodes = markdown.markdown_to_nodes("Uno\n\n\n\nDos")
        self.assertEqual(nodes, markdown.markdown_to_nodes("Uno\nDos"))
        text = markdown.content_to_text(nodes)
        self.assertEqual(text, "Uno\n\nDos")
        self.assertEqual(markdown.markdown_to_nodes(text), nodes)

    def test_code_block_keeps_its_own_blank_lines(self):
        nodes = markdown.markdown_to_nodes("```\na\n\nb\n```\nfin")
        self.assertEqual(markdown.content_to_text(nodes), "```\na\n\nb\n```\n\nfin")
        self.assertEqual(markdown.markdown_to_nodes(markdown.content_to_text(nodes)), nodes)


class PreviewTests(unittest.TestCase):
    def test_markdown_is_rendered(self):
        page = preview.render_preview("t", "# Uno\nTexto **negrita** y *cursiva*\n- a\n- b\n> cita\n---")
        for fragment in ("<h3>Uno</h3>", "<p>Texto <strong>negrita</strong> y <em>cursiva</em></p>", "<ul><li>a</li><li>b</li></ul>", "<blockquote><p>cita</p></blockquote>", "<hr>"):
            self.assertIn(fragment, page)

    def test_text_and_title_are_escaped(self):
        page = preview.render_preview("<T>", "hola <b>x</b>\n```\n<i>\n```")
        self.assertIn("&lt;T&gt;", page)
        self.assertIn("<p>hola &lt;b&gt;x&lt;/b&gt;</p>", page)
        self.assertIn("<pre>&lt;i&gt;</pre>", page)
        self.assertNotIn("<b>", page)

    def test_image_url_is_escaped_once(self):
        page = preview.render_preview("t", "![x](http://i/a.png?a=1&b=2)")
        self.assertIn('<img src="http://i/a.png?a=1&amp;b=2">', page)

    def test_strikethrough_and_underline_are_rendered(self):
        page = preview.render_preview("t", "~~tachado~~ y __subrayado__")
        self.assertIn("<p><s>tachado</s> y <u>subrayado</u></p>", page)
        self.assertNotIn("&amp;amp;", page)

    def test_relative_image_and_unsafe_link(self):
        page = preview.render_preview("t", "![](/file/a.jpg) [x](javascript:alert(1))")
        self.assertIn('src="https://telegra.ph/file/a.jpg"', page)
        self.assertIn('<a href="#">x</a>', page)


class FetchAllPagesTests(unittest.TestCase):
    def test_paginates_until_total(self):
        answers = [
            {"total_count": 3, "pages": [{"path": "a"}, {"path": "b"}]},
            {"total_count": 3, "pages": [{"path": "c"}]},
        ]
        with mock.patch.object(telegraph, "telegraph_api", side_effect=answers) as api:
            pages, total = telegraph.fetch_all_pages("token")
        self.assertEqual([page["path"] for page in pages], ["a", "b", "c"])
        self.assertEqual(total, 3)
        self.assertEqual([call.args[1]["offset"] for call in api.call_args_list], [0, 2])

    def test_stops_on_empty_batch(self):
        with mock.patch.object(telegraph, "telegraph_api", return_value={"total_count": 5, "pages": []}):
            self.assertEqual(telegraph.fetch_all_pages("token"), ([], 5))


class WriteConfigTests(unittest.TestCase):
    def test_file_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sub" / "config.json"
            target.parent.mkdir()
            target.write_text("{}")
            os.chmod(target, 0o644)
            with mock.patch.object(config, "CONFIG_FILE", target):
                config.write_config({"access_token": "secreto"})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertIn("secreto", target.read_text())
            self.assertEqual([path.name for path in target.parent.iterdir()], ["config.json"])


if __name__ == "__main__":
    unittest.main()
