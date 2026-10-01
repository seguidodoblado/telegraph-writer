<p align="right"><a href="README.md">🇪🇸 Español</a></p>

<p align="center">
  <img src="telegraph-writer.svg" alt="Telegraph Writer logo" width="128">
</p>

<h1 align="center">Telegraph Writer</h1>

<p align="center">
  Write articles in Markdown and publish them to Telegra.ph, with a preview faithful to the final result.
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="Telegraph Writer screenshot">
</p>

Desktop application (GTK 4 + PyGObject, Spanish-language interface), for personal use: no server of its own and
no account beyond your own Telegra.ph access token.

- **Write in Markdown** (headings, bold, italics, strikethrough, underline, links, images, lists, quotes, code)
  with a formatting toolbar, instead of Telegra.ph's own web editor.
- **Faithful preview**, in a panel next to the editor that updates while you type, exactly as it will be
  published (needs `gir1.2-webkit-6.0`; without it, it opens in the browser instead).
- **Publish and update** articles on your Telegra.ph account, with protection against accidentally creating a
  duplicate.
- **Save drafts** locally as Markdown files, in addition to Telegra.ph.
- **Upload images** to [Catbox](https://catbox.moe/) and insert them into the article automatically, since
  Telegra.ph has new uploads disabled.
- **Light and dark mode**, with the matching system icons in each.

## Documentation

Full documentation — installation, usage guide, technical specifications, troubleshooting and more — is in the
**[project wiki](https://github.com/seguidodoblado/telegraph-writer/wiki)** (Spanish and English).

## Third-party services

Telegraph Writer publishes to your own [Telegra.ph](https://telegra.ph/) account through its public API, using
the access token you generate yourself; the app doesn't host the articles.

Images you insert are uploaded to [Catbox](https://catbox.moe/), an external hosting service; they're outside the
app's control and subject to Catbox's own terms of use.

## License

This project is distributed under the GNU General Public License, version 3 (see `LICENSE`).
