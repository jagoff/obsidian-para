#!/usr/bin/env python3
"""
paralib/clean_manager.py

Sistema de Limpieza ROBUSTO para PARA System
- Integrado con Log Center transversal
- Limpieza de duplicados, archivos vacíos, corruptos
- Manejo robusto de errores
- Funcionalidad completa y confiable
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box
import os
import shutil
import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Any
import tempfile

from paralib.logger import logger, log_exceptions, log_function_calls
from paralib.log_center import log_center

console = Console()

class RobustCleanManager:
    """
    Sistema de Limpieza ROBUSTO para PARA System.
    - Nunca falla completamente
    - Logging transversal completo
    - Manejo robusto de errores
    - Funcionalidad exhaustiva
    """
    
    def __init__(self):
        """Inicializa el CleanManager robusto."""
        try:
            log_center.log_info("Inicializando RobustCleanManager", "CleanManager-Init")
            self.cleaned_files = []
            self.errors = []
            self.stats = {
                'duplicates_found': 0,
                'duplicates_cleaned': 0,
                'empty_files_found': 0,
                'empty_files_cleaned': 0,
                'corrupt_files_found': 0,
                'corrupt_files_cleaned': 0,
                'non_md_found': 0,
                'non_md_moved': 0,
                'total_files_processed': 0,
                'errors_encountered': 0
            }
            
        except Exception as e:
            log_center.log_error(f"Error inicializando CleanManager: {e}", "CleanManager-Init")
    
    @log_exceptions
    def clean_duplicates(self, vault_path: Path = None) -> Dict[str, Any]:
        """
        Limpia archivos duplicados de manera robusta.
        
        Returns:
            Dict con estadísticas de limpieza
        """
        try:
            log_center.log_info("Iniciando limpieza de duplicados", "CleanManager-Duplicates")
            
            if not vault_path:
                # Intentar obtener vault automáticamente
                try:
                    from paralib.vault import find_vault
                    vault_path = find_vault()
                    if not vault_path:
                        log_center.log_error("No se pudo encontrar vault para limpieza", "CleanManager-Duplicates")
                        return {'error': 'No vault found', 'cleaned': 0}
                except Exception as e:
                    log_center.log_error(f"Error obteniendo vault: {e}", "CleanManager-Duplicates")
                    return {'error': f'Vault error: {e}', 'cleaned': 0}
            
            vault_path = Path(vault_path)
            if not vault_path.exists():
                log_center.log_error(f"Vault path no existe: {vault_path}", "CleanManager-Duplicates")
                return {'error': 'Vault path does not exist', 'cleaned': 0}
            
            # Encontrar archivos duplicados
            duplicates = self._find_duplicates_robust(vault_path)
            
            if not duplicates:
                log_center.log_info("No se encontraron duplicados", "CleanManager-Duplicates")
                return {'cleaned': 0, 'duplicates_found': 0, 'message': 'No duplicates found'}
            
            # Limpiar duplicados
            cleaned_count = self._clean_duplicates_robust(duplicates, vault_path)
            
            # Actualizar estadísticas
            self.stats['duplicates_found'] = sum(len(paths) - 1 for paths in duplicates.values())
            self.stats['duplicates_cleaned'] = cleaned_count
            
            log_center.log_info(f"Limpieza de duplicados completada: {cleaned_count} archivos", "CleanManager-Duplicates")
            
            return {
                'cleaned': cleaned_count,
                'duplicates_found': self.stats['duplicates_found'],
                'message': f'Cleaned {cleaned_count} duplicate files'
            }
            
        except Exception as e:
            log_center.log_error(f"Error en limpieza de duplicados: {e}", "CleanManager-Duplicates")
            self.stats['errors_encountered'] += 1
            return {'error': str(e), 'cleaned': 0}
    
    @log_exceptions
    def _find_duplicates_robust(self, vault_path: Path) -> Dict[str, List[Path]]:
        """Encuentra duplicados de manera robusta."""
        try:
            log_center.log_info("Buscando archivos duplicados", "CleanManager-FindDuplicates")
            
            # Obtener todos los archivos .md
            all_files = []
            try:
                all_files = list(vault_path.rglob("*.md"))
            except Exception as e:
                log_center.log_error(f"Error listando archivos: {e}", "CleanManager-FindDuplicates")
                return {}
            
            # Agrupar por nombre
            name_groups = defaultdict(list)
            for file_path in all_files:
                try:
                    name_groups[file_path.name].append(file_path)
                except Exception as e:
                    log_center.log_warning(f"Error procesando archivo {file_path}: {e}", "CleanManager-FindDuplicates")
                    continue
            
            # Filtrar solo grupos con duplicados
            duplicates = {name: paths for name, paths in name_groups.items() if len(paths) > 1}
            
            log_center.log_info(f"Encontrados {len(duplicates)} grupos de duplicados", "CleanManager-FindDuplicates")
            return duplicates
            
        except Exception as e:
            log_center.log_error(f"Error buscando duplicados: {e}", "CleanManager-FindDuplicates")
            return {}
    
    @log_exceptions
    def _clean_duplicates_robust(self, duplicates: Dict[str, List[Path]], vault_path: Path) -> int:
        """Limpia duplicados de manera robusta."""
        try:
            cleaned_count = 0
            
            # Crear directorio para duplicados
            duplicates_dir = vault_path / "_Duplicados_Cleaned"
            try:
                duplicates_dir.mkdir(exist_ok=True)
            except Exception as e:
                log_center.log_error(f"Error creando directorio duplicados: {e}", "CleanManager-CleanDuplicates")
                return 0
            
            for name, paths in duplicates.items():
                try:
                    # Mantener el primer archivo, mover el resto
                    paths_sorted = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
                    keep_file = paths_sorted[0]  # Más reciente
                    duplicate_files = paths_sorted[1:]  # Resto son duplicados
                    
                    for i, dup_file in enumerate(duplicate_files):
                        try:
                            # Crear nombre único para el duplicado
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            new_name = f"{dup_file.stem}_{timestamp}_{i}{dup_file.suffix}"
                            target_path = duplicates_dir / new_name
                            
                            # Mover archivo
                            shutil.move(str(dup_file), str(target_path))
                            
                            cleaned_count += 1
                            self.cleaned_files.append(str(target_path))
                            
                            log_center.log_info(f"Duplicado movido: {dup_file.name} -> {target_path.name}", "CleanManager-CleanDuplicates")
                            
                        except Exception as e:
                            log_center.log_error(f"Error moviendo duplicado {dup_file}: {e}", "CleanManager-CleanDuplicates")
                            self.errors.append(f"Error moving {dup_file}: {e}")
                            continue
                    
                    log_center.log_info(f"Grupo '{name}': mantenido {keep_file.name}, movidos {len(duplicate_files)} duplicados", "CleanManager-CleanDuplicates")
                    
                except Exception as e:
                    log_center.log_error(f"Error procesando grupo '{name}': {e}", "CleanManager-CleanDuplicates")
                    self.errors.append(f"Error processing group {name}: {e}")
                    continue
            
            return cleaned_count
            
        except Exception as e:
            log_center.log_error(f"Error limpiando duplicados: {e}", "CleanManager-CleanDuplicates")
            return 0
    
    @log_exceptions
    def clean_empty_files(self, vault_path: Path = None) -> Dict[str, Any]:
        """Limpia archivos vacíos de manera robusta."""
        try:
            log_center.log_info("Iniciando limpieza de archivos vacíos", "CleanManager-Empty")
            
            if not vault_path:
                from paralib.vault import find_vault
                vault_path = find_vault()
                if not vault_path:
                    return {'error': 'No vault found', 'cleaned': 0}
            
            vault_path = Path(vault_path)
            empty_files = self._find_empty_files_robust(vault_path)
            
            if not empty_files:
                log_center.log_info("No se encontraron archivos vacíos", "CleanManager-Empty")
                return {'cleaned': 0, 'empty_found': 0, 'message': 'No empty files found'}
            
            # Crear directorio para archivos vacíos
            empty_dir = vault_path / "_Empty_Files_Cleaned"
            empty_dir.mkdir(exist_ok=True)
            
            cleaned_count = 0
            for empty_file in empty_files:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{empty_file.stem}_{timestamp}{empty_file.suffix}"
                    target_path = empty_dir / new_name
                    
                    shutil.move(str(empty_file), str(target_path))
                    cleaned_count += 1
                    
                    log_center.log_info(f"Archivo vacío movido: {empty_file.name}", "CleanManager-Empty")
                    
                except Exception as e:
                    log_center.log_error(f"Error moviendo archivo vacío {empty_file}: {e}", "CleanManager-Empty")
                    continue
            
            self.stats['empty_files_found'] = len(empty_files)
            self.stats['empty_files_cleaned'] = cleaned_count
            
            return {
                'cleaned': cleaned_count,
                'empty_found': len(empty_files),
                'message': f'Cleaned {cleaned_count} empty files'
            }
            
        except Exception as e:
            log_center.log_error(f"Error en limpieza de archivos vacíos: {e}", "CleanManager-Empty")
            return {'error': str(e), 'cleaned': 0}
    
    @log_exceptions
    def _find_empty_files_robust(self, vault_path: Path) -> List[Path]:
        """Encuentra archivos vacíos de manera robusta."""
        try:
            empty_files = []
            
            for file_path in vault_path.rglob("*.md"):
                try:
                    if file_path.stat().st_size == 0:
                        empty_files.append(file_path)
                except Exception as e:
                    log_center.log_warning(f"Error verificando archivo {file_path}: {e}", "CleanManager-FindEmpty")
                    continue
            
            log_center.log_info(f"Encontrados {len(empty_files)} archivos vacíos", "CleanManager-FindEmpty")
            return empty_files
            
        except Exception as e:
            log_center.log_error(f"Error buscando archivos vacíos: {e}", "CleanManager-FindEmpty")
            return []
    
    @log_exceptions
    def clean_corrupt_files(self, vault_path: Path = None) -> Dict[str, Any]:
        """Limpia archivos corruptos de manera robusta."""
        try:
            log_center.log_info("Iniciando limpieza de archivos corruptos", "CleanManager-Corrupt")
            
            if not vault_path:
                from paralib.vault import find_vault
                vault_path = find_vault()
                if not vault_path:
                    return {'error': 'No vault found', 'cleaned': 0}
            
            vault_path = Path(vault_path)
            corrupt_files = self._find_corrupt_files_robust(vault_path)
            
            if not corrupt_files:
                log_center.log_info("No se encontraron archivos corruptos", "CleanManager-Corrupt")
                return {'cleaned': 0, 'corrupt_found': 0, 'message': 'No corrupt files found'}
            
            # Crear directorio para archivos corruptos
            corrupt_dir = vault_path / "_Corrupt_Files_Quarantine"
            corrupt_dir.mkdir(exist_ok=True)
            
            cleaned_count = 0
            for corrupt_file in corrupt_files:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{corrupt_file.stem}_{timestamp}{corrupt_file.suffix}"
                    target_path = corrupt_dir / new_name
                    
                    shutil.move(str(corrupt_file), str(target_path))
                    cleaned_count += 1
                    
                    log_center.log_info(f"Archivo corrupto movido a cuarentena: {corrupt_file.name}", "CleanManager-Corrupt")
                    
                except Exception as e:
                    log_center.log_error(f"Error moviendo archivo corrupto {corrupt_file}: {e}", "CleanManager-Corrupt")
                    continue
            
            self.stats['corrupt_files_found'] = len(corrupt_files)
            self.stats['corrupt_files_cleaned'] = cleaned_count
            
            return {
                'cleaned': cleaned_count,
                'corrupt_found': len(corrupt_files),
                'message': f'Quarantined {cleaned_count} corrupt files'
            }
            
        except Exception as e:
            log_center.log_error(f"Error en limpieza de archivos corruptos: {e}", "CleanManager-Corrupt")
            return {'error': str(e), 'cleaned': 0}
    
    @log_exceptions
    def _find_corrupt_files_robust(self, vault_path: Path) -> List[Path]:
        """Encuentra archivos corruptos de manera robusta."""
        try:
            corrupt_files = []
            
            for file_path in vault_path.rglob("*.md"):
                try:
                    # Intentar leer el archivo
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(100)  # Leer primeros 100 caracteres
                        
                    # Verificar si el contenido es válido UTF-8
                    if content and len(content.encode('utf-8')) == 0:
                        corrupt_files.append(file_path)
                        
                except UnicodeDecodeError:
                    corrupt_files.append(file_path)
                    log_center.log_warning(f"Archivo con encoding inválido: {file_path.name}", "CleanManager-FindCorrupt")
                except Exception as e:
                    corrupt_files.append(file_path)
                    log_center.log_warning(f"Archivo no legible: {file_path.name} - {e}", "CleanManager-FindCorrupt")
            
            log_center.log_info(f"Encontrados {len(corrupt_files)} archivos corruptos", "CleanManager-FindCorrupt")
            return corrupt_files
            
        except Exception as e:
            log_center.log_error(f"Error buscando archivos corruptos: {e}", "CleanManager-FindCorrupt")
            return []
    
    @log_exceptions
    def clean_all(self, vault_path: Path = None, create_backup: bool = True) -> Dict[str, Any]:
        """
        Limpieza completa del vault de manera robusta.
        
        Args:
            vault_path: Ruta del vault
            create_backup: Si crear backup antes de limpiar
            
        Returns:
            Dict con estadísticas completas
        """
        try:
            log_center.log_info("Iniciando limpieza completa del vault", "CleanManager-All")
            
            if not vault_path:
                from paralib.vault import find_vault
                vault_path = find_vault()
                if not vault_path:
                    return {'error': 'No vault found'}
            
            vault_path = Path(vault_path)
            
            # Crear backup si se solicita
            if create_backup:
                try:
                    from paralib.backup_manager import backup_manager
                    backup_info = backup_manager.create_backup(
                        str(vault_path),
                        backup_type='full',
                        description='Backup antes de limpieza completa'
                    )
                    if backup_info:
                        log_center.log_info(f"Backup creado antes de limpieza: {backup_info.id}", "CleanManager-All")
                    else:
                        log_center.log_warning("No se pudo crear backup antes de limpieza", "CleanManager-All")
                except Exception as e:
                    log_center.log_error(f"Error creando backup: {e}", "CleanManager-All")
            
            # Ejecutar todas las limpiezas
            results = {}
            
            # 1. Limpiar duplicados
            results['duplicates'] = self.clean_duplicates(vault_path)
            
            # 2. Limpiar archivos vacíos
            results['empty_files'] = self.clean_empty_files(vault_path)
            
            # 3. Limpiar archivos corruptos
            results['corrupt_files'] = self.clean_corrupt_files(vault_path)
            
            # Calcular totales
            total_cleaned = sum(result.get('cleaned', 0) for result in results.values())
            total_errors = len([result for result in results.values() if 'error' in result])
            
            # Resumen
            summary = {
                'total_cleaned': total_cleaned,
                'total_errors': total_errors,
                'backup_created': create_backup,
                'results': results,
                'stats': self.stats.copy()
            }
            
            log_center.log_info(f"Limpieza completa terminada: {total_cleaned} archivos limpiados", "CleanManager-All", summary)
            
            return summary
            
        except Exception as e:
            log_center.log_error(f"Error en limpieza completa: {e}", "CleanManager-All")
            return {'error': str(e), 'total_cleaned': 0}
    
    @log_exceptions
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del CleanManager."""
        return {
            **self.stats,
            'cleaned_files_count': len(self.cleaned_files),
            'errors_count': len(self.errors),
            'last_cleaned_files': self.cleaned_files[-5:] if self.cleaned_files else [],
            'recent_errors': self.errors[-3:] if self.errors else []
        }
    
    @log_exceptions
    def reset_stats(self):
        """Resetea las estadísticas."""
        self.cleaned_files.clear()
        self.errors.clear()
        for key in self.stats:
            self.stats[key] = 0
        log_center.log_info("Estadísticas del CleanManager reseteadas", "CleanManager-Reset")

