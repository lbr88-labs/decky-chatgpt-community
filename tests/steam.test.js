import assert from "node:assert/strict";
import test from "node:test";

import {
  CHATGPT_SHORTCUT_NAME,
  gameIdFromAppId,
  launchChatGPT,
  runWithChatGPTForeground,
} from "../src/steam.js";

const NATIVE_LAUNCH = {
  executable: "/usr/bin/codex-desktop",
  startDirectory: "/opt/codex-desktop",
  launchOptions: 'LD_PRELOAD="" %command%',
};

const APPIMAGE_LAUNCH = {
  executable:
    "/home/deck/.local/share/chatgpt-community-appimage/launch-appimage.sh",
  startDirectory: "/home/deck/.local/share/chatgpt-community-appimage",
  launchOptions: 'LD_PRELOAD="" %command%',
};

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    this.values.set(key, value);
  }
}

function fixture() {
  const calls = [];
  const apps = {
    async AddShortcut(...args) {
      calls.push(["AddShortcut", ...args]);
      return 0x81234567;
    },
    RunGame(...args) {
      calls.push(["RunGame", ...args]);
    },
    SetShortcutExe(...args) {
      calls.push(["SetShortcutExe", ...args]);
    },
    SetAppLaunchOptions(...args) {
      calls.push(["SetAppLaunchOptions", ...args]);
    },
    SetShortcutIcon(...args) {
      calls.push(["SetShortcutIcon", ...args]);
    },
    SetShortcutName(...args) {
      calls.push(["SetShortcutName", ...args]);
    },
    SetShortcutStartDir(...args) {
      calls.push(["SetShortcutStartDir", ...args]);
    },
  };
  const steamUiStore = {
    MainRunningAppID: 570,
    RunningApps: [],
    NavigateToRunningApp() {
      calls.push(["NavigateToRunningApp"]);
    },
    SetRunningApp(appId) {
      calls.push(["SetRunningApp", appId]);
      this.MainRunningAppID = appId;
    },
  };
  const appStore = {
    allApps: [],
    GetAppOverviewByAppID(appId) {
      if (appId !== 570) return undefined;
      return { GetGameID: () => "570" };
    },
  };
  return {
    dependencies: {
      apps,
      appStore,
      steamUiStore,
      storage: new MemoryStorage(),
    },
    calls,
  };
}

test("launchChatGPT creates one Steam shortcut and launches its non-Steam game ID", async () => {
  const { dependencies, calls } = fixture();

  const first = await launchChatGPT(dependencies, NATIVE_LAUNCH);
  const second = await launchChatGPT(dependencies, NATIVE_LAUNCH);

  assert.equal(first.appId, 0x81234567);
  assert.equal(first.created, true);
  assert.equal(second.created, false);
  assert.equal(
    calls.filter(([name]) => name === "AddShortcut").length,
    1,
  );
  assert.deepEqual(calls.find(([name]) => name === "AddShortcut"), [
    "AddShortcut",
    CHATGPT_SHORTCUT_NAME,
    "/usr/bin/codex-desktop",
    "/opt/codex-desktop",
    'LD_PRELOAD="" %command%',
  ]);
  assert.deepEqual(
    calls.filter(([name]) => name === "SetAppLaunchOptions"),
    [
      [
        "SetAppLaunchOptions",
        0x81234567,
        'LD_PRELOAD="" %command%',
      ],
      [
        "SetAppLaunchOptions",
        0x81234567,
        'LD_PRELOAD="" %command%',
      ],
    ],
  );
  assert.deepEqual(calls.filter(([name]) => name === "RunGame"), [
    ["RunGame", gameIdFromAppId(0x81234567), "", -1, 100],
    ["RunGame", gameIdFromAppId(0x81234567), "", -1, 100],
  ]);
});

test("launchChatGPT focuses a running shortcut without launching it again", async () => {
  const { dependencies, calls } = fixture();
  dependencies.storage.setItem(
    "decky-chatgpt-community:steam-shortcut-app-id",
    String(0x81234567),
  );
  dependencies.steamUiStore.RunningApps = [{ appid: 0x81234567 }];

  const result = await launchChatGPT(dependencies, NATIVE_LAUNCH);

  assert.equal(result.appId, 0x81234567);
  assert.equal(result.running, true);
  assert.equal(calls.some(([name]) => name === "RunGame"), false);
  assert.deepEqual(calls.slice(-2), [
    ["SetRunningApp", 0x81234567],
    ["NavigateToRunningApp"],
  ]);
});

test("runWithChatGPTForeground restores the game after the voice command", async () => {
  const { dependencies, calls } = fixture();
  const events = [];

  const result = await runWithChatGPTForeground(dependencies, NATIVE_LAUNCH, async () => {
    events.push("voice");
    return { ok: true, message: "Voice Mode toggled" };
  });

  assert.deepEqual(result, { ok: true, message: "Voice Mode toggled" });
  assert.deepEqual(events, ["voice"]);
  const chatLaunch = calls.findIndex(
    (call) => call[0] === "RunGame" && call[1] !== "570",
  );
  const gameRestore = calls.findIndex(
    (call) => call[0] === "RunGame" && call[1] === "570",
  );
  assert.ok(chatLaunch >= 0);
  assert.equal(gameRestore, -1);
  const gameFocus = calls.findIndex(
    (call) => call[0] === "SetRunningApp" && call[1] === 570,
  );
  assert.ok(gameFocus > chatLaunch);
  assert.deepEqual(calls.slice(gameFocus, gameFocus + 2), [
    ["SetRunningApp", 570],
    ["NavigateToRunningApp"],
  ]);
});

test("runWithChatGPTForeground restores the game when the command fails", async () => {
  const { dependencies, calls } = fixture();

  await assert.rejects(
    runWithChatGPTForeground(dependencies, NATIVE_LAUNCH, async () => {
      throw new Error("voice failed");
    }),
    /voice failed/,
  );

  assert.equal(
    calls.some((call) => call[0] === "RunGame" && call[1] === "570"),
    false,
  );
  assert.ok(
    calls.some((call) => call[0] === "SetRunningApp" && call[1] === 570),
  );
});

test("launchChatGPT rewrites an existing shortcut for the selected AppImage", async () => {
  const { dependencies, calls } = fixture();
  dependencies.appStore.allApps = [
    { appid: 0x81234567, display_name: CHATGPT_SHORTCUT_NAME },
  ];

  const result = await launchChatGPT(dependencies, APPIMAGE_LAUNCH);

  assert.equal(result.created, false);
  assert.equal(calls.some(([name]) => name === "AddShortcut"), false);
  assert.deepEqual(
    calls.find(([name]) => name === "SetShortcutExe"),
    ["SetShortcutExe", 0x81234567, APPIMAGE_LAUNCH.executable],
  );
  assert.deepEqual(
    calls.find(([name]) => name === "SetShortcutStartDir"),
    ["SetShortcutStartDir", 0x81234567, APPIMAGE_LAUNCH.startDirectory],
  );
  assert.deepEqual(
    calls.find(([name]) => name === "SetAppLaunchOptions"),
    ["SetAppLaunchOptions", 0x81234567, APPIMAGE_LAUNCH.launchOptions],
  );
});
