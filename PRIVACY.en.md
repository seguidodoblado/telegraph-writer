<p align="right"><a href="PRIVACY.md">🇪🇸 Español</a></p>

# Privacy policy

Last updated: October 5, 2026.

Telegraph Writer is a desktop application for personal use. It has no server or account of its own and its author
receives no data from the people who use it. It only talks to the services you use through it.

## What data it handles

- **Your articles:** the title, the author and the Markdown text you write.
- **Your Telegra.ph access token**, which you generate yourself and which lets you publish and edit the articles
  of your account.
- **The images** you choose to insert.
- **Your settings:** drafts folder, interface language and theme.

## Where it is stored

On your computer:

- The settings and the access token, in `~/.config/telegraph-writer/config.json`, readable only by your user.
  When the application restarts to change the language or the theme, that file also holds the current draft until
  the application opens again.
- The Markdown drafts, in `~/Telegra.ph/` or in the folder you choose in Settings.

## Who it is shared with

Only with the services the application uses when you ask it to:

- **[Telegra.ph](https://telegra.ph/)** (`api.telegra.ph`): when you publish, update, load or list articles, the
  access token and the content of the article are sent. They are subject to Telegra.ph's terms, and published
  articles are public.
- **[Catbox](https://catbox.moe/)** (`catbox.moe`): when you upload an image, the image file is sent. It is hosted
  on an external service, outside the application's control and subject to Catbox's terms.

The application includes no analytics, telemetry or advertising.

## How to delete your data

Remove `~/.config/telegraph-writer/` (settings and access token) and any drafts folder you no longer want.
Uninstalling the application does not delete that data by itself. Published articles are managed from Telegra.ph,
and images uploaded to Catbox, from Catbox.

## Changes to this policy

If it changes, this document and the date above will be updated; the history is in the repository.

## Contact

Jose Antonio Seguido Doblado · jose.antonio.seguido@gmail.com
