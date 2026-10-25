# Recent Chat Picker and Voice Controls

## Intent

Make the Decky plugin a dependable in-game control surface for ChatGPT Community. A player should be able to choose the intended recent chat before opening ChatGPT or starting Voice Mode, then control ChatGPT's microphone and playback without muting World of Warcraft or the Steam Deck itself.

## Goals

- Show non-archived chats ordered by most recent activity, five at a time.
- Provide **Open** and **Open + Voice** on every chat row.
- Provide Previous/Next paging and an explicit refresh action.
- Preserve the running game: briefly focus ChatGPT only when an operation requires it, then return to the game.
- Keep the existing overall Voice Mode start/stop control.
- Add explicit **Mute microphone**, **Unmute microphone**, **Mute speaker**, and **Unmute speaker** controls for the active ChatGPT voice session.
- Make every action fail closed with a short, useful Decky notification.

## Non-goals and anti-goals

- No separate pinned-chat section, full-history search, chat creation, message preview, editing, or deletion in the first version.
- Do not mute the system microphone, system output, World of Warcraft, or any other application.
- Do not scrape the ChatGPT screen by coordinates, read private message bodies, or guess which chat is active.
- Do not start Voice Mode in a chat unless that selected chat has been opened successfully.
- Do not render an unbounded list in Decky's Quick Access panel.

## Constraints

- The Decky backend may run with a different environment from the signed-in desktop user. Session requests and deep links must execute in the `deck` user's ChatGPT/Codex context.
- ChatGPT remains a Steam-launched application; Decky is the controller, not a replacement chat client.
- The current plugin exposes only an overall Voice Mode toggle. The four new mute actions must target verified ChatGPT voice-session commands and report unavailable if the installed app version does not expose a compatible contract.
- Thread identifiers and pagination cursors are internal data and must not be shown in the UI or logs intended for the user.

## Approaches considered

1. **Supported Codex session interface plus ChatGPT deep links — selected.** Use the local Codex app-server's `thread/list` method with a five-item limit, descending recency order, and opaque cursor paging. Open the chosen item through the registered `codex://threads/<thread-id>` handler. This gives stable titles, timestamps, and paging without reading message content.
2. **Automate the visible chat search UI.** This would depend on focus, timing, labels, and layout, making it fragile in Gaming Mode.
3. **Read local history files directly.** This would couple the plugin to private storage formats and require unnecessary access to conversation contents.

The supported session interface was chosen because it is bounded, metadata-only, and versioned. The other approaches work against the reliability and privacy goals.

## Decky experience

The plugin adds a **Recent chats** section beneath status:

- The initial view loads the five most recently active, non-archived chats.
- Each row shows a truncated title and compact relative timestamp.
- **Open** launches or reuses ChatGPT, opens that chat, and leaves ChatGPT visible.
- **Open + Voice** launches or reuses ChatGPT, opens that chat, starts Voice Mode only after navigation succeeds, and returns focus to the game that was running.
- Previous and Next operate on cursor-backed pages. Previous is disabled on the first page; Next is disabled when no next cursor exists.
- Refresh returns to the first page and reloads recent chats.
- Loading, empty, unavailable, and retry states replace the list rather than stacking extra controls.
- Only one action may run at a time.

The existing overall Voice Mode control remains available. When a voice session is active, a **Voice controls** section exposes four explicit commands: Mute microphone, Unmute microphone, Mute speaker, and Unmute speaker. These are idempotent state-setting actions, not ambiguous toggles. Controls that already match the known state may be disabled. If state cannot be verified, the action remains explicit and the result is refreshed after it runs.

## Backend flow

### Listing chats

The backend owns a small app-server client. It initializes one bounded local process in the `deck` user's environment and requests `thread/list` with:

- `limit: 5`
- `archived: false`
- `sortKey: recency_at`
- `sortDirection: desc`
- the server-provided cursor for subsequent pages

The backend returns only the title, last-activity timestamp, opaque selection token, and whether another page exists. The frontend keeps a small stack of prior page cursors for Previous navigation. A process timeout or malformed response produces an unavailable state and retry action.

### Opening and starting Voice Mode

The selected item is resolved by the backend, ChatGPT is launched or reused through the existing Steam shortcut flow, and its registered thread deep link is opened. **Open + Voice** then waits for the ChatGPT window and a bounded navigation-ready condition before invoking the verified Voice Mode command. If navigation is not confirmed, Voice Mode is not started. After successful activation, focus returns to the previously running game.

### Session-only mute controls

The compatibility layer is extended with four distinct ChatGPT voice contracts: microphone mute, microphone unmute, speaker mute, and speaker unmute. The controller focuses the verified ChatGPT window, invokes the requested app-level command, verifies or refreshes session state, and restores the game. It never calls system mixer, PipeWire/PulseAudio global mute, Steam input mute, or per-game audio controls.

If the installed ChatGPT build lacks a reliable app-level command for any control, that control is shown as unavailable rather than approximated with clicks or system-wide muting. Compatibility is checked again after app updates.

## Privacy and failure behavior

- Fetch metadata only; do not request turns or message bodies.
- Keep at most the visible page, the cursor stack, and the current selection in plugin memory.
- Do not persist chat titles, thread identifiers, or cursors.
- Never include raw identifiers in toast messages or user-facing logs.
- Time out stalled app-server, launch, navigation, and voice operations.
- Do not send a voice or mute command unless the correct app window and compatible command contract are verified.

## Verification

Automated coverage will include app-server request/response parsing, five-item boundaries, cursor paging, refresh, empty/error states, identifier redaction, selected-chat routing, navigation failure, and all four idempotent mute commands. Existing Steam focus-restoration tests will be extended to every new action.

Manual Gaming Mode verification will confirm that:

1. Five recent chats appear in correct order and page correctly.
2. Open selects the intended chat.
3. Open + Voice starts Voice Mode in that chat and returns to World of Warcraft.
4. Muting and unmuting the ChatGPT microphone affects only ChatGPT input.
5. Muting and unmuting the ChatGPT speaker affects only ChatGPT playback while World of Warcraft audio continues.
6. Closing, updating, or failing to navigate ChatGPT produces a clear failure without sending input to another window.

## Builder decisions

The builder may choose the smallest maintainable JSON-RPC client and Decky component layout already compatible with this repository. Exact relative-time wording, button icons, and bounded readiness timing are implementation choices, provided the five-item paging, explicit actions, app-only audio scope, and fail-closed behavior remain unchanged.
