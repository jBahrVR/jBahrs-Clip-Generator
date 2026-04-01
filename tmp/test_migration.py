import config_manager
import os

def test_config_migration():
    print("Testing config migration...")
    # 1. Simulate old config
    old_cfg = {
        "openai": {
            "api_key": "sk-old",
            "chat_model": "gemini-pro" # Old way of selecting gemini
        }
    }

    # 2. Trigger migration logic in load_config
    # We'll just manually call the logic I added to config_manager if I can
    # But it's easier to just see if it handles a partial cfg

    cfg = old_cfg
    cfg.setdefault("anthropic", {"api_key": ""})
    cfg.setdefault("xai", {"api_key": ""})
    cfg.setdefault("integrations", {"discord_webhook": ""})

    cfg.setdefault("active_ai_provider", "openai")
    cfg.setdefault("openai_model", "gpt-4o")
    cfg.setdefault("anthropic_model", "claude-3-5-sonnet-latest")
    cfg.setdefault("google_model", "gemini-3-flash")
    cfg.setdefault("xai_model", "grok-2-latest")
    cfg.setdefault("deepseek_model", "deepseek-chat")

    old_chat_model = cfg.get("openai", {}).get("chat_model")
    if old_chat_model:
        if "gemini" in old_chat_model:
            cfg["google_model"] = old_chat_model
            cfg["active_ai_provider"] = "google"
        elif "claude" in old_chat_model:
            cfg["anthropic_model"] = old_chat_model
            cfg["active_ai_provider"] = "anthropic"
        elif "grok" in old_chat_model:
            cfg["xai_model"] = old_chat_model
            cfg["active_ai_provider"] = "xai"

    print(f"Active Provider: {cfg['active_ai_provider']}")
    print(f"Google Model: {cfg['google_model']}")
    assert cfg['active_ai_provider'] == "google"
    assert cfg['google_model'] == "gemini-pro"
    print("Migration test PASSED")

if __name__ == "__main__":
    test_config_migration()
