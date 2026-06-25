# src/settings_manager.py
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "model_url": "http://10.164.224.226:1234/v1",
    "model_name": "qwen/qwen3-vl-8b",
    "big_model_name": "eva-qwen2.5-14b-v0.2"
}

def load_settings():
    """Загружает настройки из файла или возвращает значения по умолчанию."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    """Сохраняет настройки в файл."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_model_url():
    return load_settings().get("model_url", DEFAULT_SETTINGS["model_url"])

def get_model_name():
    return load_settings().get("model_name", DEFAULT_SETTINGS["model_name"])

def get_big_model_name():
    return load_settings().get("big_model_name", DEFAULT_SETTINGS["big_model_name"])