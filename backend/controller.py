import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from .compatibility import VoiceContract, check_voice_contract
from .desktop import graphical_environment
from .installations import Installation, select_installation
from .models import OperationResult
from .processes import AppProcess, find_app_processes
from .status import read_package_info, read_updater_status, request_update_check


class ChatGPTController:
    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        popen: Callable[..., object] = subprocess.Popen,
        process_finder: Callable[[], list[AppProcess]] = find_app_processes,
        installation_selector: Callable[[], Installation | None] = select_installation,
        contract_checker: Callable[[Path], VoiceContract] = check_voice_contract,
        environment_builder: Callable[..., dict[str, str]] = graphical_environment,
        sleep: Callable[[float], None] = time.sleep,
        launch_attempts: int = 120,
        app_asar: Path | None = None,
        uid: int | None = None,
    ) -> None:
        self._runner = runner
        self._popen = popen
        self._process_finder = process_finder
        self._installation_selector = installation_selector
        self._contract_checker = contract_checker
        self._environment_builder = environment_builder
        self._sleep = sleep
        self._launch_attempts = launch_attempts
        self._app_asar = app_asar
        self._uid = os.getuid() if uid is None else uid

    def status(self) -> dict[str, object]:
        installation = self._installation_selector()
        if installation is None:
            return {
                "installed": False,
                "version": None,
                "running": False,
                "voiceCompatible": False,
                "voiceMessage": "ChatGPT Community is not installed",
                "updater": None,
                "installationMode": None,
                "launch": None,
            }
        processes = self._process_finder(installation)
        if installation.mode == "native":
            package = read_package_info(
                self._runner,
                app_executable=installation.app_executable,
                metadata_path=installation.metadata_path,
            )
            updater = read_updater_status(self._runner)
        else:
            package = None
            updater = None
        app_asar = self._contract_path(installation, processes)
        contract = (
            self._contract_checker(app_asar)
            if app_asar is not None
            else VoiceContract(
                False,
                (),
                "Start the AppImage once to verify Voice Mode compatibility",
            )
        )
        return {
            "installed": True if package is None else package.installed,
            "version": installation.installed_version() if package is None else package.version,
            "running": bool(processes),
            "voiceCompatible": contract.compatible,
            "voiceMessage": contract.message,
            "updater": updater,
            "installationMode": installation.mode,
            "launch": installation.launch_dict(),
        }

    def open_app(self) -> OperationResult:
        window = self._ensure_window()
        if isinstance(window, OperationResult):
            return window
        focus = self._focus(window[0], window[1])
        if not focus.ok:
            return focus
        return OperationResult(True, "ChatGPT Community is open")

    def toggle_voice(self) -> OperationResult:
        installation = self._installation_selector()
        if installation is None:
            return OperationResult(False, "ChatGPT Community is not installed")
        processes = self._process_finder(installation)
        app_asar = self._contract_path(installation, processes)
        if app_asar is None:
            return OperationResult(False, "Could not locate the running AppImage bundle")
        contract = self._contract_checker(app_asar)
        if not contract.compatible:
            return OperationResult(False, contract.message)
        return self._send_shortcut("ctrl+shift+v", "Voice Mode toggled")

    def new_chat(self) -> OperationResult:
        return self._send_shortcut("ctrl+n", "New ChatGPT conversation opened")

    def check_updates(self) -> OperationResult:
        installation = self._installation_selector()
        if installation is None:
            return OperationResult(False, "ChatGPT Community is not installed")
        return request_update_check(installation, self._runner)

    def _contract_path(
        self, installation: Installation, processes: list[AppProcess]
    ) -> Path | None:
        if self._app_asar is not None:
            return self._app_asar
        if installation.mode == "native":
            return installation.app_asar
        for process in processes:
            app_asar = installation.runtime_asar(process.executable)
            if app_asar is not None:
                return app_asar
        return None

    def _send_shortcut(self, shortcut: str, message: str) -> OperationResult:
        window = self._ensure_window()
        if isinstance(window, OperationResult):
            return window
        environment, window_id = window
        focus = self._focus(environment, window_id)
        if not focus.ok:
            return focus
        result = self._xdotool(
            ("key", "--window", window_id, "--clearmodifiers", shortcut),
            environment,
        )
        if result is None or result.returncode != 0:
            return OperationResult(False, "ChatGPT did not accept the keyboard command")
        return OperationResult(True, message)

    def _ensure_window(self) -> tuple[dict[str, str], str] | OperationResult:
        installation = self._installation_selector()
        if installation is None:
            return OperationResult(False, "ChatGPT Community is not installed")
        saw_process = False
        for attempt in range(self._launch_attempts):
            processes = self._process_finder(installation)
            saw_process = saw_process or bool(processes)
            for process in processes:
                primary_environment = self._environment_builder(
                    self._uid,
                    process.environment,
                    prefer_gamescope=not bool(process.environment.get("DISPLAY")),
                )
                for environment in self._display_environments(
                    primary_environment,
                    discover=not bool(process.environment.get("DISPLAY")),
                ):
                    window_id = self._largest_window(environment, installation.window_class)
                    if window_id is not None:
                        return environment, window_id
            if attempt + 1 < self._launch_attempts:
                self._sleep(0.25)

        if not saw_process:
            return OperationResult(
                False,
                "ChatGPT Community did not start through Steam",
            )
        return OperationResult(False, "Could not find ChatGPT Community's Steam window")

    @staticmethod
    def _display_environments(
        primary: dict[str, str], *, discover: bool
    ) -> list[dict[str, str]]:
        environments = [primary]
        if not discover:
            return environments

        seen = {primary.get("DISPLAY")}
        sockets = sorted(
            Path("/tmp/.X11-unix").glob("X*"),
            key=lambda path: int(path.name[1:]) if path.name[1:].isdigit() else -1,
        )
        for socket in sockets:
            number = socket.name[1:]
            if not number.isdigit():
                continue
            display = f":{number}"
            if display in seen:
                continue
            environment = dict(primary)
            environment["DISPLAY"] = display
            environments.append(environment)
            seen.add(display)
        return environments

    def _largest_window(
        self, environment: dict[str, str], window_class: str
    ) -> str | None:
        result = self._xdotool(
            ("search", "--onlyvisible", "--class", f"^{window_class}$"),
            environment,
        )
        if result is None or result.returncode != 0:
            return None
        candidates: list[tuple[int, str]] = []
        for window_id in result.stdout.split():
            if not window_id.isdigit():
                continue
            geometry = self._xdotool(
                ("getwindowgeometry", "--shell", window_id), environment
            )
            if geometry is None or geometry.returncode != 0:
                continue
            values = {}
            for line in geometry.stdout.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value
            try:
                area = int(values["WIDTH"]) * int(values["HEIGHT"])
            except (KeyError, ValueError):
                continue
            candidates.append((area, window_id))
        return max(candidates)[1] if candidates else None

    def _focus(self, environment: dict[str, str], window_id: str) -> OperationResult:
        result = self._xdotool(("windowactivate", "--sync", window_id), environment)
        if result is None or result.returncode != 0:
            result = self._xdotool(("windowfocus", "--sync", window_id), environment)
        if result is None or result.returncode != 0:
            return OperationResult(False, "Could not focus ChatGPT Community")
        return OperationResult(True, "ChatGPT Community focused")

    def _xdotool(
        self, arguments: tuple[str, ...], environment: dict[str, str]
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            return self._runner(
                ("/usr/bin/xdotool", *arguments),
                env=environment,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