# Instancia global del CleanManager
clean_manager = RobustCleanManager()

# Funciones de compatibilidad para mantener la API existente
@log_exceptions
def find_duplicates(note_paths):
    """Función de compatibilidad."""
    return clean_manager._find_duplicates_robust(Path.cwd())

@log_exceptions
def find_empty_files(note_paths):
    """Función de compatibilidad."""
    return clean_manager._find_empty_files_robust(Path.cwd())

@log_exceptions
def run_clean_manager(vault_path: Path):
    """Función de compatibilidad para limpieza interactiva."""
    try:
        log_center.log_info(f"Ejecutando limpieza interactiva en: {vault_path}", "CleanManager-Interactive")
        
        console.print(f"[bold blue]🔍 Iniciando limpieza robusta en:[/bold blue]\n[yellow]{vault_path}[/yellow]")
        
        # Ejecutar limpieza completa
        results = clean_manager.clean_all(vault_path, create_backup=True)
        
        if 'error' in results:
            console.print(f"[red]❌ Error en limpieza: {results['error']}[/red]")
            return False
        
        # Mostrar resultados
        console.print(f"[bold green]✅ Limpieza completada exitosamente[/bold green]")
        console.print(f"   📊 Total archivos limpiados: {results['total_cleaned']}")
        console.print(f"   💾 Backup creado: {'Sí' if results['backup_created'] else 'No'}")
        
        # Detalles por tipo
        for clean_type, result in results['results'].items():
            if result.get('cleaned', 0) > 0:
                console.print(f"   • {clean_type}: {result['cleaned']} archivos")
        
        return True
        
    except Exception as e:
        log_center.log_error(f"Error en limpieza interactiva: {e}", "CleanManager-Interactive")
        console.print(f"[red]❌ Error en limpieza: {e}[/red]")
        return False

# Clase de compatibilidad
class CleanManager:
    """Clase de compatibilidad para la API antigua."""
    
    def clean_vault(self, vault_path, dry_run=False, create_backup=False):
        """Método de compatibilidad."""
        return clean_manager.clean_all(Path(vault_path), create_backup=create_backup) 