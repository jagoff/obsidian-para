#!/usr/bin/env python3
"""
consolidation_manager.py

Módulo para manejar la consolidación de carpetas en el sistema PARA.
"""
from pathlib import Path
from typing import Dict, List, Any

from paralib.logger import logger
from paralib.log_center import log_center


def consolidate_excessive_folders(vault_path: Path, execute: bool = False) -> Dict[str, int]:
    """
    Consolida carpetas excesivas en grupos más lógicos para reducir fragmentación.
    
    Args:
        vault_path: Ruta del vault
        execute: Si ejecutar la consolidación o solo simular
        
    Returns:
        Diccionario con estadísticas de consolidación
    """
    stats = {
        'total_consolidations': 0,
        'folders_merged': 0,
        'files_moved': 0
    }
    
    # Definir grupos de consolidación por categoría
    consolidation_groups = {
        '01-Projects': {
            'Desarrollo': ['Adam Spec', 'Api', 'Terraform', 'Development', 'Code', 'Programming'],
            'Análisis': ['Analysis', 'Review', 'Análisis', 'Chequeo', 'Check'],
            'BBI': ['Bbi', 'BBI'],
            'Marketing': ['Marketing', 'Launch', 'Lanzamiento'],
            'General': ['Project', 'Task', 'Work']
        },
        '02-Areas': {
            'Personal': ['Personal', 'Health', 'Salud', 'Fitness'],
            'Finanzas': ['Finance', 'Finanzas', 'Money'],
            'Reuniones': ['Meeting', 'Reunión', 'Standup'],
            'Rutinas': ['Routine', 'Habit', 'Rutina']
        },
        '03-Resources': {
            'Tecnología': ['AWS', 'API', 'Database', 'Tech', 'Tutorial', 'Guide'],
            'Documentación': ['Documentation', 'Manual', 'Reference', 'Doc'],
            'Capacitación': ['Training', 'Course', 'Learning', 'Certification'],
            'Herramientas': ['Tools', 'Software', 'App'],
            'Bases de Datos': ['Database', 'DB', 'SQL', 'Chroma'],
            'General': ['Resource', 'Reference', 'Info']
        },
        '04-Archive': {
            'Proyectos Completados': ['Completed', 'Finished', 'Done', 'Completado'],
            'Obsoleto': ['Obsolete', 'Deprecated', 'Old', '2021', '2022'],
            'General': ['Archive', 'Old']
        }
    }
    
    for category, groups in consolidation_groups.items():
        category_path = vault_path / category
        if not category_path.exists():
            continue
        
        print(f"\n📁 Procesando {category}...")
        
        # Obtener todas las carpetas en la categoría
        folders = [f for f in category_path.iterdir() if f.is_dir()]
        
        for group_name, keywords in groups.items():
            matching_folders = []
            
            # Encontrar carpetas que coincidan con las palabras clave
            for folder in folders:
                folder_name_lower = folder.name.lower()
                for keyword in keywords:
                    if keyword.lower() in folder_name_lower:
                        matching_folders.append(folder)
                        break
            
            if len(matching_folders) > 1:  # Solo consolidar si hay más de una carpeta
                print(f"  🔄 Consolidando {len(matching_folders)} carpetas en '{group_name}':")
                
                # Crear carpeta de destino
                target_folder = category_path / group_name
                
                if execute:
                    target_folder.mkdir(exist_ok=True)
                
                # Mover archivos de cada carpeta
                for folder in matching_folders:
                    print(f"    📂 {folder.name} → {group_name}")
                    
                    if execute:
                        try:
                            # Mover todos los archivos .md
                            for md_file in folder.glob("*.md"):
                                target_file = target_folder / md_file.name
                                
                                # Evitar sobrescribir
                                if target_file.exists():
                                    counter = 2
                                    while target_file.exists():
                                        name_parts = md_file.stem, f"_{counter}", md_file.suffix
                                        target_file = target_folder / "".join(name_parts)
                                        counter += 1
                                
                                md_file.rename(target_file)
                                stats['files_moved'] += 1
                            
                            # Eliminar carpeta origen si está vacía
                            if not any(folder.iterdir()):
                                folder.rmdir()
                                stats['folders_merged'] += 1
                                print(f"      ✅ Carpeta eliminada")
                            
                        except Exception as e:
                            print(f"      ⚠️ Error moviendo {folder.name}: {e}")
                            log_center.log_error(f"Error moviendo {folder.name}: {str(e)}", "Consolidation")
                
                stats['total_consolidations'] += 1
    
    return stats


