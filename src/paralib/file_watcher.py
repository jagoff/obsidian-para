#!/usr/bin/env python3
"""
paralib/file_watcher.py

Sistema de monitoreo de archivos en tiempo real usando Watchdog
Para auto-clasificación y sincronización automática del vault de Obsidian
"""
import os
import time
from pathlib import Path
from typing import Dict, List, Callable, Optional, Set
from datetime import datetime
from threading import Thread, Event
import json

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    FileSystemEvent = None

from paralib.log_center import log_center, log_function_call

class ObsidianFileHandler(FileSystemEventHandler):
    """Manejador de eventos de archivos específico para Obsidian."""
    
    def __init__(self, callback: Callable, vault_path: Path):
        super().__init__()
        self.callback = callback
        self.vault_path = Path(vault_path)
        self.ignored_patterns = {
            '.obsidian',
            '.git',
            '.DS_Store',
            'Thumbs.db',
            '.tmp',
            '.temp'
        }
        self.markdown_extensions = {'.md', '.markdown', '.txt'}
        
        # Debounce para evitar múltiples eventos del mismo archivo
        self.recent_events: Dict[str, float] = {}
        self.debounce_time = 1.0  # 1 segundo
        
        log_center.log_info("ObsidianFileHandler inicializado", "FileWatcher")
    
    def should_ignore(self, path: str) -> bool:
        """Determina si un archivo debe ser ignorado."""
        path_obj = Path(path)
        
        # Ignorar archivos en directorios específicos
        for part in path_obj.parts:
            if any(pattern in part for pattern in self.ignored_patterns):
                return True
        
        # Solo procesar archivos markdown y texto
        if path_obj.suffix.lower() not in self.markdown_extensions:
            return True
        
        # Ignorar archivos temporales
        if path_obj.name.startswith('.') or path_obj.name.startswith('~'):
            return True
        
        return False
    
    def is_debounced(self, path: str) -> bool:
        """Verifica si el evento debe ser ignorado por debounce."""
        current_time = time.time()
        last_event_time = self.recent_events.get(path, 0)
        
        if current_time - last_event_time < self.debounce_time:
            return True
        
        self.recent_events[path] = current_time
        return False
    
    def on_created(self, event: FileSystemEvent):
        """Archivo creado."""
        if not event.is_directory and not self.should_ignore(event.src_path):
            if not self.is_debounced(event.src_path):
                log_center.log_info(f"Archivo creado: {event.src_path}", "FileWatcher")
                self.callback('created', event.src_path)
    
    def on_modified(self, event: FileSystemEvent):
        """Archivo modificado."""
        if not event.is_directory and not self.should_ignore(event.src_path):
            if not self.is_debounced(event.src_path):
                log_center.log_info(f"Archivo modificado: {event.src_path}", "FileWatcher")
                self.callback('modified', event.src_path)
    
    def on_moved(self, event: FileSystemEvent):
        """Archivo movido/renombrado."""
        if not event.is_directory and not self.should_ignore(event.dest_path):
            log_center.log_info(f"Archivo movido: {event.src_path} -> {event.dest_path}", "FileWatcher")
            self.callback('moved', event.dest_path, event.src_path)
    
    def on_deleted(self, event: FileSystemEvent):
        """Archivo eliminado."""
        if not event.is_directory and not self.should_ignore(event.src_path):
            log_center.log_info(f"Archivo eliminado: {event.src_path}", "FileWatcher")
            self.callback('deleted', event.src_path)

