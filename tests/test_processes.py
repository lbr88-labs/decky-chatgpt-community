import os
import tempfile
import unittest
from pathlib import Path

from backend.installations import Installation
from backend.processes import find_app_processes


class AppProcessTests(unittest.TestCase):
    def setUp(self):
        self.native = Installation.native()
        self.appimage = Installation.appimage(
            Path("/home/deck/.local/share/chatgpt-community-appimage"),
            Path("/home/deck/.cache/chatgpt-runtime"),
        )

    def _process(
        self,
        root: Path,
        pid: int,
        *,
        executable: str,
        cmdline: tuple[str, ...],
        environment: dict[str, str],
    ) -> None:
        process = root / str(pid)
        process.mkdir()
        (process / "exe").symlink_to(executable)
        (process / "cmdline").write_bytes(
            b"\0".join(item.encode() for item in cmdline) + b"\0"
        )
        (process / "environ").write_bytes(
            b"\0".join(f"{key}={value}".encode() for key, value in environment.items())
            + b"\0"
        )

    def test_finds_only_exact_app_executable_and_filters_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            self._process(
                proc,
                200,
                executable="/opt/codex-desktop/ChatGPT",
                cmdline=("/opt/codex-desktop/ChatGPT", "--type=browser"),
                environment={
                    "DISPLAY": ":4",
                    "XAUTHORITY": "/run/user/1000/xauth",
                    "HOME": "/home/deck",
                    "ACCOUNT_TOKEN": "must-not-leave-proc",
                },
            )
            self._process(
                proc,
                201,
                executable="/opt/codex-desktop/browser_crashpad_handler",
                cmdline=("/opt/codex-desktop/browser_crashpad_handler",),
                environment={"DISPLAY": ":4"},
            )

            result = find_app_processes(self.native, proc)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pid, 200)
        self.assertEqual(result[0].executable, "/opt/codex-desktop/ChatGPT")
        self.assertEqual(
            result[0].environment,
            {
                "DISPLAY": ":4",
                "XAUTHORITY": "/run/user/1000/xauth",
                "HOME": "/home/deck",
            },
        )

    def test_launcher_cmdline_is_recognized_without_substring_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            self._process(
                proc,
                300,
                executable="/usr/bin/bash",
                cmdline=("/usr/bin/codex-desktop",),
                environment={"DISPLAY": ":1"},
            )
            self._process(
                proc,
                301,
                executable="/usr/bin/bash",
                cmdline=("/tmp/not-codex-desktop",),
                environment={"DISPLAY": ":1"},
            )

            result = find_app_processes(self.native, proc)

        self.assertEqual([process.pid for process in result], [300])

    def test_racing_or_incomplete_process_entries_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            (proc / "400").mkdir()
            (proc / "not-a-pid").mkdir()

            result = find_app_processes(self.native, proc)

        self.assertEqual(result, [])

    def test_appimage_matches_only_main_executable_in_its_runtime_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            valid = (
                "/home/deck/.cache/chatgpt-runtime/run.A1b2/"
                "appimage_extracted_deadbeef/opt/codex-desktop/ChatGPT"
            )
            self._process(
                proc,
                500,
                executable=valid,
                cmdline=(valid, "--class=chatgpt-community-appimage"),
                environment={"DISPLAY": ":7"},
            )
            self._process(
                proc,
                501,
                executable=valid.replace("ChatGPT", "browser_crashpad_handler"),
                cmdline=("browser_crashpad_handler",),
                environment={"DISPLAY": ":7"},
            )
            lookalike = "/tmp/run.A1b2/appimage_extracted_deadbeef/opt/codex-desktop/ChatGPT"
            self._process(
                proc,
                502,
                executable=lookalike,
                cmdline=(lookalike,),
                environment={"DISPLAY": ":7"},
            )

            result = find_app_processes(self.appimage, proc)

        self.assertEqual([process.pid for process in result], [500])
        self.assertEqual(result[0].executable, valid)

    def test_appimage_rejects_electron_child_processes_using_main_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            executable = (
                "/home/deck/.cache/chatgpt-runtime/run.A1b2/"
                "appimage_extracted_deadbeef/opt/codex-desktop/ChatGPT"
            )
            for offset, role in enumerate(("renderer", "gpu-process", "utility")):
                self._process(
                    proc,
                    600 + offset,
                    executable=executable,
                    cmdline=(executable, f"--type={role}"),
                    environment={"DISPLAY": ":7"},
                )
            self._process(
                proc,
                603,
                executable=executable,
                cmdline=(executable, "--class=chatgpt-community-appimage"),
                environment={"DISPLAY": ":7"},
            )

            result = find_app_processes(self.appimage, proc)

        self.assertEqual([process.pid for process in result], [603])


if __name__ == "__main__":
    unittest.main()
