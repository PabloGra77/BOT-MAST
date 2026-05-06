from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
RUNTIME_LOG_DIR = LOGS_DIR / "runtime"
DOWNLOADS_DIR = BASE_DIR / "downloads"
HC_OUTPUT_DIR = DOWNLOADS_DIR / "hc"
CHROME_DOWNLOAD_DIR = DOWNLOADS_DIR / "browser"
CONFIG_PATH = CONFIG_DIR / "config.json"
ALERTS_LOG_PATH = LOGS_DIR / "admin_alerts.log"
JOB_CONFIG_DIR = BASE_DIR / "downloads" / "runtime" / "job_configs"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_main_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_main_config(config: dict[str, Any]) -> None:
    _ensure_parent(CONFIG_PATH)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=4, ensure_ascii=False)


def _nested_get(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def get_api_key(config: dict[str, Any] | None = None) -> str:
    cfg = config if config is not None else load_main_config()
    return os.environ.get("AGENDA_API_KEY") or _nested_get(cfg, "security", "api_key", default="")


def get_secret_key(config: dict[str, Any] | None = None) -> str:
    cfg = config if config is not None else load_main_config()
    return os.environ.get("AGENDA_SECRET_KEY") or _nested_get(cfg, "security", "secret_key", default="")


def get_reset_token(config: dict[str, Any] | None = None) -> str:
    cfg = config if config is not None else load_main_config()
    return os.environ.get("AGENDA_RESET_TOKEN") or _nested_get(cfg, "security", "reset_token", default="")
