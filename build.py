#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de compilacion para crear el paquete BOT (aplicacion de escritorio).

Uso:
    python build.py

Requisitos:
    pip install pyinstaller pyinstaller-hooks-contrib
    (mas las dependencias de requirements.txt)

Resultado:
    dist/BOT/BOT.exe            (carpeta onedir, autocontenida)
    dist/BOT-v<version>.zip     (la misma carpeta comprimida para distribuir)

NOTA: se uso onefile hasta la v1.0.4, pero PyQt6 fallaba al cargar dentro
del .exe empaquetado ("DLL load failed while importing QtCore") tanto en
build local como en maquinas de usuarios reales. Onedir evita la
auto-extraccion a una carpeta temporal en cada arranque, que es la causa
mas comun de ese fallo con Qt. Ver bot.spec para mas detalle.
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()


def _read_version() -> str:
    ns: dict = {}
    exec((PROJECT_ROOT / "__version__.py").read_text(encoding="utf-8"), ns)
    return ns.get("__version__", "0.0.0")


VERSION = _read_version()


def _zip_dir(src_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(src_dir.parent))


def main() -> bool:
    print("=" * 60)
    print(f"  BOT - Build Script  (v{VERSION})")
    print("=" * 60)

    spec_file = PROJECT_ROOT / "bot.spec"
    if not spec_file.exists():
        print(f"[ERROR] No se encontro {spec_file}")
        return False

    # 1) Limpiar salidas anteriores.
    print("\n[1/3] Limpiando builds anteriores...")
    for folder in ("build", "dist", "release"):
        p = PROJECT_ROOT / folder
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            print(f"      - {folder}/ eliminado")

    # 2) Compilar con PyInstaller (onedir -> dist/BOT/BOT.exe).
    print("\n[2/3] Compilando con PyInstaller (puede tardar varios minutos)...")
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

    dist_folder = PROJECT_ROOT / "dist" / "BOT"
    exe_path = dist_folder / "BOT.exe"
    if not exe_path.exists():
        print(f"\n[ERROR] No se genero el ejecutable: {exe_path}")
        return False

    # Limpiar la carpeta de trabajo intermedia.
    shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True)

    # 3) Comprimir la carpeta para distribucion.
    print("\n[3/3] Comprimiendo paquete portable...")
    zip_path = PROJECT_ROOT / "dist" / f"BOT-v{VERSION}.zip"
    _zip_dir(dist_folder, zip_path)

    folder_size_mb = sum(f.stat().st_size for f in dist_folder.rglob("*") if f.is_file()) / (1024 * 1024)
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  BUILD COMPLETADO")
    print("=" * 60)
    print(f"  Carpeta: dist/BOT/  ({folder_size_mb:.1f} MB)")
    print(f"  Zip:     {zip_path.name}  ({zip_size_mb:.1f} MB)")
    print("  Para usar: descomprimir el .zip y ejecutar BOT.exe dentro de la carpeta.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
