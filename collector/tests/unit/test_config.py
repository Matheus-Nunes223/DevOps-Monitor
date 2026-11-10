import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monitor.config import load_settings


class SettingsTests(unittest.TestCase):
    def test_environment_overrides_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(
                "database_url: postgresql://yaml.example/db\ncollect_interval_seconds: 20\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"SUPABASE_DB_URL": "postgresql://env.example/db"},
                clear=True,
            ):
                settings = load_settings(path, env_file=None)
        self.assertEqual(settings.database_url.get_secret_value(), "postgresql://env.example/db")
        self.assertEqual(settings.collect_interval_seconds, 20)

    def test_rejects_interval_shorter_than_cycle_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text(
                "database_url: postgresql://localhost/db\ncollect_interval_seconds: 5\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_settings(path, env_file=None)

    def test_defaults_do_not_contain_a_database_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text("collect_interval_seconds: 15\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    load_settings(path, env_file=None)


if __name__ == "__main__":
    unittest.main()