class PARAFileWatcher:
    """Sistema de monitoreo de archivos para PARA System."""
    
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path
        self.observer = None
        self.is_watching = False
        self.callbacks: Dict[str, List[Callable]] = {
            'created': [],
            'modified': [],
            'moved': [],
            'deleted': []
        }
        
        # Estadísticas
        self.stats = {
            'files_created': 0,
            'files_modified': 0,
            'files_moved': 0,
            'files_deleted': 0,
            'total_events': 0,
            'start_time': None
        }
        
        self.stop_event = Event()
        
        if not WATCHDOG_AVAILABLE:
            log_center.log_warning("Watchdog no está disponible. Instala con: pip install watchdog", "FileWatcher")
        else:
            log_center.log_info("PARAFileWatcher inicializado", "FileWatcher")
    
    @log_function_call
    def set_vault_path(self, vault_path: Path):
        """Establece la ruta del vault a monitorear."""
        self.vault_path = Path(vault_path)
        log_center.log_info(f"Vault path establecido: {self.vault_path}", "FileWatcher")
    
    def add_callback(self, event_type: str, callback: Callable):
        """Agrega un callback para un tipo de evento específico."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            log_center.log_info(f"Callback agregado para evento: {event_type}", "FileWatcher")
        else:
            log_center.log_warning(f"Tipo de evento no válido: {event_type}", "FileWatcher")
    
    def remove_callback(self, event_type: str, callback: Callable):
        """Remueve un callback específico."""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            log_center.log_info(f"Callback removido para evento: {event_type}", "FileWatcher")
    
    def _handle_file_event(self, event_type: str, file_path: str, old_path: str = None):
        """Maneja un evento de archivo ejecutando todos los callbacks."""
        try:
            # Actualizar estadísticas
            self.stats[f'files_{event_type}'] += 1
            self.stats['total_events'] += 1
            
            # Ejecutar callbacks
            for callback in self.callbacks[event_type]:
                try:
                    if event_type == 'moved' and old_path:
                        callback(file_path, old_path)
                    else:
                        callback(file_path)
                except Exception as e:
                    log_center.log_error(f"Error en callback {event_type}: {e}", "FileWatcher")
        
        except Exception as e:
            log_center.log_error(f"Error manejando evento {event_type}: {e}", "FileWatcher")
    
    @log_function_call
    def start_watching(self) -> bool:
        """Inicia el monitoreo de archivos."""
        if not WATCHDOG_AVAILABLE:
            log_center.log_error("No se puede iniciar watchdog: no está instalado", "FileWatcher")
            return False
        
        if not self.vault_path or not self.vault_path.exists():
            log_center.log_error("Vault path no válido para monitoreo", "FileWatcher")
            return False
        
        if self.is_watching:
            log_center.log_warning("El monitoreo ya está activo", "FileWatcher")
            return True
        
        try:
            self.observer = Observer()
            event_handler = ObsidianFileHandler(self._handle_file_event, self.vault_path)
            
            self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
            self.observer.start()
            
            self.is_watching = True
            self.stats['start_time'] = datetime.now()
            
            log_center.log_info(f"Monitoreo iniciado en: {self.vault_path}", "FileWatcher")
            return True
            
        except Exception as e:
            log_center.log_error(f"Error iniciando monitoreo: {e}", "FileWatcher")
            return False
    
    @log_function_call
    def stop_watching(self):
        """Detiene el monitoreo de archivos."""
        if not self.is_watching:
            return
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
                self.observer = None
            
            self.is_watching = False
            self.stop_event.set()
            
            log_center.log_info("Monitoreo de archivos detenido", "FileWatcher")
            
        except Exception as e:
            log_center.log_error(f"Error deteniendo monitoreo: {e}", "FileWatcher")
    
    def get_status(self) -> Dict:
        """Obtiene el estado actual del file watcher."""
        return {
            'is_watching': self.is_watching,
            'vault_path': str(self.vault_path) if self.vault_path else None,
            'watchdog_available': WATCHDOG_AVAILABLE,
            'total_callbacks': sum(len(callbacks) for callbacks in self.callbacks.values()),
            'uptime': str(datetime.now() - self.stats['start_time']) if self.stats['start_time'] else None
        }
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del monitoreo."""
        stats = self.stats.copy()
        if stats['start_time']:
            stats['uptime'] = str(datetime.now() - stats['start_time'])
        return stats
    
    def is_available(self) -> bool:
        """Verifica si watchdog está disponible."""
        return WATCHDOG_AVAILABLE
    
    def __del__(self):
        """Destructor para limpiar recursos - Seguro durante cierre de Python."""
        try:
            # Verificar si Python se está cerrando
            import sys
            if sys.meta_path is None:
                # Python cerrándose - cleanup silencioso
                if hasattr(self, 'observer') and self.observer:
                    try:
                        self.observer.stop()
                        self.observer = None
                    except:
                        pass  # Ignorar errores durante cierre
                return
            
            # Cleanup normal
            self.stop_watching()
            
        except (ImportError, AttributeError, Exception):
            # Cualquier error durante cleanup del destructor - ignorar silenciosamente
            # Esto es seguro durante el cierre de Python
            pass

