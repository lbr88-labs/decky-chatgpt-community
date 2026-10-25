#!/usr/bin/env python3
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.compatibility import check_voice_contract  # noqa: E402
from backend.installations import Installation, select_installation  # noqa: E402
from backend.processes import AppProcess, find_app_processes  # noqa: E402


def default_app_asar(
    *,
    installation: Installation | None = None,
    processes: list[AppProcess] | None = None,
) -> Path | None:
    selected = installation or select_installation()
    if selected is None:
        return None
    if selected.mode == "native":
        return selected.app_asar
    running = find_app_processes(selected) if processes is None else processes
    for process in running:
        app_asar = selected.runtime_asar(process.executable)
        if app_asar is not None:
            return app_asar
    return None


def main() -> int:
    app_asar = Path(sys.argv[1]) if len(sys.argv) > 1 else default_app_asar()
    if app_asar is None:
        print(
            "ERROR: no supported ChatGPT Community installation is running or installed",
            file=sys.stderr,
        )
        return 1
    result = check_voice_contract(app_asar)
    if result.compatible:
        print(f"OK: {result.message}: {app_asar}")
        return 0
    print(f"ERROR: {result.message}: {app_asar}", file=sys.stderr)
    if result.missing:
        print(f"Missing: {', '.join(result.missing)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
