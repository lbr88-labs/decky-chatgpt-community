import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.sessions import CodexSessionClient, SessionProtocolError, _codex_binary, _stdio_request


class SessionClientTests(unittest.TestCase):
    def test_codex_binary_supports_appimage_native_and_standalone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            appimage = runtime / "run.A" / "appimage_extracted_build" / "opt/codex-desktop/resources/codex"
            native = root / "native-codex"
            standalone = root / "standalone-codex"
            for candidate in (appimage, native, standalone):
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text("binary")
                candidate.chmod(0o755)

            self.assertEqual(_codex_binary(runtime, native, standalone), appimage)
            appimage.unlink()
            self.assertEqual(_codex_binary(runtime, native, standalone), native)
            native.unlink()
            self.assertEqual(_codex_binary(runtime, native, standalone), standalone)

    def test_stdio_request_uses_resolved_absolute_path(self):
        with patch("backend.sessions._codex_binary", return_value=Path("/chosen/codex")), patch(
            "backend.sessions.subprocess.Popen", side_effect=FileNotFoundError
        ) as popen:
            with self.assertRaises(SessionProtocolError):
                _stdio_request("thread/list", {})

        self.assertEqual(popen.call_args.args[0][0], "/chosen/codex")

    def test_lists_five_recent_non_archived_threads_without_turns(self):
        calls = []

        def request(method, params):
            calls.append((method, params))
            return {
                "data": [
                    {"id": "thread-secret", "name": "Deck setup", "updatedAt": 50},
                ],
                "nextCursor": "cursor-secret",
            }

        client = CodexSessionClient(request=request)
        page = client.list_recent()

        self.assertEqual(calls, [("thread/list", {
            "limit": 5,
            "archived": False,
            "sortKey": "recency_at",
            "sortDirection": "desc",
        })])
        self.assertEqual(page.items[0].title, "Deck setup")
        self.assertEqual(page.items[0].updated_at, 50)
        self.assertNotEqual(page.items[0].selection_token, "thread-secret")
        self.assertEqual(page.next_cursor, "cursor-secret")

    def test_passes_opaque_cursor_and_maps_title_fallback(self):
        calls = []

        def request(method, params):
            calls.append(params)
            return {"data": [{"id": "t2", "title": "Second", "updatedAt": 7}]}

        page = CodexSessionClient(request=request).list_recent("opaque")

        self.assertEqual(calls[0]["cursor"], "opaque")
        self.assertEqual(page.items[0].title, "Second")
        self.assertIsNone(page.next_cursor)

    def test_resolves_only_tokens_from_current_page(self):
        responses = iter([
            {"data": [{"id": "first", "name": "First", "updatedAt": 1}]},
            {"data": [{"id": "second", "name": "Second", "updatedAt": 2}]},
        ])
        client = CodexSessionClient(request=lambda _method, _params: next(responses))
        first = client.list_recent().items[0]
        second = client.list_recent().items[0]

        self.assertIsNone(client.resolve(first.selection_token))
        self.assertEqual(client.resolve(second.selection_token).thread_id, "second")

    def test_rejects_malformed_response(self):
        client = CodexSessionClient(request=lambda _method, _params: {"data": "bad"})

        with self.assertRaises(SessionProtocolError):
            client.list_recent()


if __name__ == "__main__":
    unittest.main()
