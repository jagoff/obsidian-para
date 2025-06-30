#!/usr/bin/env python3
"""
RG (ripgrep) Utilities
Proporciona funciones para usar ripgrep con la ruta correcta en macOS.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

def get_rg_path() -> Optional[str]:
    """
    Obtiene la ruta correcta de rg (ripgrep).
    
    Returns:
        str: Ruta al ejecutable de rg, o None si no se encuentra
    """
    # Ruta conocida en macOS con Homebrew
    homebrew_path = "/opt/homebrew/bin/rg"
    if Path(homebrew_path).exists():
        return homebrew_path
    
    # Buscar en PATH como fallback
    system_path = shutil.which("rg")
    if system_path:
        return system_path
    
    return None

def rg_search(pattern: str, path: str, 
              files_with_matches: bool = False,
              case_insensitive: bool = True,
              file_type: Optional[str] = None) -> List[str]:
    """
    Ejecuta búsqueda con rg usando la ruta correcta.
    
    Args:
        pattern: Patrón a buscar
        path: Directorio donde buscar  
        files_with_matches: Solo devolver nombres de archivos que coinciden
        case_insensitive: Búsqueda sin distinción de mayúsculas
        file_type: Filtrar por tipo de archivo (ej: "md")
        
    Returns:
        List[str]: Líneas de resultado de rg
    """
    rg_path = get_rg_path()
    if not rg_path:
        raise FileNotFoundError("rg (ripgrep) no encontrado en el sistema")
    
    cmd = [rg_path]
    
    # Opciones
    if case_insensitive:
        cmd.append("-i")
    
    if files_with_matches:
        cmd.append("-l")
    
    if file_type:
        cmd.extend(["-t", file_type])
    
    # Patrón y path
    cmd.extend([pattern, path])
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout else []
        elif result.returncode == 1:
            # No matches found - esto es normal
            return []
        else:
            # Error real
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
            
    except FileNotFoundError:
        raise FileNotFoundError(f"No se pudo ejecutar rg en: {rg_path}")

def count_files_with_pattern(pattern: str, path: str, 
                           case_insensitive: bool = True,
                           file_type: str = "md") -> int:
    """
    Cuenta archivos que contienen un patrón.
    
    Args:
        pattern: Patrón a buscar
        path: Directorio donde buscar
        case_insensitive: Búsqueda sin distinción de mayúsculas  
        file_type: Tipo de archivo a buscar
        
    Returns:
        int: Número de archivos que contienen el patrón
    """
    try:
        matches = rg_search(
            pattern=pattern,
            path=path,
            files_with_matches=True,
            case_insensitive=case_insensitive,
            file_type=file_type
        )
        return len([m for m in matches if m.strip()])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return 0

def verify_rg_installation() -> dict:
    """
    Verifica que rg esté correctamente instalado.
    
    Returns:
        dict: Información sobre la instalación de rg
    """
    rg_path = get_rg_path()
    
    if not rg_path:
        return {
            "installed": False,
            "path": None,
            "version": None,
            "error": "rg (ripgrep) no encontrado"
        }
    
    try:
        result = subprocess.run(
            [rg_path, "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        
        version_line = result.stdout.split('\n')[0]
        
        return {
            "installed": True,
            "path": rg_path,
            "version": version_line,
            "error": None
        }
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return {
            "installed": False,
            "path": rg_path,
            "version": None,
            "error": str(e)
        }

# Función de conveniencia para importar fácilmente
def search_files_containing(pattern: str, directory: str) -> List[str]:
    """
    Función simple para buscar archivos que contienen un patrón.
    
    Args:
        pattern: Texto a buscar
        directory: Directorio donde buscar
        
    Returns:
        List[str]: Lista de rutas de archivos que contienen el patrón
    """
    return rg_search(
        pattern=pattern,
        path=directory,
        files_with_matches=True,
        case_insensitive=True,
        file_type="md"
    ) 