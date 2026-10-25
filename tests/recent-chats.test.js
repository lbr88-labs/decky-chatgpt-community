import assert from "node:assert/strict";
import test from "node:test";

import { firstPage, nextPage, previousPage, refreshPage } from "../src/recent-chats.js";

test("next page records the current cursor and uses the server cursor", () => {
  assert.deepEqual(nextPage(firstPage(), "next-1"), {
    cursor: "next-1",
    previous: [null],
  });
});

test("previous page restores the prior cursor", () => {
  const state = nextPage(nextPage(firstPage(), "next-1"), "next-2");
  assert.deepEqual(previousPage(state), { cursor: "next-1", previous: [null] });
});

test("refresh returns to the first page", () => {
  assert.deepEqual(refreshPage({ cursor: "next", previous: [null] }), firstPage());
});

test("missing next cursor leaves paging state unchanged", () => {
  const state = firstPage();
  assert.deepEqual(nextPage(state, null), state);
});
