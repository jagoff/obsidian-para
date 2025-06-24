"""
paralib/logger.py

Módulo centralizado de logging para PARA System.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
# from rich.logging import RichHandler  # Solo usar en módulos interactivos

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'para.log')

os.makedirs(LOG_DIR, exist_ok=True)

# Configuración del logger
logger = logging.getLogger("para")
logger.setLevel(logging.DEBUG)

# Handler para archivo rotativo
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8'
)
file_formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s [%(name)s:%(module)s:%(lineno)d] [PID:%(process)d] [TID:%(thread)d]\n%(message)s\n' + '-'*80,
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)

# Solo log a archivo para la CLI y scripts por defecto
logger.handlers.clear()
logger.addHandler(file_handler)
logger.propagate = False

# NOTA: Si un módulo interactivo (dashboard, UI, etc.) necesita logs en consola,
# debe crear su propio logger local con RichHandler o similar. 