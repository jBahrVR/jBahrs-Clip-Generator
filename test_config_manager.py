import sys
import os

from config_manager import get_default_config

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

if __name__ == "__main__":
    test_get_default_config()
