import {
  ButtonItem,
  Navigation,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useEffect, useState } from "react";
import { FaMicrophone } from "react-icons/fa";
import { firstPage, nextPage, previousPage, refreshPage } from "./recent-chats.js";
import {
  launchChatGPT,
  runWithChatGPTForeground,
  type SteamAppStore,
  type SteamApps,
  type ChatGPTLaunch,
  type SteamDependencies,
  type SteamNavigation,
} from "./steam.js";

declare const SteamClient: { Apps: SteamApps };

type PluginStatus = {
  installed: boolean;
  version: string | null;
  running: boolean;
  voiceCompatible: boolean;
  voiceState: "ready" | "pending" | "incompatible";
  voiceMessage: string;
  updater: Record<string, unknown> | null;
  installationMode: "appimage" | "native" | null;
  launch: ChatGPTLaunch | null;
};

type OperationResult = {
  ok: boolean;
  message: string;
};

type RecentChat = {
  selectionToken: string;
  title: string;
  updatedAt: number;
};

type RecentChatPage = {
  ok: boolean;
  message?: string;
  items: RecentChat[];
  nextCursor: string | null;
};

type PageState = { cursor: string | null; previous: Array<string | null> };

const getStatus = callable<[], PluginStatus>("get_status");
const toggleVoice = callable<[], OperationResult>("toggle_voice");
const checkUpdates = callable<[], OperationResult>("check_updates");
const listRecentChats = callable<[string | null], RecentChatPage>("list_recent_chats");
const openRecentChat = callable<[string], OperationResult>("open_recent_chat");
const openRecentChatWithVoice = callable<[string], OperationResult>("open_recent_chat_with_voice");

const menuCloseDelay = () =>
  new Promise<void>((resolve) => window.setTimeout(resolve, 250));

const steamDependencies = (): SteamDependencies => ({
  apps: SteamClient.Apps,
  appStore: window.appStore as unknown as SteamAppStore,
  steamUiStore: window.SteamUIStore as unknown as SteamNavigation,
  storage: window.localStorage,
});

