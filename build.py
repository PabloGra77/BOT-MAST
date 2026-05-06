#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de compilación para crear ejecutable BOT360.exe

Uso:
    python build.py
    
Requisitos:
    pip install pyinstaller pyinstaller-hooks-contrib
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"\n❌ Error ejecutando: {cmd}")
        return False
    return True

def main():
    """Ejecutar proceso de compilación"""
    print("\n" + "="*60)
    print("🔨 BOT360 - Build Script")
    print("="*60)
    
    project_root = Path(__file__).parent
    spec_file = project_root / "bot360.spec"
    
    if not spec_file.exists():
        print(f"❌ Error: {spec_file} no encontrado")
        return False
    
    # Step 1: Limpiar builds anteriores
    print("\n1️⃣  Limpiando builds anteriores...")
    for folder in ["build", "dist", "BOT360"]:
        folder_path = project_root / folder
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"   ✓ {folder}/ eliminado")
    
    # Step 2: Compilar con PyInstaller
    print("\n2️⃣  Compilando con PyInstaller...")
    cmd = f'pyinstaller "{spec_file}" --distpath "{project_root}/dist" --buildpath "{project_root}/build"'
    if not run_command(cmd, "PyInstaller"):
        return False
    
    # Step 3: Verificar resultado
    exe_path = project_root / "dist" / "BOT360" / "BOT360.exe"
    if exe_path.exists():
        exe_size = exe_path.stat().st_size / (1024 * 1024)  # MB
        print(f"\n✅ Compilación exitosa!")
        print(f"📦 Ejecutable: {exe_path}")
        print(f"📊 Tamaño: {exe_size:.1f} MB")
    else:
        print(f"\n❌ Error: No se encontró {exe_path}")
        return False
    
    # Step 4: Crear portable
    print("\n3️⃣  Creando versión portable...")
    portable_dir = project_root / "dist" / "BOT360_portable"
    exe_dir = project_root / "dist" / "BOT360"
    
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    
    shutil.copytree(exe_dir, portable_dir)
    
    # Copiar configuración
    config_src = project_root / "config"
    config_dst = portable_dir / "config"
    if config_src.exists() and not config_dst.exists():
        shutil.copytree(config_src, config_dst)
    
    # Copiar .env.example
    env_example = project_root / ".env.example"
    if env_example.exists():
        shutil.copy(env_example, portable_dir / ".env.example")
    
    print(f"   ✓ Portable creado en: {portable_dir}")
    
    # Step 5: Crear ZIP
    print("\n4️⃣  Creando archivo ZIP...")
    zip_path = project_root / "dist" / f"BOT360-v1.0.0-portable"
    try:
        shutil.make_archive(str(zip_path), "zip", portable_dir.parent, portable_dir.name)
        zip_size = (Path(str(zip_path) + ".zip").stat().st_size) / (1024 * 1024)
        print(f"   ✓ ZIP creado: {zip_path}.zip ({zip_size:.1f} MB)")
    except Exception as e:
        print(f"   ⚠️  Advertencia al crear ZIP: {e}")
    
    # Resumen final
    print("\n" + "="*60)
    print("✨ Build completado exitosamente")
    print("="*60)
    print(f"""
    📦 Archivos generados:
    
    1. Ejecutable individual:
       dist/BOT360/BOT360.exe
    
    2. Versión portable:
       dist/BOT360_portable/
    
    3. ZIP portátil:
       dist/BOT360-v1.0.0-portable.zip
    
    📝 Próximos pasos:
    
    1. Probar ejecutable:
       dist/BOT360/BOT360.exe
    
    2. Cargar configuración:
       Copiar .env.example a .env
       Editar credenciales
    
    3. Publicar release:
       git tag -a v1.0.0 -m "Release 1.0.0"
       git push origin v1.0.0
    
    4. Cargar a GitHub:
       Upload dist/BOT360-v1.0.0-portable.zip
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
