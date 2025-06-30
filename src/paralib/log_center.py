#!/usr/bin/env python3
"""
paralib/log_center.py

Centro de logging unificado y robusto para PARA System v2.0
"""
import logging
import logging.handlers
import json
import hashlib
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import queue
import threading
import traceback

class LogLevel(Enum):
    """Niveles de log personalizados."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogStatus(Enum):
    """Estados de los logs."""
    NEW = "new"           # Log nuevo, no procesado
    RESOLVED = "resolved" # Log resuelto por auto-fix o manual
    IGNORED = "ignored"   # Log ignorado (no requiere acción)

@dataclass
class LogEntry:
    """Estructura de entrada de log con gestión de estados."""
    timestamp: str
    level: str
    component: str
    message: str
    context: Dict[str, Any]
    session_id: str
    status: LogStatus = LogStatus.NEW
    user_id: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None

class PARALogCenter:
    """Centro de logging unificado para PARA System."""
    
    def __init__(self, log_dir: str = "logs"):
        """Inicializa el sistema de logging centralizado."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configuración - AUTO-FIX COMPLETAMENTE DESHABILITADO
        self.auto_fix_enabled = False
        self.max_log_entries = 10000
        
        # Configurar logging
        self._setup_logging()
        
        # NO cargar reglas de auto-reparación
        self.auto_fix_rules = {}
        self.error_patterns = {}
        
        # NO iniciar thread de procesamiento
        self.processing_thread = None
        
        # Métricas básicas
        self.metrics = {
            'total_logs': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0
        }
        
        # Lista simple de logs en memoria
        self.log_entries = []
        
        # Alertas básicas
        self.alerts = []
        
        # Inicialización silenciosa - NO PRINT
    
    def _setup_logging(self):
        """Configura logging SOLO A ARCHIVO - SIN CONSOLA."""
        self.logger = logging.getLogger('PARA_LogCenter')
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicación
        if self.logger.handlers:
            return
        
        # Handler SOLO para archivo - NO CONSOLA
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "para_system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setLevel(logging.DEBUG)
        
        # Formatter simple y seguro
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
        )
        
        main_handler.setFormatter(formatter)
        
        # SOLO agregar handler de archivo - NO CONSOLA
        self.logger.addHandler(main_handler)
    
    def _log(self, level: str, message: str, component: str = "Unknown", context: Dict = None, session_id: str = None):
        """Método interno de logging simplificado."""
        if context is None:
            context = {}
        
        if session_id is None:
            session_id = self._generate_session_id()
        
        # Crear entrada de log simple
        timestamp = datetime.now()
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'component': component,
            'context': context,
            'session_id': session_id
        }
        
        # Agregar a lista en memoria
        self.log_entries.append(log_entry)
        
        # Mantener solo los últimos logs
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries = self.log_entries[-self.max_log_entries:]
        
        # Actualizar métricas
        self.metrics['total_logs'] += 1
        if level == 'ERROR':
            self.metrics['errors'] += 1
        elif level == 'WARNING':
            self.metrics['warnings'] += 1
        elif level == 'INFO':
            self.metrics['info'] += 1
        
        # Log a archivo usando el logger estándar
        log_message = f"{message} | Component: {component} | Session: {session_id}"
        if context:
            log_message += f" | Context: {context}"
        
        if hasattr(self, 'logger'):
            if level == 'ERROR':
                self.logger.error(log_message)
            elif level == 'WARNING':
                self.logger.warning(log_message)
            elif level == 'INFO':
                self.logger.info(log_message)
            elif level == 'DEBUG':
                self.logger.debug(log_message)
            else:
                self.logger.info(log_message)
    
    def log_info(self, message: str, component: str = "System", extra_data: dict = None, verbose: bool = False, session_id: str = None):
        """Log información general - SOLO A ARCHIVO."""
        # Mantener compatibilidad total con todos los parámetros
        context = extra_data if extra_data is not None else {}
        self._log("INFO", message, component, context, session_id)
        # NO mostrar NUNCA en consola a menos que sea explícitamente verbose=True
        if verbose:
            print(f"ℹ️ [{component}] {message}")
    
    def log_warning(self, message: str, component: str = "Unknown", context: dict = None, session_id: str = None):
        """Log de warning SIN output a consola."""
        self._log('WARNING', message, component, context, session_id)
    
    def log_error(self, message: str, component: str = "Unknown", context: dict = None, session_id: str = None):
        """Log de error SIN output a consola."""
        self._log('ERROR', message, component, context, session_id)
    
    def log_debug(self, message: str, component: str = "System", context: dict = None):
        """Log a debug message."""
        self._log('DEBUG', message, component, context)
    
    def _generate_session_id(self) -> str:
        """Genera un ID de sesión único."""
        import random
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    def get_log_stats(self) -> dict:
        """Obtiene estadísticas de logs de forma segura."""
        try:
            return {
                'total_logs': self.metrics.get('total_logs', 0),
                'errors': self.metrics.get('errors', 0),
                'warnings': self.metrics.get('warnings', 0),
                'auto_fixes_applied': self.metrics.get('auto_fixes_applied', 0)
            }
        except Exception:
            return {
                'total_logs': 0,
                'errors': 0,
                'warnings': 0,
                'auto_fixes_applied': 0
            }
    
    def get_recent_logs(self, limit: int = 100) -> List[LogEntry]:
        """Obtiene los logs más recientes de forma segura."""
        try:
            # Devolver logs desde memoria primero
            if self.log_entries:
                recent_from_memory = []
                for entry in self.log_entries[-limit:]:
                    try:
                        log_entry = LogEntry(
                            timestamp=str(entry.get('timestamp', datetime.now())),
                            level=entry.get('level', 'INFO'),
                            component=entry.get('component', 'System'),
                            message=entry.get('message', ''),
                            context=entry.get('context', {}),
                            session_id=entry.get('session_id', 'unknown')
                        )
                        recent_from_memory.append(log_entry)
                    except Exception:
                        # Si hay error creando LogEntry, continuar con el siguiente
                        continue
                return recent_from_memory
            
            # Fallback: leer desde archivo
            log_files = sorted(self.log_dir.glob("para_system.log*"), reverse=True)
            if not log_files:
                return []
            
            recent_logs = []
            with open(log_files[0], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        try:
                            # Parsear línea de log básica con manejo seguro
                            parts = line.split(' | ')
                            timestamp = datetime.now().isoformat()
                            level = 'INFO'
                            message = line.strip()
                            
                            if len(parts) >= 1 and '[' in parts[0] and ']' in parts[0]:
                                timestamp_part = parts[0].strip('[]').split('] ')
                                if len(timestamp_part) >= 2:
                                    timestamp = timestamp_part[0]
                                    level = timestamp_part[1]
                            
                            if len(parts) >= 2:
                                message = parts[1]
                            
                            log_entry = LogEntry(
                                timestamp=timestamp,
                                level=level,
                                component='System',
                                message=message,
                                context={},
                                session_id='file_log'
                            )
                            recent_logs.append(log_entry)
                        except Exception:
                            # Si hay error parseando una línea, continuar con la siguiente
                            continue
            
            return recent_logs[-limit:]
        except Exception as e:
            # Log error de forma segura sin causar recursión
            try:
                self._log('ERROR', f"Error obteniendo logs recientes: {e}", 'LogCenter')
            except:
                pass
            return []
    
    def get_error_patterns(self) -> List[Dict[str, Any]]:
        """Obtiene patrones de errores detectados."""
        return [
            {
                'pattern': pattern,
                'count': data['count'],
                'last_seen': data['last_seen'],
                'severity': data['severity']
            }
            for pattern, data in self.error_patterns.items()
        ]

    def _attempt_auto_fix(self, log_entry):
        """Auto-fix COMPLETAMENTE DESHABILITADO."""
        return  # NO HACER NADA
    
    def _find_auto_fix_rule(self, log_entry):
        """Auto-fix rules COMPLETAMENTE DESHABILITADO."""
        return None  # NO DEVOLVER NADA

    def log_chromadb_error(self, error_message: str, context: dict = None):
        """Log específico para errores de ChromaDB."""
        self.log_error(f"[CHROMADB-ERROR] {error_message}", "ChromaDB", context)
        
        # También enviar a archivo de errores específicos
        try:
            error_file = self.log_dir / "chromadb_errors.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {error_message} | Context: {context}\n")
        except Exception:
            pass  # No fallar si no se puede escribir el archivo
    
    def log_classification_error(self, note_name: str, error_message: str, context: dict = None):
        """Log específico para errores de clasificación."""
        self.log_error(f"[CLASSIFICATION-ERROR] {note_name}: {error_message}", "Classification", context)
        
        # También enviar a archivo de errores específicos
        try:
            error_file = self.log_dir / "classification_errors.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(error_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {note_name}: {error_message} | Context: {context}\n")
        except Exception:
            pass
            
    def get_recent_errors_by_type(self, error_type: str, hours: int = 24) -> list:
        """Obtiene errores recientes de un tipo específico."""
        try:
            recent_logs = self.get_recent_logs(100)
            filtered_errors = []
            
            patterns = {
                'chromadb': ['CHROMADB-ERROR', 'ChromaPARADatabase', 'unexpected keyword argument', 'limit='],
                'classification': ['CLASSIFICATION-ERROR', 'Error procesando', 'classification error'],
                'system': ['SystemIssue', 'critical error', 'failed initialization']
            }
            
            search_patterns = patterns.get(error_type.lower(), [error_type])
            
            for log_entry in recent_logs:
                if log_entry.level.upper() in ['ERROR', 'CRITICAL']:
                    for pattern in search_patterns:
                        if pattern.lower() in log_entry.message.lower():
                            filtered_errors.append(log_entry)
                            break
            
            return filtered_errors
            
        except Exception as e:
            self.log_error(f"Error obteniendo errores recientes por tipo: {e}", "LogCenter")
            return []

