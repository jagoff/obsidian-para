"""
paralib: Lógica de negocio central para el sistema PARA (features, reglas, scoring, embeddings, logging, etc.).
""" 

from .vault import find_vault, load_para_config, save_para_config, extract_frontmatter
from .organizer import run_archive_refactor, run_inbox_classification, get_keywords, get_rules, get_profile
from .utils import auto_backup_if_needed, pre_command_checks, check_recent_errors
from .db import ChromaPARADatabase
from .logger import logger
from .log_analyzer import analyze_and_fix_log
from .clean_manager import find_non_md_files, find_corrupt_or_unreadable
from .ui import run_monitor_dashboard, select_folders_to_exclude
from .similarity import find_similar_classification, register_project_alias
from .finetune_manager import *
from .analyze_manager import *
from .classification_log import *
from .config import *
from .learning_system import *
from .log_manager import *
from .plugin_system import *

__version__ = "2.0.0"
__author__ = "PARA Team"