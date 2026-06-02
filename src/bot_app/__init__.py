"""Paquete bot_app.

El motor de automatizacion (Selenium) vive en `bot_app.automation`. NO se
importa aqui de forma eager para que leer constantes de `bot_app.common`
(rutas de config/logs/descargas) no obligue a cargar Selenium.

Para obtener el bot:  ``from bot_app.automation.loader import Bot``
"""
