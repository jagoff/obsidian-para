#!/usr/bin/env python3
"""
paralib/backup_manager.py

Backup Manager para PARA System v2.0
- Backup automático del vault
- Backup de configuración y logs
- Restore inteligente
- Gestión de versiones
- Integración con dashboard
- Auto-scheduler de backups
"""
import shutil
import zipfile
import json
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import hashlib

from .log_center import log_center, log_function_call

@dataclass
class BackupInfo:
    """Información de un backup."""
    id: str
    timestamp: datetime
    vault_path: str
    size_mb: float
    file_count: int
    backup_type: str  # 'full', 'incremental', 'config'
    description: str
    checksum: str
    status: str  # 'completed', 'failed', 'in_progress'
    metadata: Dict[str, Any]

class PARABackupManager:
    """Gestor de backups del sistema PARA."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configuración
        self.max_backups = 10
        self.auto_backup_enabled = True
        self.backup_interval_hours = 24
        
        # Estado
        self.last_backup = None
        self.backups = []
        
        # Auto-scheduler
        self._scheduler_running = False
        self._scheduler_thread = None
        
        # Cargar backups existentes
        self._load_existing_backups()
        
        # Iniciar auto-scheduler si está habilitado
        if self.auto_backup_enabled:
            self.start_auto_scheduler()
        
        log_center.log_info("Backup Manager inicializado", component='BackupManager')
    
    def _load_existing_backups(self):
        """Carga información de backups existentes."""
        try:
            self.backups = []
            
            for backup_file in self.backup_dir.glob("para_backup_*.zip"):
                try:
                    info = self._extract_backup_info(backup_file)
                    if info:
                        self.backups.append(info)
                except Exception as e:
                    log_center.log_error(f"Error cargando backup {backup_file}: {e}", component='BackupManager')
            
            # Ordenar por timestamp
            self.backups.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Actualizar último backup
            if self.backups:
                self.last_backup = self.backups[0]
            
            log_center.log_info(f"Cargados {len(self.backups)} backups existentes", component='BackupManager')
            
        except Exception as e:
            log_center.log_error(f"Error cargando backups existentes: {e}", component='BackupManager')
    
    def _extract_backup_info(self, backup_file: Path) -> Optional[BackupInfo]:
        """Extrae información de un archivo de backup."""
        try:
            # Leer metadata del zip
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                if 'metadata.json' in zip_ref.namelist():
                    metadata_content = zip_ref.read('metadata.json')
                    metadata = json.loads(metadata_content.decode('utf-8'))
                    
                    return BackupInfo(
                        id=metadata.get('id', backup_file.stem),
                        timestamp=datetime.fromisoformat(metadata.get('timestamp', '')),
                        vault_path=metadata.get('vault_path', ''),
                        size_mb=backup_file.stat().st_size / (1024 * 1024),
                        file_count=metadata.get('file_count', 0),
                        backup_type=metadata.get('backup_type', 'full'),
                        description=metadata.get('description', ''),
                        checksum=metadata.get('checksum', ''),
                        status=metadata.get('status', 'completed'),
                        metadata=metadata
                    )
            
            return None
            
        except Exception as e:
            log_center.log_error(f"Error extrayendo info de {backup_file}: {e}", component='BackupManager')
            return None
    
    @log_function_call
    def create_backup(self, vault_path: str, backup_type: str = 'full', description: str = '') -> Optional[BackupInfo]:
        """Crea un nuevo backup."""
        try:
            log_center.log_info(f"Iniciando backup {backup_type} del vault: {vault_path}", component='BackupManager')
            
            # Generar ID único
            backup_id = f"para_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_file = self.backup_dir / f"{backup_id}.zip"
            
            # Crear backup
            if backup_type == 'full':
                success = self._create_full_backup(vault_path, backup_file)
            elif backup_type == 'config':
                success = self._create_config_backup(backup_file)
            else:
                success = self._create_incremental_backup(vault_path, backup_file)
            
            if not success:
                log_center.log_error("Falló la creación del backup", component='BackupManager')
                return None
            
            # Crear metadata
            metadata = self._create_backup_metadata(backup_id, vault_path, backup_type, description, backup_file)
            
            # Crear objeto BackupInfo
            backup_info = BackupInfo(
                id=backup_id,
                timestamp=datetime.now(),
                vault_path=vault_path,
                size_mb=backup_file.stat().st_size / (1024 * 1024),
                file_count=metadata.get('file_count', 0),
                backup_type=backup_type,
                description=description,
                checksum=metadata.get('checksum', ''),
                status='completed',
                metadata=metadata
            )
            
            # Agregar a la lista
            self.backups.insert(0, backup_info)
            self.last_backup = backup_info
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            log_center.log_info(
                f"Backup completado: {backup_id} ({backup_info.size_mb:.1f} MB)",
                component='BackupManager'
            )
            
            return backup_info
            
        except Exception as e:
            log_center.log_error(f"Error creando backup: {e}", component='BackupManager')
            return None
    
    def _create_full_backup(self, vault_path: str, backup_file: Path) -> bool:
        """Crea un backup completo del vault."""
        try:
            vault_path_obj = Path(vault_path)
            if not vault_path_obj.exists():
                log_center.log_error(f"Vault no encontrado: {vault_path}", component='BackupManager')
                return False
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                # Backup del vault
                for file_path in vault_path_obj.rglob('*'):
                    if file_path.is_file():
                        # Excluir archivos del sistema PARA
                        if '.para_db' in str(file_path) or '.git' in str(file_path):
                            continue
                        
                        arcname = file_path.relative_to(vault_path_obj)
                        zip_ref.write(file_path, arcname)
                
                # Backup de configuración
                config_files = ['para_config.default.json', 'requirements.txt']
                for config_file in config_files:
                    if Path(config_file).exists():
                        zip_ref.write(config_file, f"config/{config_file}")
                
                # Backup de logs recientes
                log_dir = Path("logs")
                if log_dir.exists():
                    for log_file in log_dir.glob("*.log"):
                        if log_file.stat().st_size < 10 * 1024 * 1024:  # Solo logs < 10MB
                            zip_ref.write(log_file, f"logs/{log_file.name}")
            
            return True
            
        except Exception as e:
            log_center.log_error(f"Error en backup completo: {e}", component='BackupManager')
            return False
    
    def _create_config_backup(self, backup_file: Path) -> bool:
        """Crea un backup solo de configuración."""
        try:
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                # Archivos de configuración
                config_files = [
                    'para_config.default.json',
                    'requirements.txt',
                    'plugins/plugins_config.json'
                ]
                
                for config_file in config_files:
                    if Path(config_file).exists():
                        zip_ref.write(config_file, config_file)
                
                # Configuración del sistema
                system_config = {
                    'timestamp': datetime.now().isoformat(),
                    'python_version': os.sys.version,
                    'platform': os.name,
                    'backup_type': 'config'
                }
                
                zip_ref.writestr('system_config.json', json.dumps(system_config, indent=2))
            
            return True
            
        except Exception as e:
            log_center.log_error(f"Error en backup de configuración: {e}", component='BackupManager')
            return False
    
    def _create_incremental_backup(self, vault_path: str, backup_file: Path) -> bool:
        """Crea un backup incremental."""
        try:
            # Por ahora, igual que full backup
            return self._create_full_backup(vault_path, backup_file)
            
        except Exception as e:
            log_center.log_error(f"Error en backup incremental: {e}", component='BackupManager')
            return False
    
    def _create_backup_metadata(self, backup_id: str, vault_path: str, backup_type: str, 
                               description: str, backup_file: Path) -> Dict[str, Any]:
        """Crea metadata del backup."""
        try:
            # Calcular checksum
            checksum = self._calculate_file_checksum(backup_file)
            
            # Contar archivos
            file_count = 0
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                file_count = len(zip_ref.namelist())
            
            metadata = {
                'id': backup_id,
                'timestamp': datetime.now().isoformat(),
                'vault_path': vault_path,
                'backup_type': backup_type,
                'description': description,
                'checksum': checksum,
                'file_count': file_count,
                'size_bytes': backup_file.stat().st_size,
                'status': 'completed',
                'created_by': 'PARA_BackupManager',
                'version': '2.0'
            }
            
            # Guardar metadata en el zip
            with zipfile.ZipFile(backup_file, 'a') as zip_ref:
                zip_ref.writestr('metadata.json', json.dumps(metadata, indent=2))
            
            return metadata
            
        except Exception as e:
            log_center.log_error(f"Error creando metadata: {e}", component='BackupManager')
            return {}
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calcula el checksum de un archivo."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _cleanup_old_backups(self):
        """Limpia backups antiguos."""
        try:
            if len(self.backups) <= self.max_backups:
                return
            
            # Mantener solo los más recientes
            backups_to_remove = self.backups[self.max_backups:]
            
            for backup_info in backups_to_remove:
                backup_file = self.backup_dir / f"{backup_info.id}.zip"
                if backup_file.exists():
                    backup_file.unlink()
                    log_center.log_info(f"Backup eliminado: {backup_info.id}", component='BackupManager')
            
            # Actualizar lista
            self.backups = self.backups[:self.max_backups]
            
        except Exception as e:
            log_center.log_error(f"Error limpiando backups antiguos: {e}", component='BackupManager')
    
    @log_function_call
    def restore_backup(self, backup_id: str, target_path: str = None, 
                      restore_type: str = 'full') -> bool:
        """Restaura un backup."""
        try:
            log_center.log_info(f"Iniciando restore del backup: {backup_id}", component='BackupManager')
            
            # Encontrar backup
            backup_info = next((b for b in self.backups if b.id == backup_id), None)
            if not backup_info:
                log_center.log_error(f"Backup no encontrado: {backup_id}", component='BackupManager')
                return False
            
            backup_file = self.backup_dir / f"{backup_id}.zip"
            if not backup_file.exists():
                log_center.log_error(f"Archivo de backup no encontrado: {backup_file}", component='BackupManager')
                return False
            
            # Verificar checksum
            if not self._verify_backup_checksum(backup_file, backup_info.checksum):
                log_center.log_error(f"Checksum inválido para backup: {backup_id}", component='BackupManager')
                return False
            
            # Crear backup del estado actual antes de restaurar
            if target_path and Path(target_path).exists():
                current_backup = self.create_backup(target_path, 'config', f'Pre-restore backup for {backup_id}')
                if not current_backup:
                    log_center.log_warning("No se pudo crear backup del estado actual", component='BackupManager')
            
            # Restaurar
            success = self._perform_restore(backup_file, target_path, restore_type)
            
            if success:
                log_center.log_info(f"Restore completado: {backup_id}", component='BackupManager')
            else:
                log_center.log_error(f"Restore falló: {backup_id}", component='BackupManager')
            
            return success
            
        except Exception as e:
            log_center.log_error(f"Error en restore: {e}", component='BackupManager')
            return False
    
    def _verify_backup_checksum(self, backup_file: Path, expected_checksum: str) -> bool:
        """Verifica el checksum de un backup."""
        try:
            if not expected_checksum:
                return True  # Sin checksum para verificar
            
            actual_checksum = self._calculate_file_checksum(backup_file)
            return actual_checksum == expected_checksum
            
        except Exception:
            return False
    
    def _perform_restore(self, backup_file: Path, target_path: str, restore_type: str) -> bool:
        """Realiza la restauración."""
        try:
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                if restore_type == 'full':
                    # Restaurar todo
                    if target_path:
                        # Limpiar directorio objetivo
                        target_path_obj = Path(target_path)
                        if target_path_obj.exists():
                            shutil.rmtree(target_path_obj)
                        target_path_obj.mkdir(parents=True)
                        
                        # Extraer todo
                        zip_ref.extractall(target_path)
                    else:
                        # Extraer en ubicación original
                        zip_ref.extractall('.')
                
                elif restore_type == 'config':
                    # Restaurar solo configuración
                    config_files = [f for f in zip_ref.namelist() if f.startswith('config/')]
                    for config_file in config_files:
                        zip_ref.extract(config_file, '.')
                        # Mover de config/ a raíz
                        extracted_path = Path(config_file)
                        if extracted_path.exists():
                            extracted_path.rename(extracted_path.name)
                
                elif restore_type == 'selective':
                    # Restauración selectiva
                    # Implementar según necesidades específicas
                    pass
            
            return True
            
        except Exception as e:
            log_center.log_error(f"Error en restauración: {e}", component='BackupManager')
            return False
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de backups."""
        try:
            total_size = sum(b.size_mb for b in self.backups)
            total_files = sum(b.file_count for b in self.backups)
            
            # Agrupar por tipo
            by_type = {}
            for backup in self.backups:
                backup_type = backup.backup_type
                if backup_type not in by_type:
                    by_type[backup_type] = {'count': 0, 'size': 0}
                by_type[backup_type]['count'] += 1
                by_type[backup_type]['size'] += backup.size_mb
            
            return {
                'total_backups': len(self.backups),
                'total_size_mb': total_size,
                'total_files': total_files,
                'last_backup': self.last_backup.timestamp.isoformat() if self.last_backup else None,
                'by_type': by_type,
                'auto_backup_enabled': self.auto_backup_enabled,
                'max_backups': self.max_backups
            }
            
        except Exception as e:
            log_center.log_error(f"Error obteniendo stats de backup: {e}", component='BackupManager')
            return {}
    
    def should_create_auto_backup(self) -> bool:
        """Determina si se debe crear un backup automático."""
        if not self.auto_backup_enabled:
            return False
        
        if not self.last_backup:
            return True
        
        time_since_last = datetime.now() - self.last_backup.timestamp
        return time_since_last.total_seconds() > (self.backup_interval_hours * 3600)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todos los backups disponibles."""
        try:
            return [{
                'id': backup.id,
                'timestamp': backup.timestamp.isoformat(),
                'vault_path': backup.vault_path,
                'size_mb': backup.size_mb,
                'file_count': backup.file_count,
                'backup_type': backup.backup_type,
                'description': backup.description,
                'status': backup.status
            } for backup in self.backups]
            
        except Exception as e:
            log_center.log_error(f"Error listando backups: {e}", component='BackupManager')
            return []
    
    def delete_backup(self, backup_id: str) -> bool:
        """Elimina un backup específico."""
        try:
            backup_info = next((b for b in self.backups if b.id == backup_id), None)
            if not backup_info:
                log_center.log_error(f"Backup no encontrado para eliminar: {backup_id}", component='BackupManager')
                return False
            
            backup_file = self.backup_dir / f"{backup_id}.zip"
            if backup_file.exists():
                backup_file.unlink()
            
            self.backups.remove(backup_info)
            
            log_center.log_info(f"Backup eliminado: {backup_id}", component='BackupManager')
            return True
            
        except Exception as e:
            log_center.log_error(f"Error eliminando backup: {e}", component='BackupManager')
            return False
    
    def start_auto_scheduler(self):
        """Inicia el scheduler automático de backups."""
        if self._scheduler_running:
            return
        
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._auto_scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        log_center.log_info("Auto-scheduler de backups iniciado", component='BackupManager')
    
    def stop_auto_scheduler(self):
        """Detiene el scheduler automático."""
        self._scheduler_running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        log_center.log_info("Auto-scheduler de backups detenido", component='BackupManager')
    
    def _auto_scheduler_loop(self):
        """Loop principal del auto-scheduler."""
        while self._scheduler_running:
            try:
                # Verificar si necesita backup automático
                if self.should_create_auto_backup():
                    self._create_auto_backup()
                
                # Dormir por 1 hora antes de verificar de nuevo
                for _ in range(3600):  # 3600 segundos = 1 hora
                    if not self._scheduler_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                log_center.log_error(f"Error en auto-scheduler: {e}", component='BackupManager')
                time.sleep(300)  # Esperar 5 minutos antes de reintentar
    
    def _create_auto_backup(self):
        """Crea un backup automático."""
        try:
            # Buscar vault automáticamente
            from .vault import find_vault
            vault_path = find_vault()
            
            if not vault_path:
                log_center.log_warning("No se pudo encontrar vault para backup automático", component='BackupManager')
                return
            
            # Crear backup automático
            description = f"Backup automático - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            backup_info = self.create_backup(str(vault_path), 'full', description)
            
            if backup_info:
                log_center.log_info(f"Backup automático creado: {backup_info.id}", component='BackupManager')
            else:
                log_center.log_error("Falló la creación del backup automático", component='BackupManager')
                
        except Exception as e:
            log_center.log_error(f"Error en backup automático: {e}", component='BackupManager')
    
    def set_auto_backup_interval(self, hours: int):
        """Configura el intervalo de backup automático."""
        self.backup_interval_hours = hours
        log_center.log_info(f"Intervalo de backup automático configurado a {hours} horas", component='BackupManager')
    
    def enable_auto_backup(self, enabled: bool = True):
        """Habilita o deshabilita el backup automático."""
        self.auto_backup_enabled = enabled
        
        if enabled and not self._scheduler_running:
            self.start_auto_scheduler()
        elif not enabled and self._scheduler_running:
            self.stop_auto_scheduler()
            
        log_center.log_info(f"Backup automático {'habilitado' if enabled else 'deshabilitado'}", component='BackupManager')
    
    def __del__(self):
        """Destructor para limpiar el scheduler."""
        try:
            self.stop_auto_scheduler()
        except:
            pass

# Instancia global
backup_manager = PARABackupManager() 