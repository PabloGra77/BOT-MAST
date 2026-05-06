# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para BOT360

Compilar: pyinstaller bot360.spec
"""

import sys
import os
from pathlib import Path

# Ruta del proyecto (SPECPATH es la variable de PyInstaller con el directorio del .spec)
PROJECT_ROOT = Path(SPECPATH).resolve()

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / 'src' / 'ui' / 'desktop_app.py')],
    pathex=[str(PROJECT_ROOT / 'src')],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / 'config'), 'config'),
        (str(PROJECT_ROOT / 'docs'), 'docs'),
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.edge',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'pandas',
        'openpyxl',
        'requests',
        'fitz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BOT360',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = GUI sin consola, True = con consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Onefile: todos los recursos empaquetados en un solo .exe
    onefile=True,
    # Icono
    icon=str(PROJECT_ROOT / 'src' / 'ui' / 'assets' / 'bot360.ico') 
        if (PROJECT_ROOT / 'src' / 'ui' / 'assets' / 'bot360.ico').exists() 
        else None,
)
