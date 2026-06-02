from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def _resolve_base_dir() -> Path:
    """Carpeta raíz que contiene config/, logs/, downloads/, etc.

    - Ejecución normal con Python -> tres niveles arriba de este archivo.
    - Empaquetado con PyInstaller (`sys.frozen`) -> carpeta donde está el .exe,
      NO la carpeta temporal `_MEIxxxx`. Esto permite que `config.json`,
      `logs/` y `downloads/` persistan entre ejecuciones, junto al ejecutable.
    - Override por variable de entorno `BOT_BASE_DIR`.
    """
    override = os.environ.get("BOT_BASE_DIR")
    if override:
        return Path(override).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


BASE_DIR = _resolve_base_dir()
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
RUNTIME_LOG_DIR = LOGS_DIR / "runtime"
DOWNLOADS_DIR = BASE_DIR / "downloads"
HC_OUTPUT_DIR = DOWNLOADS_DIR / "hc"
CHROME_DOWNLOAD_DIR = DOWNLOADS_DIR / "browser"
CONFIG_PATH = CONFIG_DIR / "config.json"
JOB_CONFIG_DIR = BASE_DIR / "downloads" / "runtime" / "job_configs"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _bootstrap_config_from_bundle() -> None:
    """Si estamos empaquetados (PyInstaller) y NO existe `config/config.json`
    junto al .exe, copiar el config embebido (en `sys._MEIPASS/config/`) hacia
    `BASE_DIR/config/`. Esto permite distribuir el .exe SIN carpeta config:
    en el primer arranque se auto-extrae con las credenciales precargadas.
    """
    try:
        if CONFIG_PATH.exists():
            return
        meipass = getattr(sys, "_MEIPASS", None)
        if not meipass:
            return
        embebido = Path(meipass) / "config" / "config.json"
        if not embebido.exists():
            return
        _ensure_parent(CONFIG_PATH)
        import shutil as _sh
        _sh.copyfile(str(embebido), str(CONFIG_PATH))
    except Exception:
        # No abortar el arranque si la extraccion falla; el codigo aguas abajo
        # mostrara el error apropiado si realmente no encuentra el config.
        pass


_bootstrap_config_from_bundle()


def load_main_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        # Reintentar bootstrap por si el archivo fue removido en runtime.
        _bootstrap_config_from_bundle()
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def save_main_config(config: dict[str, Any]) -> None:
    _ensure_parent(CONFIG_PATH)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=4, ensure_ascii=False)
