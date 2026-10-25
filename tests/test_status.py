import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.installations import Installation
from backend.status import read_package_info, read_updater_status, request_update_check


class CommandRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, args, **kwargs):
        command = tuple(args)
        self.calls.append((command, kwargs))
        return self.responses[command]


class StatusTests(unittest.TestCase):
    def test_package_version_is_parsed_from_pacman(self):
        runner = CommandRunner(
            {
                ("/usr/bin/pacman", "-Q", "codex-desktop"): subprocess.CompletedProcess(
                    [], 0, "codex-desktop 2026.08.19.171554-1\n", ""
                )
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            result = read_package_info(
                runner,
                app_executable=Path(directory, "missing-ChatGPT"),
                metadata_path=Path(directory, "missing-metadata.json"),
            )

        self.assertTrue(result.installed)
        self.assertEqual(result.version, "2026.08.19.171554-1")

    def test_missing_package_is_not_an_exception(self):
        runner = CommandRunner(
            {
                ("/usr/bin/pacman", "-Q", "codex-desktop"): subprocess.CompletedProcess(
                    [], 1, "", "package 'codex-desktop' was not found"
                )
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            result = read_package_info(
                runner,
                app_executable=Path(directory, "missing-ChatGPT"),
                metadata_path=Path(directory, "missing-metadata.json"),
            )

        self.assertFalse(result.installed)
        self.assertIsNone(result.version)

    def test_verified_payload_is_used_when_decky_cannot_read_pacman_database(self):
        runner = CommandRunner(
            {
                ("/usr/bin/pacman", "-Q", "codex-desktop"): subprocess.CompletedProcess(
                    [], 1, "", "package database unavailable"
                )
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory, "ChatGPT")
            metadata = Path(directory, "linux-package-metadata.json")
            executable.write_bytes(b"official payload")
            executable.chmod(0o755)
            metadata.write_text('{"version":"26.814.41957"}', encoding="utf-8")

            result = read_package_info(
                runner,
                app_executable=executable,
                metadata_path=metadata,
            )

        self.assertTrue(result.installed)
        self.assertEqual(result.version, "26.814.41957")

    def test_updater_status_requires_a_json_object(self):
        valid = {"state": "idle", "updateAvailable": False}
        runner = CommandRunner(
            {
                (
                    "/usr/bin/codex-update-manager",
                    "status",
                    "--json",
                ): subprocess.CompletedProcess([], 0, json.dumps(valid), "")
            }
        )

        self.assertEqual(read_updater_status(runner), valid)

        invalid_runner = CommandRunner(
            {
                (
                    "/usr/bin/codex-update-manager",
                    "status",
                    "--json",
                ): subprocess.CompletedProcess([], 0, "[]", "")
            }
        )
        self.assertIsNone(read_updater_status(invalid_runner))

    def test_update_check_uses_fixed_command_and_reports_failure(self):
        command = ("/usr/bin/codex-update-manager", "check-now")
        runner = CommandRunner(
            {command: subprocess.CompletedProcess([], 2, "", "network unavailable")}
        )

        result = request_update_check(Installation.native(), runner)

        self.assertFalse(result.ok)
        self.assertIn("network unavailable", result.message)
        self.assertEqual(runner.calls[0][0], command)

    def test_appimage_update_check_never_calls_disabled_native_updater(self):
        class RejectingRunner:
            def __call__(self, *_args, **_kwargs):
                raise AssertionError("native updater must not run for AppImage")

        result = request_update_check(
            Installation.appimage(
                Path("/home/deck/.local/share/chatgpt-community-appimage"),
                Path("/home/deck/.cache/chatgpt-runtime"),
            ),
            RejectingRunner(),
        )

        self.assertTrue(result.ok)
        self.assertIn("installer", result.message.lower())


if __name__ == "__main__":
    unittest.main()
