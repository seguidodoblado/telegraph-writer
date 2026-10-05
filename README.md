<p align="right"><a href="README.en.md">🇺🇸 English</a></p>

<p align="center">
  <img src="telegraph-writer.svg" alt="Logotipo de Telegraph Writer" width="128">
</p>

<h1 align="center">Telegraph Writer</h1>

<p align="center">
  <a href="https://github.com/seguidodoblado/telegraph-writer/releases"><img src="https://img.shields.io/github/v/release/seguidodoblado/telegraph-writer" alt="release"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/ci.yml"><img src="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/cd.yml"><img src="https://github.com/seguidodoblado/telegraph-writer/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <a href="https://github.com/seguidodoblado/telegraph-writer/blob/main/COPYING"><img src="https://img.shields.io/github/license/seguidodoblado/telegraph-writer" alt="license"></a>
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
  Escribe artículos en Markdown y publícalos en Telegra.ph, con vista previa fiel al resultado final.
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="Captura de Telegraph Writer">
</p>

Aplicación de escritorio (GTK 4 + PyGObject, interfaz en español e inglés), de uso personal: sin servidor propio ni cuenta
más allá de tu access token de Telegra.ph.

- **Escribe en Markdown** (encabezados, negrita, cursiva, tachado, subrayado, enlaces, imágenes, listas, citas,
  código) con una barra de formato, en lugar del editor web de Telegra.ph.
- **Vista previa fiel**, en un panel junto al editor que se actualiza mientras escribes, tal como quedará
  publicado (necesita `gir1.2-webkit-6.0`; sin él se abre en el navegador).
- **Publica y actualiza** artículos de tu cuenta de Telegra.ph, con protección contra crear un duplicado por
  error.
- **Guarda borradores** localmente en archivos Markdown, además de en Telegra.ph.
- **Sube imágenes** a [Catbox](https://catbox.moe/) e insértalas automáticamente en el artículo, porque
  Telegra.ph tiene deshabilitadas las subidas nuevas.
- **Modo claro y oscuro**, con los iconos del sistema en cada uno.
- **Disponible en español e inglés**, según el idioma del sistema (o `$LANGUAGE`).

## Documentación

Toda la documentación —instalación, guía de uso, especificaciones técnicas, solución de problemas y más— está en
la **[wiki del proyecto](https://github.com/seguidodoblado/telegraph-writer/wiki)** (español e inglés).

## Servicios de terceros

Telegraph Writer publica en tu propia cuenta de [Telegra.ph](https://telegra.ph/) mediante su API pública, con el
access token que tú mismo generas; la aplicación no aloja los artículos.

Las imágenes que insertas se suben a [Catbox](https://catbox.moe/), un servicio externo de alojamiento; quedan
fuera del control de la aplicación y sujetas a las condiciones de uso de Catbox.

## Privacidad

Telegraph Writer no tiene servidor ni cuenta propios y no recoge datos. Solo se comunica con Telegra.ph (para publicar y listar tus artículos) y con Catbox (para alojar las imágenes que subes). Qué se guarda y dónde está en la **[política de privacidad](PRIVACY.md)**.

## Licencia

Este proyecto se distribuye bajo la GNU General Public License, versión 3 o posterior (ver `COPYING`).
