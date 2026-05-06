from flask import Flask
from .config import Config
import logging
import os


import sys


def _configure_logging(log_path):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    normalized_log_path = os.path.abspath(log_path)

    has_file_handler = any(
        isinstance(handler, logging.FileHandler)
        and os.path.abspath(getattr(handler, "baseFilename", "")) == normalized_log_path
        for handler in root_logger.handlers
    )
    has_stream_handler = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    )

    if not has_file_handler:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if not has_stream_handler:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

def create_app():
    # Ajuste para PyInstaller: Flask necesita saber dónde está la raíz cuando se ejecuta congelado
    if getattr(sys, 'frozen', False):
        template_folder = os.path.join(sys._MEIPASS, 'agenda_app', 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'agenda_app', 'static')
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(__name__)
        
    app.config.from_object(Config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Falta SECRET_KEY. Configure AGENDA_SECRET_KEY o security.secret_key en config.json")
    if not app.config.get("API_KEY"):
        raise RuntimeError("Falta API_KEY. Configure AGENDA_API_KEY o security.api_key en config.json")
    if app.config.get("API_KEY") == "dev-api-key":
        raise RuntimeError("API_KEY insegura detectada ('dev-api-key'). Configure una clave segura")

    log_path = app.config["LOG_PATH"]
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    _configure_logging(log_path)
    from .api import api_bp
    from .routes.ui import ui_bp
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app

