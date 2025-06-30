#!/usr/bin/env python3
"""
naming_manager.py

Módulo para manejar problemas de naming de carpetas en el sistema PARA.
"""
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any

from paralib.logger import logger
from paralib.log_center import log_center


def find_naming_problems(vault_path: Path, category: str = 'all') -> List[Dict[str, Any]]:
    """Encuentra problemas en nombres de carpetas."""
    problems = []
    
    # Mapeo de categorías
    category_map = {
        'projects': '01-Projects',
        'areas': '02-Areas', 
        'resources': '03-Resources',
        'archive': '04-Archive'
    }
    
    categories_to_check = []
    if category == 'all':
        categories_to_check = list(category_map.values())
    else:
        if category in category_map:
            categories_to_check = [category_map[category]]
        else:
            logger.error(f"Categoría inválida: {category}")
            return []
    
    for para_folder in categories_to_check:
        folder_path = vault_path / para_folder
        if not folder_path.exists():
            continue
            
        for subfolder in folder_path.iterdir():
            if not subfolder.is_dir() or subfolder.name.startswith('.'):
                continue
                
            issues = analyze_folder_name(subfolder.name)
            if issues['has_problems']:
                problems.append({
                    'path': subfolder,
                    'current_name': subfolder.name,
                    'category': para_folder,
                    'issues': issues,
                    'suggested_name': suggest_clean_name(subfolder.name)
                })
    
    return problems


def analyze_folder_name(name: str) -> Dict[str, Any]:
    """Analiza un nombre de carpeta para identificar problemas."""
    issues = {
        'has_problems': False,
        'problems': []
    }
    
    # Problema 1: Guiones bajos
    if '_' in name:
        issues['has_problems'] = True
        issues['problems'].append('guiones_bajos')
    
    # Problema 2: Números de sufijo (_1, _2, etc.)
    if re.search(r'_\d+$', name):
        issues['has_problems'] = True
        issues['problems'].append('sufijo_numerico')
    
    # Problema 3: Múltiples guiones bajos seguidos
    if re.search(r'_{2,}', name):
        issues['has_problems'] = True
        issues['problems'].append('multiples_guiones')
    
    # Problema 4: Nombres muy largos
    if len(name) > 50:
        issues['has_problems'] = True
        issues['problems'].append('muy_largo')
    
    # Problema 5: Caracteres especiales problemáticos
    if re.search(r'[(){}[\]#@$%^&*]', name):
        issues['has_problems'] = True
        issues['problems'].append('caracteres_especiales')
    
    return issues


def suggest_clean_name(name: str) -> str:
    """Sugiere un nombre limpio para la carpeta."""
    clean_name = name
    
    # 1. Remover números de sufijo
    clean_name = re.sub(r'_\d+$', '', clean_name)
    
    # 2. Reemplazar guiones bajos con espacios
    clean_name = clean_name.replace('_', ' ')
    
    # 3. Limpiar múltiples espacios
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    # 4. Capitalizar correctamente
    clean_name = clean_name.title()
    
    # 5. Remover caracteres especiales problemáticos
    clean_name = re.sub(r'[(){}[\]#@$%^&*]', '', clean_name)
    
    # 6. Limitar longitud manteniendo palabras completas
    if len(clean_name) > 40:
        words = clean_name.split()
        clean_name = ""
        for word in words:
            if len(clean_name + " " + word) <= 40:
                clean_name += (" " + word) if clean_name else word
            else:
                break
    
    return clean_name.strip()


def display_naming_problems(problems: List[Dict[str, Any]]) -> None:
    """Muestra los problemas encontrados."""
    print("\n📋 PROBLEMAS ENCONTRADOS:")
    print("-" * 60)
    
    for i, problem in enumerate(problems[:20], 1):  # Mostrar primeros 20
        issues_str = ', '.join(problem['issues']['problems'])
        print(f"{i:2d}. 📁 {problem['category']}")
        print(f"    ❌ {problem['current_name']}")
        print(f"    🔧 {problem['suggested_name']}")
        print(f"    🚨 Problemas: {issues_str}")
        print()
    
    if len(problems) > 20:
        print(f"... y {len(problems) - 20} problemas más")


def apply_naming_fixes(problems: List[Dict[str, Any]]) -> int:
    """Aplica las correcciones de nombres."""
    fixed = 0
    conflicts = []
    
    for problem in problems:
        current_path = problem['path']
        new_name = problem['suggested_name']
        new_path = current_path.parent / new_name
        
        # Verificar conflictos
        if new_path.exists() and new_path != current_path:
            conflicts.append({
                'current': current_path,
                'suggested': new_path,
                'problem': problem
            })
            continue
        
        try:
            current_path.rename(new_path)
            print(f"✅ {current_path.name} → {new_name}")
            fixed += 1
            log_center.log_info(f"Nombre corregido: {current_path.name} → {new_name}", "Naming-Fix")
        except Exception as e:
            print(f"❌ Error renombrando {current_path.name}: {e}")
            log_center.log_error(f"Error renombrando {current_path.name}: {str(e)}", "Naming-Fix")
    
    # Manejar conflictos
    if conflicts:
        handle_naming_conflicts(conflicts)
    
    return fixed


def handle_naming_conflicts(conflicts: List[Dict[str, Any]]) -> None:
    """Maneja conflictos donde el nombre sugerido ya existe."""
    print(f"\n🔄 CONFLICTOS DETECTADOS ({len(conflicts)}):")
    print("Las siguientes carpetas no se pudieron renombrar porque ya existe una con el nombre sugerido:")
    
    for conflict in conflicts:
        print(f"   📁 {conflict['current'].name}")
        print(f"      → Quiere renombrarse a: {conflict['suggested'].name}")
        print(f"      ⚠️ Pero ya existe")
        
    print("\n💡 Usa 'para consolidate' para fusionar carpetas similares")
    log_center.log_warning(f"Conflictos de naming detectados: {len(conflicts)}", "Naming-Conflict") 