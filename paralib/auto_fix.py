#!/usr/bin/env python3
"""
paralib/auto_fix.py

Módulo centralizado de auto-fix para errores de código usando IA.
Reutilizable desde cualquier script del sistema PARA.
"""
import os
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    RICH = True
except ImportError:
    RICH = False

from .logger import logger

# ChromaDB para historial de bugs autocorregidos
try:
    from .db import ChromaPARADatabase
    chroma_db = ChromaPARADatabase()
except Exception:
    chroma_db = None

class AutoFixEngine:
    """Motor centralizado de auto-fix para errores de código."""
    
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.backup_dir = Path(__file__).parent.parent / "logs" / "autofix_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def fix_code_error(self, file_path: str, line_num: int, error_message: str, code_context: str = None) -> bool:
        """
        Intenta corregir un error de código usando IA.
        
        Args:
            file_path: Ruta del archivo con error
            line_num: Número de línea del error
            error_message: Mensaje de error
            code_context: Contexto del código (opcional)
            
        Returns:
            bool: True si se aplicó el fix, False en caso contrario
        """
        try:
            import ollama
        except ImportError:
            logger.error("Ollama no está disponible para auto-fix")
            return False
            
        if not os.path.exists(file_path):
            logger.error(f"Archivo no encontrado: {file_path}")
            return False
            
        # Verificar si ya fue corregido
        error_signature = error_message.strip().split('\n')[-1][:120]
        if self._already_fixed_bug(file_path, line_num, error_signature):
            logger.info(f"Bug ya autocorregido previamente en {file_path}:{line_num}")
            return True
            
        # Crear backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"{Path(file_path).name}_{timestamp}.bak"
        shutil.copy2(file_path, backup_path)
        
        # Obtener contexto del código si no se proporciona
        if not code_context:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_lines = f.readlines()
            start = max(0, line_num - 6)
            end = min(len(code_lines), line_num + 5)
            code_context = ''.join(code_lines[start:end])
        
        # Crear prompt para IA
        prompt = f"""
Corrige el siguiente error de Python en el archivo {Path(file_path).name}:

Error:
{error_message}

Código relevante:
{code_context}

Devuelve solo el código corregido, pero en la línea corregida agrega un comentario así:
# ✓ [AUTO-FIXED] Bug: {error_signature} - corregido el {datetime.now().date()} por IA
"""
        
        try:
            response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])
            fixed_code = response['message']['content']
            
            # Aplicar el fix
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
                
            # Registrar el bug corregido
            self._register_fixed_bug(file_path, line_num, error_signature, error_message)
            
            logger.info(f"Auto-fix aplicado a {file_path}. Backup en {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error aplicando auto-fix: {e}")
            return False
    
    def _already_fixed_bug(self, file_path: str, line_num: int, error_signature: str) -> bool:
        """Verifica si este bug ya fue autocorregido."""
        if not chroma_db:
            return False
        results = chroma_db.search_similar_notes(f"{file_path}:{line_num}:{error_signature}")
        return bool(results and results.get('documents'))
    
    def _register_fixed_bug(self, file_path: str, line_num: int, error_signature: str, description: str):
        """Registra el bug autocorregido en ChromaDB."""
        if not chroma_db:
            return
        chroma_db.add_note(
            content=f"{file_path}:{line_num}:{error_signature}",
            metadata={
                'file': file_path,
                'line': line_num,
                'error': error_signature,
                'description': description,
                'fixed_at': datetime.now().isoformat()
            }
        )
    
    def analyze_and_fix_logs(self, log_file_path: str = None) -> Dict:
        """
        Analiza logs y aplica auto-fixes para errores de código.
        
        Returns:
            Dict con estadísticas del proceso
        """
        if not log_file_path:
            log_file_path = Path(__file__).parent.parent / "logs" / "para.log"
            
        if not os.path.exists(log_file_path):
            return {"processed": 0, "fixed": 0, "errors": 0}
            
        stats = {"processed": 0, "fixed": 0, "errors": 0}
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-500:]  # Últimas 500 líneas
            
        error_lines = [l for l in lines if 'ERROR' in l or 'CRITICAL' in l]
        
        for line in error_lines:
            # Detectar tracebacks de Python
            tb_match = re.search(r'File "([^"]+)", line (\d+)', line)
            if tb_match:
                file_path, line_num = tb_match.group(1), int(tb_match.group(2))
                if os.path.exists(file_path):
                    stats["processed"] += 1
                    if self.fix_code_error(file_path, line_num, line):
                        stats["fixed"] += 1
                    else:
                        stats["errors"] += 1
                        
        return stats

# Instancia global para reutilización
auto_fix_engine = AutoFixEngine() 