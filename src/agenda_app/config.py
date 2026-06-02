import os
import glob

from bot_app.common.settings import BASE_DIR as ROOT_BASE_DIR, CONFIG_PATH


class Config:
    """Configuracion de rutas para la aplicacion de escritorio.

    Las antiguas claves de seguridad web (SECRET_KEY/API_KEY/RESET_TOKEN) se
    eliminaron junto con la interfaz Flask: la app es ahora solo de escritorio.
    """

    BASE_DIR = str(ROOT_BASE_DIR)
    CONFIG_JSON_PATH = str(CONFIG_PATH)

    _users_candidates = glob.glob(os.path.join(BASE_DIR, "usuario", "USUARIOS*.xlsx"))
    USERS_EXCEL_PATH = _users_candidates[0] if _users_candidates else os.path.join(BASE_DIR, "usuario", "USUARIOS.xlsx")
