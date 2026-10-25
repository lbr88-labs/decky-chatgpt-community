# Recent Session Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a five-at-a-time recent-chat picker and ChatGPT-session-only microphone and speaker controls to the Decky plugin.

**Architecture:** A focused Python JSON-RPC client reads metadata-only pages from the local Codex app-server. The Decky bridge exposes list, open, voice, and explicit audio-state operations; the React panel renders bounded pages and routes focus-sensitive actions through the existing Steam helper. Voice controls use only verified ChatGPT application commands and fail closed when unsupported.

**Tech Stack:** Python 3, JSON-RPC over stdio, Decky Python bridge, React/TypeScript, Node test runner, unittest.

**Spec:** `docs/superpowers/specs/2026-10-25-recent-session-picker-design.md`

## Global Constraints

- Show exactly five non-archived chats per page, ordered by descending `recency_at`.
- Expose Open and Open + Voice for each row, with cursor-backed Previous, Next, and Refresh.
- Never fetch or persist message bodies, and never expose raw thread IDs or cursors in user-facing output.
- Microphone and speaker controls affect only ChatGPT's active voice session, never system or game audio.
- All focus-sensitive commands verify the ChatGPT window and fail closed.

## Review Focus

- App-server exits, hangs, or emits malformed JSON: return a bounded unavailable result and permit retry.
- A stale or forged selection token: reject it without opening a deep link or starting Voice Mode.
- Fewer than five results or a missing next cursor: render correctly and disable Next.
- Deep-link navigation does not become ready: do not issue the Voice Mode command.
- An installed ChatGPT build lacks a mute command contract: disable that control without touching system audio.

---

### Task 1: Metadata-only recent-chat client

**Files:**
- Create: `backend/sessions.py`
- Create: `tests/test_sessions.py`

**Interfaces:**
- Produces: `SessionPage`, `RecentSession`, and `CodexSessionClient.list_recent(cursor: str | None, limit: int = 5) -> SessionPage`.
- Produces: `CodexSessionClient.resolve(selection_token: str) -> RecentSession | None` using only tokens from the current in-memory page cache.

- [ ] Write failing tests for five-item `thread/list` parameters, response mapping, cursor paging, malformed output, timeout, and stale-token rejection.
- [ ] Run `python -m unittest tests.test_sessions -v`; expect failures because `backend.sessions` does not exist.
- [ ] Implement the smallest line-delimited JSON-RPC client and in-memory selection-token cache.
- [ ] Run `python -m unittest tests.test_sessions -v`; expect all tests to pass.
- [ ] Commit `test: add bounded recent session client`.

### Task 2: Decky bridge and selected-chat navigation

**Files:**
- Modify: `backend/controller.py`
- Modify: `main.py`
- Modify: `tests/test_controller.py`
- Modify: `tests/test_plugin_bridge.py`

**Interfaces:**
- Consumes: `CodexSessionClient.list_recent` and `.resolve` from Task 1.
- Produces: `ChatGPTController.list_recent_chats(cursor=None)`, `open_recent_chat(selection_token)`, and `open_recent_chat_with_voice(selection_token)` plus matching async Decky methods.

- [ ] Write failing tests for metadata serialization, token resolution, registered `codex://threads/` opening, navigation timeout, and no voice command on navigation failure.
- [ ] Run the focused Python tests; expect missing-method failures.
- [ ] Implement deep-link opening in the verified `deck` graphical environment and compose it with existing window and Voice Mode operations.
- [ ] Run the focused tests; expect all to pass.
- [ ] Commit `feat: open selected recent chats`.

### Task 3: Five-item Decky picker

**Files:**
- Create: `src/recent-chats.ts`
- Modify: `src/index.tsx`
- Create: `tests/recent-chats.test.js`

**Interfaces:**
- Consumes: Decky calls from Task 2.
- Produces: cursor-stack reducer/state helpers and a Recent chats panel with row actions and bounded state rendering.

- [ ] Write failing Node tests for initial five-item page, Previous/Next cursor behavior, refresh-to-first-page, missing-next behavior, and error state.
- [ ] Run `node --test tests/recent-chats.test.js`; expect module-not-found failure.
- [ ] Implement the pure paging helper and the panel UI with one-operation-at-a-time behavior.
- [ ] Run Node tests and `pnpm typecheck`; expect both to pass.
- [ ] Commit `feat: add recent chat picker`.

### Task 4: Explicit ChatGPT voice-session controls

**Files:**
- Modify: `backend/compatibility.py`
- Modify: `backend/controller.py`
- Modify: `main.py`
- Modify: `src/index.tsx`
- Modify: `tests/test_compatibility.py`
- Modify: `tests/test_controller.py`
- Modify: `tests/test_plugin_bridge.py`

**Interfaces:**
- Produces: compatibility flags and idempotent `mute_microphone`, `unmute_microphone`, `mute_speaker`, and `unmute_speaker` operations.
- Consumes: existing verified-window and focus-restoration flow.

- [ ] Write failing tests for all four semantic actions, their compatibility gates, idempotent results, and proof that no system mixer command is invoked.
- [ ] Run focused Python tests; expect missing-method or missing-contract failures.
- [ ] Implement verified application-level command adapters and bridge methods; unsupported app builds return unavailable without approximating clicks or system mute.
- [ ] Add the four explicit Decky buttons with per-control availability and busy-state handling.
- [ ] Run focused tests and `pnpm typecheck`; expect all to pass.
- [ ] Commit `feat: add session-only voice controls`.

### Task 5: Integration, documentation, and package verification

**Files:**
- Modify: `README.md`
- Modify: `tests/steam.test.js`
- Modify: `package.json` and `plugin.json` only if a release version is prepared.

**Interfaces:**
- Consumes: all preceding tasks.
- Produces: documented Gaming Mode behavior and a verified release build.

- [ ] Add integration tests proving game focus restoration for Open + Voice and each supported voice control.
- [ ] Run the full `pnpm test`, `pnpm typecheck`, and `pnpm build`; expect zero failures.
- [ ] Document recent-chat paging, Open/Open + Voice, and ChatGPT-only mute semantics.
- [ ] Perform a manual Gaming Mode smoke test without publishing or pushing.
- [ ] Commit `docs: describe recent chats and voice controls`.
