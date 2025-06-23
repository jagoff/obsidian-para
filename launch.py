#!/usr/bin/env python3
"""
launch.py

Script de arranque universal para PARA System (reemplaza launch.sh).
- Activa/crea entorno virtual
- Instala dependencias si es necesario
- Lanza la CLI principal
"""
import os
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
VENV_DIR = SCRIPT_DIR / 'venv'
DEPS_MARKER = VENV_DIR / '.deps_installed'
REQUIREMENTS = SCRIPT_DIR / 'requirements.txt'
PYTHON = sys.executable

# 1. Crear entorno virtual si no existe
def ensure_venv():
    if not VENV_DIR.exists():
        print(f"🐍 Creando entorno virtual en '{VENV_DIR}'...")
        subprocess.check_call([PYTHON, '-m', 'venv', str(VENV_DIR)])

# 2. Activar entorno virtual y devolver el path a python dentro del venv
def venv_python():
    if sys.platform == 'win32':
        return VENV_DIR / 'Scripts' / 'python.exe'
    else:
        return VENV_DIR / 'bin' / 'python'

# 3. Instalar dependencias si es necesario
def ensure_deps():
    if not DEPS_MARKER.exists() or REQUIREMENTS.stat().st_mtime > DEPS_MARKER.stat().st_mtime:
        print("📦 Instalando/actualizando dependencias...")
        subprocess.check_call([str(venv_python()), '-m', 'pip', 'install', '--upgrade', 'pip'])
        subprocess.check_call([str(venv_python()), '-m', 'pip', 'install', '--no-cache-dir', '-r', str(REQUIREMENTS)])
        DEPS_MARKER.touch()
        print("✅ Dependencias listas.")

# 4. Lanzar la CLI principal
def launch_cli():
    args = sys.argv[1:]
    print("🚀 Lanzando PARA CLI...")
    os.execv(str(venv_python()), [str(venv_python()), str(SCRIPT_DIR / 'para_cli.py')] + args)

if __name__ == '__main__':
    ensure_venv()
    ensure_deps()
    launch_cli() 