def consolidate_aggressive(vault_path: Path, execute: bool = False) -> Dict[str, int]:
    """
    Consolidación agresiva de carpetas restantes para reducir aún más la fragmentación.
    
    Args:
        vault_path: Ruta del vault
        execute: Si ejecutar la consolidación o solo simular
        
    Returns:
        Diccionario con estadísticas de consolidación
    """
    stats = {
        'total_consolidations': 0,
        'folders_merged': 0,
        'files_moved': 0
    }
    
    # Consolidación agresiva por categoría
    aggressive_groups = {
        '01-Projects': {
            'Proyectos Activos': ['Project', 'Task', 'Work', 'Development', 'Analysis', 'Review'],
            'BBI': ['Bbi', 'BBI'],
            'Marketing': ['Marketing', 'Launch', 'Lanzamiento', 'Campaign'],
            'General': ['General', 'Misc', 'Other']
        },
        '02-Areas': {
            'Personal': ['Personal', 'Health', 'Salud', 'Fitness', 'Equipo'],
            'Finanzas': ['Finance', 'Finanzas', 'Money', 'Budget'],
            'Reuniones': ['Meeting', 'Reunión', 'Standup', 'Call'],
            'Rutinas': ['Routine', 'Habit', 'Rutina', 'Daily']
        },
        '03-Resources': {
            'Tecnología': ['AWS', 'API', 'Database', 'Tech', 'Tutorial', 'Guide', 'Development', 'Programming'],
            'Documentación': ['Documentation', 'Manual', 'Reference', 'Doc', 'Notas', 'Docker'],
            'Capacitación': ['Training', 'Course', 'Learning', 'Certification', 'Avature'],
            'Herramientas': ['Tools', 'Software', 'App', 'AI', 'BBI'],
            'Bases de Datos': ['Database', 'DB', 'SQL', 'Chroma', 'Mysql', 'Wordpress'],
            'Referencias': ['Reference', 'Info', 'Data', 'Statistics', 'Gartner'],
            'General': ['General', 'Misc', 'Other', 'Resource']
        },
        '04-Archive': {
            'Proyectos Completados': ['Completed', 'Finished', 'Done', 'Completado'],
            'Obsoleto': ['Obsolete', 'Deprecated', 'Old', '2021', '2022', '12 Old'],
            'General': ['Archive', 'Old', 'General']
        }
    }
    
    for category, groups in aggressive_groups.items():
        category_path = vault_path / category
        if not category_path.exists():
            continue
        
        print(f"\n📁 Procesando {category} (consolidación agresiva)...")
        
        # Obtener todas las carpetas en la categoría
        folders = [f for f in category_path.iterdir() if f.is_dir() ]
        
        # Agrupar carpetas por similitud de nombre
        folder_groups = {}
        for folder in folders:
            folder_name_lower = folder.name.lower()
            
            # Encontrar el grupo más apropiado
            assigned_group = None
            for group_name, keywords in groups.items():
                for keyword in keywords:
                    if keyword.lower() in folder_name_lower:
                        assigned_group = group_name
                        break
                if assigned_group:
                    break
            
            # Si no se encontró grupo específico, asignar a General
            if not assigned_group:
                assigned_group = 'General'
            
            if assigned_group not in folder_groups:
                folder_groups[assigned_group] = []
            folder_groups[assigned_group].append(folder)
        
        # Consolidar grupos con múltiples carpetas
        for group_name, folder_list in folder_groups.items():
            if len(folder_list) > 1:
                print(f"  🔥 Consolidando {len(folder_list)} carpetas en '{group_name}':")
                
                # Crear carpeta de destino
                target_folder = category_path / group_name
                
                if execute:
                    target_folder.mkdir(exist_ok=True)
                
                # Mover archivos de cada carpeta
                for folder in folder_list:
                    print(f"    📂 {folder.name} → {group_name}")
                    
                    if execute:
                        try:
                            # Mover todos los archivos .md
                            for md_file in folder.glob("*.md"):
                                target_file = target_folder / md_file.name
                                
                                # Evitar sobrescribir
                                if target_file.exists():
                                    counter = 2
                                    while target_file.exists():
                                        name_parts = md_file.stem, f"_{counter}", md_file.suffix
                                        target_file = target_folder / "".join(name_parts)
                                        counter += 1
                                
                                md_file.rename(target_file)
                                stats['files_moved'] += 1
                            
                            # Eliminar carpeta origen si está vacía
                            if not any(folder.iterdir()):
                                folder.rmdir()
                                stats['folders_merged'] += 1
                                print(f"      ✅ Carpeta eliminada")
                            
                        except Exception as e:
                            print(f"      ⚠️ Error moviendo {folder.name}: {e}")
                            log_center.log_error(f"Error moviendo {folder.name}: {str(e)}", "Consolidation-Aggressive")
                
                stats['total_consolidations'] += 1
    
    return stats


