<p align="right"><a href="README.md">🇪🇸 Español</a></p>

<p align="center">
  <img src="telegraph-writer.svg" alt="Telegraph Writer logo" width="128">
</p>

<h1 align="center">Telegraph Writer</h1>

<p align="center">
  <a href="https://github.com/seguidodoblado/telegraph-writer/releases"><img src="https://img.shields.io/github/v/release/seguidodoblado/telegraph-writer" alt="release"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/ci.yml"><img src="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/cd.yml"><img src="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/blob/main/LICENSE"><img src="https://img.shields.io/github/license/seguidodoblado/telegraph-writer" alt="license"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/commits/main/"><img src="https://img.shields.io/github/last-commit/seguidodoblado/telegraph-writer" alt="last commit"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/commits/main/"><img src="https://img.shields.io/github/commit-activity/t/seguidodoblado/telegraph-writer" alt="total commits"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/releases"><img src="https://img.shields.io/github/downloads/seguidodoblado/telegraph-writer/total" alt="downloads"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/stargazers"><img src="https://img.shields.io/github/stars/seguidodoblado/telegraph-writer?style=flat" alt="stars"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/issues"><img src="https://img.shields.io/github/issues/seguidodoblado/telegraph-writer" alt="issues"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer"><img src="https://img.shields.io/github/languages/top/seguidodoblado/telegraph-writer" alt="language"></a>
  <a href="https://codetime.dev"><img alt="CodeTime Badge" src="https://shields.jannchie.com/endpoint?style=flat&color=0284c7&url=https%3A%2F%2Fcodetime.dev%2Fv3%2Fusers%2Fshield%3Fuid%3D36830"></a>
  <a href="https://wakatime.com/badge/github/seguidodoblado/telegraph-writer"><img src="https://wakatime.com/badge/github/seguidodoblado/telegraph-writer.svg" alt="wakatime"></a>
</p>

<p align="center">
  Write articles in Markdown and publish them to Telegra.ph, with a preview faithful to the final result.
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="Telegraph Writer screenshot">
</p>

Desktop application (GTK 4 + PyGObject, interface in Spanish and English), for personal use: no server of its own and
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
- **Available in Spanish and English**, following the system's language (or `$LANGUAGE`).

## Documentation

Full documentation — installation, usage guide, technical specifications, troubleshooting and more — is in the
**[project wiki](https://github.com/seguidodoblado/telegraph-writer/wiki)** (Spanish and English).

## Third-party services

Telegraph Writer publishes to your own [Telegra.ph](https://telegra.ph/) account through its public API, using
the access token you generate yourself; the app doesn't host the articles.

Images you insert are uploaded to [Catbox](https://catbox.moe/), an external hosting service; they're outside the
app's control and subject to Catbox's own terms of use.

## Privacy

Telegraph Writer has no server or account of its own and collects no data. It only talks to Telegra.ph (to publish and list your articles) and to Catbox (to host the images you upload). What is stored and where is in the **[privacy policy](PRIVACY.en.md)**.

## License

This project is distributed under the GNU General Public License, version 3 or later (see `LICENSE`).
