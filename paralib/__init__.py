"""
PARA System Library

Sistema completo para organizar automáticamente vaults de Obsidian usando la metodología PARA
con IA local y base de datos vectorial.

Módulos principales:
- organizer: Clasificación y organización de notas
- learning_system: Sistema de aprendizaje autónomo
- db: Base de datos vectorial ChromaDB
- ai_engine: Motor de IA con Ollama
- dashboard: Dashboard unificado del sistema
- log_manager: Gestión de logs y errores
- plugin_system: Sistema de plugins extensible
- vault: Gestión de vaults de Obsidian
- config: Configuración del sistema
"""

__version__ = "2.0.0"
__author__ = "PARA System Team"
__description__ = "Sistema de organización automática de notas con IA"

# Imports principales
from .organizer import PARAOrganizer, run_full_reclassification
from .learning_system import PARA_Learning_System
from .db import ChromaPARADatabase
from .ai_engine import ai_engine
from .dashboard import PARADashboard
from .log_manager import PARALogManager
from .plugin_system import PARAPluginManager
from .vault import find_vault
from .config import load_config

__all__ = [
    'PARAOrganizer',
    'run_full_reclassification', 
    'PARA_Learning_System',
    'ChromaPARADatabase',
    'ai_engine',
    'PARADashboard',
    'PARALogManager',
    'PARAPluginManager',
    'find_vault',
    'load_config'
]