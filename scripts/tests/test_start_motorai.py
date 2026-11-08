import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.start_motorai import (
    BACKEND_URL,
    FRONTEND_URL,
    Launcher,
    StartupError,
    api_identity,
)

HEALTH = json.dumps(
    {"status": "ok", "persistence": "postgresql", "llm_configured": False}
)


class LauncherTests(unittest.TestCase):
    @patch("scripts.start_motorai.webbrowser.open", return_value=True)
    @patch("scripts.start_motorai.get", return_value=HEALTH)
    @patch("scripts.start_motorai.api_identity", return_value=True)
    @patch("scripts.start_motorai.listening", return_value=True)
    def test_repeated_launch_reuses_services_and_opens_real_app(
        self, ports, identity, get, browser
    ):
        launcher = Launcher()
        with (
            patch.object(launcher, "frontend_identity", return_value=True),
            patch.object(launcher, "start_process") as spawn,
        ):
            self.assertTrue(launcher.run()["ready"])
            self.assertTrue(launcher.run()["ready"])
        spawn.assert_not_called()
        self.assertEqual(browser.call_count, 2)
        browser.assert_called_with(FRONTEND_URL + "/", new=2)

    @patch("scripts.start_motorai.api_identity", return_value=False)
    @patch("scripts.start_motorai.listening", return_value=True)
    def test_occupied_backend_port_is_not_replaced(self, ports, identity):
        launcher = Launcher()
        with (
            patch.object(launcher, "start_process") as spawn,
            self.assertRaisesRegex(StartupError, "8002.*Nothing was stopped"),
        ):
            launcher.run(open_browser=False)
        spawn.assert_not_called()

    @patch("scripts.start_motorai.get", return_value=None)
    @patch("scripts.start_motorai.api_identity", return_value=True)
    @patch("scripts.start_motorai.listening", return_value=True)
    def test_database_failure_does_not_start_frontend_or_open_browser(
        self, ports, identity, get
    ):
        launcher = Launcher()
        with (
            patch.object(launcher, "start_process") as spawn,
            patch("scripts.start_motorai.webbrowser.open") as browser,
            self.assertRaisesRegex(StartupError, "PostgreSQL"),
        ):
            launcher.run()
        spawn.assert_not_called()
        browser.assert_not_called()

    @patch("scripts.start_motorai.get", return_value=HEALTH)
    @patch("scripts.start_motorai.api_identity", return_value=True)
    @patch("scripts.start_motorai.listening", return_value=True)
    def test_occupied_frontend_port_is_not_replaced(self, ports, identity, get):
        launcher = Launcher()
        with (
            patch.object(launcher, "frontend_identity", return_value=False),
            patch.object(launcher, "start_process") as spawn,
            self.assertRaisesRegex(StartupError, "5174.*Nothing was stopped"),
        ):
            launcher.run(open_browser=False)
        spawn.assert_not_called()

    @patch("scripts.start_motorai.get", return_value=HEALTH)
    @patch("scripts.start_motorai.listening", return_value=False)
    def test_cold_start_uses_existing_environments_and_preserves_config(
        self, ports, get
    ):
        with tempfile.TemporaryDirectory(
            prefix="MotorAI project with spaces "
        ) as folder:
            root = Path(folder)
            files = [
                ".venv/Scripts/python.exe",
                "backend/.env",
                "frontend/node_modules/vite/bin/vite.js",
                ".local-tools/node-v24.22.2-win-x64/node.exe",
            ]
            for filename in files:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original local fixture", encoding="utf-8")
            launcher = Launcher(root)
            with (
                patch.object(launcher, "wait_until"),
                patch.object(launcher, "start_process", return_value=Mock()) as spawn,
            ):
                self.assertTrue(launcher.run(open_browser=False)["ready"])
            self.assertEqual(spawn.call_count, 2)
            backend, frontend = spawn.call_args_list
            self.assertEqual(backend.args[0], [root / files[0], "-m", "app"])
            self.assertEqual(backend.args[1], root / "backend")
            self.assertEqual(frontend.args[1], root / "frontend")
            self.assertIn("--strictPort", frontend.args[0])
            self.assertEqual(frontend.args[3]["API_PROXY_TARGET"], BACKEND_URL)
            self.assertEqual(frontend.args[3]["VITE_API_BASE_URL"], "/api/v1")
            self.assertEqual(
                (root / "backend/.env").read_text(), "original local fixture"
            )

    @patch(
        "scripts.start_motorai.get",
        side_effect=[HEALTH, '{"status":"ok","persistence":"memory"}'],
    )
    @patch("scripts.start_motorai.api_identity", return_value=True)
    @patch("scripts.start_motorai.listening", return_value=True)
    def test_wrong_proxy_does_not_open_a_disconnected_or_mock_app(
        self, ports, identity, get
    ):
        launcher = Launcher()
        with (
            patch.object(launcher, "frontend_identity", return_value=True),
            patch("scripts.start_motorai.webbrowser.open") as browser,
            self.assertRaisesRegex(StartupError, "proxy configuration"),
        ):
            launcher.run()
        browser.assert_not_called()

    def test_identity_requires_expected_title_and_routes(self):
        for payload in [None, "not json", "[]", '{"info":{"title":"AI Golf Coach"}}']:
            with (
                self.subTest(payload=payload),
                patch("scripts.start_motorai.get", return_value=payload),
            ):
                self.assertFalse(api_identity(BACKEND_URL))


if __name__ == "__main__":
    unittest.main()
