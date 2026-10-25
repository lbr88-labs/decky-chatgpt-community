import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.compatibility import VOICE_MARKERS
from backend.installations import Installation
from backend.processes import AppProcess


ROOT = Path(__file__).parents[1]


class ReleaseScriptTests(unittest.TestCase):
    def test_verifier_selects_running_appimage_bundle_and_native_fallback(self):
        spec = importlib.util.spec_from_file_location(
            "verify_installed_app", ROOT / "scripts/verify-installed-app.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        runtime_executable = (
            "/home/deck/.cache/chatgpt-runtime/run.A1/"
            "appimage_extracted_deadbeef/opt/codex-desktop/ChatGPT"
        )
        appimage = Installation.appimage(
            Path("/home/deck/.local/share/chatgpt-community-appimage"),
            Path("/home/deck/.cache/chatgpt-runtime"),
        )

        selected = module.default_app_asar(
            installation=appimage,
            processes=[AppProcess(42, runtime_executable, {})],
        )
        native = module.default_app_asar(
            installation=Installation.native(),
            processes=[],
        )

        self.assertEqual(
            selected,
            Path(runtime_executable).parent / "resources/app.asar",
        )
        self.assertEqual(native, Path("/opt/codex-desktop/resources/app.asar"))

    def test_verifier_exit_code_tracks_real_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            app_asar = Path(directory, "app.asar")
            app_asar.write_bytes(b"|".join(VOICE_MARKERS))

            compatible = subprocess.run(
                [sys.executable, "scripts/verify-installed-app.py", str(app_asar)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            app_asar.write_bytes(VOICE_MARKERS[0])
            incompatible = subprocess.run(
                [sys.executable, "scripts/verify-installed-app.py", str(app_asar)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(compatible.returncode, 0)
        self.assertIn("compatible", compatible.stdout.lower())
        self.assertEqual(incompatible.returncode, 1)
        self.assertIn("missing", incompatible.stderr.lower())

    def test_release_archive_contains_only_runtime_allowlist(self):
        build = subprocess.run(
            ["bash", "scripts/package-release.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(build.returncode, 0, build.stderr)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        archive = (
            ROOT
            / "dist-release"
            / f"decky-chatgpt-community-{package['version']}.zip"
        )
        self.assertTrue(archive.is_file())
        stable_archive = ROOT / "dist-release" / "decky-chatgpt-community.zip"
        desktop = ROOT / "dist-release" / "Install-ChatGPT-Community-Decky.desktop"
        installer = (
            ROOT / "dist-release" / "install-chatgpt-community-decky.sh"
        )
        checksums = ROOT / "dist-release" / "SHA256SUMS"
        self.assertTrue(stable_archive.is_file())
        self.assertTrue(desktop.is_file())
        self.assertTrue(installer.is_file())
        self.assertTrue(checksums.is_file())
        expected_checksum = hashlib.sha256(stable_archive.read_bytes()).hexdigest()
        self.assertEqual(
            checksums.read_text(encoding="utf-8"),
            f"{expected_checksum}  decky-chatgpt-community.zip\n",
        )

        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())

        prefix = "decky-chatgpt-community/"
        required = {
            f"{prefix}dist/index.js",
            f"{prefix}main.py",
            f"{prefix}backend/controller.py",
            f"{prefix}backend/installations.py",
            f"{prefix}backend/sessions.py",
            f"{prefix}backend/voice_controls.mjs",
            f"{prefix}plugin.json",
            f"{prefix}package.json",
            f"{prefix}README.md",
            f"{prefix}LICENSE",
        }
        self.assertTrue(required.issubset(names))
        self.assertFalse(any("node_modules" in name for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertTrue(all(name.startswith(prefix) for name in names))

    def test_local_installer_rejects_an_unexpected_home(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment["HOME"] = directory
            result = subprocess.run(
                ["bash", "scripts/install-local.sh"],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/home/deck", result.stderr)


if __name__ == "__main__":
    unittest.main()
