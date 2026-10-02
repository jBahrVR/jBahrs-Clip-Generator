import os
import stat
import json
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass
class YoutubeConfig:
    channel_id: str = ""

@dataclass
class TwitchConfig:
    username: str = ""

@dataclass
class OpenAIConfig:
    api_key: str = ""
    chat_model: str = "gpt-4o"
    whisper_model: str = "base"
    whisper_language: str = "Auto-Detect"
    base_url: str = ""

@dataclass
class AnthropicConfig:
    api_key: str = ""

@dataclass
class XAIConfig:
    api_key: str = ""

@dataclass
class GoogleConfig:
    api_key: str = ""

@dataclass
class IntegrationsConfig:
    discord_webhook: str = ""

@dataclass
class SettingsConfig:
    download_quality: str = "Best"
    download_dir: str = ""
    clips_dir: str = ""
    auth_browser: str = "None"
    vr_stabilization: bool = False
    vertical_export: bool = False
    vertical_mode: str = "Standard Center Crop"
    crop_x: str = "0"
    crop_y: str = "0"
    crop_w: str = "400"
    crop_h: str = "225"
    hardware_encoding: bool = False
    audio_downmix: bool = True
    audio_peak_detection: bool = True
    combat_detection: bool = True
    burn_subtitles: bool = False
    subtitle_style: str = "Viral Yellow Highlight"
    subtitle_position: str = "Bottom Third"
    subtitle_font_size: int = 24

@dataclass
class PromptsConfig:
    active_profile: str = "Omni-Genre Broad Net"
    profiles: Dict[str, str] = field(default_factory=lambda: {
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
    })

@dataclass
class AutoSchedulerConfig:
    platform: str = "YouTube"
    video_type: str = "Livestreams Only"
    target_orientation: str = "Horizontal Only"
    lookback_days: str = "7 Days"
    check_interval: str = "Every 4 Hours"
    auto_prompt_profile: str = "Omni-Genre Broad Net"


@dataclass
class SocialConfig:
    youtube: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "client_id": "",
        "client_secret": "",
        "refresh_token": ""
    })
    tiktok: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "client_key": "",
        "client_secret": "",
        "access_token": ""
    })
    instagram: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "access_token": "",
        "user_id": ""
    })


class DictLikeSection(dict):
    def __init__(self, data_cls_inst: Any) -> None:
        self.__dict__['_dataclass'] = data_cls_inst
        super().__init__(asdict(data_cls_inst))
        
    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        if hasattr(self._dataclass, key):
            setattr(self._dataclass, key, value)
            
    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        if hasattr(self._dataclass, key):
            delattr(self._dataclass, key)
            
    def __setattr__(self, name: str, value: Any) -> None:
        if name == '_dataclass':
            self.__dict__['_dataclass'] = value
        else:
            if hasattr(self._dataclass, name):
                setattr(self._dataclass, name, value)
                super().__setitem__(name, value)
            else:
                super().__setattr__(name, value)
                
    def __getattr__(self, name: str) -> Any:
        if name == '_dataclass':
            return self.__dict__['_dataclass']
        if hasattr(self._dataclass, name):
            return getattr(self._dataclass, name)
        raise AttributeError(f"Section has no attribute '{name}'")

    def setdefault(self, key: str, default: Any = None) -> Any:
        if key not in self:
            self[key] = default
        return self[key]