def test_naming_system(vault_path: Path) -> None:
    """
    Prueba el sistema de naming inteligente para verificar que no genera sufijos numéricos.
    
    Args:
        vault_path: Ruta del vault
    """
    try:
        # Importar funciones necesarias
        from paralib.intelligent_naming import create_intelligent_name
        from paralib.organizer import _generate_folder_name_from_content
        
        # Crear contenido de prueba
        test_contents = [
            "Proyecto de desarrollo web con React y Node.js",
            "Análisis de datos para el cliente Moka",
            "Documentación técnica de API",
            "Planificación de sprint Q1 2024",
            "Recursos de aprendizaje de Python"
        ]
        
        categories = ['01-Projects', '02-Areas', '03-Resources']
        
        print(f"\n📋 [bold]Probando naming inteligente:[/bold]")
        
        for i, content in enumerate(test_contents, 1):
            print(f"\n{i}. [cyan]Contenido:[/cyan] {content[:50]}...")
            
            # Obtener carpetas existentes para la categoría
            existing_folders = set()
            for category in categories:
                category_path = vault_path / category
                if category_path.exists():
                    try:
                        existing_folders.update({f.name for f in category_path.iterdir() if f.is_dir()})
                    except Exception:
                        pass
            
            # Probar naming inteligente directo
            try:
                intelligent_name = create_intelligent_name([content], 'project', existing_folders, vault_path, '01-Projects')
                print(f"   🧠 [green]Naming inteligente:[/green] '{intelligent_name}'")
            except Exception as e:
                print(f"   ❌ [red]Error naming inteligente:[/red] {e}")
            
            # Probar función del organizer
            try:
                organizer_name = _generate_folder_name_from_content(content, 'Projects', vault_path, existing_folders, True)
                print(f"   📁 [blue]Organizer:[/blue] '{organizer_name}'")
            except Exception as e:
                print(f"   ❌ [red]Error organizer:[/red] {e}")
            
            # Verificar que no hay sufijos numéricos
            import re
            if re.search(r'_\d+$', intelligent_name) or re.search(r'\s+\d+$', intelligent_name):
                print(f"   ⚠️ [yellow]ADVERTENCIA: Naming inteligente generó sufijo numérico![/yellow]")
            if re.search(r'_\d+$', organizer_name) or re.search(r'\s+\d+$', organizer_name):
                print(f"   ⚠️ [yellow]ADVERTENCIA: Organizer generó sufijo numérico![/yellow]")
        
        print(f"\n✅ [green]Prueba completada. Verifica que no hay sufijos numéricos en los nombres generados.[/green]")
            
    except Exception as e:
        logger.error(f"Error en test naming: {e}")
        log_center.log_error(f"Error en test naming: {str(e)}", "Test-Naming")
        print(f"❌ Error: {e}") 