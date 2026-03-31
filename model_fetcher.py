import os
import logging
from openai import OpenAI
import anthropic
import google.generativeai as genai

# Setup logging
logger = logging.getLogger("model_fetcher")

# Curated list of "main" models for each provider
MAIN_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini", "gpt-4-turbo"],
    "anthropic": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
    "google": [
        "gemini-2.5-flash", "gemini-2.5-pro", 
        "gemini-3.1-pro", "gemini-3-flash", 
        "gemini-2.0-flash"
    ],
    "xai": ["grok-2-latest", "grok-2-mini"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"]
}

# Keywords for filtering common chat models (if not using whitelisted-only)
INCLUDE_KEYWORDS = [
    "gpt-4", "gpt-3.5", "claude-3", "claude-2", "gemini", 
    "grok", "llama", "deepseek", "mistral", "mixtral", 
    "command-r", "phi-3", "qwen", "perplex"
]

EXCLUDE_KEYWORDS = [
    "embedding", "vision-only", "tts", "whisper", "dall-e", 
    "moderation", "audio-only", "edit", "search"
]

def is_chat_model(model_id):
    """Filters for models that are likely to be suitable for chat/reasoning."""
    model_id_lower = model_id.lower()
    
    # Check for exclusion keywords first
    for kw in EXCLUDE_KEYWORDS:
        if kw in model_id_lower:
            return False
            
    # Check for inclusion keywords
    for kw in INCLUDE_KEYWORDS:
        if kw in model_id_lower:
            return True
            
    return False

def fetch_openai_models(api_key, base_url=None):
    """Fetches models from OpenAI or an OpenAI-compatible provider (like OpenRouter)."""
    if not api_key:
        return []
        
    try:
        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
            
        client = OpenAI(**client_args)
        models_data = client.models.list()
        
        provider_key = "deepseek" if base_url and "deepseek" in base_url.lower() else "openai"
        whitelist = MAIN_MODELS.get(provider_key, MAIN_MODELS["openai"])
        
        # OpenRouter/OpenAI-compatible models usually have 'id'
        model_ids = [m.id for m in models_data]
        
        # Filter: only if it's in our main list OR if it's a chat model (fallback)
        # We'll stick to ONLY the main list if whitelist yields results
        filtered = [m for m in model_ids if m in whitelist]
        if not filtered:
             filtered = [m for m in model_ids if is_chat_model(m)]
        return filtered
    except Exception as e:
        logger.error(f"Error fetching OpenAI models: {e}")
        return []

def fetch_anthropic_models(api_key):
    """Fetches models from Anthropic."""
    if not api_key:
        return []
        
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Anthropic added the models.list() method recently
        models_data = client.models.list()
        # Anthropic model objects have an 'id'
        model_ids = [m.id for m in models_data]
        
        whitelist = MAIN_MODELS["anthropic"]
        filtered = [m for m in model_ids if m in whitelist]
        
        if not filtered:
            # Fallback for dynamic aliases
            filtered = [m for m in model_ids if is_chat_model(m)]
            
        return filtered if filtered else whitelist
    except Exception as e:
        logger.error(f"Error fetching Anthropic models: {e}")
        return MAIN_MODELS["anthropic"]

def fetch_google_models(api_key):
    """Fetches models from Google Gemini."""
    if not api_key:
        return []
        
    try:
        genai.configure(api_key=api_key)
        models_data = genai.list_models()
        # Filter for models that support generating content
        model_ids = [m.name for m in models_data if "generateContent" in m.supported_generation_methods]
        clean_ids = [m.replace("models/", "") for m in model_ids]
        
        whitelist = MAIN_MODELS["google"]
        # Only return models that are in our whitelist to avoid the "dozens of experimental" clutter
        filtered = [m for m in clean_ids if m in whitelist]
        
        # fallback to minimal set if nothing found but key is valid
        return filtered if filtered else whitelist
    except Exception as e:
        logger.error(f"Error fetching Google models: {e}")
        return []

def fetch_xai_models(api_key):
    """Fetches models from Grok / xAI."""
    if not api_key:
        return []
        
    models = fetch_openai_models(api_key, base_url="https://api.x.ai/v1")
    return [m for m in models if m in MAIN_MODELS["xai"]] or MAIN_MODELS["xai"]

def fetch_all_available_models(config):
    """Orchestrates model fetching from all configured providers."""
    all_models = []
    
    # 1. OpenAI / OpenRouter / DeepSeek
    openai_key = config.get("openai", {}).get("api_key", "").strip()
    openai_base_url = config.get("openai", {}).get("base_url", "").strip()
    if openai_key:
        all_models.extend(fetch_openai_models(openai_key, openai_base_url))
        
    # 2. Anthropic
    anthropic_key = config.get("anthropic", {}).get("api_key", "").strip()
    if anthropic_key:
        all_models.extend(fetch_anthropic_models(anthropic_key))
        
    # 3. Google Gemini
    google_key = config.get("google", {}).get("api_key", "").strip()
    if google_key:
        all_models.extend(fetch_google_models(google_key))
        
    # 4. Grok / xAI
    xai_key = config.get("xai", {}).get("api_key", "").strip()
    if xai_key:
        all_models.extend(fetch_xai_models(xai_key))
        
    # Remove duplicates and sort
    seen_models = set()
    unique_models = []
    for m in all_models:
        if m not in seen_models:
            unique_models.append(m)
            seen_models.add(m)
            
    # Default fallback if NO keys are provided (show all main ones for awareness)
    if not unique_models:
        for provider_models in MAIN_MODELS.values():
            for m in provider_models:
                if m not in seen_models:
                    unique_models.append(m)
                    seen_models.add(m)

    return sorted(unique_models)
