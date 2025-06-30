"""
PARA System Library

Sistema completo para organizar automáticamente vaults de Obsidian usando la metodología PARA
con IA local y base de datos vectorial.

Módulos principales:
- organizer: Clasificación y organización de notas
- learning_system: Sistema de aprendizaje autónomo
- db: Base de datos vectorial ChromaDB
- ai_engine: Motor de IA con Ollama
- dashboard_unified: Dashboard unificado del sistema v4.0
- backup_center: Centro especializado de backups
- log_manager: Gestión de logs y errores
- plugin_system: Sistema de plugins extensible
- vault: Gestión de vaults de Obsidian
- config: Configuración del sistema
- update_center: Centro de actualizaciones automático
"""

__version__ = "2.0.0"
__author__ = "PARA System Team"
__description__ = "Sistema de organización automática de notas con IA"

# Imports principales
from .organizer import run_full_reclassification_safe, run_inbox_classification, run_archive_refactor, auto_consolidate_post_organization
from .learning_system import PARA_Learning_System
from .db import ChromaPARADatabase
from .ai_engine import ai_engine
# from .dashboard_unified import PARADashboardUnified
from .log_manager import PARALogManager
from .plugin_system import PARAPluginManager
from .vault import find_vault
from .config import load_config
from .update_center import update_center, check_updates, get_embedding_models_status
from .rg_utils import get_rg_path, rg_search, count_files_with_pattern, verify_rg_installation, search_files_containing

__all__ = [
    'run_full_reclassification_safe', 
    'run_inbox_classification',
    'run_archive_refactor',
    'auto_consolidate_post_organization',
    'PARA_Learning_System',
    'ChromaPARADatabase',
    'ai_engine',
    # 'PARADashboardUnified',
    'PARALogManager',
    'PARAPluginManager',
    'find_vault',
    'load_config',
    'update_center',
    'check_updates',
    'get_embedding_models_status',
    'get_rg_path',
    'rg_search', 
    'count_files_with_pattern',
    'verify_rg_installation',
    'search_files_containing'
]
