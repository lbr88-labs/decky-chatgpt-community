import json
import os
from dataclasses import dataclass
from pathlib import Path


APPIMAGE_ROOT = Path("/home/deck/.local/share/chatgpt-community-appimage")
APPIMAGE_RUNTIME_ROOT = Path("/home/deck/.cache/chatgpt-runtime")
NATIVE_LAUNCHER = Path("/usr/bin/codex-desktop")
NATIVE_EXECUTABLE = Path("/opt/codex-desktop/ChatGPT")


@dataclass(frozen=True)
class Installation:
    mode: str
    launch_executable: Path
    start_directory: Path
    window_class: str
    runtime_root: Path | None = None
    app_executable: Path | None = None
    app_asar: Path | None = None
    metadata_path: Path | None = None

    @classmethod
    def appimage(cls, root: Path, runtime_root: Path) -> "Installation":
        return cls(
            mode="appimage",
            launch_executable=root / "launch-appimage.sh",
            start_directory=root,
            window_class="chatgpt-community-appimage",
            runtime_root=runtime_root,
            metadata_path=root / "build-info.json",
        )

    @classmethod
    def native(
        cls,
        launcher: Path = NATIVE_LAUNCHER,
        executable: Path = NATIVE_EXECUTABLE,
    ) -> "Installation":
        root = executable.parent
        return cls(
            mode="native",
            launch_executable=launcher,
            start_directory=root,
            window_class="codex-desktop",
            app_executable=executable,
            app_asar=root / "resources/app.asar",
            metadata_path=root / "resources/linux-package-metadata.json",
        )

    def installed_version(self) -> str | None:
        if self.metadata_path is None:
            return None
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(metadata, dict):
            return None
        if self.mode == "appimage":
            package = metadata.get("upstreamLinuxPackage")
            version = package.get("version") if isinstance(package, dict) else None
        else:
            version = metadata.get("version")
        return version if isinstance(version, str) and version else None

    def matches_executable(self, executable: str) -> bool:
        path = Path(executable)
        if self.mode == "native":
            return path == self.app_executable
        if self.runtime_root is None:
            return False
        try:
            relative = path.relative_to(self.runtime_root)
        except ValueError:
            return False
        parts = relative.parts
        return (
            len(parts) == 5
            and parts[0].startswith("run.")
            and len(parts[0]) > len("run.")
            and parts[1].startswith("appimage_extracted_")
            and len(parts[1]) > len("appimage_extracted_")
            and parts[2:] == ("opt", "codex-desktop", "ChatGPT")
        )

    def runtime_asar(self, executable: str) -> Path | None:
        if self.mode == "native":
            return self.app_asar
        if not self.matches_executable(executable):
            return None
        return Path(executable).parent / "resources/app.asar"

    def launch_dict(self) -> dict[str, str]:
        return {
            "executable": str(self.launch_executable),
            "startDirectory": str(self.start_directory),
            "launchOptions": (
                'LD_PRELOAD="" %command% '
                '--remote-debugging-address=127.0.0.1 --remote-debugging-port=9223'
            ),
        }


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def select_installation(
    *,
    appimage_root: Path = APPIMAGE_ROOT,
    native_launcher: Path = NATIVE_LAUNCHER,
    native_executable: Path = NATIVE_EXECUTABLE,
    runtime_root: Path = APPIMAGE_RUNTIME_ROOT,
) -> Installation | None:
    appimage = Installation.appimage(appimage_root, runtime_root)
    if _is_executable(appimage_root / "ChatGPT-Community.AppImage") and _is_executable(
        appimage.launch_executable
    ):
        return appimage
    if _is_executable(native_launcher) and _is_executable(native_executable):
        return Installation.native(native_launcher, native_executable)
    return None
