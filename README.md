# ChatGPT Community for Decky

A Steam Deck Quick Access plugin for the installed **ChatGPT Community** Linux
app. It opens ChatGPT, starts a new chat, checks for updates, and toggles
ChatGPT's real live Voice Mode.

This is not an API client. It uses the ChatGPT app already signed in on your
Steam Deck. There is no API key, separate account, transcription service, or
replacement voice implementation.

## Related project

This plugin controls an existing ChatGPT Community installation. Install the
app first with
**[ChatGPT Community for Steam Deck](https://github.com/LBR88/chatgpt-steam-deck)**,
then install this Decky plugin for Gaming Mode Quick Access controls. The two
repositories remain separate so the app installer and optional Decky
integration can be installed or updated independently.

## Current status

Version 0.2.0 supports both ChatGPT Community installation methods. When both
are present, the plugin uses the user-owned AppImage; otherwise it keeps using
the native `codex-desktop` package exactly as before.

The official bundle already contains:

- `composer.startVoiceMode`
- the Linux shortcut `Ctrl+Shift+V`
- the description `Start or stop voice chat`
- the bundled `realtimeVoiceRuntime`

Because that is a complete callable contract, this release applies **zero app
patches**. See [the patch policy](patches/README.md).

## Requirements

- SteamOS on Steam Deck
- Decky Loader
- ChatGPT Community installed as the AppImage or native `codex-desktop` package
- `/usr/bin/xdotool` (present on the tested SteamOS installation)

## Install

1. Switch the Steam Deck to **Desktop Mode**.
2. Download **[Install ChatGPT Community for Decky][desktop-installer]**.
3. Open the downloaded file and choose **Execute** if SteamOS asks.
4. Enter the Deck user's sudo password in the visible terminal when prompted.
5. Return to Gaming Mode, open Quick Access, and select **ChatGPT Community**.

The desktop installer downloads the latest plugin release, verifies its SHA-256
checksum, safely extracts it, preserves the previous plugin as a backup, and
restarts Decky Loader. It does not clone this repository.

For manual installation, download `decky-chatgpt-community.zip` and install it
with Decky Loader's plugin/developer installer.

The plugin does not uninstall or replace your working ChatGPT Community app.

## Use

- **Open ChatGPT** creates or reuses a Steam shortcut and switches to the app.
- **Toggle Voice Mode** remembers the game you are playing, briefly switches to
  ChatGPT, starts or stops its live Voice Mode, and returns to your game.
- **Recent chats** shows five non-archived chats at a time, newest first. Each
  row can open the selected chat or open it and start Voice Mode before returning
  to the running game. Previous, Next, and Refresh keep the Decky panel bounded.
- **Voice controls** explicitly mute or unmute the active ChatGPT Voice session's
  microphone and speaker. They do not mute SteamOS, World of Warcraft, or any
  other application.
- **Check for Updates** asks `codex-update-manager` for native installations;
  AppImage installations direct you to rerun the Steam Deck app installer,
  because their native updater is intentionally disabled.
- **Refresh Status** rechecks the package, process, updater, and Voice Mode
  compatibility contract.

ChatGPT remains running as a background companion after the plugin returns to
your game, so the voice session can continue while you play. Steam does not
close the original game. The Quick Access menu closes before focus-sensitive
commands. Voice Mode is disabled if the installed app no longer contains the
verified command contract. The plugin never falls back to screen coordinates.

## Local development

Use pnpm 9, matching Decky's official plugin template:

```bash
corepack pnpm@9.15.9 install --frozen-lockfile
corepack pnpm@9.15.9 run build
python -m unittest discover -s tests -v
python scripts/verify-installed-app.py
bash scripts/package-release.sh
bash scripts/install-local.sh
```

The last command only accepts the `deck` user and only writes to
`/home/deck/homebrew/plugins/decky-chatgpt-community`.

## How it works

The Decky frontend creates one native non-Steam shortcut for the selected
installation and launches it with `SteamClient.Apps.RunGame`. It prefers
`~/.local/share/chatgpt-community-appimage/launch-appimage.sh` when the
AppImage is installed and otherwise uses `/usr/bin/codex-desktop`. This
keeps ChatGPT in Steam's process tree, allowing Gamescope to focus its window.
The shortcut clears Steam's `LD_PRELOAD` only for the ChatGPT launch because
Steam's overlay library crashes Electron child processes on the tested SteamOS
version. Gamescope still owns and presents the app normally.
The shortcut also enables a loopback-only Chromium control endpoint. The plugin
uses it only to activate ChatGPT's own accessible Voice buttons by their exact
labels, making mute and unmute state-setting operations idempotent without
screen coordinates. The endpoint is not exposed on the network.
For an in-game Voice Mode toggle, the plugin records Steam's currently running
game, focuses the already-running ChatGPT shortcut without relaunching it,
invokes the verified app shortcut, then restores the recorded game even when
the operation fails.

The unprivileged Python backend finds either the exact native
`/opt/codex-desktop/ChatGPT` process or the AppImage main process inside its
fixed `~/.cache/chatgpt-runtime/run.*/appimage_extracted_*/` runtime. It reads
only display-related process environment, locates the largest visible window
whose class exactly matches the selected installation (`codex-desktop` or
`chatgpt-community-appimage`), focuses it, and sends the app's own shortcut
through `xdotool`. It never launches a hidden ChatGPT process itself.

SteamOS can use multiple Xwayland displays in Gaming Mode, so the plugin uses
the display belonging to ChatGPT rather than assuming `DISPLAY=:0`. When
SteamOS masks a sibling process's environment, the backend checks only numeric
Xwayland sockets available to the session and still requires the exact
`codex-desktop` window class. If the app is not running, it launches it with
SteamOS's Gamescope environment and waits for the verified window.

## Privacy and security

- No OpenAI API calls or API keys
- Recent-chat listing uses the local Codex app-server and requests thread
  metadata only; it does not fetch message bodies or persist thread identifiers.
- No conversation, audio, or account-data access
- No shell commands supplied by the frontend
- No root Decky backend
- No screen-coordinate automation
- No copied OpenAI application payload in this repository or release zip
- Release ZIP verification before the desktop installer changes Decky files

## Troubleshooting

If Voice Mode says **Unavailable**, run:

```bash
python scripts/verify-installed-app.py
```

With a running AppImage, the verifier derives `app.asar` from that exact
runtime process. With the native package it uses the fixed installed bundle.
You can still pass an explicit ASAR path for diagnostics. If the verifier
reports missing markers, update this plugin and ChatGPT Community. Do not force
the shortcut: the compatibility gate is intentionally fail closed.

If the first Voice Mode toggle takes several seconds, let ChatGPT finish
starting. The plugin waits up to 30 seconds for its Steam-owned window and then
returns to the game that was already running.

## License

MIT. ChatGPT, the official Linux application, and OpenAI services remain the
property of their respective owners. This is an independent community plugin.

[desktop-installer]: https://github.com/LBR88/decky-chatgpt-community/releases/latest/download/Install-ChatGPT-Community-Decky.desktop
