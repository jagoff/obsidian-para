#!/usr/bin/env python3
"""
Enhanced Progress Bar
=====================

Implementación mejorada de barra de progreso que mantiene los logs visibles.
Sistema de detección inmediata y logging de múltiples barras de progreso.
Integrado completamente con el sistema de logging de PARA.
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import time
import sys
from io import StringIO
from contextlib import contextmanager
import threading
from queue import Queue
import os
import logging

# Importar configuración de debug
try:
    from .debug_config import should_show, DEBUG_LEVEL, DEBUG_LEVELS
except ImportError:
    # Fallback si no está disponible
    def should_show(feature: str) -> bool:
        return True
    DEBUG_LEVEL = 2  # NORMAL
    DEBUG_LEVELS = {'SILENT': 0, 'MINIMAL': 1, 'NORMAL': 2, 'VERBOSE': 3, 'DEBUG': 4}

# Importar sistema de logging de PARA
try:
    from .log_center import log_center
    from .logger import logger
    from .log_manager import PARALogManager
    PARA_LOGGING_AVAILABLE = True
except ImportError:
    PARA_LOGGING_AVAILABLE = False
    # Fallback logger
    progress_logger = logging.getLogger('para_progress')
    progress_logger.setLevel(logging.INFO)

class ProgressErrorDetector:
    """Detector de errores en barras de progreso con logging inmediato integrado con PARA."""
    
    def __init__(self):
        self.progress_lines_detected = 0
        self.last_progress_time = 0
        self.error_threshold = 1  # CUALQUIER línea adicional de progreso = error
        self.time_threshold = 1.0  # 1 segundo entre líneas = error
        self.errors_logged = []
        self.progress_messages = []  # Lista de mensajes de progreso para detectar duplicaciones
        
        # Inicializar log manager si está disponible
        self.log_manager = None
        if PARA_LOGGING_AVAILABLE:
            try:
                self.log_manager = PARALogManager()
            except Exception as e:
                if PARA_LOGGING_AVAILABLE:
                    log_center.log_error(f"Error inicializando log manager: {e}", "ProgressErrorDetector")
        
    def check_progress_line(self, message: str, timestamp: float = None):
        """Verifica si una línea es de progreso y detecta errores."""
        if timestamp is None:
            timestamp = time.time()
            
        # Patrones que indican barras de progreso (más amplios)
        progress_patterns = [
            '█', '░', '▒', '▓',  # Caracteres de barra
            'progress', 'Progress', 'PROGRESS',
            'spinner', 'Spinner', 'SPINNER',
            '|', '/', '-', '\\',  # Caracteres de spinner
            '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏',  # Spinners Unicode
            '━', '╸', '━', '╸',  # Caracteres de barra horizontal
            '━', '╸', '━', '╸',  # Caracteres de barra gruesa
            '━', '╸', '━', '╸',  # Caracteres de barra fina
            'Procesando', 'procesando', 'PROCESANDO',
            'Clasificando', 'clasificando', 'CLASIFICANDO',
            'Analizando', 'analizando', 'ANALIZANDO',
            'Consultando', 'consultando', 'CONSULTANDO',
            'Generando', 'generando', 'GENERANDO',
            'Movido', 'movido', 'MOVIDO',
            'Factor', 'factor', 'FACTOR',
            'DISCREPANCIA', 'discrepancia', 'Discrepancia',
            'Naming inteligente', 'naming inteligente',
            'PARA AI', 'para ai', 'Para AI'
        ]
        
        is_progress = any(pattern in message for pattern in progress_patterns)
        
        if is_progress:
            self.progress_lines_detected += 1
            self.progress_messages.append(message)
            time_diff = timestamp - self.last_progress_time
            
            # Detectar CUALQUIER línea adicional de progreso como error
            if self.progress_lines_detected > 1:
                error_msg = f"BARRAS MÚLTIPLES DETECTADAS: {self.progress_lines_detected} líneas en {time_diff:.3f}s"
                self._log_error_immediately(error_msg, message)
                return True
            
            # Detectar duplicaciones de mensajes
            if len(self.progress_messages) > 1:
                last_message = self.progress_messages[-2]
                if message.strip() == last_message.strip():
                    error_msg = f"DUPLICACIÓN DETECTADA: Mensaje repetido"
                    self._log_error_immediately(error_msg, message)
                    return True
            
            # Detectar líneas muy rápidas
            if time_diff < self.time_threshold and self.progress_lines_detected > 1:
                error_msg = f"BARRAS RÁPIDAS: {self.progress_lines_detected} líneas en {time_diff:.3f}s"
                self._log_error_immediately(error_msg, message)
                return True
            
            self.last_progress_time = timestamp
            
        return False
    
    def _log_error_immediately(self, error_msg: str, problematic_message: str):
        """Logea el error inmediatamente usando todos los sistemas de logging de PARA."""
        error_id = f"progress_error_{len(self.errors_logged) + 1}"
        timestamp = time.strftime('%H:%M:%S')
        
        # 1. Log con log_center (sistema principal)
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_error(
                    f"[{error_id}] {error_msg}",
                    "ProgressErrorDetector",
                    {
                        "error_id": error_id,
                        "problematic_message": problematic_message,
                        "progress_lines_detected": self.progress_lines_detected,
                        "all_messages": self.progress_messages.copy(),
                        "timestamp": timestamp
                    }
                )
            except Exception as e:
                print(f"Error logging to log_center: {e}")
        
        # 2. Log con logger estándar
        if PARA_LOGGING_AVAILABLE:
            try:
                logger.error(
                    f"[{error_id}] {error_msg} | Mensaje: {problematic_message} | Líneas: {self.progress_lines_detected}",
                    context={
                        "error_id": error_id,
                        "all_messages": self.progress_messages.copy()
                    }
                )
            except Exception as e:
                print(f"Error logging to logger: {e}")
        else:
            # Fallback logger
            progress_logger.error(f"[{error_id}] {error_msg}")
            progress_logger.error(f"[{error_id}] Mensaje problemático: {problematic_message}")
            progress_logger.error(f"[{error_id}] Líneas de progreso detectadas: {self.progress_lines_detected}")
            progress_logger.error(f"[{error_id}] Todos los mensajes: {self.progress_messages}")
        
        # 3. Log con log_manager (si está disponible)
        if self.log_manager:
            try:
                # Crear entrada para log_manager
                from .log_manager import LogEntry, LogStatus
                entry = LogEntry(
                    id=len(self.errors_logged) + 1,
                    timestamp=time.time(),
                    level="ERROR",
                    module="ProgressErrorDetector",
                    message=f"[{error_id}] {error_msg}",
                    status=LogStatus.PENDING
                )
                self.log_manager._save_entry(entry)
            except Exception as e:
                if PARA_LOGGING_AVAILABLE:
                    log_center.log_error(f"Error logging to log_manager: {e}", "ProgressErrorDetector")
        
        # 4. Agregar a lista de errores local
        self.errors_logged.append({
            'id': error_id,
            'error': error_msg,
            'message': problematic_message,
            'count': self.progress_lines_detected,
            'timestamp': time.time(),
            'all_messages': self.progress_messages.copy()
        })
        
        # 5. Mostrar error inmediatamente en consola
        print(f"\n🚨 [{error_id}] ERROR DE PROGRESO DETECTADO:")
        print(f"   ❌ {error_msg}")
        print(f"   📝 Mensaje actual: {problematic_message[:100]}...")
        print(f"   🔢 Total líneas: {self.progress_lines_detected}")
        print(f"   ⏰ Timestamp: {timestamp}")
        print(f"   📋 Todos los mensajes:")
        for i, msg in enumerate(self.progress_messages, 1):
            print(f"      {i}. {msg[:80]}...")
        print(f"   💡 INTERRUMPIENDO PROCESAMIENTO...")
        
        # 6. Log adicional con contexto completo
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_critical(
                    f"PROCESAMIENTO INTERRUMPIDO por error de progreso: {error_msg}",
                    "ProgressErrorDetector",
                    {
                        "error_id": error_id,
                        "interruption": True,
                        "total_errors": len(self.errors_logged),
                        "session_affected": True
                    }
                )
            except Exception as e:
                print(f"Error logging critical: {e}")
        
        # Interrumpir el procesamiento
        raise ProgressBarError(error_msg, error_id)
    
    def get_error_summary(self):
        """Obtiene un resumen de errores detectados."""
        return {
            'total_errors': len(self.errors_logged),
            'progress_lines': self.progress_lines_detected,
            'errors': self.errors_logged.copy()
        }

class ProgressBarError(Exception):
    """Excepción específica para errores de barras de progreso."""
    def __init__(self, message: str, error_id: str):
        self.message = message
        self.error_id = error_id
        super().__init__(message)

class SuppressedConsole:
    """Consola que suprime la salida durante el procesamiento con detección de errores."""
    
    def __init__(self, original_console):
        self.original_console = original_console
        self.suppressed = False
        self.captured_messages = []
        self.error_detector = ProgressErrorDetector()
        
    def print(self, *args, **kwargs):
        """Captura mensajes durante la supresión y detecta errores."""
        if self.suppressed:
            message = " ".join(str(arg) for arg in args)
            self.captured_messages.append(message)
            
            # Verificar si es un error de progreso
            try:
                self.error_detector.check_progress_line(message)
            except ProgressBarError as e:
                # Re-lanzar la excepción para interrumpir el procesamiento
                raise e
        else:
            self.original_console.print(*args, **kwargs)
    
    def start_suppression(self):
        """Inicia la supresión de salida."""
        self.suppressed = True
        self.captured_messages = []
        self.error_detector = ProgressErrorDetector()  # Reset detector
        
        # Log inicio de supresión
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_info("Iniciando supresión de salida para progreso", "SuppressedConsole")
            except Exception:
                pass
    
    def stop_suppression(self):
        """Detiene la supresión y retorna los mensajes capturados."""
        self.suppressed = False
        
        # Log fin de supresión
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_info(
                    f"Supresión terminada. Mensajes capturados: {len(self.captured_messages)}",
                    "SuppressedConsole",
                    {"captured_count": len(self.captured_messages)}
                )
            except Exception:
                pass
        
        return self.captured_messages.copy()
    
    def get_error_summary(self):
        """Obtiene resumen de errores detectados."""
        return self.error_detector.get_error_summary()

def create_progress_layout():
    """Crea un layout con barra de progreso fija y área de logs."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="progress", size=4),
        Layout(name="logs", ratio=1)
    )
    return layout

