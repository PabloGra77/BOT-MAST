#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 INICIO RÁPIDO - BOT360

Este script te ayuda a comenzar rápidamente.
Ejecutar: python quick_start.py
"""

import os
import sys
import shutil
from pathlib import Path

def print_header(text):
    """Imprimir encabezado"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def main():
    """Menú de inicio rápido"""
    project_root = Path(__file__).parent
    
    print_header("🤖 BOT360 - Inicio Rápido v1.0.0")
    
    print("""
OPCIÓN 1: Ejecutar aplicación desktop
   $ python -m src.ui.desktop_app
   
OPCIÓN 2: Instalar en modo desarrollo
   $ python -m venv venv
   $ venv\\Scripts\\activate
   $ pip install -r requirements.txt
   
OPCIÓN 3: Compilar ejecutable .EXE
   $ pip install pyinstaller pyinstaller-hooks-contrib
   $ python build.py
   
OPCIÓN 4: Preparar para GitHub
   $ git init
   $ git add .
   $ git commit -m "Initial: BOT360 v1.0.0"
   $ git remote add origin https://github.com/usuario/bot360
   $ git push -u origin main
   $ git tag -a v1.0.0 -m "Release v1.0.0"
   $ git push origin v1.0.0
   
OPCIÓN 5: Ver documentación
   - README.md               ← Guía principal
   - docs/GUI_USAGE.md       ← Cómo usar la GUI
   - MEJORAS_APLICADAS.md    ← Cambios realizados
   - CHANGELOG.md            ← Historial de versiones

OPCIÓN 6: Configurar credenciales
   $ copy .env.example .env
   $ notepad .env
   # Editar con tus credenciales INPEC
""")
    
    print("="*60)
    print("""
PASOS RECOMENDADOS:

1. Configurar credenciales (.env):
   copy .env.example .env
   
2. Probar aplicación:
   python -m src.ui.desktop_app
   
3. Compilar .exe (opcional):
   python build.py
   
4. Subir a GitHub:
   git init
   git add .
   git commit -m "BOT360 v1.0.0"
   ...

ARCHIVOS IMPORTANTES:

📄 Configuración:
   .env.example          ← Copiar a .env (tus credenciales)
   config/config.json    ← Datos de sedes
   requirements.txt      ← Dependencias Python

📚 Documentación:
   README.md             ← Inicio y uso
   docs/GUI_USAGE.md     ← Cómo usar la interfaz
   MEJORAS_APLICADAS.md  ← Cambios y correcciones
   CONTRIBUTING.md       ← Cómo contribuir

🔨 Build:
   build.py              ← Compilar ejecutable
   bot360.spec           ← Configuración PyInstaller
   setup.py              ← Instalación Python

📦 Código:
   src/agenda_app/       ← Gestión de agendas
   src/bot360_app/       ← Automatización
   src/ui/               ← Interfaz desktop NUEVA
   tests/                ← Pruebas

""")
    
    print("="*60)
    print("✅ BOT360 listo para usar")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
    print("\n💡 Próximo paso: Leer README.md")
    print("📖 O ejecutar: python -m src.ui.desktop_app\n")