function Content() {
  const [status, setStatus] = useState<PluginStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [pageState, setPageState] = useState<PageState>(firstPage());
  const [recent, setRecent] = useState<RecentChatPage | null>(null);

  const refresh = async () => {
    try {
      setStatus(await getStatus());
    } catch (error) {
      console.error("ChatGPT Community status failed", error);
      toaster.toast({
        title: "ChatGPT Community",
        body: "Could not read app status",
      });
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const loadRecent = async (state: PageState = pageState) => {
    try {
      setRecent(await listRecentChats(state.cursor));
    } catch (error) {
      console.error("Recent chats failed", error);
      setRecent({ ok: false, message: "Could not load recent chats", items: [], nextCursor: null });
    }
  };

  useEffect(() => {
    void loadRecent(pageState);
  }, [pageState.cursor]);

  const runOperation = async (
    title: string,
    operation: () => Promise<OperationResult>,
    closeMenus = false,
  ) => {
    setBusy(true);
    try {
      if (closeMenus) {
        Navigation.CloseSideMenus();
        await menuCloseDelay();
      }
      const result = await operation();
      toaster.toast({ title, body: result.message });
      await refresh();
    } catch (error) {
      console.error(`${title} failed`, error);
      toaster.toast({ title, body: "The Decky backend did not respond" });
    } finally {
      setBusy(false);
    }
  };

  const installed = status?.installed === true;
  const compatible = status?.voiceCompatible === true;
  const voicePending = status?.voiceState === "pending";
  const launch = status?.launch ?? null;
  const version = status?.version ?? "not installed";

  return (
    <>
      <PanelSection title="Status">
        <PanelSectionRow>
          <div style={{ width: "100%", lineHeight: 1.5 }}>
            <div>
              <strong>App:</strong>{" "}
              {status === null
                ? "Checking…"
                : status.running
                  ? `Running (${version})`
                  : installed
                    ? `Installed (${version})`
                    : "Not installed"}
            </div>
            <div>
              <strong>Voice Mode:</strong>{" "}
              {status === null
                ? "Checking…"
                : compatible
                  ? "Ready"
                  : voicePending
                    ? "Ready after launch"
                  : "Unavailable"}
            </div>
            {status !== null && !compatible ? (
              <div style={{ opacity: 0.75, marginTop: 4 }}>
                {status.voiceMessage}
              </div>
            ) : null}
            {compatible ? (
              <div style={{ opacity: 0.75, marginTop: 4 }}>
                Voice stays active while you return to your game.
              </div>
            ) : null}
          </div>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="ChatGPT Community">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            disabled={busy || !installed || launch === null}
            onClick={() =>
              void runOperation(
                "Open ChatGPT",
                async () => {
                  const result = await launchChatGPT(steamDependencies(), launch!);
                  return {
                    ok: true,
                    message: result.created
                      ? "Added to Steam and opening ChatGPT Community"
                      : "Opening ChatGPT Community through Steam",
                  };
                },
                true,
              )
            }
          >
            Open ChatGPT
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            disabled={
              busy ||
              !installed ||
              launch === null ||
              (!compatible && !voicePending)
            }
            onClick={() =>
              void runOperation(
                "ChatGPT Voice Mode",
                () =>
                  runWithChatGPTForeground(
                    steamDependencies(),
                    launch!,
                    toggleVoice,
                  ),
                true,
              )
            }
          >
            Toggle Voice Mode
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ width: "100%", opacity: 0.75 }}>
            Voice Mode briefly switches to ChatGPT, toggles the live voice
            session, then returns to the game that was already running.
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            disabled={busy || !installed}
            onClick={() =>
              void runOperation("ChatGPT Updates", checkUpdates)
            }
          >
            Check for Updates
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={busy} onClick={() => void refresh()}>
            Refresh Status
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Recent chats">
        {recent === null ? (
          <PanelSectionRow>Loading…</PanelSectionRow>
        ) : !recent.ok ? (
          <PanelSectionRow>
            <div style={{ width: "100%" }}>
              <div>{recent.message ?? "Recent chats are unavailable"}</div>
              <ButtonItem layout="below" disabled={busy} onClick={() => void loadRecent()}>
                Retry
              </ButtonItem>
            </div>
          </PanelSectionRow>
        ) : recent.items.length === 0 ? (
          <PanelSectionRow>No recent chats</PanelSectionRow>
        ) : recent.items.map((chat) => (
          <PanelSectionRow key={chat.selectionToken}>
            <div style={{ width: "100%" }}>
              <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {chat.title}
              </div>
              <div style={{ opacity: 0.65, marginBottom: 4 }}>
                {new Date(chat.updatedAt * 1000).toLocaleString()}
              </div>
              <ButtonItem
                layout="below"
                disabled={busy || !installed || launch === null}
                onClick={() => void runOperation("Open chat", async () => {
                  await launchChatGPT(steamDependencies(), launch!);
                  return openRecentChat(chat.selectionToken);
                }, true)}
              >
                Open
              </ButtonItem>
              <ButtonItem
                layout="below"
                disabled={busy || !installed || launch === null || (!compatible && !voicePending)}
                onClick={() => void runOperation("Open chat with Voice", () =>
                  runWithChatGPTForeground(
                    steamDependencies(),
                    launch!,
                    () => openRecentChatWithVoice(chat.selectionToken),
                  ), true)}
              >
                Open + Voice
              </ButtonItem>
            </div>
          </PanelSectionRow>
        ))}
        <PanelSectionRow>
          <div style={{ width: "100%" }}>
            <ButtonItem
              layout="below"
              disabled={busy || pageState.previous.length === 0}
              onClick={() => setPageState(previousPage(pageState))}
            >
              Previous
            </ButtonItem>
            <ButtonItem
              layout="below"
              disabled={busy || recent?.nextCursor == null}
              onClick={() => setPageState(nextPage(pageState, recent?.nextCursor ?? null))}
            >
              Next
            </ButtonItem>
            <ButtonItem
              layout="below"
              disabled={busy}
              onClick={() => {
                const first = refreshPage();
                if (pageState.cursor === null) void loadRecent(first);
                else setPageState(first);
              }}
            >
              Refresh chats
            </ButtonItem>
          </div>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}

export default definePlugin(() => ({
  name: "ChatGPT Community",
  titleView: <div className={staticClasses.Title}>ChatGPT Community</div>,
  content: <Content />,
  icon: <FaMicrophone />,
  alwaysRender: true,
  onDismount() {
    console.log("ChatGPT Community plugin unloaded");
  },
}));
