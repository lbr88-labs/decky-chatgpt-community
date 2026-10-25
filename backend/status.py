import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .installations import Installation
from .models import OperationResult


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class PackageInfo:
    installed: bool
    version: str | None


def _run(runner: Runner, command: tuple[str, ...]) -> subprocess.CompletedProcess[str] | None:
    try:
        return runner(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def read_package_info(
    runner: Runner = subprocess.run,
    *,
    app_executable: Path = Path("/opt/codex-desktop/ChatGPT"),
    metadata_path: Path = Path(
        "/opt/codex-desktop/resources/linux-package-metadata.json"
    ),
) -> PackageInfo:
    result = _run(runner, ("/usr/bin/pacman", "-Q", "codex-desktop"))
    if result is not None and result.returncode == 0:
        fields = result.stdout.strip().split()
        if len(fields) == 2 and fields[0] == "codex-desktop":
            return PackageInfo(True, fields[1])

    try:
        if not app_executable.is_file():
            return PackageInfo(False, None)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return PackageInfo(True, None)

    version = metadata.get("version") if isinstance(metadata, dict) else None
    return PackageInfo(True, version if isinstance(version, str) and version else None)


def read_updater_status(runner: Runner = subprocess.run) -> dict[str, Any] | None:
    result = _run(
        runner,
        ("/usr/bin/codex-update-manager", "status", "--json"),
    )
    if result is None or result.returncode != 0:
        return None
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def request_update_check(
    installation: Installation,
    runner: Runner = subprocess.run,
) -> OperationResult:
    if installation.mode == "appimage":
        return OperationResult(
            True,
            "AppImage updates use the ChatGPT Community Steam Deck installer; run it again to check and update",
        )
    result = _run(runner, ("/usr/bin/codex-update-manager", "check-now"))
    if result is None:
        return OperationResult(False, "Could not run the ChatGPT Community updater")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown updater error"
        return OperationResult(False, f"Update check failed: {detail}")
    message = result.stdout.strip() or "Update check requested"
    return OperationResult(True, message)
