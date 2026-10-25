# Dual Installation Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every Decky operation prefer the installed AppImage and fall back to the existing native package.

**Architecture:** Add one immutable installation descriptor selected by a filesystem probe. Pass it through process discovery, compatibility, status/update handling, window lookup, and the Steam shortcut rather than duplicating mode checks across modules.

**Tech Stack:** Python 3.11 standard library, unittest, JavaScript node:test, TypeScript 5, Rollup, pnpm.

**Spec:** `docs/superpowers/specs/2026-10-25-dual-installation-support.md`

## Global Constraints

- Prefer AppImage when both modes are installed; preserve native-only behavior.
- Do not remove or modify either ChatGPT installation.
- Fail closed before Voice Mode input unless the selected runtime and window are verified.
- Use fixed paths, argument arrays, and no frontend-controlled shell text.
- Update the live Decky plugin only through the repository's constrained local installer after verification.

## Review Focus

- Both modes installed must never mix the native process/window/updater with the selected AppImage.
- A stopped AppImage must remain launchable even though its runtime ASAR does not yet exist.
- Dynamic AppImage runtime paths must reject helpers and lookalike paths outside the fixed cache root.
- A remembered Steam shortcut must be rewritten when selection changes from native to AppImage.
- Native-only installations must keep their exact launch and update behavior.

---

### Task 1: Installation selection and backend behavior

**Files:**
- Create: `backend/installations.py`
- Modify: `backend/processes.py`
- Modify: `backend/status.py`
- Modify: `backend/controller.py`
- Test: `tests/test_installations.py`
- Test: `tests/test_processes.py`
- Test: `tests/test_status.py`
- Test: `tests/test_controller.py`

**Interfaces:**
- Produces: `Installation` and `select_installation() -> Installation | None`
- Produces: mode-aware `find_app_processes(installation, proc_root)`
- Produces: launch configuration fields in `ChatGPTController.status()`

- [ ] **Step 1: Write failing selection, process, status, and controller tests**

Assert AppImage preference, native fallback, no-install state, metadata version,
AppImage manual-update response, exact dynamic process matching, dynamic ASAR
verification, and selected window class.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m unittest tests.test_installations tests.test_processes tests.test_status tests.test_controller -v`

Expected: failures because installation-aware interfaces do not exist.

- [ ] **Step 3: Implement the minimal installation descriptor and consumers**

Keep native defaults intact. Derive AppImage runtime resources only from an
accepted main process and return a pending compatibility message when stopped.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused command; expected all pass.

### Task 2: Mode-aware Steam shortcut and panel

**Files:**
- Modify: `src/steam.js`
- Modify: `src/index.tsx`
- Modify: `src/steam.d.ts`
- Test: `tests/steam.test.js`

**Interfaces:**
- Consumes: status `launch` object with executable, startDirectory, launchOptions
- Produces: Steam shortcut updated for the selected installation

- [ ] **Step 1: Write failing JavaScript tests**

Assert AppImage launch settings are used, remembered shortcuts are rewritten,
and native launch settings remain supported.

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test tests/steam.test.js`

Expected: AppImage configuration assertions fail.

- [ ] **Step 3: Implement parameterized launch settings and panel wiring**

Require launch settings from backend status before enabling open/voice actions.

- [ ] **Step 4: Run JavaScript tests, typecheck, and build**

Run: `node --test tests/steam.test.js && pnpm run typecheck && pnpm run build`

Expected: all commands exit 0.

### Task 3: Documentation, scripts, and release verification

**Files:**
- Modify: `README.md`
- Modify: `scripts/verify-installed-app.py`
- Modify: `scripts/install-local.sh`
- Modify: `tests/test_release_scripts.py`

**Interfaces:**
- Consumes: installation selection and packaged backend module
- Produces: dual-mode verifier and installable release archive

- [ ] **Step 1: Write failing verifier/release tests**

Assert the verifier selects a running AppImage ASAR or native fallback and the
release/local installer include the new backend module.

- [ ] **Step 2: Run release tests and verify RED**

Run: `python -m unittest tests.test_release_scripts -v`

Expected: failures for missing selection/module behavior.

- [ ] **Step 3: Update verifier, packaging allowlists, and user documentation**

Document AppImage preference, native fallback, per-mode updates, and dynamic
compatibility behavior.

- [ ] **Step 4: Run complete verification**

Run: `pnpm test && pnpm run typecheck && pnpm run build && bash scripts/package-release.sh && git diff --check`

Expected: all commands exit 0 and the release archive contains only its allowlist.
