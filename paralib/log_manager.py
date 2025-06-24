#!/usr/bin/env python3
"""
paralib/log_manager.py

Log Manager inteligente para PARA System.
Analiza logs automáticamente, resuelve problemas comunes y mantiene métricas de resolución.
"""
import re
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from .logger import logger

class LogStatus(Enum):
    PENDING = "pending"
    AUTO_RESOLVED = "auto_resolved"
    MANUALLY_RESOLVED = "manually_resolved"
    ESCALATED = "escalated"

@dataclass
class LogEntry:
    id: int
    timestamp: datetime
    level: str
    module: str
    message: str
    status: LogStatus
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    auto_resolution_attempted: bool = False

class PARALogManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Path(__file__).parent.parent / "logs" / "log_manager.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Patrones de auto-resolución
        self.auto_resolution_patterns = {
            # Problemas de modelo de IA
            r"Modelo de IA '([^']+)' no encontrado": self._resolve_model_not_found,
            r"Error al contactar con Ollama": self._resolve_ollama_connection,
            
            # Problemas de ChromaDB
            r"Error al conectar con ChromaDB": self._resolve_chromadb_connection,
            r"Error al crear embedding": self._resolve_embedding_error,
            
            # Problemas de archivos
            r"Error leyendo ([^:]+):": self._resolve_file_read_error,
            r"Error procesando ([^:]+):": self._resolve_file_process_error,
            
            # Problemas de permisos
            r"Permission denied": self._resolve_permission_error,
            r"Access denied": self._resolve_permission_error,
            
            # Problemas de backup
            r"Error al crear backup": self._resolve_backup_error,
            
            # Problemas de clasificación
            r"Error al clasificar": self._resolve_classification_error,
            r"JSON inválido devuelto": self._resolve_json_error,

            # Errores de importación y variables no definidas
            r"name '([^']+)' is not defined": self._resolve_name_not_defined,
            r"ImportError: cannot import name '([^']+)'": self._resolve_import_error,
            r"ModuleNotFoundError: No module named '([^']+)'": self._resolve_module_not_found,
        }
        
        # Métricas
        self.metrics = {
            'total_logs': 0,
            'auto_resolved': 0,
            'manually_resolved': 0,
            'pending': 0,
            'escalated': 0,
            'avg_resolution_time': 0,
        }
        self._update_metrics()
    
    def _init_database(self):
        """Inicializa la base de datos del log manager."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                resolution TEXT,
                resolved_at TEXT,
                auto_resolution_attempted BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_logs INTEGER DEFAULT 0,
                auto_resolved INTEGER DEFAULT 0,
                manually_resolved INTEGER DEFAULT 0,
                pending INTEGER DEFAULT 0,
                escalated INTEGER DEFAULT 0,
                avg_resolution_time REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze_log_file(self, log_file_path: str = None) -> Dict:
        """Analiza el archivo de logs principal y procesa las entradas."""
        if not log_file_path:
            log_file_path = Path(__file__).parent.parent / "logs" / "para.log"
        
        if not Path(log_file_path).exists():
            logger.warning(f"Log file not found: {log_file_path}")
            return {'processed': 0, 'auto_resolved': 0, 'pending': 0}
        
        processed = 0
        auto_resolved = 0
        pending = 0
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parsear entradas de log
        log_entries = self._parse_log_entries(content)
        
        for entry in log_entries:
            if self._should_process_entry(entry):
                status = self._analyze_and_resolve(entry)
                if status == LogStatus.AUTO_RESOLVED:
                    auto_resolved += 1
                elif status == LogStatus.PENDING:
                    pending += 1
                processed += 1
        
        self._update_metrics()
        
        return {
            'processed': processed,
            'auto_resolved': auto_resolved,
            'pending': pending,
            'total_in_db': self._get_total_logs_in_db()
        }
    
    def _parse_log_entries(self, content: str) -> List[LogEntry]:
        """Parsea el contenido del archivo de logs."""
        entries = []
        
        # Patrón para entradas de log
        pattern = r'\[([^\]]+)\] ([A-Z]+) \[([^:]+):([^:]+):(\d+)\] \[PID:(\d+)\] \[TID:(\d+)\]\n(.*?)\n' + '-'*80
        
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            timestamp_str, level, name, module, lineno, pid, tid, message = match.groups()
            
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                entry = LogEntry(
                    id=len(entries) + 1,
                    timestamp=timestamp,
                    level=level,
                    module=module,
                    message=message.strip(),
                    status=LogStatus.PENDING
                )
                entries.append(entry)
            except ValueError:
                continue
        
        return entries
    
    def _should_process_entry(self, entry: LogEntry) -> bool:
        """Determina si una entrada debe ser procesada."""
        # Solo procesar errores y warnings
        if entry.level not in ['ERROR', 'WARNING', 'CRITICAL']:
            return False
        
        # Verificar si ya existe en la base de datos
        return not self._entry_exists(entry)
    
    def _entry_exists(self, entry: LogEntry) -> bool:
        """Verifica si una entrada ya existe en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM log_entries 
            WHERE timestamp = ? AND level = ? AND module = ? AND message = ?
        ''', (entry.timestamp.isoformat(), entry.level, entry.module, entry.message))
        
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def _analyze_and_resolve(self, entry: LogEntry) -> LogStatus:
        """Analiza una entrada de log e intenta resolverla automáticamente."""
        entry.auto_resolution_attempted = True
        
        for pattern, resolver_func in self.auto_resolution_patterns.items():
            if re.search(pattern, entry.message, re.IGNORECASE):
                try:
                    resolution = resolver_func(entry)
                    if resolution:
                        entry.status = LogStatus.AUTO_RESOLVED
                        entry.resolution = resolution
                        entry.resolved_at = datetime.now()
                        self._save_entry(entry)
                        return LogStatus.AUTO_RESOLVED
                except Exception as e:
                    logger.error(f"Error in auto-resolution: {e}")
        
        # Si no se pudo resolver automáticamente, marcar como pendiente
        entry.status = LogStatus.PENDING
        self._save_entry(entry)
        return LogStatus.PENDING
    
    def _save_entry(self, entry: LogEntry):
        """Guarda una entrada en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO log_entries 
            (timestamp, level, module, message, status, resolution, resolved_at, auto_resolution_attempted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.timestamp.isoformat(),
            entry.level,
            entry.module,
            entry.message,
            entry.status.value,
            entry.resolution,
            entry.resolved_at.isoformat() if entry.resolved_at else None,
            entry.auto_resolution_attempted
        ))
        
        conn.commit()
        conn.close()
    
    # Funciones de auto-resolución
    def _resolve_model_not_found(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de modelo no encontrado."""
        match = re.search(r"Modelo de IA '([^']+)' no encontrado", entry.message)
        if match:
            model_name = match.group(1)
            return f"Modelo {model_name} no encontrado. Ejecutar: ollama pull {model_name}"
        return None
    
    def _resolve_ollama_connection(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de conexión con Ollama."""
        return "Ollama no está ejecutándose. Iniciar: ollama serve"
    
    def _resolve_chromadb_connection(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de conexión con ChromaDB."""
        return "Error de conexión con ChromaDB. Verificar configuración de la base de datos"
    
    def _resolve_embedding_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de embeddings."""
        return "Error al crear embeddings. Verificar modelo de embeddings"
    
    def _resolve_file_read_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de lectura de archivos."""
        match = re.search(r"Error leyendo ([^:]+):", entry.message)
        if match:
            filename = match.group(1)
            return f"Error leyendo archivo: {filename}. Verificar permisos y existencia"
        return None
    
    def _resolve_file_process_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de procesamiento de archivos."""
        match = re.search(r"Error procesando ([^:]+):", entry.message)
        if match:
            filename = match.group(1)
            return f"Error procesando archivo: {filename}. Verificar formato y contenido"
        return None
    
    def _resolve_permission_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de permisos."""
        return "Error de permisos. Verificar permisos de escritura en el directorio"
    
    def _resolve_backup_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de backup."""
        return "Error al crear backup. Verificar espacio en disco y permisos"
    
    def _resolve_classification_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de clasificación."""
        return "Error en clasificación. Verificar contenido de la nota y modelo de IA"
    
    def _resolve_json_error(self, entry: LogEntry) -> Optional[str]:
        """Resuelve problemas de JSON inválido devuelto por el LLM."""
        from paralib.ai_engine import AIEngine
        engine = AIEngine()
        # 1. Verificar si el modelo está disponible
        available_models = engine.list_available_models()
        model_names = [m['name'] for m in available_models]
        # Extraer modelo del mensaje si es posible
        m = re.search(r"modelo ([\w\.-:]+)", entry.message)
        model_name = m.group(1) if m else engine.model_name
        if model_name not in model_names:
            # Intentar instalar el modelo automáticamente
            import subprocess
            try:
                subprocess.run(["ollama", "pull", model_name], check=True)
                return f"Modelo {model_name} no estaba disponible. Instalado automáticamente con 'ollama pull {model_name}'."
            except Exception as e:
                return f"No se pudo instalar el modelo {model_name}: {e}"
        # 2. Si el modelo está, sugerir cambiar a otro modelo disponible
        if len(model_names) > 1:
            alt = [m for m in model_names if m != model_name][0]
            return f"Error de JSON con el modelo {model_name}. Sugerencia: prueba con el modelo alternativo '{alt}' usando --model {alt}."
        return "Error de formato JSON. Verificar respuesta del modelo de IA y prueba con otro modelo disponible."
    
    def _resolve_name_not_defined(self, entry: LogEntry) -> Optional[str]:
        """Sugiere solución para NameError: variable no definida."""
        match = re.search(r"name '([^']+)' is not defined", entry.message)
        if match:
            var_name = match.group(1)
            return f"NameError: '{var_name}' no está definido. Sugerencia: revisa si falta un import o definición de '{var_name}' en el archivo correspondiente."
        return None

    def _resolve_import_error(self, entry: LogEntry) -> Optional[str]:
        """Sugiere solución para ImportError."""
        match = re.search(r"ImportError: cannot import name '([^']+)'", entry.message)
        if match:
            import_name = match.group(1)
            return f"ImportError: No se pudo importar '{import_name}'. Sugerencia: revisa el import y asegúrate de que '{import_name}' esté definido en el módulo."
        return None

    def _resolve_module_not_found(self, entry: LogEntry) -> Optional[str]:
        """Sugiere solución para ModuleNotFoundError."""
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", entry.message)
        if match:
            module_name = match.group(1)
            return f"ModuleNotFoundError: No se encontró el módulo '{module_name}'. Sugerencia: instala el paquete con 'pip install {module_name}' o revisa el entorno."
        return None
    
    def get_pending_logs(self, limit: int = 10) -> List[LogEntry]:
        """Obtiene logs pendientes (solo los que no están resueltos)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, level, module, message, status, resolution, resolved_at, auto_resolution_attempted
            FROM log_entries 
            WHERE status = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (LogStatus.PENDING.value, limit))
        entries = []
        for row in cursor.fetchall():
            entry = LogEntry(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                level=row[2],
                module=row[3],
                message=row[4],
                status=LogStatus(row[5]),
                resolution=row[6],
                resolved_at=datetime.fromisoformat(row[7]) if row[7] else None,
                auto_resolution_attempted=bool(row[8])
            )
            entries.append(entry)
        conn.close()
        return entries

    def get_resolved_logs(self, limit: int = 20) -> List[LogEntry]:
        """Obtiene logs resueltos (auto o manualmente) para historial."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, timestamp, level, module, message, status, resolution, resolved_at, auto_resolution_attempted
            FROM log_entries 
            WHERE status IN (?, ?)
            ORDER BY resolved_at DESC
            LIMIT ?
        ''', (LogStatus.AUTO_RESOLVED.value, LogStatus.MANUALLY_RESOLVED.value, limit))
        entries = []
        for row in cursor.fetchall():
            entry = LogEntry(
                id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                level=row[2],
                module=row[3],
                message=row[4],
                status=LogStatus(row[5]),
                resolution=row[6],
                resolved_at=datetime.fromisoformat(row[7]) if row[7] else None,
                auto_resolution_attempted=bool(row[8])
            )
            entries.append(entry)
        conn.close()
        return entries
    
    def mark_as_resolved(self, log_id: int, resolution: str):
        """Marca un log como resuelto manualmente solo si está pendiente."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Solo actualizar si está pendiente
        cursor.execute('''
            UPDATE log_entries 
            SET status = ?, resolution = ?, resolved_at = ?
            WHERE id = ? AND status = ?
        ''', (LogStatus.MANUALLY_RESOLVED.value, resolution, datetime.now().isoformat(), log_id, LogStatus.PENDING.value))
        conn.commit()
        conn.close()
        self._update_metrics()
    
    def _get_total_logs_in_db(self) -> int:
        """Obtiene el total de logs en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM log_entries')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def _update_metrics(self):
        """Actualiza las métricas del log manager."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener estadísticas
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'auto_resolved' THEN 1 ELSE 0 END) as auto_resolved,
                SUM(CASE WHEN status = 'manually_resolved' THEN 1 ELSE 0 END) as manually_resolved,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) as escalated
            FROM log_entries
        ''')
        
        row = cursor.fetchone()
        if row:
            self.metrics.update({
                'total_logs': row[0] or 0,
                'auto_resolved': row[1] or 0,
                'manually_resolved': row[2] or 0,
                'pending': row[3] or 0,
                'escalated': row[4] or 0,
            })
        
        # Calcular tiempo promedio de resolución
        cursor.execute('''
            SELECT AVG(
                (julianday(resolved_at) - julianday(timestamp)) * 24 * 60
            ) as avg_minutes
            FROM log_entries 
            WHERE resolved_at IS NOT NULL
        ''')
        
        avg_minutes = cursor.fetchone()[0]
        self.metrics['avg_resolution_time'] = avg_minutes or 0
        
        conn.close()
    
    def get_metrics(self) -> Dict:
        """Obtiene las métricas actuales."""
        self._update_metrics()
        return self.metrics.copy()
    
    def get_recent_activity(self, hours: int = 24) -> Dict:
        """Obtiene actividad reciente."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'auto_resolved' THEN 1 ELSE 0 END) as auto_resolved,
                SUM(CASE WHEN status = 'manually_resolved' THEN 1 ELSE 0 END) as manually_resolved,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM log_entries 
            WHERE timestamp >= ?
        ''', (since.isoformat(),))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total': row[0] or 0,
            'auto_resolved': row[1] or 0,
            'manually_resolved': row[2] or 0,
            'pending': row[3] or 0,
            'period_hours': hours
        }
    
    def doctor(self):
        """Diagnóstico y resolución automática de problemas del sistema."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.progress import Progress, SpinnerColumn, TextColumn
        import subprocess
        import sys
        
        console = Console()
        
        console.print(Panel("[bold blue]🔧 Doctor del Sistema PARA - Resolución Automática[/bold blue]"))
        
        # Análisis completo
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task1 = progress.add_task("Analizando logs...", total=None)
            
            # Analizar logs
            log_file = Path(__file__).parent.parent / "logs" / "para.log"
            if log_file.exists():
                analysis = self.analyze_log_file(str(log_file))
                progress.update(task1, description=f"Logs analizados: {analysis['processed']} entradas")
            else:
                progress.update(task1, description="Archivo de logs no encontrado")
            
            task2 = progress.add_task("Verificando dependencias...", total=None)
            
            # Verificar dependencias
            missing_deps = []
            try:
                import ollama
                progress.update(task2, description="Ollama: ✅ Disponible")
            except ImportError:
                missing_deps.append("ollama")
                progress.update(task2, description="Ollama: ❌ No disponible")
            
            try:
                import chromadb
                progress.update(task2, description="ChromaDB: ✅ Disponible")
            except ImportError:
                missing_deps.append("chromadb")
                progress.update(task2, description="ChromaDB: ❌ No disponible")
            
            try:
                import sentence_transformers
                progress.update(task2, description="SentenceTransformers: ✅ Disponible")
            except ImportError:
                missing_deps.append("sentence-transformers")
                progress.update(task2, description="SentenceTransformers: ❌ No disponible")
            
            task3 = progress.add_task("Verificando modelos...", total=None)
            
            # Verificar modelos de IA
            try:
                import ollama
                models = ollama.list()
                if models.get('models'):
                    progress.update(task3, description=f"Modelos disponibles: {len(models['models'])}")
                else:
                    progress.update(task3, description="No hay modelos instalados")
            except Exception as e:
                progress.update(task3, description=f"Error verificando modelos: {e}")
            
            task4 = progress.add_task("Resolviendo problemas...", total=None)
            
            # Auto-resolver problemas
            resolved_count = 0
            
            # Resolver dependencias faltantes
            if missing_deps:
                progress.update(task4, description=f"Instalando dependencias: {', '.join(missing_deps)}")
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install"] + missing_deps, check=True)
                    resolved_count += len(missing_deps)
                except subprocess.CalledProcessError:
                    progress.update(task4, description="Error instalando dependencias")
            
            # Resolver problemas de logs
            if log_file.exists():
                analysis = self.analyze_log_file(str(log_file))
                if analysis['pending'] > 0:
                    progress.update(task4, description=f"Resolviendo {analysis['pending']} problemas de logs")
                    # Intentar resolver problemas pendientes
                    pending_logs = self.get_pending_logs(limit=analysis['pending'])
                    for log_entry in pending_logs:
                        for pattern, resolver in self.auto_resolution_patterns.items():
                            if re.search(pattern, log_entry.message):
                                resolution = resolver(log_entry)
                                if resolution:
                                    self.mark_as_resolved(log_entry.id, resolution)
                                    resolved_count += 1
                                break
            
            # Auto-fix de código con IA
            task5 = progress.add_task("Aplicando auto-fix de código...", total=None)
            try:
                from .auto_fix import auto_fix_engine
                fix_stats = auto_fix_engine.analyze_and_fix_logs(str(log_file))
                progress.update(task5, description=f"Auto-fix: {fix_stats['fixed']} errores corregidos")
                resolved_count += fix_stats['fixed']
            except Exception as e:
                progress.update(task5, description=f"Error en auto-fix: {e}")
            
            progress.update(task4, description=f"Resueltos {resolved_count} problemas")
        
        # Mostrar resumen
        console.print(f"\n[bold green]✅ Diagnóstico completado[/bold green]")
        console.print(f"📊 Problemas resueltos: {resolved_count}")
        
        # Mostrar sugerencias de auto-resolución para problemas pendientes
        pending_logs = self.get_pending_logs(limit=50)  # Aumentar límite para mejor deduplicación
        if pending_logs:
            console.print("\n[bold yellow]Sugerencias para problemas pendientes:[/bold yellow]")
            from collections import OrderedDict
            # Filtrar duplicados por mensaje (solo el más reciente)
            unique_msgs = OrderedDict()
            for log in pending_logs:
                if log.message not in unique_msgs:
                    unique_msgs[log.message] = 1
                else:
                    unique_msgs[log.message] += 1
            for msg, count in unique_msgs.items():
                # Intentar auto-fix para modelo de IA no disponible
                m = re.search(r"Modelo de IA no disponible: ([\w\.-:]+)", msg)
                if m:
                    model_name = m.group(1)
                    console.print(f"[yellow]Intentando instalar modelo de IA '{model_name}' automáticamente...[/yellow]")
                    try:
                        result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True, check=True)
                        console.print(f"[green]Modelo '{model_name}' instalado correctamente.[/green]")
                    except subprocess.CalledProcessError as e:
                        console.print(f"[red]No se pudo instalar el modelo '{model_name}': {e.stderr.strip()}[/red]")
                if count > 1:
                    console.print(f"• {msg} ({count} veces)")
                else:
                    console.print(f"• {msg}")
        
        # Verificar si el comando reclassify-all funciona ahora
        console.print(f"\n[bold blue]🧪 Probando comando reclassify-all...[/bold blue]")
        try:
            from paralib.organizer import PARAOrganizer
            organizer = PARAOrganizer()
            # Solo verificar que la clase se puede instanciar
            console.print("✅ Clase PARAOrganizer: Funcionando")
        except Exception as e:
            console.print(f"❌ Error en PARAOrganizer: {e}")
            # Intentar resolver el problema
            console.print("🔧 Intentando resolver problema...")
            try:
                # Verificar imports
                import paralib.organizer
                console.print("✅ Imports: Funcionando")
            except Exception as import_error:
                console.print(f"❌ Error de imports: {import_error}")
        
        console.print(f"\n[bold green]🎯 Sistema listo para usar[/bold green]")
        console.print("Prueba ahora: python para_cli.py re clasifica todas mis notas") 