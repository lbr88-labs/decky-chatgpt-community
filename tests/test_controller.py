import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.compatibility import VoiceContract
from backend.controller import ChatGPTController
from backend.installations import Installation
from backend.processes import AppProcess


class XdotoolRunner:
    def __init__(self, windows=("10", "20"), windows_by_display=None):
        self.windows = windows
        self.windows_by_display = windows_by_display
        self.calls = []
        self.environments = []

    def __call__(self, args, **kwargs):
        command = tuple(args)
        self.calls.append(command)
        self.environments.append(kwargs.get("env", {}))
        if command[:4] == (
            "/usr/bin/xdotool",
            "search",
            "--onlyvisible",
            "--class",
        ):
            windows = self.windows
            if self.windows_by_display is not None:
                windows = self.windows_by_display.get(kwargs.get("env", {}).get("DISPLAY"), ())
            return subprocess.CompletedProcess(
                args,
                0 if windows else 1,
                "\n".join(windows) + ("\n" if windows else ""),
                "",
            )
        if command == ("/usr/bin/xdotool", "getwindowgeometry", "--shell", "10"):
            return subprocess.CompletedProcess(args, 0, "WIDTH=100\nHEIGHT=100\n", "")
        if command == ("/usr/bin/xdotool", "getwindowgeometry", "--shell", "20"):
            return subprocess.CompletedProcess(args, 0, "WIDTH=640\nHEIGHT=480\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")


