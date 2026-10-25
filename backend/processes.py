from dataclasses import dataclass
from pathlib import Path

from .installations import Installation, select_installation

_DISPLAY_KEYS = {
    "DBUS_SESSION_BUS_ADDRESS",
    "DISPLAY",
    "HOME",
    "PATH",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "XDG_RUNTIME_DIR",
}


@dataclass(frozen=True)
class AppProcess:
    pid: int
    executable: str
    environment: dict[str, str]


def _nul_items(path: Path) -> list[str]:
    return [
        item.decode("utf-8", errors="replace")
        for item in path.read_bytes().split(b"\0")
        if item
    ]


def _environment(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _nul_items(path):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key in _DISPLAY_KEYS:
            result[key] = value
    return result


def find_app_processes(
    installation: Installation | None = None,
    proc_root: Path = Path("/proc"),
) -> list[AppProcess]:
    result: list[AppProcess] = []
    selected = installation or select_installation()
    if selected is None:
        return result
    try:
        entries = sorted(
            (entry for entry in proc_root.iterdir() if entry.name.isdigit()),
            key=lambda entry: int(entry.name),
        )
    except OSError:
        return result

    for entry in entries:
        try:
            executable = str((entry / "exe").readlink())
            cmdline = _nul_items(entry / "cmdline")
            is_app = selected.matches_executable(executable)
            if selected.mode == "appimage" and any(
                argument == "--type" or argument.startswith("--type=")
                for argument in cmdline[1:]
            ):
                is_app = False
            is_launcher = (
                selected.mode == "native"
                and bool(cmdline)
                and cmdline[0] == str(selected.launch_executable)
            )
            if not is_app and not is_launcher:
                continue
            result.append(
                AppProcess(int(entry.name), executable, _environment(entry / "environ"))
            )
        except (OSError, ValueError):
            continue
    return result
