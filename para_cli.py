#!/usr/bin/env python3
"""
para_cli.py - CLI principal para PARA System

Este archivo es el punto de entrada principal que importa desde la nueva estructura src/
"""

import sys
from pathlib import Path

# Agregar src al path para imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Importar y ejecutar el CLI principal
from para_cli import main

if __name__ == "__main__":
    main() 