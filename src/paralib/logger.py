#!/usr/bin/env python3
"""
paralib/logger.py

Sistema de logging robusto y centralizado para PARA System.
Captura todos los errores, excepciones y eventos del sistema.
"""
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import threading
from functools import wraps

class PARALogger:
    """
    Sistema de logging robusto para PARA System.
    
    Características:
    - Logging multi-nivel (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Rotación automática de archivos
    - Captura de excepciones no manejadas
    - Logging estructurado con contexto
    - Integración con el sistema de auto-fix
    """
    
    def __init__(self, name: str = "PARA", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicación de handlers
        if not self.logger.handlers:
            self._setup_handlers()
        
        # Capturar excepciones no manejadas
        self._setup_exception_handling()
        
        # Contexto de logging
        self.context = {}
        self._context_lock = threading.Lock()
    
    def _setup_handlers(self):
        """Configura los handlers de logging."""
        
        # Handler para archivo principal con rotación
        main_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "para.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        
        # Handler para errores críticos
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "para_errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # Handler para consola (solo errores y warnings)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(module)s:%(lineno)d] [PID:%(process)d] [TID:%(thread)d]\n%(message)s\n' + '-'*80
        )
        
        simple_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
        )
        
        # Aplicar formatters
        main_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        # Agregar handlers
        self.logger.addHandler(main_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
    
    def _setup_exception_handling(self):
        """Configura el manejo de excepciones no capturadas."""
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                # No loguear interrupciones del usuario
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Loggear excepción no manejada
            self.critical(
                f"Excepción no manejada: {exc_type.__name__}: {exc_value}",
                exc_info=(exc_type, exc_value, exc_traceback),
                context={"unhandled_exception": True}
            )
        
        sys.excepthook = handle_exception
    
    def set_context(self, **kwargs):
        """Establece contexto para el logging."""
        with self._context_lock:
            self.context.update(kwargs)
    
    def clear_context(self):
        """Limpia el contexto de logging."""
        with self._context_lock:
            self.context.clear()
    
    def _format_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Formatea el mensaje con contexto."""
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            return f"{message} | Context: {context_str}"
        elif self.context:
            context_str = " | ".join([f"{k}={v}" for k, v in self.context.items()])
            return f"{message} | Context: {context_str}"
        return message
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log de nivel DEBUG."""
        formatted_message = self._format_message(message, context)
        self.logger.debug(formatted_message)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log de nivel INFO."""
        formatted_message = self._format_message(message, context)
        self.logger.info(formatted_message)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log de nivel WARNING."""
        formatted_message = self._format_message(message, context)
        self.logger.warning(formatted_message)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log de nivel ERROR."""
        formatted_message = self._format_message(message, context)
        self.logger.error(formatted_message, exc_info=exc_info)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log de nivel CRITICAL."""
        formatted_message = self._format_message(message, context)
        self.logger.critical(formatted_message, exc_info=exc_info)
    
    def exception(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log de excepción con traceback automático."""
        formatted_message = self._format_message(message, context)
        self.logger.exception(formatted_message)
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None, context: Optional[Dict[str, Any]] = None):
        """Log de llamada a función."""
        args_str = str(args) if args else "()"
        kwargs_str = str(kwargs) if kwargs else "{}"
        message = f"FUNCTION_CALL: {func_name}{args_str} {kwargs_str}"
        self.debug(message, context)
    
    def log_function_result(self, func_name: str, result: Any = None, context: Optional[Dict[str, Any]] = None):
        """Log del resultado de una función."""
        result_str = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
        message = f"FUNCTION_RESULT: {func_name} -> {result_str}"
        self.debug(message, context)
    
    def log_function_error(self, func_name: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log de error en función."""
        message = f"FUNCTION_ERROR: {func_name} -> {type(error).__name__}: {error}"
        self.error(message, context=context, exc_info=True)
    
    def log_system_event(self, event_type: str, event_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """Log de eventos del sistema."""
        event_json = json.dumps(event_data, ensure_ascii=False, default=str)
        message = f"SYSTEM_EVENT: {event_type} | Data: {event_json}"
        self.info(message, context)
    
    def log_performance(self, operation: str, duration: float, context: Optional[Dict[str, Any]] = None):
        """Log de métricas de rendimiento."""
        message = f"PERFORMANCE: {operation} took {duration:.3f}s"
        self.info(message, context)
    
    def log_security_event(self, event_type: str, details: str, context: Optional[Dict[str, Any]] = None):
        """Log de eventos de seguridad."""
        message = f"SECURITY: {event_type} | {details}"
        self.warning(message, context)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los logs."""
        try:
            main_log = self.log_dir / "para.log"
            error_log = self.log_dir / "para_errors.log"
            
            stats = {
                "main_log_size": main_log.stat().st_size if main_log.exists() else 0,
                "error_log_size": error_log.stat().st_size if error_log.exists() else 0,
                "main_log_lines": 0,
                "error_log_lines": 0,
                "last_modified": None
            }
            
            if main_log.exists():
                with open(main_log, 'r', encoding='utf-8') as f:
                    stats["main_log_lines"] = sum(1 for _ in f)
                stats["last_modified"] = datetime.fromtimestamp(main_log.stat().st_mtime).isoformat()
            
            if error_log.exists():
                with open(error_log, 'r', encoding='utf-8') as f:
                    stats["error_log_lines"] = sum(1 for _ in f)
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_old_logs(self, days: int = 30):
        """Limpia logs antiguos."""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned_count = 0
            
            for log_file in self.log_dir.glob("*.log.*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            
            self.info(f"Logs cleanup completed: {cleaned_count} files removed")
            return cleaned_count
        except Exception as e:
            self.error(f"Error during logs cleanup: {e}")
            return 0

# Instancia global del logger
logger = PARALogger()

# Decorador para logging automático de funciones
def log_function_calls(func):
    """Decorador para logging automático de llamadas a funciones."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Log de entrada
        logger.log_function_call(func_name, args, kwargs)
        
        try:
            # Ejecutar función
            start_time = datetime.now()
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Log de resultado
            logger.log_function_result(func_name, result)
            logger.log_performance(func_name, duration)
            
            return result
        except Exception as e:
            # Log de error
            logger.log_function_error(func_name, e)
            raise
    
    return wrapper

# Decorador para logging de excepciones
def log_exceptions(func):
    """Decorador para logging automático de excepciones."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            func_name = f"{func.__module__}.{func.__name__}"
            logger.log_function_error(func_name, e)
            raise
    
    return wrapper

# Función para configurar logging específico de módulo
def get_module_logger(module_name: str) -> PARALogger:
    """Obtiene un logger específico para un módulo."""
    return PARALogger(f"PARA.{module_name}")

# Función para logging de eventos del sistema
def log_system_event(event_type: str, event_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
    """Función de conveniencia para logging de eventos del sistema."""
    logger.log_system_event(event_type, event_data, context)

# Función para logging de errores críticos
def log_critical_error(message: str, error: Exception = None, context: Optional[Dict[str, Any]] = None):
    """Función de conveniencia para logging de errores críticos."""
    if error:
        logger.critical(f"{message}: {type(error).__name__}: {error}", context=context, exc_info=True)
    else:
        logger.critical(message, context=context) 