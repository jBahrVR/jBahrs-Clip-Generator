import os
import json
import stat
import shutil
import tempfile
import subprocess
import unittest
from unittest.mock import patch, mock_open

import config_manager
from config_manager import get_default_config, save_config, load_config, AppConfig


class TestConfigDefaultsAndTypes(unittest.TestCase):
    def test_get_default_config_structure(self):
        config = get_default_config()

        self.assertIsInstance(config, AppConfig)
        self.assertIsInstance(config.to_dict(), dict)

        expected_keys = [
            "youtube", "twitch", "openai", "anthropic", "xai",
            "google", "integrations", "settings", "prompts", "auto_scheduler"
        ]
        config_dict = config.to_dict()
        for key in expected_keys:
            self.assertIn(key, config_dict, f"Missing key '{key}' in default config")

        # Assert default values
        self.assertEqual(config.youtube.channel_id, "")
        self.assertEqual(config.twitch.username, "")
        self.assertEqual(config.openai.api_key, "")
        self.assertEqual(config.openai.chat_model, "gpt-4o")
        self.assertEqual(config.openai.whisper_model, "base")
        self.assertEqual(config.openai.whisper_language, "Auto-Detect")
        self.assertEqual(config.openai.base_url, "")

        self.assertEqual(config.anthropic.api_key, "")
        self.assertEqual(config.xai.api_key, "")
        self.assertEqual(config.google.api_key, "")

        self.assertEqual(config.settings.download_quality, "Best")
        self.assertEqual(config.prompts.active_profile, "Omni-Genre Broad Net")
        self.assertEqual(config.auto_scheduler.platform, "YouTube")


class TestConfigPersistenceAndMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_config_file = os.path.join(self.test_dir.name, "sandbox_config.json")
        self.test_old_config = os.path.join(self.test_dir.name, "sandbox_old_config.json")

        self.patch_config_file = patch('config_manager.CONFIG_FILE', self.test_config_file)
        self.patch_old_config = patch('config_manager.OLD_LOCAL_CONFIG', self.test_old_config)
        self.patch_config_file.start()
        self.patch_old_config.start()

    def tearDown(self):
        self.patch_config_file.stop()
        self.patch_old_config.stop()
        self.test_dir.cleanup()

    def test_save_config_creates_file_in_sandbox(self):
        config = get_default_config()
        config.openai.api_key = "test-sandbox-key"

        save_config(config)

        self.assertTrue(os.path.exists(self.test_config_file), "Config file was not created in sandbox")
        with open(self.test_config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data["openai"]["api_key"], "test-sandbox-key")

        # Test file permissions on POSIX
        if os.name != 'nt':
            file_stat = os.stat(self.test_config_file)
            owner_permissions = file_stat.st_mode & 0o777
            self.assertEqual(owner_permissions, 0o600)

    def test_load_config_no_file_returns_default(self):
        self.assertFalse(os.path.exists(self.test_config_file))
        config = load_config()
        self.assertEqual(config.to_dict(), get_default_config().to_dict())

    def test_load_config_migration(self):
        # Create old config in sandbox
        old_data = {"openai": {"api_key": "migrated-key"}}
        with open(self.test_old_config, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)

        self.assertTrue(os.path.exists(self.test_old_config))
        self.assertFalse(os.path.exists(self.test_config_file))

        config = load_config()

        self.assertEqual(config.openai.api_key, "migrated-key")
        self.assertEqual(config.openai.whisper_language, "Auto-Detect")
        self.assertTrue(os.path.exists(self.test_config_file))
        self.assertFalse(os.path.exists(self.test_old_config))

    def test_load_config_migration_exception(self):
        with open(self.test_old_config, 'w', encoding='utf-8') as f:
            f.write("{}")

        with patch('shutil.move', side_effect=Exception("Disk Full")), \
             patch('builtins.print') as mock_print:
            config = load_config()
            mock_print.assert_called_with("Failed to migrate old config file: Disk Full")
            self.assertEqual(config.to_dict(), get_default_config().to_dict())

    def test_load_config_invalid_json(self):
        with open(self.test_config_file, 'w', encoding='utf-8') as f:
            f.write("{invalid_json: true}")

        with patch('builtins.print') as mock_print:
            config = load_config()
            self.assertEqual(config.to_dict(), get_default_config().to_dict())
            mock_print.assert_called_once()
            self.assertIn("Failed to decode config file:", mock_print.call_args[0][0])

    def test_custom_config_path_support(self):
        custom_path = os.path.join(self.test_dir.name, "custom_subdir", "custom.json")
        config = get_default_config()
        config.settings.download_quality = "720p"

        save_config(config, config_path=custom_path)
        self.assertTrue(os.path.exists(custom_path))

        loaded = load_config(config_path=custom_path)
        self.assertEqual(loaded.settings.download_quality, "720p")

    @patch('subprocess.run')
    def test_secure_file_permissions_windows_calls_icacls(self, mock_run):
        with patch('os.name', 'nt'), patch.dict(os.environ, {'USERNAME': 'testuser'}):
            config_manager.secure_file_permissions("dummy_path.json")
            mock_run.assert_called_once_with(
                ["icacls", "dummy_path.json", "/inheritance:r", "/grant:r", "testuser:(R,W)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )


class TestAppConfigDataclass(unittest.TestCase):
    def test_dot_notation_read(self):
        config = get_default_config()
        self.assertEqual(config.openai.chat_model, "gpt-4o")
        self.assertEqual(config.settings.download_quality, "Best")

    def test_sync_dot_to_dict(self):
        config = get_default_config()
        config.openai.chat_model = "gpt-4-custom"
        self.assertEqual(config["openai"]["chat_model"], "gpt-4-custom")

    def test_sync_dict_to_dot(self):
        config = get_default_config()
        config["settings"]["download_quality"] = "1080p"
        self.assertEqual(config.settings.download_quality, "1080p")

    def test_attribute_error(self):
        config = get_default_config()
        with self.assertRaises(AttributeError):
            _ = config.openai.nonexistent_field

    def test_serialization(self):
        config = get_default_config()
        config.openai.api_key = "test-key"
        serialized = config.to_dict()
        self.assertEqual(serialized["openai"]["api_key"], "test-key")

        # Load back
        deserialized = config.from_dict(serialized)
        self.assertEqual(deserialized.openai.api_key, "test-key")


if __name__ == "__main__":
    unittest.main()
