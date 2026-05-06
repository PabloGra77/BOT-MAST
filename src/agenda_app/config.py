import os
import glob

from bot360_app.common.settings import (
    BASE_DIR as ROOT_BASE_DIR,
    CONFIG_PATH,
    get_api_key,
    get_reset_token,
    get_secret_key,
)


class Config:
    BASE_DIR = str(ROOT_BASE_DIR)
    SECRET_KEY = get_secret_key()
    API_KEY = get_api_key()
    ADMIN_RESET_TOKEN = get_reset_token()
    LOG_PATH = os.environ.get(
        "AGENDA_LOG_PATH",
        os.path.join(BASE_DIR, "logs", "agenda_app.log"),
    )
    CONFIG_JSON_PATH = str(CONFIG_PATH)
    _users_candidates = glob.glob(os.path.join(BASE_DIR, "usuario", "USUARIOS*.xlsx"))
    USERS_EXCEL_PATH = _users_candidates[0] if _users_candidates else os.path.join(BASE_DIR, "usuario", "USUARIOS.xlsx")
    DEBUG = os.environ.get("AGENDA_DEBUG", "false").lower() == "true"
