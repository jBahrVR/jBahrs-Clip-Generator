import sys
import os
from unittest.mock import patch, mock_open

from config_manager import get_default_config, save_config, CONFIG_FILE

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

@patch('config_manager.json.dump')
@patch('config_manager.os.chmod')
@patch('config_manager.os.fdopen')
@patch('config_manager.os.open')
def test_save_config_content(mock_os_open, mock_os_fdopen, mock_os_chmod, mock_json_dump):
    # Setup mock returns
    mock_os_open.return_value = 3  # Dummy file descriptor
    mock_file = mock_open()()
    mock_os_fdopen.return_value.__enter__.return_value = mock_file

    # Create a dummy configuration to save
    test_config = {
        "test_key": "test_value",
        "nested": {"key": 123}
    }

    # Call the function being tested
    save_config(test_config)

    # Verify os.open was called with correct arguments
    mock_os_open.assert_called_once_with(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    # Verify os.fdopen was called correctly
    mock_os_fdopen.assert_called_once_with(3, 'w')

    # Verify json.dump was called with the correct dictionary and file object
    mock_json_dump.assert_called_once_with(test_config, mock_file, indent=4)

    # Verify os.chmod was called
    mock_os_chmod.assert_called_once_with(CONFIG_FILE, 0o600)

    print("All tests for test_save_config_content passed!")

if __name__ == "__main__":
    test_get_default_config()
    test_save_config_permissions()
    test_save_config_content()
