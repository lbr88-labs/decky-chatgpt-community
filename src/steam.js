export const CHATGPT_SHORTCUT_NAME = "ChatGPT Community";

const SHORTCUT_STORAGE_KEY = "decky-chatgpt-community:steam-shortcut-app-id";
const GAMEPAD_UI_LAUNCH_SOURCE = 100;

function normalizedAppId(value) {
  const number = Number(value);
  if (!Number.isInteger(number) || number === 0) return null;
  return number >>> 0;
}

export function gameIdFromAppId(appId) {
  return (
    (BigInt(normalizedAppId(appId)) << 32n) |
    0x02000000n
  ).toString();
}

function recalledAppId(storage) {
  try {
    return normalizedAppId(storage.getItem(SHORTCUT_STORAGE_KEY));
  } catch {
    return null;
  }
}

function rememberAppId(storage, appId) {
  try {
    storage.setItem(SHORTCUT_STORAGE_KEY, String(appId));
  } catch {
    // Steam can still launch the shortcut for this plugin session.
  }
}

function existingShortcutAppId(appStore) {
  const overview = appStore.allApps?.find(
    (app) => app.display_name === CHATGPT_SHORTCUT_NAME,
  );
  return normalizedAppId(overview?.appid);
}

async function ensureShortcut({ apps, appStore, storage }, launch) {
  let appId = recalledAppId(storage) ?? existingShortcutAppId(appStore);
  let created = false;

  if (appId === null) {
    appId = normalizedAppId(
      await apps.AddShortcut(
        CHATGPT_SHORTCUT_NAME,
        launch.executable,
        launch.startDirectory,
        launch.launchOptions,
      ),
    );
    if (appId === null) {
      throw new Error("Steam did not create the ChatGPT Community shortcut");
    }
    created = true;
  }

  apps.SetShortcutName(appId, CHATGPT_SHORTCUT_NAME);
  apps.SetShortcutExe(appId, launch.executable);
  apps.SetShortcutStartDir(appId, launch.startDirectory);
  apps.SetAppLaunchOptions(appId, launch.launchOptions);
  rememberAppId(storage, appId);
  return { appId, created };
}

export async function launchChatGPT(dependencies, launch) {
  const result = await ensureShortcut(dependencies, launch);
  const running = dependencies.steamUiStore.RunningApps?.some(
    (app) => normalizedAppId(app.appid) === result.appId,
  );
  if (!running) {
    dependencies.apps.RunGame(
      gameIdFromAppId(result.appId),
      "",
      -1,
      GAMEPAD_UI_LAUNCH_SOURCE,
    );
  }
  dependencies.steamUiStore.SetRunningApp(result.appId);
  dependencies.steamUiStore.NavigateToRunningApp();
  return { ...result, running: Boolean(running) };
}

export async function runWithChatGPTForeground(dependencies, launch, operation) {
  const previousAppId = normalizedAppId(
    dependencies.steamUiStore.MainRunningAppID,
  );
  const { appId } = await launchChatGPT(dependencies, launch);

  try {
    return await operation();
  } finally {
    if (previousAppId !== null && previousAppId !== appId) {
      const previous = dependencies.appStore.GetAppOverviewByAppID(previousAppId);
      const previousGameId = previous?.GetGameID?.();
      if (previousGameId) {
        dependencies.steamUiStore.SetRunningApp(previousAppId);
        dependencies.steamUiStore.NavigateToRunningApp();
      }
    }
  }
}
