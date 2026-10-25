import asyncio
import sys
from pathlib import Path

import decky

PLUGIN_ROOT = Path(__file__).resolve().parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from backend.controller import ChatGPTController


class Plugin:
    def __init__(self, controller=None):
        self._controller = controller or ChatGPTController()

    async def _main(self):
        decky.logger.info("ChatGPT Community controller loaded")

    async def _unload(self):
        decky.logger.info("ChatGPT Community controller unloaded")

    async def get_status(self):
        try:
            return await asyncio.to_thread(self._controller.status)
        except Exception:
            decky.logger.exception("Status request failed")
            return {
                "installed": False,
                "version": None,
                "running": False,
                "voiceCompatible": False,
                "voiceMessage": "Could not inspect ChatGPT Community",
                "updater": None,
            }

    async def open_app(self):
        return await self._operation("open_app")

    async def toggle_voice(self):
        return await self._operation("toggle_voice")

    async def new_chat(self):
        return await self._operation("new_chat")

    async def list_recent_chats(self, cursor=None):
        try:
            return await asyncio.to_thread(self._controller.list_recent_chats, cursor)
        except Exception:
            decky.logger.exception("Recent chat request failed")
            return {"ok": False, "message": "Could not load recent chats", "items": [], "nextCursor": None}

    async def open_recent_chat(self, selection_token):
        return await self._operation("open_recent_chat", selection_token)

    async def open_recent_chat_with_voice(self, selection_token):
        return await self._operation("open_recent_chat_with_voice", selection_token)

    async def mute_microphone(self):
        return await self._operation("mute_microphone")

    async def unmute_microphone(self):
        return await self._operation("unmute_microphone")

    async def mute_speaker(self):
        return await self._operation("mute_speaker")

    async def unmute_speaker(self):
        return await self._operation("unmute_speaker")

    async def check_updates(self):
        return await self._operation("check_updates")

    async def _operation(self, name, *args):
        try:
            operation = getattr(self._controller, name)
            result = await asyncio.to_thread(operation, *args)
            decky.logger.info("Operation %s finished: ok=%s", name, result.ok)
            return result.to_dict()
        except Exception:
            decky.logger.exception("Operation %s failed", name)
            return {"ok": False, "message": "Unexpected plugin error"}