def should_display_message(message: str, debug_level: int) -> bool:
    """Determina si un mensaje debe mostrarse basado en el nivel de debug."""
    # Mensajes críticos siempre se muestran
    if '❌' in message or 'CRITICAL' in message or 'ERROR' in message:
        return True
    
    # En modo MINIMAL, solo errores
    if debug_level <= DEBUG_LEVELS['MINIMAL']:
        return False
    
    # En modo NORMAL, errores y éxitos
    if debug_level == DEBUG_LEVELS['NORMAL']:
        return '✅' in message or '❌' in message or '⚠️' in message
    
    # En modo VERBOSE o superior, todos los mensajes
    return True

def extract_message_info(message: str) -> dict:
    """Extrae información del mensaje para determinar cómo mostrarlo."""
    try:
        # Determinar status basado en el contenido del mensaje
        if '❌' in message or 'ERROR' in message or 'CRITICAL' in message:
            status = '❌'
            style = 'red'
        elif '✅' in message or 'SUCCESS' in message:
            status = '✅'
            style = 'green'
        elif '⚠️' in message or 'WARNING' in message or '🔄' in message:
            status = '⚠️'
            style = 'yellow'
        elif '📋' in message or '📝' in message or 'INFO' in message:
            status = '📝'
            style = 'dim'
        elif '🤖' in message or '🔍' in message or '⚡' in message:
            status = '🤖'
            style = 'cyan'
        else:
            status = 'ℹ️'
            style = 'blue'
        
        # Limpiar el mensaje de emojis de status para evitar duplicación
        clean_message = message
        for emoji in ['❌', '✅', '⚠️', '🔄', '📋', '📝', '🤖', '🔍', '⚡']:
            clean_message = clean_message.replace(emoji, '')
        clean_message = clean_message.strip()
        
        return {
            'status': status,
            'style': style,
            'message': clean_message,
            'original': message
        }
    except Exception as e:
        # Fallback en caso de error
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_warning(f"Error en extract_message_info: {e}", "EnhancedProgress")
            except Exception:
                pass
        return {
            'status': 'ℹ️',
            'style': 'blue',
            'message': str(message)[:100] if message else 'Mensaje desconocido',
            'original': str(message) if message else ''
        }

