#!/usr/bin/env python3
"""
paralib/log_status_manager.py

Gestor de estados de logs para PARA System.
Permite marcar logs como resueltos, nuevos o ignorados.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class LogStatus(Enum):
    """Estados de los logs."""
    NEW = "new"           # Log nuevo, no procesado
    RESOLVED = "resolved" # Log resuelto por auto-fix o manual
    IGNORED = "ignored"   # Log ignorado (no requiere acción)

@dataclass
class LogEntryWithStatus:
    """Entrada de log con estado gestionado."""
    id: str
    timestamp: str
    level: str
    component: str
    message: str
    context: Dict[str, Any]
    session_id: str
    status: LogStatus = LogStatus.NEW
    resolution_notes: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    auto_fix_applied: bool = False
    error_signature: Optional[str] = None

class LogStatusManager:
    """Gestor de estados de logs."""
    
    def __init__(self, status_file: str = "logs/log_status.json"):
        self.status_file = Path(status_file)
        self.status_file.parent.mkdir(exist_ok=True)
        self.log_entries: Dict[str, LogEntryWithStatus] = {}
        self._load_status()
    
    def _load_status(self):
        """Carga el estado de logs desde archivo."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data.get('entries', []):
                        entry = LogEntryWithStatus(
                            id=entry_data['id'],
                            timestamp=entry_data['timestamp'],
                            level=entry_data['level'],
                            component=entry_data['component'],
                            message=entry_data['message'],
                            context=entry_data.get('context', {}),
                            session_id=entry_data['session_id'],
                            status=LogStatus(entry_data.get('status', 'new')),
                            resolution_notes=entry_data.get('resolution_notes'),
                            resolved_at=entry_data.get('resolved_at'),
                            resolved_by=entry_data.get('resolved_by'),
                            auto_fix_applied=entry_data.get('auto_fix_applied', False),
                            error_signature=entry_data.get('error_signature')
                        )
                        self.log_entries[entry.id] = entry
        except Exception as e:
            print(f"Error cargando estado de logs: {e}")
    
    def _save_status(self):
        """Guarda el estado de logs a archivo."""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'entries': [asdict(entry) for entry in self.log_entries.values()]
            }
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando estado de logs: {e}")
    
    def add_log_entry(self, log_entry: LogEntryWithStatus):
        """Agrega una nueva entrada de log."""
        self.log_entries[log_entry.id] = log_entry
        self._save_status()
    
    def mark_as_resolved(self, log_id: str, resolution_notes: str = None, 
                        resolved_by: str = "auto-fix", auto_fix_applied: bool = True):
        """Marca un log como resuelto."""
        if log_id in self.log_entries:
            entry = self.log_entries[log_id]
            entry.status = LogStatus.RESOLVED
            entry.resolution_notes = resolution_notes
            entry.resolved_at = datetime.now().isoformat()
            entry.resolved_by = resolved_by
            entry.auto_fix_applied = auto_fix_applied
            self._save_status()
            return True
        return False
    
    def mark_as_ignored(self, log_id: str, reason: str = None):
        """Marca un log como ignorado."""
        if log_id in self.log_entries:
            entry = self.log_entries[log_id]
            entry.status = LogStatus.IGNORED
            entry.resolution_notes = f"Ignorado: {reason}" if reason else "Ignorado manualmente"
            entry.resolved_at = datetime.now().isoformat()
            entry.resolved_by = "manual"
            self._save_status()
            return True
        return False
    
    def get_new_logs(self) -> List[LogEntryWithStatus]:
        """Obtiene logs con estado NEW."""
        return [entry for entry in self.log_entries.values() 
                if entry.status == LogStatus.NEW]
    
    def get_resolved_logs(self) -> List[LogEntryWithStatus]:
        """Obtiene logs resueltos."""
        return [entry for entry in self.log_entries.values() 
                if entry.status == LogStatus.RESOLVED]
    
    def get_ignored_logs(self) -> List[LogEntryWithStatus]:
        """Obtiene logs ignorados."""
        return [entry for entry in self.log_entries.values() 
                if entry.status == LogStatus.IGNORED]
    
    def get_logs_by_status(self, status: LogStatus) -> List[LogEntryWithStatus]:
        """Obtiene logs por estado específico."""
        return [entry for entry in self.log_entries.values() 
                if entry.status == status]
    
    def get_error_logs(self) -> List[LogEntryWithStatus]:
        """Obtiene logs de error (nuevos o resueltos)."""
        return [entry for entry in self.log_entries.values() 
                if entry.level.upper() in ['ERROR', 'CRITICAL']]
    
    def get_warning_logs(self) -> List[LogEntryWithStatus]:
        """Obtiene logs de warning."""
        return [entry for entry in self.log_entries.values() 
                if entry.level.upper() == 'WARNING']
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de logs por estado."""
        total = len(self.log_entries)
        new_count = len(self.get_new_logs())
        resolved_count = len(self.get_resolved_logs())
        ignored_count = len(self.get_ignored_logs())
        error_count = len(self.get_error_logs())
        warning_count = len(self.get_warning_logs())
        
        return {
            'total': total,
            'new': new_count,
            'resolved': resolved_count,
            'ignored': ignored_count,
            'errors': error_count,
            'warnings': warning_count,
            'resolution_rate': (resolved_count / total * 100) if total > 0 else 0
        }
    
    def cleanup_old_resolved_logs(self, days: int = 7):
        """Limpia logs resueltos antiguos."""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
        to_remove = []
        
        for log_id, entry in self.log_entries.items():
            if entry.status == LogStatus.RESOLVED and entry.resolved_at:
                try:
                    resolved_time = datetime.fromisoformat(entry.resolved_at).timestamp()
                    if resolved_time < cutoff_time:
                        to_remove.append(log_id)
                except:
                    pass
        
        for log_id in to_remove:
            del self.log_entries[log_id]
        
        if to_remove:
            self._save_status()
            return len(to_remove)
        return 0
    
    def find_similar_logs(self, message: str, component: str = None) -> List[LogEntryWithStatus]:
        """Encuentra logs similares basado en mensaje y componente."""
        similar = []
        message_lower = message.lower()
        
        for entry in self.log_entries.values():
            if message_lower in entry.message.lower():
                if component is None or entry.component == component:
                    similar.append(entry)
        
        return similar

# Instancia global
log_status_manager = LogStatusManager() 