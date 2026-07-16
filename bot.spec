# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller para BOT (aplicacion de escritorio).

Genera una carpeta (modo "onedir"): dist/BOT/BOT.exe + archivos de soporte.
Punto de entrada: src/ui/desktop_app.py (el propio script inserta src/ y la
raiz del proyecto en sys.path, por lo que puede ejecutarse de forma directa).

`pathex` incluye src/ para que PyInstaller pueda resolver los paquetes
propios bot_app.* y agenda_app.* (viven junto a ui/, no en la raiz).

NOTA sobre onedir vs onefile: se uso onefile hasta intentar la v1.0.4, pero
en maquinas reales (y en este entorno de build) PyQt6 fallaba al cargar
dentro del .exe empaquetado con "ImportError: DLL load failed while
importing QtCore: No se encontro el proceso especificado". Este es un
problema conocido del modo onefile de PyInstaller con Qt: cada arranque
auto-extrae todo a una carpeta temporal nueva, lo que puede causar
colisiones/errores de carga de DLLs nativas. El modo onedir (carpeta fija,
sin auto-extraccion en cada arranque) es el fix recomendado para este
problema especifico. build.py comprime la carpeta resultante en un .zip
portable para distribucion.
"""
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH)
SRC_DIR = PROJECT_ROOT / "src"

block_cipher = None

a = Analysis(
    [str(SRC_DIR / "ui" / "desktop_app.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "bot_app",
        "bot_app.automation",
        "bot_app.automation.bot_engine",
        "bot_app.automation.loader",
        "bot_app.common",
        "bot_app.common.settings",
        "bot_app.common.job_config",
        "agenda_app",
        "agenda_app.bot",
        "agenda_app.bot.runner",
        "agenda_app.bot.excel_lookup",
        "agenda_app.domain",
        "agenda_app.domain.requests",
        "agenda_app.config",
        "webdriver_manager",
        "webdriver_manager.chrome",
        "webdriver_manager.microsoft",
        "fitz",
        "openpyxl",
        "psutil",
        "dotenv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BOT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BOT",
)
