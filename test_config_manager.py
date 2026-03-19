import sys
import os
import json
from unittest.mock import patch, mock_open, MagicMock

from config_manager import get_default_config, save_config, load_config, CONFIG_FILE, OLD_LOCAL_CONFIG

def test_get_default_config():
    config = get_default_config()

    # Assert that the returned object is a dictionary
    assert isinstance(config, dict), "config should be a dictionary"

    # Expected top-level keys
    expected_keys = [
        "youtube", "twitch", "openai", "anthropic", "xai",
        "google", "integrations", "settings", "prompts", "auto_scheduler"
    ]
    for key in expected_keys:
        assert key in config, f"Missing key '{key}' in default config"

    # Assert specific default values inside these nested dictionaries
    assert config["youtube"]["channel_id"] == "", "Default youtube channel_id should be empty"
    assert config["twitch"]["username"] == "", "Default twitch username should be empty"

    assert config["openai"]["api_key"] == "", "Default openai api_key should be empty"
    assert config["openai"]["chat_model"] == "gpt-4o", "Default openai chat_model should be 'gpt-4o'"
    assert config["openai"]["whisper_model"] == "base", "Default openai whisper_model should be 'base'"
    assert config["openai"]["base_url"] == "", "Default openai base_url should be empty"

    assert config["anthropic"]["api_key"] == "", "Default anthropic api_key should be empty"
    assert config["xai"]["api_key"] == "", "Default xai api_key should be empty"
    assert config["google"]["api_key"] == "", "Default google api_key should be empty"

    assert config["settings"]["download_quality"] == "Best", "Default download_quality should be 'Best'"

    assert config["prompts"]["active_profile"] == "Omni-Genre Broad Net", "Default active_profile should be 'Omni-Genre Broad Net'"

    assert config["auto_scheduler"]["platform"] == "YouTube", "Default auto_scheduler platform should be 'YouTube'"

    print("All tests for get_default_config passed!")

def test_save_config_permissions():
    config = get_default_config()

    # Save the config
    save_config(config)

    # Check that the file exists
    assert os.path.exists(CONFIG_FILE), "Config file was not created"

    # Check file permissions
    file_stat = os.stat(CONFIG_FILE)
    mode = file_stat.st_mode

    # Mask out everything except the owner permissions
    owner_permissions = mode & 0o777

    # The permissions should be 0o600 (-rw-------)
    assert owner_permissions == 0o600, f"Expected permissions 0o600, but got {oct(owner_permissions)}"

    print("All tests for test_save_config_permissions passed!")

def test_load_config_no_file():
    with patch('os.path.exists', return_value=False):
        config = load_config()
        assert config == get_default_config(), "Should return default config when no file exists"
    print("Test test_load_config_no_file passed!")

def test_load_config_migration():
    def mock_exists(path):
        if path == OLD_LOCAL_CONFIG:
            return True
        if path == CONFIG_FILE:
            return False
        return False

    with patch('os.path.exists', side_effect=mock_exists), \
         patch('shutil.move') as mock_move, \
         patch('builtins.open', mock_open(read_data='{}')):
        config = load_config()
        mock_move.assert_called_once_with(OLD_LOCAL_CONFIG, CONFIG_FILE)
    print("Test test_load_config_migration passed!")

def test_load_config_migration_exception():
    def mock_exists(path):
        if path == OLD_LOCAL_CONFIG:
            return True
        if path == CONFIG_FILE:
            return False
        return False

    with patch('os.path.exists', side_effect=mock_exists), \
         patch('shutil.move', side_effect=Exception("Migration Failed")) as mock_move, \
         patch('builtins.print') as mock_print, \
         patch('builtins.open', mock_open(read_data='{}')):
        config = load_config()
        mock_move.assert_called_once_with(OLD_LOCAL_CONFIG, CONFIG_FILE)
        mock_print.assert_called_with("Failed to migrate old config file: Migration Failed")
    print("Test test_load_config_migration_exception passed!")

def test_load_config_invalid_json():
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data='{invalid_json: true}')), \
         patch('builtins.print') as mock_print:
        config = load_config()
        assert config == get_default_config(), "Should return default config on invalid JSON"
        mock_print.assert_called_once()
        assert "Failed to decode config file:" in mock_print.call_args[0][0]
    print("Test test_load_config_invalid_json passed!")


if __name__ == "__main__":
    test_get_default_config()
    test_save_config_permissions()
    test_load_config_no_file()
    test_load_config_migration()
    test_load_config_migration_exception()
    test_load_config_invalid_json()
