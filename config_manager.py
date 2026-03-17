import os
import json
import shutil

def get_app_data_path():
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = "."
    config_dir = os.path.join(str(app_data), "jBahrsClipGenerator")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir

def get_config_path():
    return os.path.join(get_app_data_path(), "config.json")

CONFIG_FILE = get_config_path()
OLD_LOCAL_CONFIG = "config.json"

def get_default_config():
    return {
        "youtube": {"channel_id": ""},
        "twitch": {"username": ""},
        "openai": {
            "api_key": "", 
            "chat_model": "gpt-4o", 
            "whisper_model": "base",
            "base_url": ""
        },
        "anthropic": {
            "api_key": ""
        },
        "xai": {
            "api_key": ""
        },
        "google": {
            "api_key": ""
        },
        "integrations": {
            "discord_webhook": ""
        },
        "settings": {
            "download_quality": "Best", 
            "download_dir": "", 
            "clips_dir": "",
            "auth_browser": "None",
            "vr_stabilization": False,
            "vertical_export": False,
            "vertical_mode": "Standard Center Crop",
            "crop_x": "0",
            "crop_y": "0",
            "crop_w": "400",
            "crop_h": "225",
            "hardware_encoding": False,
            "audio_downmix": True,
            "audio_peak_detection": True,
            "combat_detection": True
        },
        "prompts": {
            "active_profile": "Omni-Genre Broad Net", 
            "profiles": {
                "Omni-Genre Broad Net": (
                    "You are the Lead Content Strategist for a viral gaming channel. You are analyzing a chunk of a raw stream transcript. "
                    "Each line starts with a timestamp and a loudness level, like [LOUDNESS: 60%] [14.5s - 18.2s]. Use these exact numbers for your start_time and end_time.\n\n"
                    "### THE 'CLIP THAT' OVERRIDE (CRITICAL)\n"
                    "If anyone explicitly says 'clip it', 'clip that', or 'that's a clip', you MUST extract it.\n"
                    "- Set the `end_time` right after the command is spoken.\n"
                    "- Dynamically look backward (up to 90 seconds) to find the start of the action for the `start_time`.\n"
                    "- Give this an automatic virality_score of 10.\n\n"
                    "### THE REALITY OF GAMING & VR TRANSCRIPTS (READ CAREFULLY)\n"
                    "Gameplay transcripts often look incredibly boring in plain text. A player quietly saying 'wow', 'nice', or whispering 'what is that' might actually be them witnessing an insane visual glitch, hitting a crazy shot, or staring at a terrifying monster. Do not judge the gameplay purely on how 'literary' the text sounds.\n\n"
                    "**CRITICAL NEW TOOLS:**\n"
                    "- [LOUDNESS: XX%]: A metric on every line. A sudden spike from 10% to 90% during silence is almost always a jump scare, a massive gunfight, or a chaotic VR moment. A sustained 100% loudness means someone is screaming or laughing hysterically.\n"
                    "- [ACTION: COMBAT]: If you see this tag, it means the audio analyzer has detected rapid, percussive transients characteristic of gunfire or explosions. Even if the player is quiet, this indicates an intense action sequence is happening.\n"
                    "### VIRAL GAMING ARCHETYPES TO LOOK FOR\n"
                    "1. The Jump Scare (Horror): Long periods of eerie silence (Low Loudness) that violently explodes into panic, rapid cursing, or screams (100% Loudness).\n"
                    "2. Paranoia & Bargaining (Horror): Hilarious pleading with an in-game monster to let them live, terrified heavy breathing, or hyper-fixating on a harmless sound.\n"
                    "3. The '1vX Clutch' (FPS): Dead silence and hyper-focus, short tactical callouts, ending in a massive release of tension, screaming, or teammates going wild.\n"
                    "4. The Kill Streak / Chaos (FPS): Rapid-fire communication ('one dead', 'reloading'), heavy breathing, or overwhelming auditory chaos over the sound of continuous gunfire.\n"
                    "5. The Comedic Banter (Social): Friends arguing over trivial things, roasting each other, or telling a weird story that has nothing to do with the game.\n"
                    "6. The Out-of-Context Gold (Social): A player saying something that sounds hilarious, wildly inappropriate, or absurd without context.\n"
                    "7. The Physical Toll (High-Immersion/VR): Grunting, physical exhaustion, complaining about real-world physical space ('my wall!'), or getting tangled up during a frantic moment.\n\n"
                    "### CLIP STRUCTURE & QUALITY CONTROL\n"
                    "- Duration: STRICTLY between 15 and 90 seconds. Find natural pauses in speech to start and end the clip.\n"
                    "- Strict Quality: Rank clips 1-10. Because text lacks visual context, lower your standards slightly. You must extract ANY clip that scores a 6 or higher. \n\n"
                    "### FORMATTING INSTRUCTIONS\n"
                    "Output STRICTLY valid JSON with no markdown. Your output must be an object with a 'clips' array. \n"
                    "There is NO limit to the number of clips you can extract; find as many as you deem viral! \n"
                    "Each clip object in the array must contain exactly these 4 fields:\n"
                    "1. 'start_time' (float)\n"
                    "2. 'end_time' (float)\n"
                    "3. 'virality_score' (1-10)\n"
                    "4. 'reasoning' (A mandatory 1-3 sentence explanation. Mention Loudness Spikes, Jump Scares, or Banter.)\n"
                )
            }
        },
        "auto_scheduler": {
            "platform": "YouTube", 
            "video_type": "Livestreams Only",
            "target_orientation": "Horizontal Only",
            "lookback_days": "7 Days",
            "check_interval": "Every 4 Hours",
            "auto_prompt_profile": "Omni-Genre Broad Net"
        }
    }

def load_config():
    if os.path.exists(OLD_LOCAL_CONFIG) and not os.path.exists(CONFIG_FILE):
        try:
            shutil.move(OLD_LOCAL_CONFIG, CONFIG_FILE)
        except Exception:
            pass 

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
            
            # Inject new settings if they don't exist in saved config
            settings = cfg.setdefault("settings", {})
            settings.setdefault("hardware_encoding", False)
            settings.setdefault("audio_downmix", True)
            settings.setdefault("audio_peak_detection", True)
            settings.setdefault("combat_detection", True)
            
            openai_cfg = cfg.setdefault("openai", {})
            openai_cfg.setdefault("base_url", "")
            
            cfg.setdefault("anthropic", {"api_key": ""})
            cfg.setdefault("xai", {"api_key": ""})
            cfg.setdefault("integrations", {"discord_webhook": ""})
            
            # MIGRATION UPDATE: Force update the default Omni-Genre prompt if they have the old version
            prompts = cfg.setdefault("prompts", {})
            profiles = prompts.setdefault("profiles", {})
            default_prompts = get_default_config()["prompts"]
            
            if "Omni-Genre Broad Net" not in profiles:
                profiles["Omni-Genre Broad Net"] = default_prompts["profiles"]["Omni-Genre Broad Net"] # type: ignore
                prompts.setdefault("active_profile", "Omni-Genre Broad Net")
            else:
                old_prompt = profiles["Omni-Genre Broad Net"]
                if "LOUDNESS: XX%" not in old_prompt or "[ACTION: COMBAT]" not in old_prompt:
                     profiles["Omni-Genre Broad Net"] = default_prompts["profiles"]["Omni-Genre Broad Net"] # type: ignore
            
            return cfg
            
    # Default Config
    return get_default_config()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)