def run_with_fixed_progress(notes_to_process, process_function, title="Procesando...", console=None):
    """
    Ejecuta una función de procesamiento con barra de progreso fija.
    Sistema de detección inmediata de errores de múltiples barras.
    Integrado completamente con el sistema de logging de PARA.
    
    Args:
        notes_to_process: Lista de elementos a procesar
        process_function: Función que procesa cada elemento
        title: Título de la barra de progreso
        console: Consola de Rich (opcional)
    """
    if not console:
        console = Console()
    
    # Log inicio del procesamiento
    if PARA_LOGGING_AVAILABLE:
        try:
            log_center.log_info(
                f"Iniciando procesamiento con barra fija: {title}",
                "EnhancedProgress",
                {"total_items": len(notes_to_process), "title": title}
            )
        except Exception:
            pass
    
    # Crear consola suprimida con detector de errores
    suppressed_console = SuppressedConsole(console)
    
    # Usar progreso simple sin Live display para evitar duplicaciones
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        task = progress.add_task(title, total=len(notes_to_process))
        
        for i, item in enumerate(notes_to_process):
            try:
                # Suprimir salida durante el procesamiento
                suppressed_console.start_suppression()
                
                # Llamar a la función de procesamiento
                result = process_function(item, i, len(notes_to_process))
                
                # Detener supresión
                captured_messages = suppressed_console.stop_suppression()
                
                # Verificar si hubo errores de progreso
                error_summary = suppressed_console.get_error_summary()
                if error_summary['total_errors'] > 0:
                    if PARA_LOGGING_AVAILABLE:
                        try:
                            log_center.log_error(
                                f"Errores de progreso detectados: {error_summary['total_errors']}",
                                "EnhancedProgress",
                                error_summary
                            )
                        except Exception:
                            pass
                    print(f"\n🚨 ERRORES DE PROGRESO DETECTADOS: {error_summary['total_errors']}")
                    for error in error_summary['errors']:
                        print(f"   ❌ {error['error']}")
                    raise ProgressBarError("Múltiples barras de progreso detectadas", "batch_error")
                
                # En modo NORMAL, mostrar resultados importantes
                if result and DEBUG_LEVEL >= DEBUG_LEVELS['NORMAL']:
                    status = result.get('status', '✅')
                    if status == '❌' or status == '⚠️':
                        message = result.get('message', f'Procesado: {item}')
                        style = result.get('style', 'green')
                        if style:
                            console.print(f"{status} [{style}]{message}[/{style}]")
                        else:
                            console.print(f"{status} {message}")
                
            except ProgressBarError as e:
                suppressed_console.stop_suppression()
                print(f"\n🚨 INTERRUMPIENDO PROCESAMIENTO: {e.message}")
                print(f"💡 Revisa los logs para más detalles")
                if PARA_LOGGING_AVAILABLE:
                    try:
                        log_center.log_error(f"Procesamiento interrumpido por error de progreso: {e.message}", "EnhancedProgress")
                    except Exception:
                        pass
                raise e
            except Exception as e:
                suppressed_console.stop_suppression()
                # Manejar errores específicos de forma más elegante
                error_msg = str(e)
                if 'list index out of range' in error_msg or isinstance(e, IndexError):
                    if PARA_LOGGING_AVAILABLE:
                        try:
                            log_center.log_warning(f"Error de índice en procesamiento: {error_msg}", "EnhancedProgress")
                        except Exception:
                            pass
                    continue  # Continuar con el siguiente elemento
                else:
                    # Otros errores - mostrar normalmente
                    if PARA_LOGGING_AVAILABLE:
                        try:
                            log_center.log_error(f"Error en procesamiento: {error_msg}", "EnhancedProgress")
                        except Exception:
                            pass
                
            # Actualizar progreso
            progress.advance(task)
        
        # Log fin del procesamiento
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_info("Procesamiento completado", "EnhancedProgress")
            except Exception:
                pass
        
        return [] 