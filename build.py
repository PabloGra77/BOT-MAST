#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de compilacion para crear el ejecutable BOT (aplicacion de escritorio).

Uso:
    python build.py

Requisitos:
    pip install pyinstaller pyinstaller-hooks-contrib
    (mas las dependencias de requirements.txt)

Resultado:
    UN UNICO ejecutable: dist/BOT.exe   (onefile, autocontenido)
"""

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()


def _read_version() -> str:
    ns: dict = {}
    exec((PROJECT_ROOT / "__version__.py").read_text(encoding="utf-8"), ns)
    return ns.get("__version__", "0.0.0")


VERSION = _read_version()


def main() -> bool:
    print("=" * 60)
    print(f"  BOT - Build Script  (v{VERSION})")
    print("=" * 60)

    spec_file = PROJECT_ROOT / "bot.spec"
    if not spec_file.exists():
        print(f"[ERROR] No se encontro {spec_file}")
        return False

    # 1) Limpiar salidas anteriores (incluye carpetas/zip de versiones viejas).
    print("\n[1/2] Limpiando builds anteriores...")
    for folder in ("build", "dist", "release"):
        p = PROJECT_ROOT / folder
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            print(f"      - {folder}/ eliminado")
    old_zip = PROJECT_ROOT / "dist.zip"
    if old_zip.exists():
        old_zip.unlink()

    # 2) Compilar con PyInstaller (onefile -> dist/BOT.exe).
    print("\n[2/2] Compilando con PyInstaller (puede tardar varios minutos)...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--distpath", str(PROJECT_ROOT / "dist"),
        "--workpath", str(PROJECT_ROOT / "build"),
        "--noconfirm",
    ]
    print("      $ " + " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        print("\n[ERROR] PyInstaller fallo.")
        return False

    exe_path = PROJECT_ROOT / "dist" / "BOT.exe"
    if not exe_path.exists():
        print(f"\n[ERROR] No se genero el ejecutable: {exe_path}")
        return False

    # Limpiar la carpeta de trabajo intermedia: dejar SOLO el .exe.
    shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True)

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  BUILD COMPLETADO")
    print("=" * 60)
    print(f"  Unico ejecutable: dist/BOT.exe  ({size_mb:.1f} MB)")
    print("  Es autocontenido: copialo donde quieras y ejecutalo.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