class AppConfig(dict):
    def __init__(self, youtube: YoutubeConfig, twitch: TwitchConfig, openai: OpenAIConfig, 
                 anthropic: AnthropicConfig, xai: XAIConfig, google: GoogleConfig, 
                 integrations: IntegrationsConfig, settings: SettingsConfig, 
                 prompts: PromptsConfig, auto_scheduler: AutoSchedulerConfig,
                 social: Optional[SocialConfig] = None) -> None:
        self.youtube = DictLikeSection(youtube)
        self.twitch = DictLikeSection(twitch)
        self.openai = DictLikeSection(openai)
        self.anthropic = DictLikeSection(anthropic)
        self.xai = DictLikeSection(xai)
        self.google = DictLikeSection(google)
        self.integrations = DictLikeSection(integrations)
        self.settings = DictLikeSection(settings)
        self.prompts = DictLikeSection(prompts)
        self.auto_scheduler = DictLikeSection(auto_scheduler)
        self.social = DictLikeSection(social if social is not None else SocialConfig())
        
        super().__init__({
            "youtube": self.youtube,
            "twitch": self.twitch,
            "openai": self.openai,
            "anthropic": self.anthropic,
            "xai": self.xai,
            "google": self.google,
            "integrations": self.integrations,
            "settings": self.settings,
            "prompts": self.prompts,
            "auto_scheduler": self.auto_scheduler,
            "social": self.social,
        })
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "youtube": asdict(self.youtube._dataclass),
            "twitch": asdict(self.twitch._dataclass),
            "openai": asdict(self.openai._dataclass),
            "anthropic": asdict(self.anthropic._dataclass),
            "xai": asdict(self.xai._dataclass),
            "google": asdict(self.google._dataclass),
            "integrations": asdict(self.integrations._dataclass),
            "settings": asdict(self.settings._dataclass),
            "prompts": asdict(self.prompts._dataclass),
            "auto_scheduler": asdict(self.auto_scheduler._dataclass),
            "social": asdict(self.social._dataclass),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        youtube_data = data.get("youtube", {})
        twitch_data = data.get("twitch", {})
        openai_data = data.get("openai", {})
        anthropic_data = data.get("anthropic", {})
        xai_data = data.get("xai", {})
        google_data = data.get("google", {})
        integrations_data = data.get("integrations", {})
        settings_data = data.get("settings", {})
        prompts_data = data.get("prompts", {})
        auto_scheduler_data = data.get("auto_scheduler", {})
        social_data = data.get("social", {})

        return cls(
            youtube=YoutubeConfig(**{k: v for k, v in youtube_data.items() if k in YoutubeConfig.__dataclass_fields__}),
            twitch=TwitchConfig(**{k: v for k, v in twitch_data.items() if k in TwitchConfig.__dataclass_fields__}),
            openai=OpenAIConfig(**{k: v for k, v in openai_data.items() if k in OpenAIConfig.__dataclass_fields__}),
            anthropic=AnthropicConfig(**{k: v for k, v in anthropic_data.items() if k in AnthropicConfig.__dataclass_fields__}),
            xai=XAIConfig(**{k: v for k, v in xai_data.items() if k in XAIConfig.__dataclass_fields__}),
            google=GoogleConfig(**{k: v for k, v in google_data.items() if k in GoogleConfig.__dataclass_fields__}),
            integrations=IntegrationsConfig(**{k: v for k, v in integrations_data.items() if k in IntegrationsConfig.__dataclass_fields__}),
            settings=SettingsConfig(**{k: v for k, v in settings_data.items() if k in SettingsConfig.__dataclass_fields__}),
            prompts=PromptsConfig(
                active_profile=prompts_data.get("active_profile", "Omni-Genre Broad Net"),
                profiles=prompts_data.get("profiles", get_raw_default_dict()["prompts"]["profiles"])
            ),
            auto_scheduler=AutoSchedulerConfig(**{k: v for k, v in auto_scheduler_data.items() if k in AutoSchedulerConfig.__dataclass_fields__}),
            social=SocialConfig(**{k: v for k, v in social_data.items() if k in SocialConfig.__dataclass_fields__})
        )


def get_app_data_path() -> str:
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = "."
    config_dir = os.path.join(str(app_data), "jBahrsClipGenerator")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir

def get_config_path() -> str:
    return os.path.join(get_app_data_path(), "config.json")

CONFIG_FILE: str = get_config_path()
OLD_LOCAL_CONFIG: str = "config.json"

