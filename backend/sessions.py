import json
import os
import secrets
import select
import subprocess
import time
from dataclasses import dataclass
from typing import Callable
from pathlib import Path


class SessionProtocolError(RuntimeError):
    pass


def _codex_binary(
    runtime_root: Path = Path("/home/deck/.cache/chatgpt-runtime"),
    native: Path = Path("/opt/codex-desktop/resources/codex"),
    standalone: Path = Path("/home/deck/.local/bin/codex"),
) -> Path:
    appimage_candidates = sorted(
        runtime_root.glob(
            "run.*/appimage_extracted_*/opt/codex-desktop/resources/codex"
        ),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    for candidate in (*appimage_candidates, native, standalone):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise SessionProtocolError("Start ChatGPT Community once, then refresh recent chats")


@dataclass(frozen=True)
class RecentSession:
    selection_token: str
    thread_id: str
    title: str
    updated_at: int

    def to_dict(self) -> dict[str, object]:
        return {
            "selectionToken": self.selection_token,
            "title": self.title,
            "updatedAt": self.updated_at,
        }


@dataclass(frozen=True)
class SessionPage:
    items: tuple[RecentSession, ...]
    next_cursor: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "nextCursor": self.next_cursor,
        }


def _stdio_request(method: str, params: dict[str, object]) -> dict[str, object]:
    codex_binary = _codex_binary()
    try:
        process = subprocess.Popen(
            [str(codex_binary), "app-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
    except OSError as error:
        raise SessionProtocolError("Could not start the local session service") from error
    if process.stdin is None or process.stdout is None:
        raise SessionProtocolError("Could not start the local session service")
    messages = (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "decky-chatgpt-community", "version": "0.2.0"}
        }},
        {"jsonrpc": "2.0", "method": "initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": method, "params": params},
    )
    try:
        for message in messages:
            process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            ready, _, _ = select.select([process.stdout], [], [], 0.25)
            if not ready:
                if process.poll() is not None:
                    break
                continue
            line = process.stdout.readline()
            if not line:
                break
            response = json.loads(line)
            if response.get("id") != 2:
                continue
            if "error" in response:
                raise SessionProtocolError("The local session service rejected the request")
            result = response.get("result")
            if not isinstance(result, dict):
                raise SessionProtocolError("The local session service returned invalid data")
            return result
        raise SessionProtocolError("The local session service did not respond")
    except (json.JSONDecodeError, OSError) as error:
        raise SessionProtocolError("The local session service returned invalid data") from error
    finally:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()


class CodexSessionClient:
    def __init__(
        self,
        request: Callable[[str, dict[str, object]], dict[str, object]] = _stdio_request,
    ) -> None:
        self._request = request
        self._selections: dict[str, RecentSession] = {}

    def list_recent(self, cursor: str | None = None, limit: int = 5) -> SessionPage:
        params: dict[str, object] = {
            "limit": limit,
            "archived": False,
            "sortKey": "recency_at",
            "sortDirection": "desc",
        }
        if cursor is not None:
            params["cursor"] = cursor
        response = self._request("thread/list", params)
        data = response.get("data")
        if not isinstance(data, list):
            raise SessionProtocolError("The recent chat list is unavailable")
        selections: dict[str, RecentSession] = {}
        items: list[RecentSession] = []
        for raw in data:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                raise SessionProtocolError("The recent chat list is unavailable")
            title = raw.get("name") or raw.get("title") or "Untitled chat"
            updated_at = raw.get("recencyAt") or raw.get("updatedAt") or 0
            token = secrets.token_urlsafe(18)
            item = RecentSession(token, raw["id"], str(title), int(updated_at))
            selections[token] = item
            items.append(item)
        self._selections = selections
        next_cursor = response.get("nextCursor")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise SessionProtocolError("The recent chat list is unavailable")
        return SessionPage(tuple(items), next_cursor)

    def resolve(self, selection_token: str) -> RecentSession | None:
        return self._selections.get(selection_token)
