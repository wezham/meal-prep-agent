import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/meal-prep-agent"


class BundledMcpContractTests(unittest.TestCase):
    def test_plugin_declares_companion_mcp_config(self):
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")

        config = json.loads((PLUGIN / ".mcp.json").read_text())
        server = config["mcpServers"]["woolworths"]
        self.assertEqual(server["command"], "uv")
        self.assertEqual(server["cwd"], ".")
        self.assertIn("--frozen", server["args"])
        self.assertIn("./mcp/bootstrap.py", server["args"])

    def test_bundled_python_project_is_complete(self):
        project = tomllib.loads((PLUGIN / "mcp/pyproject.toml").read_text())
        self.assertEqual(project["project"]["name"], "woolworths-mcp")
        self.assertEqual(project["project"]["requires-python"], ">=3.12,<3.13")

        required = (
            "mcp/uv.lock",
            "mcp/LICENSE",
            "mcp/bootstrap.py",
            "mcp/src/woolworths_mcp/__init__.py",
            "mcp/src/woolworths_mcp/client.py",
            "mcp/src/woolworths_mcp/models.py",
            "mcp/src/woolworths_mcp/server.py",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue((PLUGIN / path).is_file())

    def test_bootstrap_keeps_installer_output_off_stdout(self):
        bootstrap = (PLUGIN / "mcp/bootstrap.py").read_text()
        self.assertIn('"playwright", "install", "chromium"', bootstrap)
        self.assertIn("stdout=sys.stderr", bootstrap)
        self.assertIn("stderr=sys.stderr", bootstrap)


if __name__ == "__main__":
    unittest.main()
