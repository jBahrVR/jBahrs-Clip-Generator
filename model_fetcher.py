"""
Dynamic AI Model Discovery and Caching Engine for jBahr's Clip Generator.
Provides curated, ideal model discovery across Google GenAI, OpenAI, Anthropic,
xAI, DeepSeek, and OpenRouter with persistent local caching.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

import config_manager

logger = logging.getLogger("model_fetcher")

CACHE_FILENAME = "models_cache.json"

# Curated, ideal models specifically suited for VOD transcript analysis and clip extraction
BASELINE_MODELS = [
    # Google Gemini (Best Speed, Large Context & Free Tier)
    "gemini-3.6-flash",
    "gemini-3.6-pro",
    "gemini-flash-latest",

    # OpenAI (Industry Standard)
    "gpt-4o",
    "gpt-4o-mini",
    "o3-mini",

    # Anthropic (Nuanced Reasoning & Instruction Following)
    "claude-3-7-sonnet-latest",
    "claude-3-5-haiku-latest",

    # xAI (Gaming Dialogue & Banter)
    "grok-2-latest",
    "grok-beta",

    # DeepSeek (Ultra Cost-Effective & Accurate JSON)
    "deepseek-chat",
    "deepseek-reasoner",

    # OpenRouter (Multi-Provider Aggregator)
    "openrouter/deepseek/deepseek-r1",
    "openrouter/google/gemini-3.6-flash",
    "openrouter/meta-llama/llama-3.3-70b-instruct"
]


def get_cache_path() -> str:
    """Returns absolute path to the local model cache JSON file."""
    app_data = config_manager.get_app_data_path()
    return os.path.join(app_data, CACHE_FILENAME)


def load_cached_models() -> List[str]:
    """Loads cached models from disk if file exists and is valid."""
    cache_file = get_cache_path()
    if not os.path.exists(cache_file):
        return []
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw = []
            if isinstance(data, dict) and "models" in data:
                raw = [m for m in data["models"] if isinstance(m, str) and m.strip()]
            elif isinstance(data, list):
                raw = [m for m in data if isinstance(m, str) and m.strip()]

            # If cache has old bloated list (>25 models), invalidate it
            if len(raw) > 25:
                return []
            return raw
    except Exception as e:
        logger.warning(f"Could not load cached models from {cache_file}: {e}")
    return []


def save_cached_models(models: List[str]) -> None:
    """Persists fetched models to local disk cache."""
    if not models:
        return
    cache_file = get_cache_path()
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "models": models
            }, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed saving models cache to {cache_file}: {e}")


def fetch_google_models(api_key: str) -> List[str]:
    """
    Dynamically queries Google GenAI SDK and selects only the ideal production models
    for transcript processing, discarding internal experimental/tool/audio variants.
    """
    if not api_key or not api_key.strip():
        return []
    ideal: List[str] = []
    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())
        available_names = set()
        for m in client.models.list():
            raw_name = m.name or ""
            name = raw_name.split("/", 1)[-1] if "/" in raw_name else raw_name
            available_names.add(name.lower())

        # Curated priority candidates for Gemini
        priority_candidates = [
            "gemini-3.6-flash",
            "gemini-3.6-pro",
            "gemini-flash-latest",
            "gemini-pro-latest",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
        ]
        for candidate in priority_candidates:
            if candidate.lower() in available_names:
                ideal.append(candidate)

        # Cap at top 3 ideal options
        return ideal[:3]
    except Exception as e:
        logger.warning(f"Error fetching Google models: {e}")
    return ideal


def fetch_openai_models(api_key: str, base_url: str = "") -> List[str]:
    """
    Dynamically queries OpenAI or compatible endpoint, returning top ideal options.
    """
    if not api_key or not api_key.strip():
        return []
    ideal: List[str] = []
    try:
        from openai import OpenAI
        client_kwargs: Dict[str, Any] = {"api_key": api_key.strip()}
        if base_url and base_url.strip():
            client_kwargs["base_url"] = base_url.strip()
        client = OpenAI(**client_kwargs)
        available_ids = set()
        for m in client.models.list():
            m_id = getattr(m, "id", "")
            if m_id:
                available_ids.add(m_id.lower())

        if base_url and base_url.strip():
            # For custom endpoints (DeepSeek / OpenRouter), pick top chat/reasoner models
            for candidate in ["deepseek-chat", "deepseek-reasoner", "deepseek-v3", "deepseek-r1"]:
                if candidate in available_ids:
                    ideal.append(candidate)
            if not ideal:
                for m_id in available_ids:
                    if not any(x in m_id for x in ["embedding", "tts", "image", "audio"]):
                        ideal.append(m_id)
                        if len(ideal) >= 3:
                            break
        else:
            # Standard OpenAI priority
            for candidate in ["gpt-4o", "gpt-4o-mini", "o3-mini", "o1"]:
                if candidate in available_ids:
                    ideal.append(candidate)

        return ideal[:3]
    except Exception as e:
        logger.warning(f"Error fetching OpenAI/Custom models: {e}")
    return ideal


def fetch_anthropic_models(api_key: str) -> List[str]:
    """Dynamically queries Anthropic API and selects top ideal Claude models."""
    if not api_key or not api_key.strip():
        return []
    ideal: List[str] = []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key.strip())
        available_ids = {getattr(m, "id", "").lower() for m in client.models.list()}

        for candidate in ["claude-3-7-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"]:
            if candidate in available_ids:
                ideal.append(candidate)
        return ideal[:2]
    except Exception as e:
        logger.warning(f"Error fetching Anthropic models: {e}")
    return ideal


def fetch_xai_models(api_key: str) -> List[str]:
    """Dynamically queries xAI and selects top ideal Grok models."""
    if not api_key or not api_key.strip():
        return []
    ideal: List[str] = []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key.strip(), base_url="https://api.x.ai/v1")
        available_ids = {getattr(m, "id", "").lower() for m in client.models.list()}

        for candidate in ["grok-2-latest", "grok-beta"]:
            if candidate in available_ids:
                ideal.append(candidate)
        return ideal[:2]
    except Exception as e:
        logger.warning(f"Error fetching xAI models: {e}")
    return ideal


def fetch_openrouter_public_models(timeout: float = 3.0) -> List[str]:
    """
    Returns curated top 3 OpenRouter models suitable for highlight extraction.
    """
    return [
        "openrouter/deepseek/deepseek-r1",
        "openrouter/google/gemini-3.6-flash",
        "openrouter/meta-llama/llama-3.3-70b-instruct"
    ]


def fetch_all_dynamic_models(
    config: dict,
    active_keys: Optional[Dict[str, str]] = None,
    current_selection: str = ""
) -> List[str]:
    """
    Main aggregator: returns a curated list of ~12-15 ideal models across all providers.
    Places the user's active/configured provider models at the top, followed by other providers.
    """
    keys = active_keys or {}
    google_key = keys.get("google") or config.get("google", {}).get("api_key", "").strip()
    openai_key = keys.get("openai") or config.get("openai", {}).get("api_key", "").strip()
    openai_base = keys.get("base_url") or config.get("openai", {}).get("base_url", "").strip()
    anthropic_key = keys.get("anthropic") or config.get("anthropic", {}).get("api_key", "").strip()
    grok_key = keys.get("xai") or config.get("xai", {}).get("api_key", "").strip()

    # Discover live from configured providers
    live_google = fetch_google_models(google_key) if google_key else []
    live_openai = fetch_openai_models(openai_key, openai_base) if (openai_key or openai_base) else []
    live_anthropic = fetch_anthropic_models(anthropic_key) if anthropic_key else []
    live_grok = fetch_xai_models(grok_key) if grok_key else []

    seen = set()
    ordered_list: List[str] = []

    def add_model(m: str):
        cleaned = m.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered_list.append(cleaned)

    # 1. Current user selection always stays at the top
    if current_selection:
        add_model(current_selection)

    # 2. Live authenticated provider models
    for m in live_google:
        add_model(m)
    for m in live_openai:
        add_model(m)
    for m in live_anthropic:
        add_model(m)
    for m in live_grok:
        add_model(m)

    # 3. Add curated baseline models for any unconfigured or remaining providers
    for m in BASELINE_MODELS:
        add_model(m)

    # Persist updated clean list to cache
    save_cached_models(ordered_list)

    return ordered_list