class FakePopen:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((tuple(args), kwargs))
        return object()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.process = AppProcess(
            88,
            "/opt/codex-desktop/ChatGPT",
            {"DISPLAY": ":8", "XAUTHORITY": "/tmp/xauth", "HOME": "/home/deck"},
        )

    def _controller(
        self,
        *,
        runner=None,
        processes=None,
        contract=None,
        popen=None,
        environment_builder=None,
        installation=None,
    ):
        selected = installation or Installation.native()
        return ChatGPTController(
            runner=runner or XdotoolRunner(),
            installation_selector=lambda: selected,
            process_finder=lambda _installation: [self.process] if processes is None else processes(),
            contract_checker=lambda _: contract
            or VoiceContract(True, (), "Realtime Voice Mode is compatible"),
            popen=popen or FakePopen(),
            sleep=lambda _: None,
            launch_attempts=2,
            app_asar=Path("/fake/app.asar"),
            uid=1000,
            **(
                {"environment_builder": environment_builder}
                if environment_builder is not None
                else {}
            ),
        )

    def test_voice_fails_closed_before_input_when_contract_is_missing(self):
        runner = XdotoolRunner()
        controller = self._controller(
            runner=runner,
            contract=VoiceContract(False, ("Ctrl+Shift+V",), "incompatible bundle"),
        )

        result = controller.toggle_voice()

        self.assertFalse(result.ok)
        self.assertIn("incompatible bundle", result.message)
        self.assertEqual(runner.calls, [])

    def test_voice_focuses_largest_exact_window_before_sending_shortcut(self):
        runner = XdotoolRunner()
        controller = self._controller(runner=runner)

        result = controller.toggle_voice()

        self.assertTrue(result.ok)
        self.assertIn(
            (
                "/usr/bin/xdotool",
                "search",
                "--onlyvisible",
                "--class",
                "^codex-desktop$",
            ),
            runner.calls,
        )
        focus = ("/usr/bin/xdotool", "windowactivate", "--sync", "20")
        key = (
            "/usr/bin/xdotool",
            "key",
            "--window",
            "20",
            "--clearmodifiers",
            "ctrl+shift+v",
        )
        self.assertLess(runner.calls.index(focus), runner.calls.index(key))

    def test_missing_verified_window_never_sends_key(self):
        runner = XdotoolRunner(windows=())
        controller = self._controller(runner=runner)

        result = controller.toggle_voice()

        self.assertFalse(result.ok)
        self.assertIn("window", result.message.lower())
        self.assertFalse(any("key" in call for call in runner.calls))

    def test_open_waits_for_steam_launched_app_then_focuses_its_window(self):
        sightings = iter(([], [self.process]))
        popen = FakePopen()
        runner = XdotoolRunner(windows=("20",))
        controller = self._controller(
            runner=runner,
            processes=lambda: next(sightings, [self.process]),
            popen=popen,
            environment_builder=lambda _uid, _inherited=None, **_kwargs: {
                "HOME": "/home/deck",
                "PATH": "/usr/bin",
                "DISPLAY": ":0",
            },
        )

        result = controller.open_app()

        self.assertTrue(result.ok)
        self.assertEqual(popen.calls, [])
        self.assertIn(
            ("/usr/bin/xdotool", "windowactivate", "--sync", "20"),
            runner.calls,
        )

    def test_voice_waits_for_steam_window_without_spawning_a_hidden_process(self):
        sightings = iter(([], [self.process]))
        popen = FakePopen()
        controller = self._controller(
            runner=XdotoolRunner(windows=("20",)),
            processes=lambda: next(sightings, [self.process]),
            popen=popen,
            environment_builder=lambda _uid, inherited=None, **_kwargs: {
                **(inherited or {}),
                "PATH": "/usr/bin",
            },
        )

        result = controller.toggle_voice()

        self.assertTrue(result.ok)
        self.assertEqual(popen.calls, [])

    def test_new_chat_uses_the_apps_fixed_shortcut(self):
        runner = XdotoolRunner(windows=("20",))
        controller = self._controller(runner=runner)

        result = controller.new_chat()

        self.assertTrue(result.ok)
        self.assertIn(
            (
                "/usr/bin/xdotool",
                "key",
                "--window",
                "20",
                "--clearmodifiers",
                "ctrl+n",
            ),
            runner.calls,
        )

    def test_masked_process_environment_falls_back_to_gamescope_display(self):
        runner = XdotoolRunner(windows=("20",))
        masked_process = AppProcess(88, "/opt/codex-desktop/ChatGPT", {})

        def environment_builder(_uid, _inherited=None, *, prefer_gamescope=True):
            return {"DISPLAY": ":0"} if prefer_gamescope else {}

        controller = ChatGPTController(
            runner=runner,
            installation_selector=Installation.native,
            process_finder=lambda _installation: [masked_process],
            contract_checker=lambda _: VoiceContract(True, (), "compatible"),
            environment_builder=environment_builder,
            app_asar=Path("/fake/app.asar"),
            uid=1000,
        )

        result = controller.toggle_voice()

        self.assertTrue(result.ok)
        self.assertTrue(runner.environments)
        self.assertTrue(all(env.get("DISPLAY") == ":0" for env in runner.environments))

    def test_masked_process_environment_finds_window_on_secondary_xwayland(self):
        runner = XdotoolRunner(windows_by_display={":1": ("20",)})
        masked_process = AppProcess(88, "/opt/codex-desktop/ChatGPT", {})
        controller = ChatGPTController(
            runner=runner,
            installation_selector=Installation.native,
            process_finder=lambda _installation: [masked_process],
            contract_checker=lambda _: VoiceContract(True, (), "compatible"),
            environment_builder=lambda *_args, **_kwargs: {"DISPLAY": ":0"},
            app_asar=Path("/fake/app.asar"),
            uid=1000,
            launch_attempts=1,
        )

        with patch(
            "backend.controller.Path.glob",
            return_value=[Path("/tmp/.X11-unix/X0"), Path("/tmp/.X11-unix/X1")],
        ):
            result = controller.toggle_voice()

        self.assertTrue(result.ok)
        key_environments = [
            environment
            for call, environment in zip(runner.calls, runner.environments)
            if "key" in call
        ]
        self.assertEqual(key_environments[0]["DISPLAY"], ":1")

    def test_appimage_voice_uses_runtime_asar_and_appimage_window_class(self):
        executable = (
            "/home/deck/.cache/chatgpt-runtime/run.A1b2/"
            "appimage_extracted_deadbeef/opt/codex-desktop/ChatGPT"
        )
        process = AppProcess(99, executable, {"DISPLAY": ":8"})
        runner = XdotoolRunner(windows=("20",))
        checked = []
        installation = Installation.appimage(
            Path("/home/deck/.local/share/chatgpt-community-appimage"),
            Path("/home/deck/.cache/chatgpt-runtime"),
        )
        controller = ChatGPTController(
            runner=runner,
            installation_selector=lambda: installation,
            process_finder=lambda _installation: [process],
            contract_checker=lambda path: checked.append(path)
            or VoiceContract(True, (), "compatible"),
            environment_builder=lambda *_args, **_kwargs: {"DISPLAY": ":8"},
            uid=1000,
        )

        result = controller.toggle_voice()

        self.assertTrue(result.ok)
        self.assertEqual(
            checked,
            [Path(executable).parent / "resources/app.asar"],
        )
        self.assertIn(
            (
                "/usr/bin/xdotool",
                "search",
                "--onlyvisible",
                "--class",
                "^chatgpt-community-appimage$",
            ),
            runner.calls,
        )

    def test_status_exposes_selected_launch_configuration(self):
        installation = Installation.appimage(
            Path("/home/deck/.local/share/chatgpt-community-appimage"),
            Path("/home/deck/.cache/chatgpt-runtime"),
        )
        controller = ChatGPTController(
            runner=XdotoolRunner(),
            installation_selector=lambda: installation,
            process_finder=lambda _installation: [],
            uid=1000,
        )

        status = controller.status()

        self.assertTrue(status["installed"])
        self.assertEqual(status["installationMode"], "appimage")
        self.assertEqual(
            status["launch"],
            {
                "executable": "/home/deck/.local/share/chatgpt-community-appimage/launch-appimage.sh",
                "startDirectory": "/home/deck/.local/share/chatgpt-community-appimage",
                "launchOptions": 'LD_PRELOAD="" %command%',
            },
        )
        self.assertFalse(status["voiceCompatible"])
        self.assertIn("start", status["voiceMessage"].lower())


if __name__ == "__main__":
    unittest.main()
