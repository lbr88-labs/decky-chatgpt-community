export const CHATGPT_SHORTCUT_NAME: string;

export type SteamApps = {
  AddShortcut(
    name: string,
    executable: string,
    startDirectory: string,
    launchOptions: string,
  ): Promise<number>;
  RunGame(
    gameId: string,
    launchOptions: string,
    launchOption: number,
    launchSource: number,
  ): void;
  SetAppLaunchOptions(appId: number, launchOptions: string): void;
  SetShortcutExe(appId: number, executable: string): void;
  SetShortcutName(appId: number, name: string): void;
  SetShortcutStartDir(appId: number, directory: string): void;
};

export type SteamNavigation = {
  MainRunningAppID: number;
  RunningApps: Array<{ appid: number }>;
  NavigateToRunningApp(): void;
  SetRunningApp(appId: number): void;
};

export type SteamAppStore = {
  allApps: Array<{ appid: number; display_name: string }>;
  GetAppOverviewByAppID(
    appId: number,
  ): { GetGameID(): string } | undefined;
};

export type SteamDependencies = {
  apps: SteamApps;
  appStore: SteamAppStore;
  steamUiStore: SteamNavigation;
  storage: Storage;
};

export type ChatGPTLaunch = {
  executable: string;
  startDirectory: string;
  launchOptions: string;
};

export function gameIdFromAppId(appId: number): string;

export function launchChatGPT(
  dependencies: SteamDependencies,
  launch: ChatGPTLaunch,
): Promise<{ appId: number; created: boolean; running: boolean }>;

export function runWithChatGPTForeground<T>(
  dependencies: SteamDependencies,
  launch: ChatGPTLaunch,
  operation: () => Promise<T>,
): Promise<T>;