# Funciones de conveniencia para auto-clasificación
class AutoClassifier:
    """Sistema de auto-clasificación basado en eventos de archivos."""
    
    def __init__(self, file_watcher: PARAFileWatcher):
        self.file_watcher = file_watcher
        self.setup_auto_classification()
        log_center.log_info("AutoClassifier inicializado", "AutoClassifier")
    
    def setup_auto_classification(self):
        """Configura los callbacks para auto-clasificación."""
        self.file_watcher.add_callback('created', self.classify_new_file)
        self.file_watcher.add_callback('modified', self.reclassify_file)
        self.file_watcher.add_callback('moved', self.handle_moved_file)
    
    @log_function_call
    def classify_new_file(self, file_path: str):
        """Clasifica automáticamente un archivo nuevo."""
        try:
            log_center.log_info(f"Auto-clasificando archivo nuevo: {file_path}", "AutoClassifier")
            
            # Aquí se integraría con el sistema de clasificación PARA
            # Por ahora solo loggeamos
            
            # Ejemplo de lógica de clasificación:
            path_obj = Path(file_path)
            
            # Clasificación básica por contenido del nombre
            if any(keyword in path_obj.name.lower() for keyword in ['proyecto', 'project', 'trabajo']):
                category = 'Projects'
            elif any(keyword in path_obj.name.lower() for keyword in ['area', 'responsabilidad']):
                category = 'Areas'
            elif any(keyword in path_obj.name.lower() for keyword in ['recurso', 'reference', 'info']):
                category = 'Resources'
            else:
                category = 'Archive'
            
            log_center.log_info(f"Archivo clasificado como: {category}", "AutoClassifier")
            
        except Exception as e:
            log_center.log_error(f"Error en auto-clasificación: {e}", "AutoClassifier")
    
    @log_function_call
    def reclassify_file(self, file_path: str):
        """Re-clasifica un archivo modificado."""
        log_center.log_info(f"Re-evaluando clasificación: {file_path}", "AutoClassifier")
        # Lógica de re-clasificación
    
    @log_function_call
    def handle_moved_file(self, new_path: str, old_path: str):
        """Maneja archivos movidos."""
        log_center.log_info(f"Archivo movido de {old_path} a {new_path}", "AutoClassifier")
        # Lógica para archivos movidos

# Instancia global
file_watcher = PARAFileWatcher()

# Función de conveniencia para inicializar todo
def setup_file_monitoring(vault_path: Path, enable_auto_classification: bool = True) -> tuple:
    """Configura el monitoreo completo de archivos."""
    try:
        file_watcher.set_vault_path(vault_path)
        
        auto_classifier = None
        if enable_auto_classification:
            auto_classifier = AutoClassifier(file_watcher)
        
        success = file_watcher.start_watching()
        
        if success:
            log_center.log_info("Sistema de monitoreo configurado exitosamente", "FileWatcher")
        else:
            log_center.log_error("Error configurando sistema de monitoreo", "FileWatcher")
        
        return file_watcher, auto_classifier
        
    except Exception as e:
        log_center.log_error(f"Error en setup de monitoreo: {e}", "FileWatcher")
        return None, None 