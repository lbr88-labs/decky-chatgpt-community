import json
import tempfile
import unittest
from pathlib import Path

from backend.installations import Installation, select_installation


class InstallationSelectionTests(unittest.TestCase):
    def _paths(self, root: Path):
        return {
            "appimage_root": root / "appimage",
            "native_launcher": root / "usr/bin/codex-desktop",
            "native_executable": root / "opt/codex-desktop/ChatGPT",
            "runtime_root": root / "cache/chatgpt-runtime",
        }

    @staticmethod
    def _executable(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n", encoding="utf-8")
        path.chmod(0o755)

    def test_prefers_complete_appimage_when_native_is_also_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            self._executable(paths["native_launcher"])
            self._executable(paths["native_executable"])
            self._executable(paths["appimage_root"] / "ChatGPT-Community.AppImage")
            self._executable(paths["appimage_root"] / "launch-appimage.sh")

            selected = select_installation(**paths)

        self.assertIsNotNone(selected)
        self.assertEqual(selected.mode, "appimage")
        self.assertEqual(selected.window_class, "chatgpt-community-appimage")
        self.assertEqual(selected.launch_executable, paths["appimage_root"] / "launch-appimage.sh")

    def test_incomplete_appimage_falls_back_to_native_package(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            self._executable(paths["native_launcher"])
            self._executable(paths["native_executable"])
            self._executable(paths["appimage_root"] / "ChatGPT-Community.AppImage")

            selected = select_installation(**paths)

        self.assertIsNotNone(selected)
        self.assertEqual(selected.mode, "native")
        self.assertEqual(selected.launch_executable, paths["native_launcher"])
        self.assertEqual(selected.window_class, "codex-desktop")

    def test_returns_none_when_neither_installation_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(select_installation(**self._paths(Path(directory))))

    def test_appimage_version_comes_from_installer_build_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self._paths(Path(directory))
            self._executable(paths["appimage_root"] / "ChatGPT-Community.AppImage")
            self._executable(paths["appimage_root"] / "launch-appimage.sh")
            (paths["appimage_root"] / "build-info.json").write_text(
                json.dumps({"upstreamLinuxPackage": {"version": "26.1021.22027"}}),
                encoding="utf-8",
            )

            selected = select_installation(**paths)

            version = selected.installed_version()

        self.assertEqual(version, "26.1021.22027")

    def test_non_object_metadata_is_treated_as_unknown_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = root / "build-info.json"
            metadata.write_text("[]", encoding="utf-8")
            installation = Installation.appimage(root, root / "runtime")

            self.assertIsNone(installation.installed_version())


if __name__ == "__main__":
    unittest.main()
