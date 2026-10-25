import unittest

from backend.sessions import CodexSessionClient, SessionProtocolError


class SessionClientTests(unittest.TestCase):
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