def get_raw_default_dict() -> Dict[str, Any]:
    return {
        "youtube": {"channel_id": ""},
        "twitch": {"username": ""},
        "openai": {
            "api_key": "", 
            "chat_model": "gpt-4o", 
            "whisper_model": "base",
            "whisper_language": "Auto-Detect",
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
            "combat_detection": True,
            "burn_subtitles": False,
            "subtitle_style": "Viral Yellow Highlight",
            "subtitle_position": "Bottom Third",
            "subtitle_font_size": 24
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
        },
        "social": {
            "youtube": {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "refresh_token": ""
            },
            "tiktok": {
                "enabled": False,
                "client_key": "",
                "client_secret": "",
                "access_token": ""
            },
            "instagram": {
                "enabled": False,
                "access_token": "",
                "user_id": ""
            }
        }
    }

def get_default_config() -> AppConfig:
    return AppConfig.from_dict(get_raw_default_dict())

def load_config(config_path: Optional[str] = None) -> AppConfig:
    target_file = config_path or CONFIG_FILE
    if not config_path and os.path.exists(OLD_LOCAL_CONFIG) and not os.path.exists(target_file):
        try:
            shutil.move(OLD_LOCAL_CONFIG, target_file)
        except Exception as e:
            print(f"Failed to migrate old config file: {e}")

    if os.path.exists(target_file):
        with open(target_file, 'r', encoding='utf-8') as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Failed to decode config file: {e}")
                return get_default_config()
            
            # Inject new settings if they don't exist in saved config
            settings = cfg.setdefault("settings", {})
            settings.setdefault("hardware_encoding", False)
            settings.setdefault("audio_downmix", True)
            settings.setdefault("audio_peak_detection", True)
            settings.setdefault("combat_detection", True)
            
            openai_cfg = cfg.setdefault("openai", {})
            openai_cfg.setdefault("base_url", "")
            openai_cfg.setdefault("whisper_language", "Auto-Detect")
            
            cfg.setdefault("anthropic", {"api_key": ""})
            cfg.setdefault("xai", {"api_key": ""})
            cfg.setdefault("integrations", {"discord_webhook": ""})
            cfg.setdefault("social", get_raw_default_dict()["social"])
            
            # MIGRATION UPDATE: Force update the default Omni-Genre prompt if they have the old version
            prompts = cfg.setdefault("prompts", {})
            profiles = prompts.setdefault("profiles", {})
            default_prompts = get_raw_default_dict()["prompts"]
            
            if "Omni-Genre Broad Net" not in profiles:
                profiles["Omni-Genre Broad Net"] = default_prompts["profiles"]["Omni-Genre Broad Net"] # type: ignore
                prompts.setdefault("active_profile", "Omni-Genre Broad Net")
            else:
                old_prompt = profiles["Omni-Genre Broad Net"]
                if "LOUDNESS: XX%" not in old_prompt or "[ACTION: COMBAT]" not in old_prompt:
                     profiles["Omni-Genre Broad Net"] = default_prompts["profiles"]["Omni-Genre Broad Net"] # type: ignore
            
            return AppConfig.from_dict(cfg)
            
    # Default Config
    return get_default_config()

def secure_file_permissions(file_path: str) -> None:
    """Enforces owner-only permissions on Windows NTFS via icacls and POSIX via chmod."""
    if os.name == 'nt':
        try:
            username = os.environ.get('USERNAME')
            if username:
                subprocess.run(
                    ["icacls", file_path, "/inheritance:r", "/grant:r", f"{username}:(R,W)"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
        except Exception:
            pass
    else:
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

def save_config(config: Any, config_path: Optional[str] = None) -> None:
    target_file = config_path or CONFIG_FILE
    target_dir = os.path.dirname(target_file)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    # Open file descriptor with restrictive permissions
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    mode = stat.S_IRUSR | stat.S_IWUSR

    fd = os.open(target_file, flags, mode)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        if hasattr(config, "to_dict"):
            json.dump(config.to_dict(), f, indent=4)
        else:
            json.dump(config, f, indent=4)

    # Ensure existing files have restricted permissions
    secure_file_permissions(target_file)