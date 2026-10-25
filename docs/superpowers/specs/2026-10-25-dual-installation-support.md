# Dual Installation Support Design

## Goal

Support ChatGPT Community installed either as the user-owned AppImage or as the
existing native `codex-desktop` package. Prefer the AppImage when both are
installed and preserve current behavior when only the native package exists.

## Installation contract

The AppImage installation is valid when both of these files are executable:

- `/home/deck/.local/share/chatgpt-community-appimage/ChatGPT-Community.AppImage`
- `/home/deck/.local/share/chatgpt-community-appimage/launch-appimage.sh`

It launches through `launch-appimage.sh`, starts in the AppImage directory,
uses window class `chatgpt-community-appimage`, and reads its version from
`build-info.json` at `upstreamLinuxPackage.version`. Its running executable is
under `/home/deck/.cache/chatgpt-runtime/run.*/appimage_extracted_*/opt/codex-desktop/ChatGPT`;
the Voice Mode bundle is the sibling `resources/app.asar`.

The native installation keeps the existing launcher, start directory, exact
process path, window class, package/version lookup, updater commands, and ASAR
path. If both installations exist, every operation targets the AppImage.

## Behavior

Status reports the selected installation mode and Steam launch settings. Open
ChatGPT creates or updates the existing non-Steam shortcut with those settings.
Process and window discovery only accept the selected installation. Voice Mode
checks the selected installation's ASAR and remains fail closed. For a running
AppImage it derives the ASAR from the discovered main executable; while the
AppImage is stopped, compatibility is reported as pending until Steam starts it.

The native updater remains unchanged. AppImage update checks do not invoke the
disabled native updater and instead direct the user to rerun the Steam Deck app
installer. The AppImage build metadata supplies the installed version.

## Constraints

- Do not remove or modify either ChatGPT installation.
- Do not scan arbitrary cache payloads; derive runtime paths from exact process
  shape beneath the fixed AppImage runtime root.
- Never send shortcuts to a window class that does not match the selected mode.
- Keep fixed subprocess argument arrays and no frontend-controlled shell text.
- Keep the local Decky installation flow constrained to its documented target.