# Instancia global
log_center = PARALogCenter()

def log_function_call(func: Callable) -> Callable:
    """Decorador para loggear llamadas a funciones."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        session_id = log_center._generate_session_id()
        
        try:
            # Log de inicio
            log_center.log_info(
                f"Iniciando función: {func.__name__}",
                component=func.__module__,
                session_id=session_id
            )
            
            # Ejecutar función
            result = func(*args, **kwargs)
            
            # Log de éxito
            execution_time = time.time() - start_time
            log_center.log_info(
                f"Función completada: {func.__name__} ({execution_time:.2f}s)",
                component=func.__module__,
                session_id=session_id
            )
            
            return result
            
        except Exception as e:
            # Log de error
            execution_time = time.time() - start_time
            log_center.log_error(
                f"Error en función: {func.__name__} - {str(e)}",
                component=func.__module__,
                session_id=session_id
            )
            raise
    
    return wrapper

def log_streamlit_action(action: str, component: str = 'Dashboard'):
    """Log de acciones de Streamlit."""
    log_center.log_info(f"Acción Streamlit: {action}", component)

def log_dashboard_error(error: Exception, component: str = 'Dashboard'):
    """Log de errores del dashboard."""
    log_center.log_error(f"Error en dashboard: {str(error)}", component) 