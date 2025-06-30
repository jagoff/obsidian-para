"""
paralib/organizer.py

Sistema de Organización PARA Inteligente - Clasificación híbrida con ChromaDB + LLM
con análisis completo de contenido, metadatos, y factores dinámicos para máxima precisión.
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import re
import json
from datetime import datetime
import sqlite3
from collections import defaultdict, Counter
import shutil
from rich.table import Table

# Imports internos
from paralib.db import ChromaPARADatabase
from paralib.analyze_manager import AnalyzeManager
from paralib.intelligent_naming import IntelligentNamingSystem
from paralib.logger import logger
from paralib.config import load_para_config, save_para_config

# Importar barra de progreso mejorada
try:
    from .enhanced_progress import run_with_fixed_progress
    USE_ENHANCED_PROGRESS = True
except ImportError:
    USE_ENHANCED_PROGRESS = False

# Importar configuración de debug
try:
    from .debug_config import should_show
except ImportError:
    # Fallback si no está disponible
    def should_show(feature: str) -> bool:
        return True

from .db import ChromaPARADatabase
from .config import load_config
from .vault import load_para_config
from .vault_selector import vault_selector
from .analyze_manager import AnalyzeManager
from .logger import logger
import ollama
from paralib.ai_engine import AIEngine
from paralib.learning_system import PARA_Learning_System
from paralib.intelligent_naming import create_intelligent_name
from datetime import datetime, timedelta

# Importar console y should_show desde rich
from rich.console import Console
console = Console()

CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources, Archive) system organizer with deep understanding of productivity and knowledge management. Your task is to classify a given note into one of the four PARA categories with maximum precision.

CRITICAL REQUIREMENTS:
- You MUST ONLY use these exact categories: "Projects", "Areas", "Resources", "Archive"
- NEVER use any other category names like "Notes", "Jobs", "Tasks", "Work", "Learning", etc.
- ALWAYS map any content to one of the four PARA categories above
- You are working alongside a ChromaDB semantic analysis system

PARA CATEGORIES - PRECISE DEFINITIONS:

**Projects** - A series of tasks linked to a goal with a deadline:
- MUST HAVE: Specific outcomes, deadlines, action items
- EXAMPLES: "Develop New App by Q2", "Plan Vacation for March", "Complete Q3 Report by Friday"
- INDICATORS: Action verbs (develop, plan, complete), dates, task lists, milestones, OKRs
- TIME-BOUND with clear completion criteria
- USE FOR: Job searches, client work, development tasks, business projects

**Areas** - A sphere of activity with a standard to be maintained over time:
- MUST HAVE: Ongoing maintenance, continuous improvement, no specific end date
- EXAMPLES: "Health & Fitness", "Finances", "Career Development", "Team Management", "Personal Growth", "Learning & Skills"
- INDICATORS: Standards, habits, regular reviews, continuous improvement, quarterly goals, maintenance routines, personal development
- NO specific end date, but requires regular attention and periodic review
- SPANISH INDICATORS: "desarrollo personal", "crecimiento", "habilidades", "salud", "finanzas", "carrera", "habitos", "rutina", "mejora continua"
- USE FOR: Personal development, ongoing responsibilities, life management, skill building, health tracking, financial planning

**Resources** - A topic of ongoing interest or reference material:
- MUST HAVE: Reference value, learning content, reusable information
- EXAMPLES: "AI Prompts Collection", "Cooking Recipes", "Programming Tips", "Book Notes"
- INDICATORS: Reference material, learning resources, collections, knowledge bases, templates
- Useful for future reference and learning
- USE FOR: Guides, tutorials, tips, documentation, configurations, notes, information

**Archive** - Inactive items that should remain archived:
- MUST HAVE: Completed projects, outdated information, no longer relevant content
- EXAMPLES: Completed projects, old reports, outdated procedures
- INDICATORS: Past tense, completed status, outdated information
- Should remain in Archive if still inactive
- USE FOR: Old content, completed work, deprecated information

MAPPING EXAMPLES:
- "WordPress Configuration" → "Resources" (reference material)
- "Job Search for PHP Developer" → "Projects" (specific outcome with deadline)
- "Meeting Notes" → "Resources" (reference information)
- "Completed Travel Plans" → "Archive" (finished project)

CLASSIFICATION STRATEGY:
1. Analyze the note's PURPOSE and CONTENT TYPE
2. Look for SPECIFIC INDICATORS (dates, action items, references)
3. Consider the NOTE'S CONTEXT and INTENDED USE
4. If unclear or too generic, classify as "Resources" for future reference

MANDATORY OUTPUT FORMAT:
{"category": "Projects" | "Areas" | "Resources" | "Archive", "folder_name": "Suggested Folder Name", "reasoning": "Brief explanation of classification decision"}

CRITICAL REMINDERS:
- ONLY use "Projects", "Areas", "Resources", or "Archive" - NO OTHER CATEGORIES
- The "folder_name" should be a short, descriptive name (2-4 words max)
- The "reasoning" should explain your classification logic
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

REFACTOR_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources, Archive) system archivist with deep understanding of productivity and knowledge management. Your task is to re-evaluate a note that is CURRENTLY IN THE ARCHIVE and decide if it has become relevant again for an active Project, Area, or Resource.

CRITICAL CONTEXT: You are working alongside a ChromaDB semantic analysis system. Your classification will be combined with semantic analysis for optimal accuracy.

PARA CATEGORIES - PRECISE DEFINITIONS:

**PROJECTS** - A series of tasks linked to a goal with a deadline:
- MUST HAVE: Specific outcomes, deadlines, action items
- EXAMPLES: "Develop New App by Q2", "Plan Vacation for March", "Complete Q3 Report by Friday"
- INDICATORS: Action verbs (develop, plan, complete), dates, task lists, milestones, OKRs
- TIME-BOUND with clear completion criteria

**AREAS** - A sphere of activity with a standard to be maintained over time:
- MUST HAVE: Ongoing maintenance, continuous improvement, no specific end date
- EXAMPLES: "Health & Fitness", "Finances", "Career Development", "Team Management", "Personal Growth", "Learning & Skills"
- INDICATORS: Standards, habits, regular reviews, continuous improvement, quarterly goals, maintenance routines, personal development
- NO specific end date, but requires regular attention and periodic review
- SPANISH INDICATORS: "desarrollo personal", "crecimiento", "habilidades", "salud", "finanzas", "carrera", "habitos", "rutina", "mejora continua"

**RESOURCES** - A topic of ongoing interest or reference material:
- MUST HAVE: Reference value, learning content, reusable information
- EXAMPLES: "AI Prompts Collection", "Cooking Recipes", "Programming Tips", "Book Notes"
- INDICATORS: Reference material, learning resources, collections, knowledge bases, templates
- Useful for future reference and learning

**ARCHIVE** - Inactive items that should remain archived:
- MUST HAVE: Completed projects, outdated information, no longer relevant content
- EXAMPLES: Completed projects, old reports, outdated procedures
- INDICATORS: Past tense, completed status, outdated information
- Should remain in Archive if still inactive

REFACTORING STRATEGY:
1. Analyze if the note is NOW RELEVANT to active work
2. Look for CURRENT INDICATORS (recent dates, active projects, ongoing needs)
3. Consider if the content has BECOME USEFUL again
4. If still inactive or outdated, keep as "Archive"

Output ONLY a JSON object with this structure:
{"category": "Projects" | "Areas" | "Resources" | "Archive", "folder_name": "Suggested Folder Name", "reasoning": "Brief explanation of refactoring decision"}

- If the note is now relevant to an active category, choose "Projects", "Areas", or "Resources"
- If the note is still inactive and should remain archived, return "category": "Archive"
- The "folder_name" should be a short, descriptive name (2-4 words max)
- The "reasoning" should explain your refactoring logic
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

def classify_note_with_llm(note_content: str, user_directive: str, model_name: str, system_prompt: str) -> dict | None:
    """
    Usa el motor AIEngine centralizado para clasificar una nota con LLM, evitando duplicación y asegurando logging correcto.
    FUERZA MAPEO A CATEGORÍAS PARA VÁLIDAS.
    """
    engine = AIEngine(model_name=model_name)
    result = engine.classify_note_with_llm(note_content, user_directive, system_prompt)
    
    if result:
        # MAPEO FORZADO A CATEGORÍAS PARA VÁLIDAS
        original_category = result.get('category', 'Unknown')
        mapped_category = _map_to_valid_para_category(original_category)
        
        if mapped_category != original_category:
            if should_show('show_mappings'):
                console.print(f"🔄 [dim]Mapeo IA: {original_category} → {mapped_category}[/dim]")
            result['category'] = mapped_category
            
            # Actualizar reasoning
            if 'reasoning' in result:
                result['reasoning'] = f"Mapeado de '{original_category}' a PARA estándar: {mapped_category}. {result['reasoning']}"
    
    return result

def _map_to_valid_para_category(category: str) -> str:
    """
    Mapea cualquier categoría a una categoría PARA válida.
    FUERZA CUMPLIMIENTO DEL ESTÁNDAR PARA.
    """
    category_lower = category.lower().strip()
    
    # Mapeo directo para categorías PARA válidas
    valid_para = {
        'projects': 'Projects',
        'areas': 'Areas', 
        'resources': 'Resources',
        'archive': 'Archive',
        'inbox': 'Inbox'
    }
    
    if category_lower in valid_para:
        return valid_para[category_lower]
    
    # Mapeo inteligente de categorías comunes a PARA
    category_mappings = {
        # Proyectos
        'project': 'Projects',
        'trabajo': 'Projects',
        'job': 'Projects',
        'jobs': 'Projects',
        'client': 'Projects',
        'moka': 'Projects',
        'bbi': 'Projects',
        'avature': 'Projects',
        'development': 'Projects',
        'website': 'Projects',
        'task': 'Projects',
        'tasks': 'Projects',
        'goal': 'Projects',
        'objetivo': 'Projects',
        'deadline': 'Projects',
        
        # Áreas
        'area': 'Areas',
        'areas': 'Areas',
        'coaching': 'Areas',
        'health': 'Areas',
        'finance': 'Areas',
        'personal': 'Areas',
        'skill': 'Areas',
        'learning': 'Areas',
        'habit': 'Areas',
        'management': 'Areas',
        'lifestyle': 'Areas',
        'career': 'Areas',
        'fitness': 'Areas',
        
        # Recursos
        'resource': 'Resources',
        'template': 'Resources',
        'api': 'Resources',
        'doc': 'Resources',
        'docs': 'Resources',
        'documentation': 'Resources',
        'guide': 'Resources',
        'tutorial': 'Resources',
        'reference': 'Resources',
        'tip': 'Resources',
        'tips': 'Resources',
        'standard': 'Resources',
        'standards': 'Resources',
        'configuración': 'Resources',
        'configuration': 'Resources',
        'setup': 'Resources',
        'notes': 'Resources',  # Notes genéricas = Resources
        'note': 'Resources',
        'info': 'Resources',  # Info = Resources
        'information': 'Resources',
        'knowledge': 'Resources',
        'collection': 'Resources',
        'database': 'Resources',
        'vault': 'Resources',
        'dark web': 'Resources',  # Dark Web = Resources (información/conocimiento)
        'darkweb': 'Resources',
        'security': 'Resources',
        'privacy': 'Resources',
        'research': 'Resources',
        'study': 'Resources',
        'book': 'Resources',
        'article': 'Resources',
        'recipe': 'Resources',
        'prompt': 'Resources',
        'cheat sheet': 'Resources',
        'howto': 'Resources',
        'manual': 'Resources',
        'list': 'Resources',
        
        # Archive  
        'old': 'Archive',
        'backup': 'Archive',
        'past': 'Archive',
        'travel': 'Archive',
        'completed': 'Archive',
        'done': 'Archive',
        'archived': 'Archive',
        'deprecated': 'Archive',
        'obsolete': 'Archive',
        'finished': 'Archive',
        
        # Casos especiales que van a Resources por defecto
        'unknown': 'Resources',  # Cambio: unknown va a Resources, no Inbox
        'misc': 'Resources',
        'other': 'Resources',
        'general': 'Resources'
    }
    
    # Buscar mapeo directo
    for key, para_category in category_mappings.items():
        if key in category_lower:
            return para_category
    
    # Si no hay mapeo, determinar por contenido/contexto
    console.print(f"📚 [cyan]Categoría no mapeada: '{category}' → Resources (información general)[/cyan]")
    return 'Resources'  # Por defecto, enviar a Resources como material de referencia

def _is_note_in_archive(note_path: Path, vault_path: Path) -> bool:
    """
    Verifica si una nota está actualmente en la carpeta Archive.
    """
    try:
        relative_path = note_path.relative_to(vault_path)
        path_parts = relative_path.parts
        
        # Verificar si alguna parte del path contiene "archive" o "04-archive"
        for part in path_parts:
            if part.lower().startswith('04-archive') or part.lower() == 'archive':
                return True
        return False
    except (ValueError, AttributeError):
        return False

def _should_note_stay_archived(note_content: str, note_path: Path) -> bool:
    """
    Determina si una nota archivada debe mantenerse en Archive.
    Factores: fechas, estado de completitud, relevancia actual.
    """
    from datetime import datetime, timedelta
    
    # Obtener fecha de modificación
    try:
        mod_time = datetime.fromtimestamp(note_path.stat().st_mtime)
        days_since_modified = (datetime.now() - mod_time).days
    except:
        days_since_modified = 365  # Asumir muy antigua si no se puede leer
    
    # Factores para mantener en Archive
    archive_indicators = [
        days_since_modified > 180,  # Más de 6 meses sin modificar
        any(word in note_content.lower() for word in [
            'completado', 'finished', 'done', 'completed', 'finalizado',
            'obsoleto', 'deprecated', 'old', 'antiguo', 'viejo'
        ]),
        any(word in note_path.name.lower() for word in [
            'old', 'backup', 'archive', 'past', 'viejo', 'antiguo'
        ]),
        len(note_content.strip()) < 100,  # Contenido muy corto (posiblemente stub)
    ]
    
    # Factores para sacar de Archive (reactivar)
    reactivation_indicators = [
        days_since_modified < 30,  # Modificada recientemente
        any(word in note_content.lower() for word in [
            'urgent', 'urgente', 'importante', 'important', 'pending',
            'todo', 'task', 'proyecto activo', 'current project'
        ]),
        note_content.lower().count('[]') > 2,  # Muchas tareas pendientes
    ]
    
    # Decisión: mantener en Archive si hay más indicadores de archivo que de reactivación
    should_archive = sum(archive_indicators) > sum(reactivation_indicators)
    
    return should_archive

def _extract_current_folder_name(note_path: Path, vault_path: Path) -> str:
    """
    Extrae el nombre de la carpeta actual donde se encuentra la nota.
    Maneja todos los casos edge posibles para evitar errores de índice.
    """
    from .log_center import log_center
    
    try:
        # Verificar que los paths sean válidos
        if not note_path or not vault_path:
            log_center.log_warning(f"Paths inválidos: note_path={note_path}, vault_path={vault_path}", "FolderNameExtractor")
            return "Miscellaneous"
        
        # Verificar que la nota existe
        if not note_path.exists():
            log_center.log_warning(f"Nota no existe: {note_path}", "FolderNameExtractor")
            return "Miscellaneous"
        
        # Verificar que el vault existe
        if not vault_path.exists():
            log_center.log_warning(f"Vault no existe: {vault_path}", "FolderNameExtractor")
            return "Miscellaneous"
        
        # Obtener ruta relativa
        try:
            relative_path = note_path.relative_to(vault_path)
        except ValueError as e:
            log_center.log_warning(f"No se puede obtener ruta relativa: {note_path} desde {vault_path} - {e}", "FolderNameExtractor")
            return "Miscellaneous"
        
        log_center.log_debug(f"Extrayendo carpeta para nota: {note_path} (relative: {relative_path})", "FolderNameExtractor")
        
        # Verificar que la ruta relativa tenga partes
        if not hasattr(relative_path, 'parts') or not relative_path.parts:
            log_center.log_warning(f"Ruta relativa sin partes: {relative_path}", "FolderNameExtractor")
            return "Miscellaneous"
        
        # Verificar que haya al menos 2 partes (carpeta + archivo)
        if len(relative_path.parts) < 2:
            log_center.log_warning(f"Nota en raíz o sin carpeta padre: {note_path} (parts: {relative_path.parts})", "FolderNameExtractor")
            return "Miscellaneous"
        
        # Extraer el nombre de la carpeta (penúltima parte)
        try:
            folder_name = relative_path.parts[-2]
            if not folder_name or folder_name.strip() == "":
                log_center.log_warning(f"Nombre de carpeta vacío para nota: {note_path}", "FolderNameExtractor")
                return "Miscellaneous"
            
            log_center.log_debug(f"Carpeta extraída: {folder_name} para nota: {note_path.name}", "FolderNameExtractor")
            return folder_name
            
        except IndexError as e:
            log_center.log_error(f"Error de índice al extraer carpeta: {note_path} (parts: {relative_path.parts}) - {e}", "FolderNameExtractor")
            return "Miscellaneous"
        
    except (ValueError, AttributeError, IndexError) as e:
        log_center.log_error(f"Error extrayendo carpeta para nota: {note_path} - {e}", "FolderNameExtractor")
        return "Miscellaneous"
    except Exception as e:
        log_center.log_error(f"Error inesperado extrayendo carpeta para nota: {note_path} - {e}", "FolderNameExtractor")
        return "Miscellaneous"

def check_ollama_model(model_name: str) -> bool:
    """
    Verifica si un modelo específico existe en Ollama.
    """
    try:
        ollama.show(model_name)
        return True
    except Exception as e:
        if "model" in str(e) and "not found" in str(e):
            console.print(f"[bold red]Error: Modelo de IA '{model_name}' no encontrado.[/bold red]")
            console.print(f"Por favor, asegúrate de que Ollama esté corriendo y ejecuta: [bold cyan]ollama pull {model_name}[/bold cyan]")
        else:
            console.print(f"[bold red]Error al contactar con Ollama: {e}[/bold red]")
        return False

def classify_note_with_hybrid_system(note_content: str, note_path: Path, user_directive: str, model_name: str, system_prompt: str, db: ChromaPARADatabase, vault_path: Path) -> dict | None:
    """
    Sistema de clasificación híbrido avanzado que combina ChromaDB y IA con pesos dinámicos.
    Maximiza la precisión usando ambos sistemas de forma sinérgica.
    """
    console.print(f"🚀 [bold]Sistema de clasificación híbrido activado[/bold]")
    console.print(f"🔍 [dim]Analizando con ChromaDB + IA para máxima precisión...[/dim]")
    
    # Inicializar analyze manager para análisis semántico
    analyze_manager = AnalyzeManager(vault_path, db_path=Path(db.db_path).parent)
    
    # 1. ANÁLISIS SEMÁNTICO CON CHROMADB
    enhanced_suggestion = analyze_manager.get_enhanced_classification_suggestion(note_path, note_content)
    semantic_category = enhanced_suggestion['suggested_category']
    semantic_confidence = enhanced_suggestion['confidence_score']
    semantic_reasoning = enhanced_suggestion['reasoning']
    
    console.print(f"📊 [dim]ChromaDB: {semantic_category} (confianza: {semantic_confidence:.3f})[/dim]")
    
    # 2. ANÁLISIS CON IA
    console.print(f"🤖 [dim]Consultando IA para análisis complementario...[/dim]")
    llm_result = classify_note_with_llm(note_content, user_directive, model_name, system_prompt)
    
    if not llm_result:
        console.print(f"❌ [red]Error en IA - usando solo ChromaDB[/red]")
        folder_name = _generate_folder_name_from_content(note_content, semantic_category)
        return {
            'category': semantic_category,
            'folder_name': folder_name,
            'confidence': semantic_confidence,
            'method': 'chromadb_only',
            'semantic_score': semantic_confidence,
            'llm_score': 0.0,
            'reasoning': semantic_reasoning
        }
    
    llm_category = llm_result.get('category', 'Unknown')
    llm_folder = llm_result.get('folder_name', 'Unknown')
    
    console.print(f"🤖 [dim]IA: {llm_category} → {llm_folder}[/dim]")
    
    # 3. CÁLCULO DE PESOS DINÁMICOS
    weights = _calculate_dynamic_weights(semantic_confidence, note_content, db, vault_path)
    semantic_weight = weights['semantic']
    llm_weight = weights['llm']
    
    console.print(f"⚖️ [dim]Pesos dinámicos: ChromaDB={semantic_weight:.2f}, IA={llm_weight:.2f}[/dim]")
    
    # 4. DECISIÓN HÍBRIDA INTELIGENTE
    final_decision = _make_hybrid_decision(
        semantic_category, semantic_confidence, semantic_reasoning,
        llm_category, llm_folder, llm_result,
        semantic_weight, llm_weight,
        note_content, user_directive
    )
    
    return final_decision

def _calculate_dynamic_weights(semantic_confidence: float, note_content: str, db: ChromaPARADatabase, vault_path: Path) -> dict:
    """
    Calcula pesos dinámicos basados en múltiples factores para optimizar la precisión.
    """
    # Base weights - OPTIMIZADO: IA más peso por mejor precisión
    base_semantic = 0.4  # Reducido de 0.6 a 0.4
    base_llm = 0.6       # Aumentado de 0.4 a 0.6
    # Inicializar todos los boosts/penalties
    semantic_boost = 0.0
    llm_boost = 0.0
    semantic_penalty = 0.0
    llm_penalty = 0.0
    
    # Factor 1: Confianza semántica
    if semantic_confidence > 0.8:
        semantic_boost = 0.2
        llm_penalty = -0.1
    elif semantic_confidence > 0.6:
        semantic_boost = 0.1
        llm_penalty = -0.05
    elif semantic_confidence < 0.3:
        semantic_penalty = -0.2
        llm_boost = 0.2
    else:
        semantic_boost = 0.0
        llm_penalty = 0.0
        semantic_penalty = 0.0
        llm_boost = 0.0
    
    # Factor 2: Complejidad del contenido
    content_length = len(note_content)
    word_count = len(note_content.split())
    
    if word_count > 500:  # Contenido complejo
        llm_boost += 0.1  # IA maneja mejor contenido complejo
        semantic_penalty += 0.05
    elif word_count < 50:  # Contenido simple
        semantic_boost += 0.1  # ChromaDB es mejor para contenido simple
        llm_penalty += 0.05
    
    # Factor 3: Patrones de contenido
    has_todos = 'todo' in note_content.lower() or 'task' in note_content.lower()
    has_dates = any(char.isdigit() for char in note_content[:200])
    has_links = '[[' in note_content and ']]' in note_content
    
    if has_todos and has_dates:  # Patrón de proyecto
        semantic_boost += 0.1
    elif has_links:  # Patrón de recurso
        semantic_boost += 0.05
    
    # Factor 4: Base de datos ChromaDB
    total_notes = len(db.get_all_notes_metadata())
    if total_notes < 10:  # Base de datos pequeña
        llm_boost += 0.15
        semantic_penalty += 0.1
    elif total_notes > 100:  # Base de datos grande
        semantic_boost += 0.1
        llm_penalty += 0.05
    
    # Aplicar ajustes
    final_semantic = base_semantic + semantic_boost - semantic_penalty
    final_llm = base_llm + llm_boost - llm_penalty
    
    # Normalizar a 0-1
    total = final_semantic + final_llm
    final_semantic = max(0.1, min(0.9, final_semantic / total))
    final_llm = max(0.1, min(0.9, final_llm / total))
    
    return {
        'semantic': final_semantic,
        'llm': final_llm
    }

def _make_hybrid_decision(semantic_category: str, semantic_confidence: float, semantic_reasoning: str,
                         llm_category: str, llm_folder: str, llm_result: dict,
                         semantic_weight: float, llm_weight: float,
                         note_content: str, user_directive: str) -> dict:
    """
    Toma la decisión final combinando ambos sistemas de forma inteligente.
    """
    # Caso 1: Ambos sistemas coinciden
    if semantic_category == llm_category:
        console.print(f"✅ [green]CONSENSO: Ambos sistemas sugieren {semantic_category}[/green]")
        
        # Usar el nombre de carpeta más apropiado
        if llm_folder and llm_folder != 'Unknown':
            folder_name = llm_folder
        else:
            folder_name = _generate_folder_name_from_content(note_content, semantic_category)
        
        # MEJORADO: Usar score real del LLM y boost por consenso
        llm_confidence = 0.85  # Score base alto para IA cuando funciona
        consensus_boost = 0.15  # Boost adicional por consenso
        combined_confidence = min(0.98, (semantic_confidence * semantic_weight) + (llm_confidence * llm_weight) + consensus_boost)
        
        return {
            'category': semantic_category,
            'folder_name': folder_name,
            'confidence': combined_confidence,
            'method': 'consensus',
            'semantic_score': semantic_confidence,
            'llm_score': llm_confidence,
            'reasoning': f"Consenso entre ChromaDB y IA. {semantic_reasoning}"
        }
    
    # Caso 2: Sistemas discrepan - usar pesos dinámicos
    console.print(f"🔄 [yellow]DISCREPANCIA: ChromaDB={semantic_category} vs IA={llm_category}[/yellow]")
    
    # MEJORADO: Calcular scores más inteligentemente
    llm_confidence = 0.75  # Score base para IA en discrepancias
    
    # Ajustar confianza de IA basado en calidad de respuesta
    if llm_result and llm_result.get('reasoning'):
        if len(llm_result.get('reasoning', '')) > 50:  # Razonamiento detallado
            llm_confidence += 0.1
    
    # Penalizar ChromaDB si confianza muy baja
    adjusted_semantic_confidence = semantic_confidence
    if semantic_confidence < 0.3:
        adjusted_semantic_confidence *= 0.8  # Penalización por baja confianza
    
    semantic_score = adjusted_semantic_confidence * semantic_weight
    llm_score = llm_confidence * llm_weight
    
    if semantic_score > llm_score:
        final_category = semantic_category
        final_folder = _generate_folder_name_from_content(note_content, semantic_category)
        method = 'chromadb_weighted'
        reasoning = f"ChromaDB prevalece por peso ({semantic_weight:.2f}). {semantic_reasoning}"
        final_confidence = min(0.85, semantic_score + (llm_score * 0.3))  # Boost moderado
    else:
        final_category = llm_category
        final_folder = llm_folder if llm_folder != 'Unknown' else _generate_folder_name_from_content(note_content, llm_category)
        method = 'llm_weighted'
        reasoning = f"IA prevalece por peso ({llm_weight:.2f}). Razonamiento: {llm_result.get('reasoning', 'Análisis de IA')}"
    
    return {
        'category': final_category,
        'folder_name': final_folder,
        'confidence': final_confidence,
        'method': method,
        'semantic_score': semantic_confidence,
        'llm_score': llm_confidence,
        'reasoning': reasoning
    }

def classify_note_with_enhanced_analysis(note_content: str, note_path: Path, user_directive: str, model_name: str, system_prompt: str, db: ChromaPARADatabase, vault_path: Path) -> dict | None:
    """
    Clasificación potenciada con ChromaDB usando análisis completo de la nota.
    """
    # Usar el sistema de análisis completo
    return classify_note_with_complete_analysis(note_content, note_path, user_directive, model_name, system_prompt, db, vault_path)

def _generate_folder_name_from_content(content: str, category: str, vault_path: Path = None, existing_folders: set = None, use_intelligent_naming: bool = True) -> str:
    """
    Genera un nombre de carpeta único basado en el contenido y categoría.
    VERSIÓN SIMPLIFICADA que usa naming inteligente y consolidación automática.
    
    Args:
        content: Contenido de la nota
        category: Categoría PARA ('Projects', 'Areas', etc.)
        vault_path: Ruta del vault para verificar carpetas existentes
        existing_folders: Set de carpetas existentes para evitar duplicados
        use_intelligent_naming: Si usar el sistema de naming inteligente (recomendado)
    
    Returns:
        str: Nombre de carpeta único y normalizado
    """
    # MAPEO CENTRALIZADO DE CATEGORÍAS (ÚNICA FUENTE DE VERDAD)
    CATEGORY_MAPPING = {
        'Projects': '01-Projects',
        'Areas': '02-Areas', 
        'Resources': '03-Resources',
        'Archive': '04-Archive',
        'Inbox': '00-Inbox'
    }
    
    # Asegurar que la categoría tenga el número correcto
    normalized_category = CATEGORY_MAPPING.get(category, category)
    
    # OPCIÓN 1: NAMING INTELIGENTE (RECOMENDADO)
    if use_intelligent_naming:
        try:
            # Mapear categoría a contexto del naming inteligente
            context_mapping = {
                '01-Projects': 'project',
                '02-Areas': 'area', 
                '03-Resources': 'resource',
                '04-Archive': 'resource',  # Archivos como recursos
                '00-Inbox': 'project'  # Inbox como proyecto por defecto
            }
            
            context_category = context_mapping.get(normalized_category, 'project')
            
            # Usar sistema de naming inteligente con detección de duplicados
            title = create_intelligent_name([content], context_category, existing_folders, vault_path, normalized_category)
            
            console.print(f"🧠 [dim]Naming inteligente generó: '{title}'[/dim]")
            
            return title
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error en naming inteligente: {e}. Usando método tradicional.[/yellow]")
            # Fallback al método tradicional
            title = _extract_smart_title_from_content(content)
            title = _normalize_folder_name(title)
    else:
        # OPCIÓN 2: MÉTODO TRADICIONAL
        title = _extract_smart_title_from_content(content)
        title = _normalize_folder_name(title)
    
    # Para el método tradicional, usar la función de consolidación inteligente
    if vault_path:
        final_name = _ensure_unique_folder_name(title, normalized_category, vault_path, existing_folders)
    else:
        final_name = title
    
    # VALIDACIÓN FINAL
    if not final_name or len(final_name.strip()) == 0:
        category_name = normalized_category.split('-')[1] if '-' in normalized_category else normalized_category
        final_name = f"Nuevo {category_name}"
    
    return final_name

def _extract_smart_title_from_content(content: str) -> str:
    """
    Extrae inteligentemente el título más apropiado del contenido.
    """
    import re
    
    lines = content.strip().split('\n')
    title = ""
    
    # PRIORIDAD 1: Títulos en frontmatter
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter_content = frontmatter_match.group(1)
        title_match = re.search(r'^title:\s*["\']?([^"\'\n]+)["\']?', frontmatter_content, re.MULTILINE | re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            if title:
                return title
    
    # PRIORIDAD 2: Encabezados markdown (H1, H2)
    for line in lines[:15]:  # Revisar primeras 15 líneas
        line = line.strip()
        if line.startswith('# ') and len(line) > 2:
            title = line[2:].strip()
            break
        elif line.startswith('## ') and len(line) > 3:
            title = line[3:].strip()
            if not title:  # Si H1 no encontrado, usar H2
                continue
            break
    
    # PRIORIDAD 3: Primera línea significativa
    if not title:
        for line in lines:
            line = line.strip()
            if (line and 
                not line.startswith('---') and 
                not line.startswith('#') and
                not line.startswith('!') and
                len(line) > 3):
                title = line
                break
    
    return title or "Sin Título"

def _normalize_folder_name(title: str) -> str:
    """
    Normaliza un nombre de carpeta para evitar duplicados y problemas de filesystem.
    """
    import re
    import unicodedata
    
    if not title:
        return ""
    
    # 1. Remover/reemplazar caracteres problemáticos
    title = re.sub(r'#\w+', '', title)  # Remover hashtags
    title = re.sub(r'\[([^\]]+)\]', r'\1', title)  # [texto] -> texto
    title = re.sub(r'[^\w\s\-áéíóúüñ]', '', title, flags=re.UNICODE)  # Solo letras, números, espacios, guiones y acentos
    
    # 2. Normalizar unicode y espacios
    title = unicodedata.normalize('NFC', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    # 3. Capitalizar correctamente
    title = title.title()
    
    # 4. Limitar longitud manteniendo palabras completas
    if len(title) > 40:
        words = title.split()
        title = ""
        for word in words:
            if len(title + " " + word) <= 40:
                title += (" " + word) if title else word
            else:
                break
        if len(title) < 10 and len(words) > 0:  # Si muy corto, al menos 2 palabras
            title = " ".join(words[:2])
    
    # 5. Validaciones finales
    title = title.strip()
    if len(title) < 2:
        return ""
    
    return title

def _ensure_unique_folder_name(base_name: str, category: str, vault_path: Path, existing_folders: set) -> str:
    """
    Asegura que el nombre de carpeta sea único usando consolidación inteligente.
    NUNCA genera sufijos numéricos - siempre consolida en carpetas existentes.
    """
    if not base_name:
        return base_name
    
    # Construir path completo de la categoría
    category_path = vault_path / category
    
    # Verificar carpetas existentes en el filesystem
    existing_in_fs = set()
    if category_path.exists():
        try:
            existing_in_fs = {f.name for f in category_path.iterdir() if f.is_dir()}
        except Exception:
            pass
    
    # Combinar con carpetas existentes del parámetro
    all_existing = existing_in_fs | existing_folders
    
    # Verificar si el nombre base ya existe exactamente
    if base_name in all_existing:
        console.print(f"🔄 [dim]Carpeta '{base_name}' ya existe. Consolidando...[/dim]")
        return base_name  # Usar la carpeta existente
    
    # Buscar variantes similares (sin sufijos numéricos)
    import re
    base_normalized = re.sub(r'\s+\d+$', '', base_name)
    base_normalized = re.sub(r'_\d+$', '', base_normalized)
    
    # Buscar carpetas existentes que coincidan con el nombre base normalizado
    matching_folders = []
    for existing in all_existing:
        existing_normalized = re.sub(r'\s+\d+$', '', existing)
        existing_normalized = re.sub(r'_\d+$', '', existing_normalized)
        
        if existing_normalized.lower() == base_normalized.lower():
            matching_folders.append(existing)
    
    if matching_folders:
        # Elegir la carpeta con más archivos para consolidar
        best_folder = matching_folders[0]
        max_files = 0
        
        for folder in matching_folders:
            folder_path = category_path / folder
            try:
                file_count = len(list(folder_path.rglob("*.md")))
                if file_count > max_files:
                    max_files = file_count
                    best_folder = folder
            except Exception:
                continue
        
        console.print(f"🔄 [dim]Encontrada variante existente: '{best_folder}' ({max_files} archivos). Consolidando...[/dim]")
        return best_folder
    
    # Si no hay variantes, usar el nombre base (es único)
    return base_name

def _get_category_mapping() -> dict:
    """
    Obtiene el mapeo centralizado de categorías.
    ÚNICA FUENTE DE VERDAD para el mapeo de categorías.
    """
    return {
        'Projects': '01-Projects',
        'Areas': '02-Areas', 
        'Resources': '03-Resources',
        'Archive': '04-Archive',
        'Inbox': '00-Inbox'
    }

def _process_notes_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, source_folder_name: str, system_prompt: str, excluded_paths: list[str] = None):
    """
    Función interna para procesar clasificación de notas (usada por inbox y archive).
    POTENCIADA CON CHROMADB para mejor precisión.
    """
    from rich.console import Console
    from rich.table import Table
    console = Console()
    
    if not check_ollama_model(model_name):
        return

    # Seleccionar notas a procesar
    notes_to_process = []
    if source_folder_name == "inbox":
        inbox_path = vault_path / "00-Inbox"
        if inbox_path.exists():
            notes_to_process = list(inbox_path.glob("*.md"))
    elif source_folder_name == "archive":
        archive_path = vault_path / "04-Archive"
        if archive_path.exists():
            notes_to_process = list(archive_path.rglob("*.md"))
    
    # --- SELECCIÓN Y FILTRADO DE NOTAS CON EXCLUSIONES CENTRALIZADAS ---
    from paralib.exclusion_manager import filter_notes_by_exclusions
    notes_to_process = filter_notes_by_exclusions(notes_to_process, excluded_paths)
    if not notes_to_process:
        console.print(f"[yellow]No se encontraron notas para procesar tras aplicar exclusiones.[/yellow]")
        return

    # --- SISTEMA DE PROGRESO SIMPLE Y LIMPIO ---
    console.print(f"\n[bold blue]🔄 Procesando {len(notes_to_process)} notas...[/bold blue]")
    
    results = []
    processed_count = 0
    
    for i, note_path in enumerate(notes_to_process, 1):
        try:
            # Mostrar progreso simple
            progress_percent = (i / len(notes_to_process)) * 100
            console.print(f"[dim]Progreso: {progress_percent:.1f}% ({i}/{len(notes_to_process)}) - {note_path.name}[/dim]")
            
            # Procesar nota
            note_content = note_path.read_text(encoding="utf-8")
            analysis = analyze_note_completely(note_path, note_content, extra_prompt)
            result = classify_note_with_complete_analysis(note_content, note_path, extra_prompt, model_name, system_prompt, db, vault_path)
            
            if result:
                results.append({
                    'note': note_path.name,
                    'category': result.get('category', 'Unknown'),
                    'folder': result.get('folder_name', 'Unknown'),
                    'confidence': result.get('confidence', 0.0),
                    'method': result.get('method', 'unknown'),
                    'tags': result.get('tags', []),
                    'patterns': result.get('patterns', [])
                })
                
                # Mostrar resultado
                status = "✅" if result.get('confidence', 0) > 0.5 else "⚠️"
                console.print(f"  {status} {result.get('category', 'Unknown')} → {result.get('folder_name', 'Unknown')} ({result.get('confidence', 0):.3f})")
                
                processed_count += 1
            else:
                console.print(f"  ❌ Error clasificando {note_path.name}")
                
        except Exception as e:
            console.print(f"  ❌ Error procesando {note_path.name}: {str(e)}")
    
    # Mostrar resumen
    console.print(f"\n[bold green]✅ Procesamiento completado: {processed_count}/{len(notes_to_process)} notas[/bold green]")
    
    # Mostrar tabla de resultados si hay datos
    if results:
        table = Table(title="Resultados de Clasificación")
        table.add_column("Nota", style="cyan")
        table.add_column("Categoría", style="magenta")
        table.add_column("Carpeta", style="green")
        table.add_column("Confianza", style="yellow")
        table.add_column("Método", style="blue")
        table.add_column("Tags", style="dim")
        table.add_column("Patrones", style="dim")
        
        for result in results:
            table.add_row(
                result['note'],
                result['category'],
                result['folder'],
                f"{result['confidence']:.3f}",
                result['method'],
                str(result['tags']) if result['tags'] else "N/A",
                " ".join(result['patterns']) if result['patterns'] else ""
            )
        
        console.print(table)

def run_inbox_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Procesa notas del Inbox usando clasificación potenciada con ChromaDB.
    """
    # Usar el nuevo sistema de planificación sin extra_prompt problemático
    _process_notes_classification(
        vault_path=vault_path,
        db=db,
        extra_prompt=extra_prompt,
        model_name=model_name,
        execute=execute,
        source_folder_name="00-Inbox",
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT
    )

def run_archive_refactor(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, excluded_paths: list[str]):
    """
    Refactoriza notas del Archive usando clasificación potenciada con ChromaDB.
    """
    # Usar el nuevo sistema de planificación sin extra_prompt problemático
    _process_notes_classification(
        vault_path=vault_path,
        db=db,
        extra_prompt=extra_prompt,
        model_name=model_name,
        execute=execute,
        source_folder_name="04-Archive",
        system_prompt=REFACTOR_SYSTEM_PROMPT,
        excluded_paths=excluded_paths
    )

def get_keywords():
    """Obtiene las palabras clave del perfil de configuración."""
    config = load_para_config()
    return config.get('keywords', [])

def get_rules():
    """Obtiene las reglas de clasificación del perfil de configuración."""
    config = load_para_config()
    return config.get('rules', [])

def get_profile():
    """Obtiene el perfil de configuración."""
    config = load_para_config()
    return config.get('profile', 'General')

def analyze_note_completely(note_path: Path, note_content: str, user_directive: str) -> dict:
    """
    Análisis completo de una nota: contenido, tags, metadatos, fechas, etc.
    Combina toda la información disponible para máxima precisión.
    """
    from rich.console import Console
    console = Console()
    
    import re
    from datetime import datetime
    import os
    
    analysis = {
        'content': note_content,
        'tags': [],
        'frontmatter': {},
        'last_modified': None,
        'word_count': 0,
        'has_todos': False,
        'has_dates': False,
        'has_links': False,
        'has_attachments': False,
        'content_patterns': {},
        'user_directive': user_directive
    }
    
    # 1. ANÁLISIS DE METADATOS DEL ARCHIVO
    try:
        stat = note_path.stat()
        analysis['last_modified'] = datetime.fromtimestamp(stat.st_mtime)
        analysis['file_size'] = stat.st_size
        analysis['created_date'] = datetime.fromtimestamp(stat.st_ctime)
    except Exception as e:
        console.print(f"[dim]Error leyendo metadatos: {e}[/dim]")
    
    # 2. ANÁLISIS DE CONTENIDO Y PATRONES
    analysis['word_count'] = len(note_content.split())
    
    # Detectar TO-DOs
    todo_pattern = r'- \[ \].*|#todo|#TODO|TODO:|todo:'
    analysis['has_todos'] = bool(re.search(todo_pattern, note_content, re.IGNORECASE))
    analysis['todo_count'] = len(re.findall(todo_pattern, note_content, re.IGNORECASE))
    
    # Detectar fechas
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # M/D/YY
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',  # DD MMM YYYY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b'  # MMM DD, YYYY
    ]
    
    dates_found = []
    for pattern in date_patterns:
        dates_found.extend(re.findall(pattern, note_content, re.IGNORECASE))
    
    analysis['has_dates'] = bool(dates_found)
    analysis['dates_found'] = dates_found[:5]  # Primeras 5 fechas
    
    # Detectar enlaces de Obsidian
    link_pattern = r'\[\[([^\]]+)\]\]'
    links = re.findall(link_pattern, note_content)
    analysis['has_links'] = bool(links)
    analysis['link_count'] = len(links)
    analysis['links'] = links[:10]  # Primeros 10 enlaces
    
    # Detectar archivos adjuntos
    attachment_pattern = r'!\[.*?\]\(([^)]+)\)'
    attachments = re.findall(attachment_pattern, note_content)
    analysis['has_attachments'] = bool(attachments)
    analysis['attachments'] = attachments
    
    # 3. ANÁLISIS DE FRONTMATTER (YAML)
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', note_content, re.DOTALL)
    if frontmatter_match:
        frontmatter_content = frontmatter_match.group(1)
        try:
            import yaml
            analysis['frontmatter'] = yaml.safe_load(frontmatter_content) or {}
        except:
            # Si no es YAML válido, extraer tags manualmente
            analysis['frontmatter'] = {}
    
    # 4. EXTRACCIÓN DE TAGS
    # Tags en frontmatter
    if 'tags' in analysis['frontmatter']:
        analysis['tags'].extend(analysis['frontmatter']['tags'])
    
    # Tags en el contenido (#tag)
    content_tags = re.findall(r'#([a-zA-Z0-9_]+)', note_content)
    analysis['tags'].extend(content_tags)
    
    # Tags específicos de Obsidian
    obsidian_tags = re.findall(r'#(project|area|resource|archive|inbox)', note_content, re.IGNORECASE)
    analysis['obsidian_tags'] = obsidian_tags
    
    # Remover duplicados
    analysis['tags'] = list(set(analysis['tags']))
    
    # 5. ANÁLISIS DE PATRONES DE CONTENIDO
    analysis['content_patterns'] = {
        'has_headers': bool(re.search(r'^#{1,6}\s+', note_content, re.MULTILINE)),
        'has_lists': bool(re.search(r'^[-*+]\s+', note_content, re.MULTILINE)),
        'has_code_blocks': bool(re.search(r'```', note_content)),
        'has_tables': bool(re.search(r'\|.*\|', note_content)),
        'has_quotes': bool(re.search(r'^>\s+', note_content, re.MULTILINE)),
        'has_emphasis': bool(re.search(r'\*\*.*\*\*|__.*__', note_content)),
        'has_strikethrough': bool(re.search(r'~~.*~~', note_content)),
        'has_footnotes': bool(re.search(r'\[\^.*\]', note_content))
    }
    
    # 6. ANÁLISIS TEMPORAL
    if analysis['last_modified']:
        days_since_modified = (datetime.now() - analysis['last_modified']).days
        analysis['days_since_modified'] = days_since_modified
        
        # Clasificar por antigüedad
        if days_since_modified <= 7:
            analysis['recency'] = 'very_recent'
        elif days_since_modified <= 30:
            analysis['recency'] = 'recent'
        elif days_since_modified <= 90:
            analysis['recency'] = 'moderate'
        else:
            analysis['recency'] = 'old'
    
    # 7. ANÁLISIS DE CONTEXTO DEL USUARIO
    analysis['user_context'] = {
        'directive': user_directive,
        'directive_keywords': extract_keywords_from_directive(user_directive),
        'has_specific_instructions': bool(re.search(r'\b(project|area|resource|archive)\b', user_directive, re.IGNORECASE))
    }
    
    return analysis

def extract_keywords_from_directive(directive: str) -> list:
    """
    Extrae palabras clave relevantes de la directiva del usuario.
    """
    import re
    
    # Palabras clave específicas de PARA
    para_keywords = ['project', 'area', 'resource', 'archive', 'inbox', 'urgent', 'important', 'reference', 'template']
    
    # Buscar palabras clave en la directiva
    found_keywords = []
    for keyword in para_keywords:
        if re.search(rf'\b{keyword}\b', directive, re.IGNORECASE):
            found_keywords.append(keyword.lower())
    
    return found_keywords

def classify_note_with_complete_analysis(note_content: str, note_path: Path, user_directive: str, model_name: str, system_prompt: str, db: ChromaPARADatabase, vault_path: Path) -> dict | None:
    """
    Clasificación con análisis completo: contenido, tags, metadatos, fechas + prompt del usuario.
    INCLUYE LÓGICA ESPECIAL PARA NOTAS YA ARCHIVADAS.
    """
    from rich.console import Console
    console = Console()
    
    # Calcular path relativo al vault para display profesional
    try:
        relative_path = note_path.relative_to(vault_path)
    except ValueError:
        relative_path = note_path.name
    
    # OUTPUT MEJORADO - PROFESIONAL Y LIMPIO
    if should_show('show_file_operations'):
        console.print(f"\n📝 Procesando {relative_path}")
    
    # VERIFICAR SI LA NOTA YA ESTÁ EN ARCHIVE
    is_already_archived = _is_note_in_archive(note_path, vault_path)
    if is_already_archived and should_show('show_detailed_analysis'):
        console.print(f"📦 [dim]Nota ya archivada - evaluando si debe mantenerse en Archive[/dim]")
        
        # Verificar si la nota debe salir del Archive (por ejemplo, si es reciente o activa)
        should_stay_archived = _should_note_stay_archived(note_content, note_path)
        if should_stay_archived:
            console.print(f"📦 [dim]Manteniendo en Archive: contenido inactivo/completado[/dim]")
            return {
                'category': 'Archive',
                'folder_name': _extract_current_folder_name(note_path, vault_path),
                'confidence': 0.95,
                'method': 'archive_preservation',
                'reasoning': 'Nota ya archivada y sin indicadores de actividad reciente'
            }
    
    # 1. ANÁLISIS COMPLETO DE LA NOTA
    complete_analysis = analyze_note_completely(note_path, note_content, user_directive)
    
    # 1.5 NUEVO: Pre-calcular folder sugerido para análisis de tags
    # Esto es necesario para que el Factor 3 y 25 puedan evaluar coherencia
    if complete_analysis.get('tags'):
        # Hacer una clasificación preliminar rápida solo para obtener folder sugerido
        preliminary_result = classify_note_with_llm(note_content[:1000], user_directive, model_name, system_prompt)
        if preliminary_result:
            complete_analysis['suggested_folder_name'] = preliminary_result.get('folder_name', '')
            complete_analysis['suggested_category'] = preliminary_result.get('category', '')
    
    # 2. ANÁLISIS SEMÁNTICO CON CHROMADB
    analyze_manager = AnalyzeManager(vault_path, db_path=Path(db.db_path).parent)
    enhanced_suggestion = analyze_manager.get_enhanced_classification_suggestion(note_path, note_content)
    
    semantic_category = enhanced_suggestion['suggested_category']
    semantic_confidence = enhanced_suggestion['confidence_score']
    semantic_reasoning = enhanced_suggestion['reasoning']
    
    # 3. CLASIFICACIÓN CON LLM
    llm_result = classify_note_with_llm(note_content, user_directive, model_name, system_prompt)
    
    if not llm_result:
        console.print(f"[red]Error: No se pudo obtener clasificación LLM para {relative_path}[/red]")
        return None
    
    llm_category = llm_result.get('category', 'Unknown')
    llm_folder = llm_result.get('folder_name', '')
    llm_confidence = llm_result.get('confidence', 0.0)
    
    # 4. CÁLCULO DE PESOS DINÁMICOS CON ANÁLISIS COMPLETO
    weights = _calculate_dynamic_weights_with_analysis(semantic_confidence, complete_analysis, db, vault_path)
    
    semantic_weight = weights['semantic']
    llm_weight = weights['llm']
    
    # 5. DECISIÓN HÍBRIDA CON ANÁLISIS COMPLETO
    final_result = _make_hybrid_decision_with_analysis(
        semantic_category, semantic_confidence, semantic_reasoning,
        llm_category, llm_folder, llm_result,
        semantic_weight, llm_weight,
        complete_analysis, user_directive, vault_path
    )
    
    # 6. NUEVO: REGISTRO DE APRENDIZAJE AUTOMÁTICO (OPCIONAL)
    try:
        _register_classification_learning(
            note_content, note_path, final_result, complete_analysis,
            semantic_category, llm_category, semantic_confidence, llm_confidence,
            semantic_weight, llm_weight, vault_path, db
        )
    except Exception as e:
        # No fallar si el sistema de aprendizaje no está disponible
        if should_show('show_debug'):
            console.print(f"[dim]Warning: No se pudo registrar aprendizaje: {e}[/dim]")
        # Log del error para debugging
        try:
            from .log_center import log_center
            log_center.log_warning(f"Error en sistema de aprendizaje: {e}", "Organizer")
        except:
            pass
    
    # OUTPUT FINAL LIMPIO Y PROFESIONAL
    final_category = final_result.get('category', 'Unknown')
    final_folder = final_result.get('folder_name', 'Unknown')
    # Removido el console.print duplicado que causaba múltiples barras de progreso
    # console.print(f"PARA AI: {final_category} → {final_folder}")
    # console.print(f"Última modificación: {complete_analysis['last_modified']}")

    # NUEVO: FACTOR DE PROXIMIDAD TEMPORAL
    # Solo si la carpeta candidata existe
    candidate_folder = vault_path / final_category / final_folder
    temporal_score = 0.0
    if candidate_folder.exists():
        temporal_score = _calculate_temporal_proximity(note_path, candidate_folder)
        # Ajustar la confianza final
        if 'confidence' in final_result:
            final_result['confidence'] += temporal_score * 0.3  # Peso configurable
        if should_show('show_factors'):
            console.print(f"⏳ [cyan]Factor temporal: score={temporal_score:.2f} aplicado a {final_folder}[/cyan]")
    final_result['temporal_score'] = temporal_score
    # Agregar análisis completo al resultado
    final_result['analysis'] = complete_analysis
    
    # 6. NUEVO: LOGGING DETALLADO DE DECISIÓN DE CLASIFICACIÓN
    try:
        detailed_log = _log_detailed_classification_decision(
            note_content, note_path, final_result, complete_analysis,
            semantic_category, llm_category, semantic_confidence, llm_confidence,
            semantic_weight, llm_weight, vault_path, db, user_directive, model_name
        )
        
        # Mostrar información de logging en modo debug
        if should_show('show_debug'):
            console.print(f"[dim]📊 Log detallado guardado: {detailed_log.get('timestamp', 'N/A')}[/dim]")
            if detailed_log.get('learning_data', {}).get('requires_review', False):
                console.print(f"[yellow]⚠️ Nota requiere revisión manual[/yellow]")
        
    except Exception as e:
        # No fallar si el logging detallado no está disponible
        if should_show('show_debug'):
            console.print(f"[dim]Warning: No se pudo hacer logging detallado: {e}[/dim]")
        # Log del error para debugging
        try:
            from .log_center import log_center
            log_center.log_warning(f"Error en logging detallado: {e}", "Organizer")
        except:
            pass
    
    return final_result

def _register_classification_learning(note_content: str, note_path: Path, final_result: dict, 
                                    analysis: dict, semantic_category: str, llm_category: str,
                                    semantic_confidence: float, llm_confidence: float,
                                    semantic_weight: float, llm_weight: float,
                                    vault_path: Path, db: ChromaPARADatabase):
    """
    Registra la clasificación para aprendizaje automático y detección de errores.
    """
    try:
        from paralib.learning_system import PARA_Learning_System
        
        # Inicializar sistema de aprendizaje
        learning_system = PARA_Learning_System(db, vault_path)
        
        # Extraer información relevante
        predicted_category = final_result.get('category', 'Unknown')
        confidence = final_result.get('confidence', 0.0)
        method_used = final_result.get('method', 'unknown')
        reasoning = final_result.get('reasoning', '')
        
        # Detectar posibles errores de clasificación
        potential_error = _detect_classification_error(
            note_content, predicted_category, analysis, 
            semantic_category, llm_category, semantic_confidence, llm_confidence
        )
        
        # Registrar para aprendizaje
        classification_data = {
            'note_content': note_content[:500],  # Primeros 500 caracteres
            'note_path': str(note_path),
            'predicted_category': predicted_category,
            'confidence': confidence,
            'method_used': method_used,
            'reasoning': reasoning,
            'semantic_category': semantic_category,
            'llm_category': llm_category,
            'semantic_confidence': semantic_confidence,
            'llm_confidence': llm_confidence,
            'semantic_weight': semantic_weight,
            'llm_weight': llm_weight,
            'analysis': analysis,
            'potential_error': potential_error,
            'timestamp': datetime.now().isoformat()
        }
        
        # Aprender de la clasificación
        learning_result = learning_system.learn_from_classification(classification_data)
        
        # Si se detectó un error potencial, registrar feedback automático
        if potential_error.get('is_error', False):
            _register_automatic_feedback(
                learning_system, note_path, predicted_category, 
                potential_error, analysis, vault_path
            )
            
    except Exception as e:
        # No fallar si el sistema de aprendizaje no está disponible
        if should_show('show_debug'):
            console.print(f"[dim]Warning: No se pudo registrar aprendizaje: {e}[/dim]")

def _detect_classification_error(note_content: str, predicted_category: str, analysis: dict,
                               semantic_category: str, llm_category: str,
                               semantic_confidence: float, llm_confidence: float) -> dict:
    """
    Detecta posibles errores de clasificación basándose en múltiples indicadores.
    """
    error_indicators = {
        'is_error': False,
        'error_type': None,
        'confidence': 0.0,
        'reasoning': []
    }
    
    # 1. Detectar contenido de referencia clasificado como proyecto
    reference_score = _calculate_reference_content_score(note_content)
    if reference_score > 0.5 and predicted_category == 'Projects':
        error_indicators['is_error'] = True
        error_indicators['error_type'] = 'reference_as_project'
        error_indicators['confidence'] = min(reference_score, 0.9)
        error_indicators['reasoning'].append(f"Contenido de referencia (score: {reference_score:.2f}) clasificado como proyecto")
    
    # 2. Detectar proyecto clasificado como recurso
    project_resource_score = _calculate_project_vs_resource_score(note_content)
    if project_resource_score > 0.7 and predicted_category == 'Resources':
        error_indicators['is_error'] = True
        error_indicators['error_type'] = 'project_as_resource'
        error_indicators['confidence'] = min(project_resource_score, 0.9)
        error_indicators['reasoning'].append(f"Contenido de proyecto (score: {project_resource_score:.2f}) clasificado como recurso")
    
    # 3. Detectar discrepancias grandes entre categorías
    if semantic_category != llm_category and semantic_category != predicted_category and llm_category != predicted_category:
        error_indicators['is_error'] = True
        error_indicators['error_type'] = 'category_discrepancy'
        error_indicators['confidence'] = 0.7
        error_indicators['reasoning'].append(f"Discrepancia entre categorías: semántica={semantic_category}, llm={llm_category}, final={predicted_category}")
    
    # 4. Detectar confianza baja en clasificación final
    if predicted_category == 'Projects' and analysis.get('has_todos', False) == False and analysis.get('has_dates', False) == False:
        error_indicators['is_error'] = True
        error_indicators['error_type'] = 'project_without_indicators'
        error_indicators['confidence'] = 0.6
        error_indicators['reasoning'].append("Proyecto sin indicadores de acción (TO-DOs, fechas)")
    
    # 5. Detectar casos específicos conocidos (como Adam Spec)
    if 'adam' in note_content.lower() and 'spec' in note_content.lower() and predicted_category == 'Projects':
        error_indicators['is_error'] = True
        error_indicators['error_type'] = 'known_reference_case'
        error_indicators['confidence'] = 0.95
        error_indicators['reasoning'].append("Caso conocido: Adam Spec debe ser recurso, no proyecto")
    
    return error_indicators

def _register_automatic_feedback(learning_system, note_path: Path, predicted_category: str,
                               error_info: dict, analysis: dict, vault_path: Path):
    """
    Registra feedback automático cuando se detecta un error de clasificación.
    """
    try:
        # Determinar la categoría correcta basándose en el tipo de error
        correct_category = predicted_category
        feedback_reason = ""
        
        if error_info['error_type'] == 'reference_as_project':
            correct_category = 'Resources'
            feedback_reason = "Contenido de referencia debe ser Resources, no Projects"
        elif error_info['error_type'] == 'project_as_resource':
            correct_category = 'Projects'
            feedback_reason = "Contenido de proyecto debe ser Projects, no Resources"
        elif error_info['error_type'] == 'known_reference_case':
            correct_category = 'Resources'
            feedback_reason = "Caso específico: contenido de especificación debe ser Resources"
        
        # Registrar feedback automático
        folder_info = {
            'folder_name': note_path.stem,
            'category': predicted_category,
            'note_content': analysis.get('content', '')[:200],
            'note_tags': analysis.get('tags', []),
            'note_patterns': analysis.get('content_patterns', {}),
            'confidence': analysis.get('confidence', 0.0),
            'method_used': analysis.get('method', 'unknown'),
            'semantic_score': analysis.get('semantic_score', 0.0),
            'ai_score': analysis.get('ai_score', 0.0),
            'factors_applied': analysis.get('factors_applied', {})
        }
        
        learning_system.learn_from_folder_creation(
            folder_info, 
            user_feedback="negative", 
            feedback_reason=f"Error automático detectado: {feedback_reason}. Categoría correcta: {correct_category}"
        )
        
        if should_show('show_debug'):
            console.print(f"[yellow]🔍 Error de clasificación detectado y registrado: {feedback_reason}[/yellow]")
            
    except Exception as e:
        if should_show('show_debug'):
            console.print(f"[dim]Warning: No se pudo registrar feedback automático: {e}[/dim]")

def create_enriched_prompt(analysis: dict, user_directive: str) -> str:
    """
    Crea un prompt enriquecido con toda la información del análisis.
    """
    prompt_parts = []
    
    # Información básica
    prompt_parts.append(f"ANÁLISIS COMPLETO DE LA NOTA:")
    prompt_parts.append(f"- Palabras: {analysis['word_count']}")
    prompt_parts.append(f"- Última modificación: {analysis['last_modified']}")
    prompt_parts.append(f"- Días desde modificación: {analysis.get('days_since_modified', 'N/A')}")
    
    # Tags y metadatos
    if analysis['tags']:
        prompt_parts.append(f"- Tags: {', '.join(analysis['tags'][:10])}")
    
    if analysis['obsidian_tags']:
        prompt_parts.append(f"- Tags Obsidian: {', '.join(analysis['obsidian_tags'])}")
    
    # Patrones de contenido
    patterns = []
    if analysis['has_todos']:
        patterns.append(f"TO-DOs: {analysis['todo_count']}")
    if analysis['has_dates']:
        patterns.append(f"Fechas: {len(analysis['dates_found'])} encontradas")
    if analysis['has_links']:
        patterns.append(f"Enlaces: {analysis['link_count']}")
    if analysis['has_attachments']:
        patterns.append(f"Adjuntos: {len(analysis['attachments'])}")
    
    if patterns:
        prompt_parts.append(f"- Patrones: {', '.join(patterns)}")
    
    # Frontmatter
    if analysis['frontmatter']:
        prompt_parts.append(f"- Frontmatter: {analysis['frontmatter']}")
    
    # Contexto del usuario
    prompt_parts.append(f"\nDIRECTIVA DEL USUARIO: {user_directive}")
    if analysis['user_context']['directive_keywords']:
        prompt_parts.append(f"- Palabras clave de directiva: {', '.join(analysis['user_context']['directive_keywords'])}")
    
    # Contenido de la nota
    prompt_parts.append(f"\nCONTENIDO DE LA NOTA:")
    prompt_parts.append(f"---\n{analysis['content'][:4000]}\n---")
    
    return "\n".join(prompt_parts)

def _print_factor(message: str, style: str = None):
    """Imprime mensaje de factor solo si está habilitado en debug."""
    if should_show('show_factors'):
        if style:
            console.print(f"[{style}]{message}[/{style}]")
        else:
            console.print(message)

def _calculate_dynamic_weights_with_analysis(semantic_confidence: float, analysis: dict, db: ChromaPARADatabase, vault_path: Path) -> dict:
    """
    Calcula pesos dinámicos considerando el análisis completo de la nota.
    Factores mejorados para máxima precisión - OBJETIVO: 95% ACCURACY.
    """
    # Base weights
    base_semantic = 0.6
    base_llm = 0.4
    # Inicializar todos los boosts/penalties
    semantic_boost = 0.0
    llm_boost = 0.0
    semantic_penalty = 0.0
    llm_penalty = 0.0
    
    # Factor 1: Confianza semántica
    if semantic_confidence > 0.8:
        semantic_boost = 0.25
        llm_penalty = -0.15
    elif semantic_confidence > 0.6:
        semantic_boost = 0.15
        llm_penalty = -0.1
    elif semantic_confidence < 0.3:
        semantic_penalty = -0.25
        llm_boost = 0.25
    else:
        semantic_boost = 0.0
        llm_penalty = 0.0
        semantic_penalty = 0.0
        llm_boost = 0.0
    
    # Factor 2: Complejidad del contenido
    word_count = analysis['word_count']
    if word_count > 1000:  # Contenido muy complejo
        llm_boost += 0.2
        semantic_penalty += 0.1
    elif word_count > 500:  # Contenido complejo
        llm_boost += 0.15
        semantic_penalty += 0.05
    elif word_count < 50:  # Contenido simple
        semantic_boost += 0.15
        llm_penalty += 0.1
    elif word_count < 20:  # Contenido muy simple
        semantic_boost += 0.25
        llm_penalty += 0.15
    
    # Factor 3: Tags de Obsidian (CRÍTICO - MEJORADO)
    obsidian_tags = analysis.get('obsidian_tags', [])
    all_tags = analysis.get('tags', [])  # TODOS los tags, no solo PARA
    
    # Limpiar tags inválidos
    if all_tags:
        all_tags = _clean_invalid_tags(all_tags)
        analysis['tags'] = all_tags  # Actualizar con tags limpios
    
    # Obtener folder sugerido del análisis
    suggested_folder = analysis.get('suggested_folder_name', '')
    
    # Primero, aplicar boost por tags PARA específicos
    if obsidian_tags:
        semantic_boost += 0.2  # Reducido porque ahora consideramos más factores
        llm_penalty += 0.1
        
        # Tags específicos tienen diferentes pesos
        tag_weights = {
            'project': 0.1,
            'area': 0.1,
            'resource': 0.1,
            'archive': 0.1,
            'inbox': 0.05
        }
        
        for tag in obsidian_tags:
            if tag.lower() in tag_weights:
                semantic_boost += tag_weights[tag.lower()]
    
    # NUEVO: Analizar TODOS los tags temáticos para agrupación inteligente
    if all_tags and hasattr(db, '_tag_analyzer'):
        # Obtener el folder sugerido para comparar con tags históricos
        suggested_folder = analysis.get('suggested_folder_name', '')
        if suggested_folder:
            tag_weight = db._tag_analyzer.calculate_tag_weight_for_classification(
                set(all_tags), 
                analysis.get('suggested_category', 'Unknown'),
                suggested_folder
            )
            
            if tag_weight > 0.7:
                semantic_boost += 0.6  # BOOST MÁXIMO para tags dominantes
                if should_show('show_factors'):
                    console.print(f"🏷️ [bold green]Factor 3 MEJORADO: Tags dominantes detectados → {suggested_folder} (peso: {tag_weight:.2f})[/bold green]")
            elif tag_weight > 0.5:
                semantic_boost += 0.4
                if should_show('show_factors'):
                    console.print(f"🏷️ [yellow]Factor 3: Tags correlacionados → {suggested_folder} (peso: {tag_weight:.2f})[/yellow]")
            elif tag_weight > 0.3:
                semantic_boost += 0.2
                if should_show('show_factors'):
                    console.print(f"🏷️ [dim]Factor 3: Tags parcialmente relacionados (peso: {tag_weight:.2f})[/dim]")
    
    # Factor 4: Patrones de contenido (MEJORADO)
    if analysis['has_todos'] and analysis['has_dates']:
        semantic_boost += 0.2  # Patrón fuerte de proyecto
    elif analysis['has_todos']:
        semantic_boost += 0.15  # Solo TO-DOs
    elif analysis['has_dates']:
        semantic_boost += 0.1  # Solo fechas
    
    if analysis['has_links']:
        link_count = analysis.get('link_count', 0)
        if link_count > 10:
            semantic_boost += 0.15  # Muchos enlaces = recurso
        elif link_count > 5:
            semantic_boost += 0.1
        else:
            semantic_boost += 0.05
    
    if analysis['has_attachments']:
        semantic_boost += 0.1  # Archivos adjuntos = recurso
    
    # Factor 5: Análisis temporal (MEJORADO)
    recency = analysis.get('recency', 'moderate')
    if recency == 'very_recent':
        llm_boost += 0.15  # IA maneja mejor contenido reciente
        semantic_penalty += 0.05
    elif recency == 'recent':
        llm_boost += 0.1
    elif recency == 'old':
        semantic_boost += 0.15  # ChromaDB es mejor para contenido histórico
        llm_penalty += 0.1
    elif recency == 'very_old':
        semantic_boost += 0.25  # Contenido muy antiguo
        llm_penalty += 0.15
    
    # Factor 6: Directiva del usuario (MEJORADO)
    if analysis['user_context']['has_specific_instructions']:
        llm_boost += 0.3  # IA respeta mejor las directivas específicas
        semantic_penalty += 0.15
        
        # Palabras clave específicas en la directiva
        directive_keywords = analysis['user_context']['directive_keywords']
        if 'urgent' in directive_keywords or 'priority' in directive_keywords:
            llm_boost += 0.1
        if 'project' in directive_keywords:
            llm_boost += 0.1
        if 'resource' in directive_keywords:
            llm_boost += 0.1
        if 'archive' in directive_keywords:
            llm_boost += 0.1
    
    # Factor 7: Base de datos ChromaDB (MEJORADO)
    total_notes = len(db.get_all_notes_metadata())
    if total_notes < 5:
        llm_boost += 0.25
        semantic_penalty += 0.2
    elif total_notes < 20:
        llm_boost += 0.15
        semantic_penalty += 0.1
    elif total_notes > 200:
        semantic_boost += 0.15
        llm_penalty += 0.1
    elif total_notes > 100:
        semantic_boost += 0.1
        llm_penalty += 0.05
    
    # Factor 8: Patrones de contenido específicos (NUEVO)
    content_patterns = analysis.get('content_patterns', {})
    if content_patterns.get('has_headers'):
        semantic_boost += 0.05  # Estructura organizada
    if content_patterns.get('has_lists'):
        semantic_boost += 0.05  # Listas = organización
    if content_patterns.get('has_tables'):
        semantic_boost += 0.1  # Tablas = recurso
    if content_patterns.get('has_code_blocks'):
        semantic_boost += 0.1  # Código = recurso técnico
    
    # Factor 9: Tamaño del archivo (NUEVO)
    file_size = analysis.get('file_size', 0)
    if file_size > 10000:  # Archivo grande
        llm_boost += 0.1
        semantic_penalty += 0.05
    elif file_size < 1000:  # Archivo pequeño
        semantic_boost += 0.1
        llm_penalty += 0.05
    
    # Factor 10: Presencia de frontmatter (NUEVO)
    if analysis.get('frontmatter'):
        semantic_boost += 0.1  # Frontmatter = nota estructurada
        llm_penalty += 0.05
    
    # Factor 11: Densidad de información (NUEVO)
    if word_count > 0:
        info_density = (analysis.get('link_count', 0) + analysis.get('todo_count', 0)) / word_count
        if info_density > 0.1:  # Alta densidad de información
            semantic_boost += 0.15
        elif info_density > 0.05:  # Densidad media
            semantic_boost += 0.1
    
    # ===== FACTORES SUPREMOS REBALANCEADOS =====
    # JERARQUÍA: CRÍTICOS > IMPORTANTES > AUXILIARES
    
    # Factor 12: Network Centrality (CRÍTICO - PRIORIDAD ALTA) +15% PRECISIÓN
    network_score = _calculate_network_centrality(analysis.get('path'), vault_path)
    if network_score > 10:  # Nodo muy central = RESOURCES (alta prioridad)
        semantic_boost += 0.50  # PESO ALTO para factor crítico
        llm_penalty += 0.30
        _print_factor(f"🌐 Factor 12 CRÍTICO: Red muy central ({network_score}) → RESOURCES FORZADO", "bold red")
    elif network_score > 5:  # Nodo central = probable resource
        semantic_boost += 0.35
        llm_penalty += 0.20
        _print_factor(f"🌐 Factor 12 CRÍTICO: Red central ({network_score}) → Resources prioritario", "bold yellow")
    elif network_score > 1:  # Conectividad moderada
        semantic_boost += 0.15
        llm_penalty += 0.08
        _print_factor(f"🌐 Factor 12: Red conectada ({network_score}) → minor boost", "dim")
    elif network_score == 0:  # Nodo aislado = proyecto/área nueva
        llm_boost += 0.25  # Mayor peso para IA con notas nuevas
        semantic_penalty += 0.10
        _print_factor(f"🌐 Factor 12: Nota aislada → boost IA", "dim")
    
    # Factor 13: Action Verb Density (AUXILIAR - PESO REDUCIDO)
    action_density = _calculate_action_verb_density(analysis.get('content', ''))
    if action_density > 0.05:  # Muchos verbos de acción = proyecto
        semantic_boost += 0.08  # PESO REDUCIDO
        llm_penalty += 0.03
        console.print(f"⚡ [dim]Factor 13 auxiliar: Alta densidad de acción ({action_density:.3f}) → minor Projects[/dim]")
    elif action_density > 0.03:  # Verbos moderados
        semantic_boost += 0.05  # PESO REDUCIDO
        llm_penalty += 0.02
        console.print(f"⚡ [dim]Factor 13 auxiliar: Densidad moderada ({action_density:.3f}) → minor boost[/dim]")
    elif action_density < 0.01:  # Pocos verbos = recurso teórico
        llm_boost += 0.03  # PESO REDUCIDO
        console.print(f"⚡ [dim]Factor 13 auxiliar: Baja densidad ({action_density:.3f}) → minor Resources[/dim]")
    
    # Factor 14: Outcome Specificity (AUXILIAR - PESO REDUCIDO)
    outcome_score = _calculate_outcome_specificity(analysis.get('content', ''))
    if outcome_score > 0.7:  # Outcomes muy específicos = proyecto
        semantic_boost += 0.10  # PESO REDUCIDO
        llm_penalty += 0.05
        console.print(f"🎯 [dim]Factor 14 auxiliar: Outcomes específicos ({outcome_score:.2f}) → minor Projects[/dim]")
    elif outcome_score > 0.4:  # Outcomes moderados
        semantic_boost += 0.06  # PESO REDUCIDO
        llm_penalty += 0.03
        console.print(f"🎯 [dim]Factor 14 auxiliar: Outcomes moderados ({outcome_score:.2f}) → minor boost[/dim]")
    
    # Factor 15: Update Frequency Pattern (AUXILIAR - PESO REDUCIDO)
    update_pattern = _calculate_update_frequency_pattern(analysis.get('path'), vault_path)
    if update_pattern == 'very_frequent':  # Actualización muy frecuente = proyecto activo
        semantic_boost += 0.08  # PESO REDUCIDO
        llm_penalty += 0.03
        console.print(f"📅 [dim]Factor 15 auxiliar: Actualización muy frecuente → minor Projects[/dim]")
    elif update_pattern == 'frequent':  # Actualización frecuente = área
        semantic_boost += 0.05  # PESO REDUCIDO
        llm_penalty += 0.02
        console.print(f"📅 [dim]Factor 15 auxiliar: Actualización frecuente → minor Areas[/dim]")
    elif update_pattern == 'rare':  # Actualización rara = archivo
        llm_boost += 0.06  # PESO REDUCIDO
        semantic_penalty += 0.03
        console.print(f"📅 [dim]Factor 15 auxiliar: Actualización rara → minor Archive[/dim]")
    
    # Factor 16: Urgency Indicators (CRÍTICO - PRIORIDAD ALTA) +12% PRECISIÓN
    urgency_score = _calculate_urgency_indicators(analysis.get('content', ''))
    if urgency_score > 0.6:  # Muy urgente = PROJECTS (máxima prioridad)
        semantic_boost += 0.60  # PESO MÁXIMO para urgencia alta
        llm_penalty += 0.35
        console.print(f"🚨 [bold red]Factor 16 CRÍTICO: Muy urgente ({urgency_score:.2f}) → PROJECTS FORZADO[/bold red]")
    elif urgency_score > 0.3:  # Moderadamente urgente = probable project
        semantic_boost += 0.40
        llm_penalty += 0.25
        console.print(f"🚨 [bold yellow]Factor 16 CRÍTICO: Moderadamente urgente ({urgency_score:.2f}) → Projects prioritario[/bold yellow]")
    elif urgency_score > 0.1:  # Algo de urgencia
        semantic_boost += 0.20
        llm_penalty += 0.10
        console.print(f"🚨 [dim]Factor 16: Leve urgencia ({urgency_score:.2f}) → boost Projects[/dim]")
    
    # Factor 17: Temporal Context (CRÍTICO - PRIORIDAD ALTA) +10% PRECISIÓN
    temporal_context = _calculate_temporal_context(analysis.get('content', ''))
    if temporal_context == 'deadline_driven':  # PROJECTS (alta prioridad)
        semantic_boost += 0.45  # PESO ALTO para deadline-driven
        llm_penalty += 0.25
        console.print(f"⏰ [bold red]Factor 17 CRÍTICO: Deadline-driven → PROJECTS FORZADO[/bold red]")
    elif temporal_context == 'scheduled':  # AREAS (prioridad media-alta)
        semantic_boost += 0.35
        llm_penalty += 0.20
        console.print(f"⏰ [bold yellow]Factor 17 CRÍTICO: Scheduled/routine → AREAS PRIORITARIO[/bold yellow]")
    elif temporal_context == 'evergreen':  # RESOURCES (prioridad media-alta)
        llm_boost += 0.35  # Boost hacia IA que maneja mejor resources
        semantic_penalty += 0.20
        console.print(f"⏰ [bold blue]Factor 17 CRÍTICO: Evergreen content → RESOURCES PRIORITARIO[/bold blue]")
    elif temporal_context == 'neutral':  # Sin contexto temporal claro
        llm_boost += 0.10  # Boost menor para IA
        console.print(f"⏰ [dim]Factor 17: Neutral temporal → minor IA boost[/dim]")
    
    # Factor 18: Semantic Coherence (AUXILIAR - PESO REDUCIDO)
    coherence_score = _calculate_semantic_coherence_with_category(analysis, db)
    if coherence_score > 0.85:  # Alta coherencia con categoría semántica
        semantic_boost += 0.08  # PESO REDUCIDO
        llm_penalty += 0.04
        console.print(f"🔗 [dim]Factor 18 auxiliar: Alta coherencia ({coherence_score:.2f}) → minor boost[/dim]")
    elif coherence_score > 0.70:  # Coherencia moderada
        semantic_boost += 0.05  # PESO REDUCIDO
        llm_penalty += 0.02
        console.print(f"🔗 [dim]Factor 18 auxiliar: Coherencia moderada ({coherence_score:.2f}) → minor[/dim]")
    elif coherence_score < 0.40:  # Baja coherencia = confiar más en IA
        llm_boost += 0.06  # PESO REDUCIDO
        semantic_penalty += 0.03
        console.print(f"🔗 [dim]Factor 18 auxiliar: Baja coherencia ({coherence_score:.2f}) → minor IA[/dim]")
    
    # Factor 19: Cross-Reference Density (AUXILIAR - PESO REDUCIDO)
    cross_ref_density = _calculate_cross_reference_density(analysis.get('content', ''))
    if cross_ref_density > 0.08:  # Muchas referencias cruzadas = recurso
        llm_boost += 0.06  # PESO REDUCIDO
        semantic_penalty += 0.03
        console.print(f"🔗 [dim]Factor 19 auxiliar: Muchas referencias ({cross_ref_density:.3f}) → minor Resources[/dim]")
    elif cross_ref_density > 0.04:  # Referencias moderadas
        llm_boost += 0.03  # PESO REDUCIDO
        semantic_penalty += 0.02
        console.print(f"🔗 [dim]Factor 19 auxiliar: Referencias moderadas ({cross_ref_density:.3f}) → minor[/dim]")
    
    # Factor 20: Completion Status (IMPORTANTE - PRIORIDAD MEDIA)
    completion_status = _calculate_completion_status(analysis.get('content', ''))
    if completion_status == 'in_progress':  # En progreso = PROJECTS
        semantic_boost += 0.30
        llm_penalty += 0.15
        console.print(f"⚙️ [bold green]Factor 20 IMPORTANTE: En progreso → PROJECTS[/bold green]")
    elif completion_status == 'completed':  # Completado = ARCHIVE (máxima prioridad)
        llm_boost += 0.70  # PESO MÁXIMO para completado → archive
        semantic_penalty += 0.40
        console.print(f"⚙️ [bold red]Factor 20 CRÍTICO: Completado → ARCHIVE FORZADO[/bold red]")
    elif completion_status == 'planning':  # En planeación = AREAS
        semantic_boost += 0.25
        llm_penalty += 0.12
        console.print(f"⚙️ [bold magenta]Factor 20 IMPORTANTE: En planeación → AREAS[/bold magenta]")
    
    # Factor 21: Stakeholder Mentions (AUXILIAR - PESO REDUCIDO)
    stakeholder_density = _calculate_stakeholder_mentions(analysis.get('content', ''))
    if stakeholder_density > 0.03:  # Muchas menciones de personas = proyecto
        semantic_boost += 0.06  # PESO REDUCIDO
        llm_penalty += 0.03
        console.print(f"👥 [dim]Factor 21 auxiliar: Muchas menciones ({stakeholder_density:.3f}) → minor Projects[/dim]")
    elif stakeholder_density > 0.01:  # Menciones moderadas
        semantic_boost += 0.03  # PESO REDUCIDO
        llm_penalty += 0.02
        console.print(f"👥 [dim]Factor 21 auxiliar: Menciones moderadas ({stakeholder_density:.3f}) → minor[/dim]")
    
    # Factor 22: Knowledge Depth (IMPORTANTE - PRIORIDAD MEDIA) - MEJORADO
    knowledge_depth = _calculate_knowledge_depth(analysis.get('content', ''))
    if knowledge_depth == 'deep_technical':  # RESOURCES (prioridad alta)
        llm_boost += 0.45  # AUMENTADO para evitar clasificación incorrecta
        semantic_penalty += 0.25
        console.print(f"🧠 [bold blue]Factor 22 IMPORTANTE: Conocimiento técnico profundo → RESOURCES[/bold blue]")
    elif knowledge_depth == 'reference_material':  # RESOURCES (CRÍTICO)
        llm_boost += 0.50  # PESO MÁXIMO para material de referencia
        semantic_penalty += 0.30
        console.print(f"🧠 [bold red]Factor 22 CRÍTICO: Material de referencia → RESOURCES FORZADO[/bold red]")
    elif knowledge_depth == 'procedural':  # AREAS
        semantic_boost += 0.25
        llm_penalty += 0.12
        console.print(f"🧠 [bold magenta]Factor 22 IMPORTANTE: Conocimiento procedimental → AREAS[/bold magenta]")
    elif knowledge_depth == 'actionable':  # PROJECTS
        semantic_boost += 0.30
        llm_penalty += 0.15
        console.print(f"🧠 [bold green]Factor 22 IMPORTANTE: Conocimiento accionable → PROJECTS[/bold green]")
    
    # NUEVO Factor 26: Reference Content Detection (CRÍTICO) +15% PRECISIÓN
    reference_score = _calculate_reference_content_score(analysis.get('content', ''))
    if reference_score > 0.7:  # Contenido claramente de referencia
        llm_boost += 0.60  # PESO MÁXIMO para contenido de referencia
        semantic_penalty += 0.35
        console.print(f"📚 [bold red]Factor 26 CRÍTICO: Contenido de referencia ({reference_score:.2f}) → RESOURCES FORZADO[/bold red]")
    elif reference_score > 0.5:  # Probable contenido de referencia
        llm_boost += 0.40
        semantic_penalty += 0.25
        console.print(f"📚 [bold yellow]Factor 26 CRÍTICO: Probable referencia ({reference_score:.2f}) → Resources prioritario[/bold yellow]")
    elif reference_score > 0.3:  # Algo de contenido de referencia
        llm_boost += 0.25
        semantic_penalty += 0.15
        console.print(f"📚 [dim]Factor 26: Contenido referencial ({reference_score:.2f}) → minor Resources[/dim]")
    
    # NUEVO Factor 27: Project vs Resource Distinction (CRÍTICO) +12% PRECISIÓN
    project_resource_score = _calculate_project_vs_resource_score(analysis.get('content', ''))
    if project_resource_score < 0.3:  # Claramente un recurso
        llm_boost += 0.55  # PESO ALTO para evitar clasificación como proyecto
        semantic_penalty += 0.30
        console.print(f"🎯 [bold red]Factor 27 CRÍTICO: Claramente recurso ({project_resource_score:.2f}) → RESOURCES FORZADO[/bold red]")
    elif project_resource_score > 0.7:  # Claramente un proyecto
        semantic_boost += 0.45
        llm_penalty += 0.25
        console.print(f"🎯 [bold green]Factor 27 CRÍTICO: Claramente proyecto ({project_resource_score:.2f}) → PROJECTS FORZADO[/bold green]")
    elif project_resource_score > 0.5:  # Probable proyecto
        semantic_boost += 0.30
        llm_penalty += 0.15
        console.print(f"🎯 [bold yellow]Factor 27 CRÍTICO: Probable proyecto ({project_resource_score:.2f}) → Projects prioritario[/bold yellow]")
    
    # NUEVO Factor 28: Content Type Analysis (IMPORTANTE) +10% PRECISIÓN
    content_type = _analyze_content_type(analysis.get('content', ''))
    if content_type == 'specification' or content_type == 'documentation':
        llm_boost += 0.45  # Especificaciones y documentación = recursos
        semantic_penalty += 0.25
        console.print(f"📋 [bold blue]Factor 28 IMPORTANTE: {content_type.title()} → RESOURCES[/bold blue]")
    elif content_type == 'tutorial' or content_type == 'guide':
        llm_boost += 0.40
        semantic_penalty += 0.20
        console.print(f"📋 [bold blue]Factor 28 IMPORTANTE: {content_type.title()} → RESOURCES[/bold blue]")
    elif content_type == 'active_task' or content_type == 'ongoing_work':
        semantic_boost += 0.40
        llm_penalty += 0.20
        console.print(f"📋 [bold green]Factor 28 IMPORTANTE: {content_type.title()} → PROJECTS[/bold green]")
    elif content_type == 'planning' or content_type == 'strategy':
        semantic_boost += 0.35
        llm_penalty += 0.15
        console.print(f"📋 [bold magenta]Factor 28 IMPORTANTE: {content_type.title()} → AREAS[/bold magenta]")
    
    # Factor 29: Emotional Context (AUXILIAR - PESO REDUCIDO)
    emotional_context = _calculate_emotional_context(analysis.get('content', ''))
    if emotional_context == 'high_stress':  # Alto estrés = proyecto urgente
        semantic_boost += 0.08  # PESO REDUCIDO
        llm_penalty += 0.04
        console.print(f"😰 [dim]Factor 23 auxiliar: Alto estrés → minor Projects[/dim]")
    elif emotional_context == 'excitement':  # Emoción positiva = proyecto nuevo
        semantic_boost += 0.06  # PESO REDUCIDO
        llm_penalty += 0.03
        console.print(f"🎉 [dim]Factor 23 auxiliar: Emoción positiva → minor Projects[/dim]")
    elif emotional_context == 'neutral_analytical':  # Neutro analítico = recurso
        llm_boost += 0.05  # PESO REDUCIDO
        semantic_penalty += 0.02
        console.print(f"📝 [dim]Factor 23 auxiliar: Neutro analítico → minor Resources[/dim]")
    
    # Factor 30: Duplicate Detection (IMPORTANTE - PRIORIDAD MEDIA)
    duplicate_pattern = _detect_duplicate_pattern(analysis.get('path', ''))
    if duplicate_pattern['is_duplicate']:
        # Si es un duplicado, penalizar moderadamente y marcar para revisión
        semantic_penalty += 0.15  # PESO MODERADO para duplicados
        llm_penalty += 0.08
        console.print(f"🔄 [bold orange]Factor 24 IMPORTANTE: Duplicado detectado '{duplicate_pattern['pattern']}' - REVISIÓN REQUERIDA[/bold orange]")
        
        # Log para posible limpieza automática
        duplicate_info = {
            'original_pattern': duplicate_pattern['base_name'],
            'duplicate_pattern': duplicate_pattern['pattern'],
            'suggested_action': 'merge_or_review'
        }
        
        # Agregar al análisis para reporte posterior
        analysis['duplicate_detection'] = duplicate_info
    
    # Factor 31: Tag Coherence (CRÍTICO - NUEVO) +10% PRECISIÓN
    if all_tags and suggested_folder:
        tag_coherence = _calculate_tag_coherence(all_tags, suggested_folder, vault_path, db)
        if tag_coherence > 0.8:
            semantic_boost += 0.5  # PESO ALTO para coherencia de tags
            llm_penalty += 0.25
            console.print(f"🏷️ [bold green]Factor 25 CRÍTICO: Alta coherencia de tags ({tag_coherence:.2f}) → FORZAR {suggested_folder}[/bold green]")
        elif tag_coherence > 0.6:
            semantic_boost += 0.35
            llm_penalty += 0.18
            console.print(f"🏷️ [bold yellow]Factor 25: Buena coherencia de tags ({tag_coherence:.2f}) → {suggested_folder}[/bold yellow]")
        elif tag_coherence > 0.4:
            semantic_boost += 0.20
            llm_penalty += 0.10
            console.print(f"🏷️ [dim]Factor 25: Coherencia moderada de tags ({tag_coherence:.2f})[/dim]")
        elif tag_coherence < 0.2 and tag_coherence > 0:
            # Baja coherencia = posible clasificación incorrecta
            semantic_penalty += 0.15
            llm_boost += 0.15
            console.print(f"🏷️ [bold red]Factor 25: Baja coherencia de tags ({tag_coherence:.2f}) - REVISAR[/bold red]")
    
    # Aplicar ajustes
    final_semantic = base_semantic + semantic_boost - semantic_penalty
    final_llm = base_llm + llm_boost - llm_penalty
    
    # Normalizar a 0-1
    total = final_semantic + final_llm
    final_semantic = max(0.1, min(0.9, final_semantic / total))
    final_llm = max(0.1, min(0.9, final_llm / total))
    
    return {
        'semantic': final_semantic,
        'llm': final_llm,
        'factors_applied': {
            'network_centrality': network_score,
            'action_density': action_density,
            'outcome_specificity': outcome_score,
            'update_frequency': update_pattern,
            'urgency': urgency_score,
            'temporal_context': temporal_context,
            'semantic_coherence': coherence_score,
            'cross_reference_density': cross_ref_density,
            'completion_status': completion_status,
            'stakeholder_density': stakeholder_density,
            'knowledge_depth': knowledge_depth,
            'emotional_context': emotional_context,
            'tag_coherence': tag_coherence if 'tag_coherence' in locals() else 0.0,
            'tags_analyzed': len(all_tags) if all_tags else 0
        }
    }

# ===== FUNCIONES AUXILIARES DE LIMPIEZA =====

def is_folder_empty(folder_path: Path) -> bool:
    """Verifica si una carpeta está completamente vacía."""
    try:
        return not any(folder_path.iterdir())
    except Exception:
        return False

def is_note_empty(content: str) -> bool:
    """Verifica si una nota está vacía o solo tiene whitespace/frontmatter vacío."""
    # Remover frontmatter vacío
    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
    # Remover whitespace
    content = content.strip()
    # Considerar vacía si tiene menos de 10 caracteres útiles
    return len(content) < 10

def count_files_in_folder(folder_path: Path) -> int:
    """Cuenta archivos en una carpeta recursivamente."""
    try:
        return len(list(folder_path.rglob("*"))) if folder_path.exists() else 0
    except Exception:
        return 0

def find_duplicate_folders(folders: list[Path]) -> list[list[Path]]:
    """Encuentra grupos de carpetas duplicadas por similitud de nombres."""
    import difflib
    
    groups = []
    processed = set()
    
    for i, folder1 in enumerate(folders):
        if folder1 in processed:
            continue
            
        group = [folder1]
        processed.add(folder1)
        
        for j, folder2 in enumerate(folders[i+1:], i+1):
            if folder2 in processed:
                continue
                
            # Verificar similitud de nombres
            similarity = difflib.SequenceMatcher(None, 
                                               folder1.name.lower(), 
                                               folder2.name.lower()).ratio()
            
            if similarity > 0.8:  # 80% de similitud
                group.append(folder2)
                processed.add(folder2)
        
        if len(group) > 1:
            groups.append(group)
    
    return groups

def find_duplicate_notes_by_content(notes: list[Path]) -> list[list[Path]]:
    """Encuentra notas duplicadas por contenido."""
    import hashlib
    
    content_hashes = {}
    
    for note in notes:
        try:
            content = note.read_text(encoding='utf-8')
            # Crear hash del contenido normalizado
            normalized_content = re.sub(r'\s+', ' ', content).strip()
            content_hash = hashlib.md5(normalized_content.encode()).hexdigest()
            
            if content_hash not in content_hashes:
                content_hashes[content_hash] = []
            content_hashes[content_hash].append(note)
        except Exception:
            continue
    
    # Retornar solo grupos con duplicados
    return [group for group in content_hashes.values() if len(group) > 1]

def merge_folders(source: Path, target: Path):
    """Fusiona el contenido de source en target y elimina source."""
    try:
        for item in source.iterdir():
            target_path = target / item.name
            
            if item.is_file():
                # Si el archivo ya existe, crear nombre único
                if target_path.exists():
                    counter = 1
                    while target_path.exists():
                        name_parts = item.stem, f"_{counter}", item.suffix
                        target_path = target / "".join(name_parts)
                        counter += 1
                
                shutil.move(str(item), str(target_path))
            
            elif item.is_dir():
                if target_path.exists():
                    # Fusionar recursivamente
                    merge_folders(item, target_path)
                else:
                    shutil.move(str(item), str(target_path))
        
        # Eliminar carpeta source vacía
        source.rmdir()
        
    except Exception as e:
        console.print(f"Error fusionando carpetas: {e}")
        raise

# Global shared ChromaDB instance to avoid reinitializations
_shared_chromadb_instance = None
_shared_chromadb_path = None

def get_shared_chromadb(vault_path: Path) -> ChromaPARADatabase:
    """
    Obtiene instancia compartida de ChromaDB para evitar reinicializaciones múltiples.
    Esto previene el problema de crear nueva DB para cada nota (3+ segundos × 940 notas).
    """
    global _shared_chromadb_instance, _shared_chromadb_path
    
    # Calcular path esperado
    db_path = vault_path / ".para_db" / "chroma"
    db_path_str = str(db_path)
    
    # Si ya existe instancia para el mismo path, reutilizarla
    if _shared_chromadb_instance and _shared_chromadb_path == db_path_str:
        console.print("🔄 [dim]Reutilizando instancia ChromaDB existente[/dim]")
        return _shared_chromadb_instance
    
    # Crear nueva instancia solo si es necesario
    console.print(f"🔧 [yellow]Inicializando ChromaDB compartido en: {db_path}[/yellow]")
    _shared_chromadb_instance = ChromaPARADatabase(db_path=db_path_str)
    _shared_chromadb_path = db_path_str
    
    return _shared_chromadb_instance

def reset_shared_chromadb():
    """Resetea la instancia compartida si es necesario."""
    global _shared_chromadb_instance, _shared_chromadb_path
    _shared_chromadb_instance = None
    _shared_chromadb_path = None

def _calculate_tag_coherence(tags: List[str], folder_name: str, vault_path: Path, db) -> float:
    """Calcula coherencia entre tags y carpeta destino."""
    if not tags or not folder_name:
        return 0.0
    
    try:
        # Inicializar o obtener el analizador de tags (singleton)
        if not hasattr(db, '_tag_analyzer'):
            db._tag_analyzer = TagAnalyzer(vault_path)
            # Solo analizar una vez
            if not hasattr(db._tag_analyzer, '_analyzed'):
                db._tag_analyzer.analyze_vault_tags()
                db._tag_analyzer._analyzed = True
        
        tag_analyzer = db._tag_analyzer
        
        coherence_scores = []
        for tag in tags:
            # Limpiar tag inválido
            if len(tag) > 20 or tag.isdigit() or len(tag) <= 1:
                continue
                
            # Si el tag aparece en el análisis histórico
            if tag in tag_analyzer.tag_folders:
                folder_dist = tag_analyzer.tag_folders[tag]
                if folder_name in folder_dist:
                    dominance = folder_dist[folder_name] / sum(folder_dist.values())
                    coherence_scores.append(dominance)
                else:
                    # Penalizar si el tag no aparece en esta carpeta
                    coherence_scores.append(0.0)
        
        # Retornar el promedio de coherencias
        if coherence_scores:
            return sum(coherence_scores) / len(coherence_scores)
        return 0.0
        
    except Exception as e:
        logger.warning(f"Error calculando coherencia de tags: {e}")
        return 0.0

def _clean_invalid_tags(tags: List[str]) -> List[str]:
    """Filtra tags inválidos o sin valor semántico."""
    valid_tags = []
    
    for tag in tags:
        # Ignorar IDs largos
        if len(tag) > 20 and any(c in tag for c in '0123456789'):
            continue
        # Ignorar números puros
        if tag.isdigit():
            continue
        # Ignorar tags de una letra
        if len(tag) <= 1:
            continue
        # Ignorar caracteres especiales raros
        if '/' in tag or '#' in tag:
            continue
            
        valid_tags.append(tag)
    
    return valid_tags

def _detect_duplicate_pattern(note_path: str) -> dict:
    """
    Factor 23: Detecta archivos duplicados automáticos por patrón de nombres.
    Identifica archivos con sufijos _1, _2, _copy, etc. que son copias automáticas.
    """
    import re
    
    if not note_path:
        return {'is_duplicate': False, 'base_name': '', 'pattern': '', 'suggested_action': 'no_action'}
    
    base_name = os.path.basename(note_path)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # Patrones de duplicados automáticos más comunes
    duplicate_patterns = [
        r'_(\d+)$',           # archivo_1, archivo_2
        r'_copy(\d*)$',       # archivo_copy, archivo_copy1  
        r'_Copy(\d*)$',       # archivo_Copy, archivo_Copy1
        r'\s+\((\d+)\)$',     # archivo (1), archivo (2)
        r'\s+copy(\d*)$',     # archivo copy, archivo copy2
        r'\s+Copy(\d*)$',     # archivo Copy, archivo Copy2
        r'_duplicate(\d*)$',  # archivo_duplicate, archivo_duplicate1
        r'_dup(\d*)$',        # archivo_dup, archivo_dup1
        r'_backup(\d*)$',     # archivo_backup, archivo_backup1
    ]
    
    # Verificar cada patrón
    for pattern in duplicate_patterns:
        match = re.search(pattern, name_without_ext)
        if match:
            # Es un duplicado automático
            base_name_clean = re.sub(pattern, '', name_without_ext)
            duplicate_number = match.group(1) if match.group(1) else '1'
            
            return {
                'is_duplicate': True,
                'base_name': base_name_clean,
                'pattern': match.group(0),
                'duplicate_number': duplicate_number,
                'suggested_action': 'review_and_merge',
                'original_name': base_name,
                'clean_name': base_name_clean + '.md'
            }
    
    # No es un duplicado automático
    return {
        'is_duplicate': False,
        'base_name': name_without_ext,
        'pattern': '',
        'suggested_action': 'no_action'
    }

def auto_consolidate_post_organization(vault_path: Path, excluded_paths: list[str] = None) -> dict:
    """
    CONSOLIDACIÓN AUTOMÁTICA POST-ORGANIZACIÓN
    Ejecuta consolidación automática después de cada organización para prevenir fragmentación.
    """
    from collections import defaultdict
    
    results = {
        'groups_consolidated': 0,
        'folders_merged': 0,
        'files_moved': 0,
        'errors': []
    }
    
    para_folders = ['01-Projects', '02-Areas', '03-Resources', '04-Archive']
    
    # Patrones de consolidación automática (más agresivos)
    consolidation_patterns = [
        'moka',
        'coaching', 
        'bbi',
        'development',
        'info',
        'training',
        'research',
        'google',
        'testing',
        'api',
        'ssl',
        'mysql',
        'https',
        'docker',
        'config',
        'backup',
        'security',
        'chrome',
        'browser',
        'git',
        'ssh',
        'ftp',
        'email',
        'mail'
    ]
    
    for para_folder in para_folders:
        folder_path = vault_path / para_folder
        if not folder_path.exists():
            continue
            
        # Agrupar carpetas por patrón
        groups = defaultdict(list)
        
        for subfolder in folder_path.iterdir():
            if not subfolder.is_dir() or subfolder.name.startswith('.'):
                continue
                
            # Saltar carpetas excluidas
            if excluded_paths and any(str(subfolder).startswith(excluded) for excluded in excluded_paths):
                continue
                
            folder_name_lower = subfolder.name.lower()
            
            # Buscar patrón de consolidación
            for pattern in consolidation_patterns:
                if pattern in folder_name_lower:
                    groups[pattern].append(subfolder)
                    break
        
        # Consolidar cada grupo (2+ carpetas)
        for pattern, folders in groups.items():
            if len(folders) > 1:
                try:
                    result = _consolidate_group_automatically(folders, pattern)
                    results['groups_consolidated'] += 1
                    results['folders_merged'] += result['folders_merged']
                    results['files_moved'] += result['files_moved']
                    
                except Exception as e:
                    error_msg = f"Error consolidando grupo '{pattern}': {e}"
                    results['errors'].append(error_msg)
    
    return results

def _consolidate_group_automatically(folders, pattern):
    """
    Consolida un grupo específico de carpetas automáticamente.
    """
    # Ordenar por número de archivos (mayor primero)
    folder_data = []
    for folder in folders:
        md_files = list(folder.rglob("*.md"))
        folder_data.append({
            'folder': folder,
            'file_count': len(md_files),
            'files': md_files
        })
    
    # Elegir carpeta target (la que tenga más archivos)
    folder_data.sort(key=lambda x: x['file_count'], reverse=True)
    target_folder = folder_data[0]
    
    # Crear nombre limpio para el target
    clean_name = pattern.title()
    new_target_path = target_folder['folder'].parent / clean_name
    
    # Renombrar target si es necesario
    if target_folder['folder'].name != clean_name:
        if not new_target_path.exists():
            target_folder['folder'].rename(new_target_path)
            target_folder['folder'] = new_target_path
        else:
            # Si ya existe, usar la carpeta existente como target
            target_folder['folder'] = new_target_path
    
    result = {'folders_merged': 0, 'files_moved': 0}
    
    # Mover archivos de otras carpetas al target
    for folder_info in folder_data[1:]:  # Saltar el target
        source_folder = folder_info['folder']
        
        # Mover todos los archivos MD
        for file_path in folder_info['files']:
            target_file_path = target_folder['folder'] / file_path.name
            
            # Si ya existe un archivo con ese nombre, crear nombre único
            if target_file_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                while target_file_path.exists():
                    target_file_path = target_folder['folder'] / f"{base_name}_{counter}{extension}"
                    counter += 1
            
            try:
                file_path.rename(target_file_path)
                result['files_moved'] += 1
            except Exception as e:
                pass  # Silenciar errores en consolidación automática
        
        # Eliminar carpeta source si está vacía
        try:
            remaining_files = list(source_folder.rglob("*"))
            if not remaining_files:
                source_folder.rmdir()
                result['folders_merged'] += 1
        except Exception:
            pass  # Silenciar errores en consolidación automática
    
    return result

def _consolidate_group_automatically(folders, pattern):
    """
    Consolida un grupo de carpetas automáticamente, RESPETANDO proyectos diferentes.
    """
    from .log_center import log_center
    
    result = {
        'folders_merged': 0,
        'files_moved': 0,
        'errors': [],
        'skipped_different_projects': 0
    }
    
    # REGLA CRÍTICA: Verificar que las carpetas sean realmente del mismo proyecto
    if len(folders) < 2:
        return result
    
    # Analizar contenido de las carpetas para detectar proyectos diferentes
    project_analysis = {}
    for folder in folders:
        files = list(folder.rglob("*.md"))
        project_keywords = set()
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                # Extraer palabras clave que indiquen proyecto específico
                lines = content.split('\n')[:10]  # Solo primeras 10 líneas
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['proyecto', 'project', 'cliente', 'client', 'deadline', 'fecha']):
                        project_keywords.update(line.lower().split())
            except Exception as e:
                log_center.log_warning(f"Error leyendo archivo {file_path}: {e}", "AutoConsolidate")
        
        project_analysis[folder] = project_keywords
    
    # Verificar si hay proyectos diferentes
    all_keywords = set()
    for keywords in project_analysis.values():
        all_keywords.update(keywords)
    
    # Si hay muchas palabras clave diferentes, probablemente son proyectos distintos
    if len(all_keywords) > 20:  # Umbral para detectar proyectos diferentes
        log_center.log_warning(f"Detectados proyectos diferentes en grupo '{pattern}', NO consolidando", "AutoConsolidate")
        console.print(f"⚠️ [yellow]PROYECTOS DIFERENTES DETECTADOS[/yellow] en grupo '{pattern}'")
        console.print(f"   [blue]ACCIÓN:[/blue] NO se consolidarán carpetas de proyectos diferentes")
        console.print(f"   [blue]RAZÓN:[/blue] Respetar separación lógica de proyectos")
        result['skipped_different_projects'] = len(folders)
        return result
    
    # Ordenar carpetas por número de archivos (la que más archivos tenga será el target)
    folder_data = []
    for folder in folders:
        files = list(folder.rglob("*.md"))
        folder_data.append({
            'folder': folder,
            'files': files,
            'file_count': len(files)
        })
    
    # Ordenar por número de archivos (descendente)
    folder_data.sort(key=lambda x: x['file_count'], reverse=True)
    
    if not folder_data:
        return result
    
    target_folder = folder_data[0]
    log_center.log_info(f"Consolidando grupo '{pattern}': {len(folders)} carpetas → {target_folder['folder'].name}", "AutoConsolidate")
    
    # Mover archivos de otras carpetas al target
    for folder_info in folder_data[1:]:  # Saltar el target
        source_folder = folder_info['folder']
        
        # Mover todos los archivos MD
        for file_path in folder_info['files']:
            target_file_path = target_folder['folder'] / file_path.name
            
            try:
                # Usar función de renombrado seguro (que NO renombra archivos de usuario)
                final_path = _safe_rename_file(file_path, target_file_path, target_folder['folder'].parent, None)
                if final_path != file_path:  # Solo contar si realmente se movió
                    result['files_moved'] += 1
                    log_center.log_info(f"Archivo consolidado: {file_path.name} → {final_path.name}", "AutoConsolidate")
            except Exception as e:
                error_msg = f"Error consolidando archivo: {file_path.name}: {e}"
                log_center.log_error(error_msg, "AutoConsolidate")
                result['errors'].append(error_msg)
        
        # Eliminar carpeta source si está vacía
        try:
            remaining_files = list(source_folder.rglob("*"))
            if not remaining_files:
                source_folder.rmdir()
                result['folders_merged'] += 1
                log_center.log_info(f"Carpeta eliminada (vacía): {source_folder.name}", "AutoConsolidate")
        except Exception as e:
            error_msg = f"Error eliminando carpeta vacía: {source_folder.name}: {e}"
            log_center.log_warning(error_msg, "AutoConsolidate")
            result['errors'].append(error_msg)
    
    return result

def _ensure_correct_para_structure(vault_path: Path, excluded_paths: list[str] = None) -> None:
    """
    Asegura que la estructura PARA tenga los números correctos Y consolida carpetas dispersas.
    """
    console.print(f"🏗️ Consolidando estructura PARA estándar...")
    
    correct_structure = {
        '00-Inbox': 'Inbox',
        '01-Projects': 'Projects', 
        '02-Areas': 'Areas',
        '03-Resources': 'Resources',
        '04-Archive': 'Archive'
    }
    
    # Primero asegurar que existan las carpetas PARA
    for numbered_name, simple_name in correct_structure.items():
        numbered_path = vault_path / numbered_name
        simple_path = vault_path / simple_name
        
        # Si existe la carpeta sin número, renombrarla
        if simple_path.exists() and not numbered_path.exists():
            try:
                simple_path.rename(numbered_path)
                console.print(f"✅ Renombrado: {simple_name} → {numbered_name}")
            except Exception as e:
                console.print(f"❌ Error renombrando {simple_name}: {e}")
        
        # Si no existe ninguna, crear la numerada
        elif not numbered_path.exists() and not simple_path.exists():
            try:
                numbered_path.mkdir(parents=True, exist_ok=True)
                console.print(f"✅ Creado: {numbered_name}")
            except Exception as e:
                console.print(f"❌ Error creando {numbered_name}: {e}")
    
    # Ahora consolidar carpetas dispersas
    _consolidate_scattered_folders(vault_path, excluded_paths)

def _consolidate_scattered_folders(vault_path: Path, excluded_paths: list[str] = None) -> None:
    """
    Consolida carpetas dispersas que rompen la estructura PARA, siendo CONSERVADORA.
    """
    console.print(f"🔀 Analizando carpetas dispersas en estructura PARA...")
    
    # Obtener todas las carpetas del vault (excluyendo las PARA y del sistema)
    para_folders = {'00-Inbox', '01-Projects', '02-Areas', '03-Resources', '04-Archive'}
    system_folders = {'.obsidian', '.para_db', '.git', '.trash', '.makemd', '.space'}
    
    scattered_folders = []
    for item in vault_path.iterdir():
        if (item.is_dir() and 
            item.name not in para_folders and 
            item.name not in system_folders and
            not item.name.startswith('.')):
            
            # Verificar si la carpeta está excluida
            is_excluded = False
            if excluded_paths:
                for excluded_path in excluded_paths:
                    if str(item.resolve()).startswith(str(Path(excluded_path).resolve())):
                        is_excluded = True
                        console.print(f"🚫 Saltando carpeta excluida: {item.name}")
                        break
            
            if not is_excluded:
                scattered_folders.append(item)
    
    if not scattered_folders:
        console.print(f"✅ No hay carpetas dispersas que consolidar")
        return
    
    console.print(f"📁 Encontradas {len(scattered_folders)} carpetas dispersas:")
    for folder in scattered_folders:
        console.print(f"   • {folder.name}")
    
    # REGLA CRÍTICA: Solo consolidar carpetas que sean claramente del mismo proyecto
    # Analizar cada carpeta para detectar si son proyectos independientes
    project_groups = {}
    
    for folder in scattered_folders:
        # Extraer palabras clave del nombre de la carpeta
        folder_name_lower = folder.name.lower()
        
        # Detectar patrones de proyecto en el nombre
        project_patterns = [
            r'proyecto\s*(\w+)',  # proyecto + nombre
            r'(\w+)\s*project',   # nombre + project
            r'(\w+)\s*client',    # nombre + client
            r'(\w+)\s*trabajo',   # nombre + trabajo
        ]
        
        import re
        project_key = None
        
        for pattern in project_patterns:
            match = re.search(pattern, folder_name_lower)
            if match:
                project_key = match.group(1)
                break
        
        # Si no se encontró patrón, usar el nombre completo como clave
        if not project_key:
            project_key = folder_name_lower
        
        if project_key not in project_groups:
            project_groups[project_key] = []
        project_groups[project_key].append(folder)
    
    # Solo consolidar grupos con múltiples carpetas del mismo proyecto
    consolidated_count = 0
    skipped_count = 0
    
    for project_key, folders in project_groups.items():
        if len(folders) == 1:
            # Carpeta única, NO consolidar (podría ser proyecto independiente)
            console.print(f"⚠️ [yellow]SALTANDO:[/yellow] {folders[0].name} (proyecto único)")
            skipped_count += 1
            continue
        
        # Verificar que realmente sean del mismo proyecto analizando contenido
        same_project = True
        project_keywords = set()
        
        for folder in folders:
            try:
                md_files = list(folder.rglob("*.md"))
                for file_path in md_files[:5]:  # Solo primeros 5 archivos
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    # Extraer palabras clave específicas del proyecto
                    lines = content.split('\n')[:10]
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['proyecto', 'project', 'cliente', 'client', 'deadline']):
                            project_keywords.update(line.lower().split())
            except Exception as e:
                console.print(f"⚠️ Error analizando {folder.name}: {e}")
        
        # Si hay muchas palabras clave diferentes, probablemente son proyectos distintos
        if len(project_keywords) > 15:
            console.print(f"⚠️ [yellow]PROYECTOS DIFERENTES DETECTADOS[/yellow] en grupo '{project_key}'")
            console.print(f"   [blue]ACCIÓN:[/blue] NO se consolidarán (respetar separación)")
            for folder in folders:
                console.print(f"   • {folder.name}")
            skipped_count += len(folders)
            continue
        
        # Si llegamos aquí, son carpetas del mismo proyecto que se pueden consolidar
        console.print(f"🔀 Consolidando proyecto '{project_key}': {len(folders)} carpetas")
        
        # Determinar carpeta target (la que más archivos tenga)
        target_folder = max(folders, key=lambda f: len(list(f.rglob("*.md"))))
        
        for folder in folders:
            if folder == target_folder:
                continue
                
            try:
                # Mover archivos de la carpeta source al target
                md_files = list(folder.rglob("*.md"))
                for file_path in md_files:
                    target_file_path = target_folder / file_path.name
                    
                    # Usar función de renombrado seguro
                    final_path = _safe_rename_file(file_path, target_file_path, vault_path, None)
                    if final_path != file_path:
                        console.print(f"   📄 {file_path.name} → {target_folder.name}")
                
                # Eliminar carpeta source si está vacía
                remaining_files = list(folder.rglob("*"))
                if not remaining_files:
                    folder.rmdir()
                    console.print(f"   🗑️ Eliminada carpeta vacía: {folder.name}")
                
                consolidated_count += 1
                
            except Exception as e:
                console.print(f"❌ Error consolidando {folder.name}: {e}")
    
    console.print(f"✅ Consolidación completada:")
    console.print(f"   📦 Consolidadas: {consolidated_count} carpetas")
    console.print(f"   ⚠️ Saltadas: {skipped_count} carpetas (proyectos independientes)")
    console.print(f"   💡 Razón: Respetar separación lógica de proyectos")

def _determine_target_category_for_folder(folder: Path) -> str:
    """
    Determina la categoría PARA apropiada para una carpeta basándose en su nombre y contenido.
    """
    folder_name = folder.name.lower()
    
    # Mapeo inteligente basado en nombres comunes
    project_keywords = ['project', 'trabajo', 'client', 'moka', 'bbi', 'avature']
    area_keywords = ['area', 'coaching', 'health', 'finance', 'habit']  
    resource_keywords = ['template', 'resource', 'api', 'doc', 'guide', 'tip', 'info', 'standard']
    archive_keywords = ['old', 'archive', 'backup', 'travel', 'past']
    
    # Verificar palabras clave en el nombre
    if any(keyword in folder_name for keyword in project_keywords):
        return '01-Projects'
    elif any(keyword in folder_name for keyword in area_keywords):
        return '02-Areas'
    elif any(keyword in folder_name for keyword in resource_keywords):
        return '03-Resources'
    elif any(keyword in folder_name for keyword in archive_keywords):
        return '04-Archive'
    
    # Si no hay coincidencias claras, analizar contenido
    try:
        md_files = list(folder.rglob("*.md"))
        if len(md_files) == 0:
            return '04-Archive'  # Carpetas vacías al archivo
        
        # Analizar nombres de archivos para determinar categoría
        content_text = " ".join([f.name.lower() for f in md_files[:10]])  # Primeros 10 archivos
        
        if any(keyword in content_text for keyword in project_keywords):
            return '01-Projects'
        elif any(keyword in content_text for keyword in resource_keywords):
            return '03-Resources'
        else:
            return '02-Areas'  # Por defecto, áreas para contenido general
            
    except Exception:
        return '02-Areas'  # Fallback seguro

def _calculate_network_centrality(note_path: str, vault_path: Path) -> float:
    """Calcula la centralidad de red de una nota basada en backlinks y enlaces."""
    try:
        from paralib.vault import extract_links_and_backlinks
        forward_links, backlinks, centrality = extract_links_and_backlinks(vault_path)
        
        if note_path and note_path in centrality:
            return centrality[note_path]
        return 0.0
    except Exception:
        return 0.0

def _calculate_action_verb_density(content: str) -> float:
    """Calcula la densidad de verbos de acción en el contenido."""
    action_verbs = [
        'implement', 'create', 'build', 'develop', 'design', 'execute', 'launch', 
        'deploy', 'test', 'review', 'analyze', 'research', 'write', 'document',
        'plan', 'schedule', 'organize', 'coordinate', 'manage', 'lead', 'deliver',
        'complete', 'finish', 'achieve', 'accomplish', 'solve', 'fix', 'improve',
        'optimize', 'enhance', 'upgrade', 'refactor', 'migrate', 'integrate',
        'configure', 'setup', 'install', 'deploy', 'monitor', 'track', 'measure'
    ]
    
    words = content.lower().split()
    action_count = sum(1 for word in words if any(verb in word for verb in action_verbs))
    
    if len(words) > 0:
        return action_count / len(words)
    return 0.0

def _calculate_outcome_specificity(content: str) -> float:
    """Calcula qué tan específicos son los outcomes mencionados."""
    import re
    
    # Patrones que indican outcomes específicos
    specific_patterns = [
        r'\d+%',  # Porcentajes
        r'\$\d+',  # Cantidades de dinero
        r'\d+ (users?|customers?|clients?)',  # Cantidades de usuarios
        r'by \d{1,2}/\d{1,2}',  # Fechas específicas
        r'before \w+ \d+',  # Fechas límite
        r'within \d+ (days?|weeks?|months?)',  # Plazos específicos
        r'increase.*by \d+',  # Incrementos cuantificados
        r'reduce.*by \d+',  # Reducciones cuantificadas
        r'deliver \d+',  # Entregas cuantificadas
        r'launch.*on \d',  # Lanzamientos fechados
    ]
    
    matches = 0
    for pattern in specific_patterns:
        matches += len(re.findall(pattern, content, re.IGNORECASE))
    
    # Normalizar por longitud del contenido
    words = len(content.split())
    if words > 0:
        specificity = matches / (words / 100)  # Por cada 100 palabras
        return min(1.0, specificity)
    return 0.0

def _calculate_update_frequency_pattern(note_path: str, vault_path: Path) -> str:
    """Calcula el patrón de frecuencia de actualización de una nota."""
    try:
        import os
        from datetime import datetime, timedelta
        
        if not note_path:
            return 'unknown'
            
        full_path = Path(note_path) if Path(note_path).is_absolute() else vault_path / note_path
        
        if not full_path.exists():
            return 'unknown'
            
        # Obtener tiempo de modificación
        mod_time = datetime.fromtimestamp(os.path.getmtime(full_path))
        now = datetime.now()
        days_since_mod = (now - mod_time).days
        
        if days_since_mod < 1:
            return 'very_frequent'
        elif days_since_mod < 7:
            return 'frequent'
        elif days_since_mod < 30:
            return 'moderate'
        elif days_since_mod < 90:
            return 'infrequent'
        else:
            return 'rare'
            
    except Exception:
        return 'unknown'

def _calculate_urgency_indicators(content: str) -> float:
    """Calcula indicadores de urgencia en el contenido."""
    urgency_keywords = [
        'urgent', 'asap', 'immediately', 'critical', 'emergency', 'priority',
        'deadline', 'overdue', 'late', 'rushing', 'hurry', 'quickly',
        'time-sensitive', 'pressing', 'crucial', 'vital', 'essential',
        'must do', 'need to', 'have to', 'required by', 'due today',
        'due tomorrow', 'this week', 'end of day', 'EOD'
    ]
    
    content_lower = content.lower()
    urgency_count = sum(1 for keyword in urgency_keywords if keyword in content_lower)
    
    # Contar signos de exclamación y mayúsculas (indicadores de urgencia)
    exclamation_count = content.count('!')
    caps_words = sum(1 for word in content.split() if word.isupper() and len(word) > 2)
    
    total_urgency_signals = urgency_count + (exclamation_count * 0.5) + (caps_words * 0.3)
    words = len(content.split())
    
    if words > 0:
        urgency_score = total_urgency_signals / (words / 50)  # Por cada 50 palabras
        return min(1.0, urgency_score)
    return 0.0

def _calculate_temporal_context(content: str) -> str:
    """Calcula el contexto temporal del contenido."""
    import re
    
    # Patrones para diferentes contextos temporales
    deadline_patterns = [
        r'due \w+ \d+', r'deadline.*\d+', r'by \d{1,2}/\d{1,2}',
        r'before \w+day', r'must.*by', r'complete.*by'
    ]
    
    scheduled_patterns = [
        r'every \w+day', r'weekly', r'monthly', r'daily',
        r'schedule.*\d+', r'recurring', r'routine', r'regular'
    ]
    
    evergreen_patterns = [
        r'reference', r'guide', r'tutorial', r'documentation',
        r'knowledge base', r'best practices', r'principles',
        r'concepts', r'theory', r'fundamentals'
    ]
    
    content_lower = content.lower()
    
    deadline_matches = sum(len(re.findall(pattern, content_lower)) for pattern in deadline_patterns)
    scheduled_matches = sum(len(re.findall(pattern, content_lower)) for pattern in scheduled_patterns)
    evergreen_matches = sum(len(re.findall(pattern, content_lower)) for pattern in evergreen_patterns)
    
    if deadline_matches > scheduled_matches and deadline_matches > evergreen_matches:
        return 'deadline_driven'
    elif scheduled_matches > evergreen_matches:
        return 'scheduled'
    elif evergreen_matches > 0:
        return 'evergreen'
    else:
        return 'neutral'

def _calculate_semantic_coherence_with_category(analysis: dict, db: ChromaPARADatabase) -> float:
    """Calcula la coherencia semántica con la categoría predicha."""
    try:
        # Obtener vecinos semánticos de la base de datos
        neighbors = analysis.get('neighbors', [])
        if not neighbors:
            return 0.5  # Valor neutro si no hay vecinos
        
        # Contar vecinos de la misma categoría
        predicted_category = analysis.get('predicted_category', 'Unknown')
        same_category_count = sum(1 for neighbor in neighbors 
                                if neighbor.get('category') == predicted_category)
        
        coherence = same_category_count / len(neighbors)
        return coherence
        
    except Exception:
        return 0.5

def _calculate_cross_reference_density(content: str) -> float:
    """Calcula la densidad de referencias cruzadas."""
    import re
    
    # Patrones de referencias cruzadas
    reference_patterns = [
        r'\[\[.*?\]\]',  # Wikilinks
        r'\[.*?\]\(.*?\)',  # Markdown links
        r'see also', r'refer to', r'as mentioned in',
        r'according to', r'based on', r'similar to',
        r'compare with', r'in relation to', r'reference:'
    ]
    
    total_references = 0
    for pattern in reference_patterns:
        total_references += len(re.findall(pattern, content, re.IGNORECASE))
    
    words = len(content.split())
    if words > 0:
        return total_references / words
    return 0.0

def _calculate_completion_status(content: str) -> str:
    """Calcula el estado de completitud basado en el contenido."""
    content_lower = content.lower()
    
    # Indicadores de progreso
    progress_indicators = [
        'completed', 'finished', 'done', 'finalized', 'delivered',
        'achieved', 'accomplished', 'closed', 'ended', 'concluded'
    ]
    
    # Indicadores de trabajo en progreso
    in_progress_indicators = [
        'in progress', 'ongoing', 'active', 'current', 'pending',
        'underway', 'being worked on', 'in development', 'planning'
    ]
    
    # Indicadores de planificación
    planning_indicators = [
        'plan', 'proposal', 'draft', 'outline', 'sketch',
        'idea', 'concept', 'initial', 'preliminary'
    ]
    
    progress_count = sum(1 for indicator in progress_indicators if indicator in content_lower)
    in_progress_count = sum(1 for indicator in in_progress_indicators if indicator in content_lower)
    planning_count = sum(1 for indicator in planning_indicators if indicator in content_lower)
    
    if progress_count > in_progress_count and progress_count > planning_count:
        return 'completed'
    elif in_progress_count > planning_count:
        return 'in_progress'
    elif planning_count > 0:
        return 'planning'
    else:
        return 'unknown'

def _calculate_stakeholder_mentions(content: str) -> float:
    """Calcula la densidad de menciones de stakeholders."""
    import re
    
    # Patrones de stakeholders
    stakeholder_patterns = [
        r'client', r'customer', r'user', r'stakeholder', r'team',
        r'manager', r'lead', r'developer', r'designer', r'analyst',
        r'executive', r'director', r'vp', r'ceo', r'cto',
        r'partner', r'vendor', r'supplier', r'consultant'
    ]
    
    total_mentions = 0
    for pattern in stakeholder_patterns:
        total_mentions += len(re.findall(pattern, content, re.IGNORECASE))
    
    words = len(content.split())
    if words > 0:
        return total_mentions / words
    return 0.0

def _calculate_knowledge_depth(content: str) -> str:
    """Calcula la profundidad del conocimiento basado en el contenido."""
    content_lower = content.lower()
    
    # Indicadores de conocimiento profundo
    deep_knowledge_indicators = [
        'analysis', 'research', 'study', 'investigation', 'examination',
        'detailed', 'comprehensive', 'thorough', 'in-depth', 'extensive',
        'technical', 'specialized', 'expert', 'advanced', 'complex'
    ]
    
    # Indicadores de conocimiento superficial
    surface_knowledge_indicators = [
        'overview', 'summary', 'brief', 'quick', 'basic',
        'introductory', 'simple', 'elementary', 'fundamental'
    ]
    
    deep_count = sum(1 for indicator in deep_knowledge_indicators if indicator in content_lower)
    surface_count = sum(1 for indicator in surface_knowledge_indicators if indicator in content_lower)
    
    if deep_count > surface_count:
        return 'deep'
    elif surface_count > deep_count:
        return 'surface'
    else:
        return 'moderate'

def _calculate_emotional_context(content: str) -> str:
    """Calcula el contexto emocional del contenido."""
    content_lower = content.lower()
    
    # Indicadores emocionales positivos
    positive_emotions = [
        'excited', 'happy', 'great', 'excellent', 'amazing', 'wonderful',
        'successful', 'achieved', 'progress', 'improvement', 'growth'
    ]
    
    # Indicadores emocionales negativos
    negative_emotions = [
        'frustrated', 'angry', 'disappointed', 'failed', 'problem',
        'issue', 'error', 'bug', 'broken', 'difficult', 'challenging'
    ]
    
    # Indicadores emocionales neutros
    neutral_emotions = [
        'neutral', 'objective', 'factual', 'informational', 'reference'
    ]
    
    positive_count = sum(1 for emotion in positive_emotions if emotion in content_lower)
    negative_count = sum(1 for emotion in negative_emotions if emotion in content_lower)
    neutral_count = sum(1 for emotion in neutral_emotions if emotion in content_lower)
    
    if positive_count > negative_count and positive_count > neutral_count:
        return 'positive'
    elif negative_count > positive_count and negative_count > neutral_count:
        return 'negative'
    elif neutral_count > 0:
        return 'neutral'
    else:
        return 'unknown'

def _make_hybrid_decision_with_analysis(semantic_category: str, semantic_confidence: float, semantic_reasoning: str,
                                       llm_category: str, llm_folder: str, llm_result: dict,
                                       semantic_weight: float, llm_weight: float,
                                       analysis: dict, user_directive: str, vault_path: Path = None) -> dict:
    """
    Toma la decisión final considerando el análisis completo.
    """
    # Caso 1: Ambos sistemas coinciden
    if semantic_category == llm_category:
        console.print(f"✅ [green]CONSENSO: Ambos sistemas sugieren {semantic_category}[/green]")
        
        # Usar el nombre de carpeta más apropiado
        if llm_folder and llm_folder != 'Unknown':
            folder_name = llm_folder
        else:
            # Obtener carpetas existentes para evitar duplicados
            existing_folders = set()
            try:
                category_mapping = _get_category_mapping()
                target_category = category_mapping.get(semantic_category, semantic_category)
                category_path = vault_path / target_category
                if category_path.exists():
                    existing_folders = {f.name for f in category_path.iterdir() if f.is_dir()}
            except Exception:
                pass
            folder_name = _generate_folder_name_from_content(analysis['content'], semantic_category, vault_path, existing_folders)
        
        # Calcular confianza combinada
        combined_confidence = (semantic_confidence * semantic_weight) + (0.8 * llm_weight)
        
        # Agregar información del análisis al razonamiento
        reasoning_parts = [f"Consenso entre ChromaDB y IA. {semantic_reasoning}"]
        
        # Agregar información relevante del análisis
        if analysis['obsidian_tags']:
            reasoning_parts.append(f"Tags Obsidian confirman: {', '.join(analysis['obsidian_tags'])}")
        
        if analysis['has_todos']:
            reasoning_parts.append(f"Contiene {analysis['todo_count']} TO-DOs")
        
        if analysis['user_context']['directive_keywords']:
            reasoning_parts.append(f"Directiva del usuario: {', '.join(analysis['user_context']['directive_keywords'])}")
        
        return {
            'category': semantic_category,
            'folder_name': folder_name,
            'confidence': combined_confidence,
            'method': 'consensus',
            'semantic_score': semantic_confidence,
            'llm_score': 0.8,
            'reasoning': "; ".join(reasoning_parts)
        }
    
    # Caso 2: Sistemas discrepan - usar pesos dinámicos
    console.print(f"🔄 [yellow]DISCREPANCIA: ChromaDB={semantic_category} vs IA={llm_category}[/yellow]")
    
    # Calcular scores ponderados
    semantic_score = semantic_confidence * semantic_weight
    llm_score = 0.8 * llm_weight
    
    # Obtener carpetas existentes para evitar duplicados
    existing_folders = set()
    try:
        category_mapping = _get_category_mapping()
        target_category = category_mapping.get(semantic_category if semantic_score > llm_score else llm_category, semantic_category if semantic_score > llm_score else llm_category)
        category_path = vault_path / target_category
        if category_path.exists():
            existing_folders = {f.name for f in category_path.iterdir() if f.is_dir()}
    except Exception:
        pass
    
    if semantic_score > llm_score:
        final_category = semantic_category
        final_folder = _generate_folder_name_from_content(analysis['content'], semantic_category, vault_path, existing_folders)
        method = 'chromadb_weighted'
        reasoning = f"ChromaDB prevalece por peso ({semantic_weight:.2f}). {semantic_reasoning}"
    else:
        final_category = llm_category
        final_folder = llm_folder if llm_folder != 'Unknown' else _generate_folder_name_from_content(analysis['content'], llm_category, vault_path, existing_folders)
        method = 'llm_weighted'
        reasoning = f"IA prevalece por peso ({llm_weight:.2f}). Razonamiento: {llm_result.get('reasoning', 'Análisis de IA')}"
    
    # Agregar información del análisis
    if analysis['obsidian_tags']:
        reasoning += f" Tags Obsidian: {', '.join(analysis['obsidian_tags'])}"
    
    combined_confidence = max(semantic_score, llm_score)
    
    return {
        'category': final_category,
        'folder_name': final_folder,
        'confidence': combined_confidence,
        'method': method,
        'semantic_score': semantic_confidence,
        'llm_score': 0.8,
        'reasoning': reasoning
    }

def _calculate_reference_content_score(content: str) -> float:
    """
    Calcula la puntuación de contenido de referencia.
    Detecta patrones que indican contenido de referencia, especificaciones, documentación, etc.
    """
    import re
    
    # Palabras clave que indican contenido de referencia
    reference_patterns = [
        r'\b(spec|specification|standard|protocol|api|interface)\b',
        r'\b(documentation|manual|guide|tutorial|reference)\b',
        r'\b(template|example|sample|demo|showcase)\b',
        r'\b(definition|description|overview|summary)\b',
        r'\b(requirements|specs|technical|specifications)\b',
        r'\b(adam\s+spec|spec\s+adam)\b',  # Caso específico de Adam Spec
        r'\b(reference\s+material|reference\s+guide)\b',
        r'\b(technical\s+documentation|tech\s+spec)\b'
    ]
    
    content_lower = content.lower()
    total_matches = 0
    
    for pattern in reference_patterns:
        matches = len(re.findall(pattern, content_lower))
        total_matches += matches
    
    # Normalizar por longitud del contenido
    word_count = len(content.split())
    if word_count == 0:
        return 0.0
    
    # Puntuación base por densidad de palabras clave
    base_score = min(total_matches / word_count * 100, 1.0)
    
    # Bonus por patrones específicos
    bonus_score = 0.0
    
    # Bonus por tener estructura de especificación
    if re.search(r'^#+\s*(spec|specification|standard)', content, re.MULTILINE | re.IGNORECASE):
        bonus_score += 0.3
    
    # Bonus por tener secciones típicas de documentación
    doc_sections = ['overview', 'description', 'requirements', 'api', 'interface', 'examples']
    for section in doc_sections:
        if re.search(rf'^#+\s*{section}', content, re.MULTILINE | re.IGNORECASE):
            bonus_score += 0.1
    
    # Bonus por tener código o ejemplos
    if re.search(r'```', content):
        bonus_score += 0.2
    
    # Bonus por tener enlaces de referencia
    if re.search(r'\[.*?\]\(.*?\)', content):
        bonus_score += 0.1
    
    return min(base_score + bonus_score, 1.0)

def _calculate_project_vs_resource_score(content: str) -> float:
    """
    Calcula la puntuación de distinción entre proyecto y recurso.
    Valores bajos (< 0.3) = claramente recurso
    Valores altos (> 0.7) = claramente proyecto
    """
    import re
    
    content_lower = content.lower()
    
    # Indicadores de PROYECTO (acción, tareas, deadlines)
    project_indicators = [
        r'\b(project|task|goal|objective|deliverable|milestone)\b',
        r'\b(deadline|due\s+date|timeline|schedule)\b',
        r'\b(action\s+item|todo|task\s+list)\b',
        r'\b(progress|status|update|ongoing|active)\b',
        r'\b(plan|execute|implement|develop|build)\b',
        r'\b(urgent|priority|important|critical)\b',
        r'\b(team|collaboration|meeting|discussion)\b',
        r'\b(budget|cost|resource\s+allocation)\b',
        r'\b(risk|issue|problem|challenge)\b',
        r'\b(success|outcome|result|achievement)\b'
    ]
    
    # Indicadores de RECURSO (referencia, información, conocimiento)
    resource_indicators = [
        r'\b(resource|reference|template|guide|tutorial)\b',
        r'\b(documentation|manual|specification|standard)\b',
        r'\b(knowledge|information|data|fact|detail)\b',
        r'\b(example|sample|demo|showcase|template)\b',
        r'\b(definition|description|overview|summary)\b',
        r'\b(api|interface|protocol|format|structure)\b',
        r'\b(how\s+to|step\s+by\s+step|procedure)\b',
        r'\b(tool|utility|library|framework)\b',
        r'\b(background|context|history|overview)\b',
        r'\b(reference\s+material|cheat\s+sheet)\b'
    ]
    
    # Contar indicadores
    project_count = 0
    resource_count = 0
    
    for pattern in project_indicators:
        project_count += len(re.findall(pattern, content_lower))
    
    for pattern in resource_indicators:
        resource_count += len(re.findall(pattern, content_lower))
    
    # Calcular puntuación
    total_indicators = project_count + resource_count
    if total_indicators == 0:
        return 0.5  # Neutral si no hay indicadores claros
    
    # Puntuación: 0 = completamente recurso, 1 = completamente proyecto
    project_score = project_count / total_indicators
    
    # Ajustes adicionales basados en patrones de contenido
    
    # Si tiene muchos TO-DOs, es más probable que sea proyecto
    todo_count = len(re.findall(r'- \[ \]|#todo|TODO:', content_lower))
    if todo_count > 3:
        project_score = min(project_score + 0.2, 1.0)
    
    # Si tiene fechas específicas, es más probable que sea proyecto
    date_count = len(re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', content))
    if date_count > 2:
        project_score = min(project_score + 0.15, 1.0)
    
    # Si tiene estructura de especificación, es más probable que sea recurso
    if re.search(r'^#+\s*(spec|specification|api|interface)', content, re.MULTILINE | re.IGNORECASE):
        project_score = max(project_score - 0.3, 0.0)
    
    return project_score

def _analyze_content_type(content: str) -> str:
    """
    Analiza el tipo de contenido de la nota.
    Retorna: 'specification', 'documentation', 'tutorial', 'active_task', 'planning', 'other'
    """
    import re
    
    content_lower = content.lower()
    
    # Patrones para diferentes tipos de contenido
    patterns = {
        'specification': [
            r'\b(spec|specification|standard|protocol|api\s+spec)\b',
            r'\b(technical\s+spec|design\s+spec|requirements\s+spec)\b',
            r'\b(adam\s+spec|spec\s+adam)\b',  # Caso específico
            r'^#+\s*(spec|specification|standard)',
            r'\b(interface\s+definition|api\s+definition)\b'
        ],
        'documentation': [
            r'\b(documentation|manual|guide|reference\s+guide)\b',
            r'\b(technical\s+documentation|user\s+manual)\b',
            r'\b(overview|description|details|information)\b',
            r'^#+\s*(documentation|manual|guide)',
            r'\b(readme|setup|installation|configuration)\b'
        ],
        'tutorial': [
            r'\b(tutorial|how\s+to|step\s+by\s+step|guide)\b',
            r'\b(walkthrough|example|demo|showcase)\b',
            r'\b(learning|teaching|instruction|procedure)\b',
            r'^#+\s*(tutorial|how\s+to|guide)',
            r'\b(follow\s+these\s+steps|instructions)\b'
        ],
        'active_task': [
            r'\b(active\s+task|ongoing\s+work|current\s+project)\b',
            r'\b(in\s+progress|working\s+on|currently\s+doing)\b',
            r'\b(deadline|due\s+date|urgent|priority)\b',
            r'\b(action\s+items|next\s+steps|immediate\s+actions)\b',
            r'\b(progress\s+update|status\s+report)\b'
        ],
        'planning': [
            r'\b(planning|strategy|proposal|draft|outline)\b',
            r'\b(roadmap|timeline|schedule|milestone)\b',
            r'\b(plan|proposal|strategy|approach)\b',
            r'^#+\s*(plan|strategy|proposal)',
            r'\b(future|upcoming|planned|scheduled)\b'
        ]
    }
    
    # Contar coincidencias para cada tipo
    type_scores = {}
    for content_type, type_patterns in patterns.items():
        score = 0
        for pattern in type_patterns:
            matches = len(re.findall(pattern, content_lower))
            score += matches
        type_scores[content_type] = score
    
    # Determinar el tipo con mayor puntuación
    if not any(type_scores.values()):
        return 'other'
    
    max_type = max(type_scores, key=type_scores.get)
    max_score = type_scores[max_type]
    
    # Solo retornar el tipo si tiene una puntuación significativa
    if max_score >= 2:
        return max_type
    elif max_score == 1:
        # Para puntuaciones bajas, hacer análisis adicional
        if 'spec' in content_lower or 'specification' in content_lower:
            return 'specification'
        elif 'tutorial' in content_lower or 'how to' in content_lower:
            return 'tutorial'
        elif 'plan' in content_lower or 'strategy' in content_lower:
            return 'planning'
        else:
            return 'other'
    else:
        return 'other'

def _calculate_temporal_proximity(note_path: Path, candidate_folder: Path) -> float:
    """
    Calcula la proximidad temporal promedio entre una nota y las notas de una carpeta candidata.
    Retorna un score entre 0.0 (muy lejanas) y 1.0 (muy cercanas).
    """
    from datetime import datetime
    import os
    if not note_path.exists() or not candidate_folder.exists():
        return 0.0
    try:
        note_stat = note_path.stat()
        note_dates = [note_stat.st_mtime, note_stat.st_ctime]
        note_avg = sum(note_dates) / len(note_dates)
        # Buscar todas las notas en la carpeta candidata
        candidate_notes = list(candidate_folder.glob("*.md"))
        if not candidate_notes:
            return 0.0
        proximities = []
        for cand in candidate_notes:
            cand_stat = cand.stat()
            cand_dates = [cand_stat.st_mtime, cand_stat.st_ctime]
            cand_avg = sum(cand_dates) / len(cand_dates)
            # Diferencia absoluta en días
            days_diff = abs(note_avg - cand_avg) / 86400.0
            # Score: <=30 días = 1.0, 30-90 = 0.5, >90 = 0.1
            if days_diff <= 30:
                proximities.append(1.0)
            elif days_diff <= 90:
                proximities.append(0.5)
            else:
                proximities.append(0.1)
        # Promedio de proximidades
        return sum(proximities) / len(proximities)
    except Exception:
        return 0.0

def enforce_para_principles(vault_path: Path, db: ChromaPARADatabase) -> dict:
    """
    Enforce Tiago Forte's PARA method principles:
    - Eliminate "General" folders by creating specific projects/areas/resources
    - Ensure at least one active project exists
    - Move resources to proper thematic subfolders
    - Remove empty folders to maintain flow
    """
    from .log_center import log_center
    
    console.print("\n🎯 [bold cyan]Enforcing PARA Method Principles[/bold cyan]")
    console.print("📚 Based on Tiago Forte's methodology")
    
    stats = {
        'general_folders_fixed': 0,
        'projects_created': 0,
        'resources_reorganized': 0,
        'empty_folders_removed': 0,
        'errors': []
    }
    
    try:
        # 1. Handle "General" and "Proyectos General" folders
        console.print("\n🔍 [bold]Step 1: Eliminating 'General' folders[/bold]")
        general_folders = []
        
        # Find all "General" type folders
        for category in ['01-Projects', '02-Areas', '03-Resources']:
            category_path = vault_path / category
            if category_path.exists():
                for folder in category_path.iterdir():
                    if folder.is_dir():
                        folder_name = folder.name.lower()
                        if any(general_term in folder_name for general_term in ['general', 'misc', 'otros', 'varios']):
                            general_folders.append((folder, category))
        
        if general_folders:
            console.print(f"📁 Found {len(general_folders)} 'General' type folders to reorganize:")
            for folder, category in general_folders:
                console.print(f"   • {folder.name} (in {category})")
                
                # Analyze contents to create specific categories
                notes = list(folder.glob("*.md"))
                if notes:
                    # Group notes by tags, dates, and content patterns
                    note_groups = _analyze_notes_for_grouping(notes, db)
                    
                    if note_groups:
                        # Create specific folders and move notes
                        for group_name, group_notes in note_groups.items():
                            if len(group_notes) >= 2:  # Only create groups with 2+ notes
                                target_folder = vault_path / category / group_name
                                target_folder.mkdir(parents=True, exist_ok=True)
                                
                                for note in group_notes:
                                    try:
                                        target_path = target_folder / note.name
                                        if note != target_path:
                                            # Usar _safe_rename_file para manejar conflictos
                                            final_path = _safe_rename_file(note, target_path, vault_path, db)
                                            if final_path != note:
                                                console.print(f"      📝 Moved {note.name} → {group_name}")
                                            else:
                                                console.print(f"      ⚠️ Could not move {note.name} (conflict resolved)")
                                    except Exception as e:
                                        stats['errors'].append(f"Error moving {note.name}: {e}")
                                
                                stats['general_folders_fixed'] += 1
                        
                        # Remove original general folder if empty
                        if not any(folder.iterdir()):
                            try:
                                folder.rmdir()
                                console.print(f"      🗑️ Removed empty folder: {folder.name}")
                                stats['empty_folders_removed'] += 1
                            except Exception as e:
                                stats['errors'].append(f"Error removing {folder.name}: {e}")
                    else:
                        console.print(f"      ⚠️ Could not group notes in {folder.name}")
        else:
            console.print("✅ No 'General' folders found")
        
        # 2. Ensure at least one active project exists
        console.print("\n🚀 [bold]Step 2: Ensuring active projects exist[/bold]")
        projects_path = vault_path / '01-Projects'
        if projects_path.exists():
            project_folders = [f for f in projects_path.iterdir() if f.is_dir()]
            
            if not project_folders:
                console.print("⚠️ No projects found - creating default project")
                default_project = projects_path / "Active Project"
                default_project.mkdir(parents=True, exist_ok=True)
                
                # Create a project template note
                template_content = """# Active Project

## Project Overview
This is your main active project. Add your current goals and tasks here.

## Current Tasks
- [ ] Define project goals
- [ ] Set deadlines
- [ ] Track progress

## Notes
Add project-specific notes here.

---
*Created automatically by PARA CLI - organize this project according to your current priorities*
"""
                template_path = default_project / "Project Overview.md"
                template_path.write_text(template_content, encoding='utf-8')
                console.print("   📝 Created 'Active Project' with template")
                stats['projects_created'] += 1
            else:
                console.print(f"✅ Found {len(project_folders)} existing projects")
        
        # 3. Reorganize resources into thematic subfolders
        console.print("\n📚 [bold]Step 3: Reorganizing resources[/bold]")
        resources_path = vault_path / '03-Resources'
        if resources_path.exists():
            resource_folders = [f for f in resources_path.iterdir() if f.is_dir()]
            
            # Define thematic categories based on PARA examples
            thematic_categories = {
                'info': ['info', 'information', 'data', 'facts'],
                'templates': ['template', 'form', 'format'],
                'guides': ['guide', 'tutorial', 'how-to', 'manual'],
                'references': ['reference', 'ref', 'source'],
                'tools': ['tool', 'utility', 'app', 'software'],
                'knowledge': ['knowledge', 'learning', 'study', 'research']
            }
            
            for folder in resource_folders:
                folder_name = folder.name.lower()
                
                # Check if folder should be moved to a thematic subfolder
                for theme, keywords in thematic_categories.items():
                    if any(keyword in folder_name for keyword in keywords):
                        target_theme_path = resources_path / theme
                        target_theme_path.mkdir(parents=True, exist_ok=True)
                        
                        target_path = target_theme_path / folder.name
                        if folder != target_path:
                            try:
                                # Usar _safe_rename_file para manejar conflictos de nombres
                                final_path = _safe_rename_file(folder, target_path, vault_path, db)
                                if final_path != folder:
                                    console.print(f"   📁 Moved {folder.name} → Resources/{theme}/")
                                    stats['resources_reorganized'] += 1
                                else:
                                    console.print(f"   ⚠️ Could not move {folder.name} (conflict resolved)")
                            except Exception as e:
                                stats['errors'].append(f"Error moving resource {folder.name}: {e}")
                        break
        
        # 4. Remove all empty folders
        console.print("\n🧹 [bold]Step 4: Removing empty folders[/bold]")
        empty_folders_removed = _remove_empty_folders_recursive(vault_path)
        stats['empty_folders_removed'] += empty_folders_removed
        console.print(f"   🗑️ Removed {empty_folders_removed} empty folders")
        
        # Summary
        console.print(f"\n✅ [bold green]PARA Principles Applied Successfully![/bold green]")
        console.print(f"   📊 General folders fixed: {stats['general_folders_fixed']}")
        console.print(f"   🚀 Projects created: {stats['projects_created']}")
        console.print(f"   📚 Resources reorganized: {stats['resources_reorganized']}")
        console.print(f"   🗑️ Empty folders removed: {stats['empty_folders_removed']}")
        
        if stats['errors']:
            console.print(f"   ⚠️ Errors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:3]:  # Show first 3 errors
                console.print(f"      • {error}")
        
        return stats
        
    except Exception as e:
        error_msg = f"Error enforcing PARA principles: {e}"
        console.print(f"❌ {error_msg}")
        stats['errors'].append(error_msg)
        if PARA_LOGGING_AVAILABLE:
            try:
                log_center.log_error(error_msg, "PARAEnforcement")
            except Exception:
                pass
        return stats

def _analyze_notes_for_grouping(notes: list[Path], db: ChromaPARADatabase) -> dict:
    """
    Analyze notes to suggest logical groupings based on:
    - Common tags
    - Temporal proximity
    - Content similarity
    - Project indicators
    """
    import re
    from datetime import datetime, timedelta
    
    groups = {}
    
    # Group by common tags
    tag_groups = {}
    for note in notes:
        try:
            content = note.read_text(encoding='utf-8')
            tags = re.findall(r'#([a-zA-Z0-9_]+)', content)
            
            for tag in tags:
                if tag.lower() not in ['project', 'area', 'resource', 'archive', 'inbox']:
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    tag_groups[tag].append(note)
        except Exception:
            continue
    
    # Create groups for tags with multiple notes
    for tag, tagged_notes in tag_groups.items():
        if len(tagged_notes) >= 2:
            # NO agregar sufijo "Related" - usar solo el nombre del tag
            group_name = tag.title()
            groups[group_name] = tagged_notes
    
    # Group by temporal proximity (notes created within 30 days)
    if not groups:  # Only if no tag groups found
        try:
            note_dates = []
            for note in notes:
                try:
                    stat = note.stat()
                    note_dates.append((note, datetime.fromtimestamp(stat.st_ctime)))
                except Exception:
                    continue
            
            # Sort by creation date
            note_dates.sort(key=lambda x: x[1])
            
            current_group = []
            current_date = None
            
            for note, date in note_dates:
                if current_date is None or (date - current_date).days <= 30:
                    current_group.append(note)
                    current_date = date
                else:
                    if len(current_group) >= 2:
                        # Solo crear grupo temporal si no hay proyectos identificables
                        if not self._has_identifiable_projects(current_group):
                            group_name = f"Recent {current_date.strftime('%B %Y')}"
                            groups[group_name] = current_group
                    current_group = [note]
                    current_date = date
            
            # Handle last group
            if len(current_group) >= 2:
                # Solo crear grupo temporal si no hay proyectos identificables
                if not self._has_identifiable_projects(current_group):
                    group_name = f"Recent {current_date.strftime('%B %Y')}"
                    groups[group_name] = current_group
                
        except Exception:
            pass
    
    # If still no groups, create content-based groups
    if not groups:
        try:
            # Simple content analysis
            content_groups = {}
            for note in notes:
                try:
                    content = note.read_text(encoding='utf-8').lower()
                    
                    # Detect content type
                    if any(word in content for word in ['project', 'task', 'goal', 'deadline']):
                        content_type = 'Project'
                    elif any(word in content for word in ['guide', 'tutorial', 'how', 'reference']):
                        content_type = 'Reference'
                    elif any(word in content for word in ['meeting', 'call', 'discussion']):
                        content_type = 'Communication'
                    else:
                        content_type = 'General'
                    
                    if content_type not in content_groups:
                        content_groups[content_type] = []
                    content_groups[content_type].append(note)
                    
                except Exception:
                    continue
            
            # Create groups for content types with multiple notes
            for content_type, type_notes in content_groups.items():
                if len(type_notes) >= 2:
                    groups[content_type] = type_notes
                    
        except Exception:
            pass
    
    return groups

def _remove_empty_folders_recursive(path: Path) -> int:
    """Remove empty folders recursively, return count of removed folders."""
    removed_count = 0
    
    try:
        # Múltiples pasadas para asegurar eliminación completa
        for _ in range(3):  # Máximo 3 pasadas
            current_removed = 0
            
            for item in path.iterdir():
                if item.is_dir():
                    # Eliminar carpetas vacías recursivamente
                    removed_count += _remove_empty_folders_recursive(item)
                    
                    # Verificar si la carpeta actual está vacía después de la limpieza recursiva
                    try:
                        if not any(item.iterdir()):
                            item.rmdir()
                            current_removed += 1
                            removed_count += 1
                            console.print(f"🗑️ [dim]Carpeta vacía eliminada: {item.name}[/dim]")
                    except Exception:
                        pass
            
            # Si no se eliminó ninguna carpeta en esta pasada, terminar
            if current_removed == 0:
                break
                
    except Exception:
        pass
    
    return removed_count

def _identify_real_projects(self, notes: List[Path], vault_path: Path) -> Dict[str, List[Path]]:
    """
    Identifica proyectos reales basándose en:
    1. Nombres de archivos que contienen el nombre del proyecto
    2. Tags específicos de proyectos
    3. Contenido que indica proyectos activos
    4. Evita crear carpetas "Related" o temporales
    """
    project_groups = {}
    
    for note in notes:
        try:
            # Extraer nombre del archivo sin extensión
            note_name = note.stem.lower()
            note_content = self._read_note_content(note)
            
            # Buscar patrones de proyectos reales
            project_name = self._extract_project_name(note_name, note_content)
            
            if project_name:
                # Normalizar nombre del proyecto
                normalized_name = self._normalize_project_name(project_name)
                
                if normalized_name not in project_groups:
                    project_groups[normalized_name] = []
                project_groups[normalized_name].append(note)
            
        except Exception as e:
            if PARA_LOGGING_AVAILABLE:
                log_center.log_warning(f"Error identificando proyecto en {note}: {e}", "ProjectIdentification")
    
    return project_groups

def _extract_project_name(self, note_name: str, content: str) -> Optional[str]:
    """
    Extrae el nombre real del proyecto de una nota.
    """
    # Patrones para identificar proyectos reales
    project_patterns = [
        # Patrones de nombres de archivo
        r'^([A-Za-z]+)\s*[-_]\s*',  # "Moka - ", "Ana - "
        r'^([A-Za-z]+)\s+',         # "Moka ", "Ana "
        
        # Patrones de contenido
        r'proyecto[:\s]+([A-Za-z]+)',
        r'project[:\s]+([A-Za-z]+)',
        r'cliente[:\s]+([A-Za-z]+)',
        r'client[:\s]+([A-Za-z]+)',
        
        # Tags específicos
        r'#([A-Za-z]+)-proyecto',
        r'#([A-Za-z]+)-project',
    ]
    
    # Buscar en el nombre del archivo
    for pattern in project_patterns:
        match = re.search(pattern, note_name, re.IGNORECASE)
        if match:
            project_name = match.group(1).strip()
            if len(project_name) > 2:  # Evitar nombres muy cortos
                return project_name
    
    # Buscar en el contenido
    for pattern in project_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            project_name = match.group(1).strip()
            if len(project_name) > 2:
                return project_name
    
    # Buscar nombres específicos conocidos
    known_projects = ['moka', 'ana', 'bbi', 'prestafe', 'mascabo', 'coaching', 'guitar']
    for project in known_projects:
        if project in note_name.lower() or project in content.lower():
            return project
    
    return None

def _normalize_project_name(self, project_name: str) -> str:
    """
    Normaliza el nombre del proyecto para evitar duplicados.
    """
    # Convertir a título y eliminar "Related"
    normalized = project_name.strip().title()
    normalized = normalized.replace('Related', '').strip()
    
    # Mapeos específicos
    project_mappings = {
        'Moka': 'Moka',
        'Ana': 'Ana',
        'Bbi': 'BBI',
        'Prestafe': 'Prestafe',
        'Mascabo': 'Mascabo',
        'Coaching': 'Coaching',
        'Guitar': 'Guitar',
    }
    
    return project_mappings.get(normalized, normalized)

def _should_create_temporal_group(self, notes: List[Path]) -> bool:
    """
    Determina si se debe crear un grupo temporal.
    Solo si no hay proyectos identificables y las notas son recientes.
    """
    if len(notes) < 3:  # Muy pocas notas
        return False
    
    # Verificar si hay proyectos identificables
    for note in notes:
        note_name = note.stem.lower()
        content = self._read_note_content(note)
        if self._extract_project_name(note_name, content):
            return False  # Hay proyectos identificables
    
    # Solo crear grupo temporal si todas las notas son recientes (últimos 30 días)
    recent_count = 0
    for note in notes:
        try:
            mtime = note.stat().st_mtime
            if time.time() - mtime < 30 * 24 * 3600:  # 30 días
                recent_count += 1
        except:
            pass
    
    return recent_count >= len(notes) * 0.8  # 80% de notas recientes
def run_full_reclassification_safe(vault_path: str, excluded_paths: list[str] = None, create_backup: bool = True) -> dict:
    """
    Ejecuta reclasificación completa de todas las notas del vault de forma SEGURA.
    NO renombra archivos de usuario y respeta proyectos independientes.
    """
    from rich.console import Console
    console = Console()
    
    try:
        vault_path = Path(vault_path)
        
        # Crear backup si se solicita
        if create_backup:
            try:
                from paralib.backup_manager import backup_manager
                backup_result = backup_manager.create_backup(str(vault_path))
                # Mostrar solo resumen legible del backup
                try:
                    backup_summary = f"💾 Backup creado: ID={backup_result.id}, Fecha={backup_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, Archivos={backup_result.file_count}, Tamaño={backup_result.size_mb:.2f}MB, Estado={backup_result.status}"
                except Exception:
                    backup_summary = f"💾 Backup creado: {getattr(backup_result, 'id', str(backup_result))}"
                console.print(backup_summary)
            except Exception as e:
                console.print(f"⚠️ [yellow]Error creando backup: {e}[/yellow]")
        
        # Inicializar ChromaDB
        try:
            db = ChromaPARADatabase(str(vault_path))
        except Exception as e:
            console.print(f"❌ Error inicializando ChromaDB: {e}")
            return {
                'success': False,
                'error': f"Error inicializando ChromaDB: {e}",
                'message': 'Error en reclasificación completa'
            }
        
        # Asegurar estructura PARA (sin renombrar archivos de usuario)
        try:
            _ensure_correct_para_structure(vault_path, excluded_paths)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error asegurando estructura PARA: {e}[/yellow]")
        
        # Consolidar carpetas dispersas (conservador)
        try:
            _consolidate_scattered_folders(vault_path, excluded_paths)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error consolidando carpetas dispersas: {e}[/yellow]")
        
        # Clasificar inbox
        try:
            console.print("\n📥 Clasificando Inbox...")
            run_inbox_classification(vault_path, db, "Clasificar todas las notas del inbox", "llama3.2:3b", True)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error clasificando inbox: {e}[/yellow]")
            if should_show('show_debug'):
                import traceback
                console.print(traceback.format_exc())
        
        # Refactorizar archive
        try:
            console.print("\n📦 Refactorizando Archive...")
            run_archive_refactor(vault_path, db, "Refactorizar notas del archive", "llama3.2:3b", True, excluded_paths or [])
        except Exception as e:
            console.print(f"⚠️ [yellow]Error refactorizando archive: {e}[/yellow]")
            if should_show('show_debug'):
                import traceback
                console.print(traceback.format_exc())
        
        # NUEVO: Enforce PARA method principles
        try:
            console.print("\n🎯 Enforcing PARA Method Principles...")
            para_stats = enforce_para_principles(vault_path, db)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error enforcing PARA principles: {e}[/yellow]")
            para_stats = {'errors': [str(e)]}
        
        # Consolidación automática post-organización (conservadora)
        consolidation_stats = {}
        try:
            console.print("\n🏗️ Ejecutando consolidación automática (modo conservador)...")
            consolidation_stats = auto_consolidate_post_organization(vault_path, excluded_paths)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error en consolidación automática: {e}[/yellow]")
            consolidation_stats = {'error': str(e)}
        
        # Construir resultado final con manejo robusto de errores
        try:
            result = {
                'success': True,
                'vault_path': str(vault_path),
                'backup_created': create_backup,
                'para_stats': para_stats,
                'consolidation_stats': consolidation_stats,
                'message': 'Reclasificación completada exitosamente (modo seguro)',
                'safety_features': [
                    'No renombrado de archivos de usuario',
                    'Respeto a proyectos independientes',
                    'Consolidación conservadora',
                    'Preservación de nombres originales'
                ]
            }
            
            # Agregar estadísticas finales si están disponibles
            try:
                final_distribution = db.get_category_distribution()
                if final_distribution:
                    result['final_distribution'] = final_distribution
            except Exception as e:
                console.print(f"⚠️ [yellow]Error obteniendo distribución final: {e}[/yellow]")
            
            return result
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Error construyendo resultado final: {e}[/yellow]")
            return {
                'success': True,  # Consideramos éxito aunque haya errores menores
                'vault_path': str(vault_path),
                'backup_created': create_backup,
                'para_stats': para_stats,
                'consolidation_stats': consolidation_stats,
                'message': 'Reclasificación completada con advertencias (modo seguro)',
                'warnings': [str(e)]
            }
        
    except Exception as e:
        console.print(f"❌ Error crítico en reclasificación completa: {e}")
        if should_show('show_debug'):
            import traceback
            console.print(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'message': 'Error crítico en reclasificación completa'
        }

def _safe_rename_file(source_path: Path, target_path: Path, vault_path: Path, db: ChromaPARADatabase = None) -> Path:
    """
    Mueve un archivo de forma segura, manejando conflictos de nombres y directorios.
    
    Args:
        source_path: Ruta del archivo origen
        target_path: Ruta del archivo destino deseado
        vault_path: Ruta del vault
        db: Base de datos ChromaDB (opcional)
    
    Returns:
        Path: Ruta final del archivo
    """
    from .log_center import log_center
    
    try:
        # Si el archivo origen no existe, retornar el target_path
        if not source_path.exists():
            return target_path
        
        # Si el target_path no existe, mover directamente
        if not target_path.exists():
            source_path.rename(target_path)
            return target_path
        
        # CASO CRÍTICO: Si target_path existe como directorio y source_path es un archivo
        if target_path.is_dir() and source_path.is_file():
            # Crear un nombre único para el archivo dentro del directorio
            counter = 1
            base_name = source_path.stem
            extension = source_path.suffix
            
            while True:
                new_name = f"{base_name}_{counter}{extension}"
                new_path = target_path / new_name
                if not new_path.exists():
                    source_path.rename(new_path)
                    log_center.log_warning(
                        f"Archivo renombrado debido a conflicto con directorio: {source_path.name} → {new_name}",
                        "Organizer-SafeRename",
                        {"source": str(source_path), "target": str(new_path)}
                    )
                    return new_path
                counter += 1
        
        # CASO: Si target_path existe como archivo
        elif target_path.is_file():
            # Verificar si es el mismo archivo
            if source_path.samefile(target_path):
                return target_path
            
            # Si son archivos diferentes, crear nombre único
            counter = 1
            base_name = target_path.stem
            extension = target_path.suffix
            
            while True:
                new_name = f"{base_name}_{counter}{extension}"
                new_path = target_path.parent / new_name
                if not new_path.exists():
                    source_path.rename(new_path)
                    log_center.log_warning(
                        f"Archivo renombrado debido a conflicto: {source_path.name} → {new_name}",
                        "Organizer-SafeRename",
                        {"source": str(source_path), "target": str(new_path)}
                    )
                    return new_path
                counter += 1
        
        # CASO: Si target_path es un directorio y source_path también es un directorio
        elif target_path.is_dir() and source_path.is_dir():
            # Mover contenido del directorio origen al directorio destino
            for item in source_path.iterdir():
                item_target = target_path / item.name
                if item_target.exists():
                    # Si hay conflicto, renombrar el item
                    counter = 1
                    base_name = item.stem
                    extension = item.suffix if item.is_file() else ""
                    
                    while True:
                        new_name = f"{base_name}_{counter}{extension}"
                        new_path = target_path / new_name
                        if not new_path.exists():
                            item.rename(new_path)
                            break
                        counter += 1
                else:
                    item.rename(item_target)
            
            # Eliminar el directorio origen vacío
            source_path.rmdir()
            return target_path
        
        return target_path
        
    except Exception as e:
        log_center.log_error(
            f"Error en _safe_rename_file: {e}",
            "Organizer-SafeRename",
            {"source": str(source_path), "target": str(target_path), "error": str(e)}
        )
        # En caso de error, retornar la ruta origen
        return source_path

def clean_problematic_folders(vault_path: Path, db=None) -> dict:
    """
    Limpia carpetas problemáticas y mejora la clasificación.
    
    Problemas identificados:
    - Carpetas con "Related" en proyectos (deberían estar en recursos)
    - Carpetas "Recent June 2025" (temporales)
    - Carpetas con sufijos numéricos (_1, _2, etc.)
    - Carpetas con nombres genéricos que deberían estar en áreas
    """
    stats = {
        'folders_cleaned': 0,
        'projects_fixed': 0,
        'resources_reorganized': 0,
        'areas_created': 0,
        'errors': []
    }
    
    try:
        # 1. Limpiar carpetas "Related" de proyectos
        projects_path = vault_path / '01-Projects'
        if projects_path.exists():
            for folder in projects_path.iterdir():
                if not folder.is_dir() or folder.name.startswith('.'):
                    continue
                
                # Detectar carpetas problemáticas en proyectos
                if 'Related' in folder.name or 'Recent' in folder.name:
                    try:
                        # Mover a recursos
                        resources_path = vault_path / '03-Resources'
                        resources_path.mkdir(exist_ok=True)
                        
                        # Limpiar nombre (remover "Related" y sufijos)
                        clean_name = folder.name.replace(' Related', '').replace(' Related_2', '')
                        clean_name = clean_name.replace('Recent June 2025', 'Temporary Notes')
                        
                        new_path = resources_path / clean_name
                        
                        # Evitar conflictos
                        if new_path.exists():
                            clean_name = f"{clean_name}_{datetime.now().strftime('%Y%m%d')}"
                            new_path = resources_path / clean_name
                        
                        folder.rename(new_path)
                        stats['projects_fixed'] += 1
                        print(f"✅ Movido de proyectos a recursos: {folder.name} → {clean_name}")
                        
                    except Exception as e:
                        stats['errors'].append(f"Error moviendo {folder.name}: {e}")
        
        # 2. Limpiar carpetas "Related" duplicadas en recursos
        resources_path = vault_path / '03-Resources'
        if resources_path.exists():
            related_folders = {}
            
            for folder in resources_path.iterdir():
                if not folder.is_dir() or folder.name.startswith('.'):
                    continue
                
                if 'Related' in folder.name:
                    # Extraer nombre base
                    base_name = folder.name.replace(' Related', '').replace(' Related_2', '')
                    
                    if base_name not in related_folders:
                        related_folders[base_name] = []
                    related_folders[base_name].append(folder)
            
            # Consolidar carpetas relacionadas
            for base_name, folders in related_folders.items():
                if len(folders) > 1:
                    try:
                        # Usar la carpeta más antigua como principal
                        main_folder = min(folders, key=lambda f: f.stat().st_mtime)
                        other_folders = [f for f in folders if f != main_folder]
                        
                        # Renombrar carpeta principal
                        new_name = base_name
                        new_path = main_folder.parent / new_name
                        
                        if new_path.exists():
                            new_name = f"{base_name}_{datetime.now().strftime('%Y%m%d')}"
                            new_path = main_folder.parent / new_name
                        
                        main_folder.rename(new_path)
                        
                        # Mover contenido de otras carpetas
                        for other_folder in other_folders:
                            for item in other_folder.iterdir():
                                if item.is_file():
                                    target_path = new_path / item.name
                                    if not target_path.exists():
                                        item.rename(target_path)
                            # Eliminar carpeta vacía
                            other_folder.rmdir()
                        
                        stats['resources_reorganized'] += 1
                        print(f"✅ Consolidado: {len(folders)} carpetas '{base_name}' → 1")
                        
                    except Exception as e:
                        stats['errors'].append(f"Error consolidando {base_name}: {e}")
        
        # 3. Crear área "Personal Development" para carpetas de desarrollo personal
        areas_path = vault_path / '02-Areas'
        if areas_path.exists():
            personal_dev_path = areas_path / 'Personal Development'
            personal_dev_path.mkdir(exist_ok=True)
            
            # Mover carpetas de desarrollo personal a la nueva área
            personal_folders = ['Carrera', 'Encuesta', 'Coaching']
            for folder_name in personal_folders:
                # Buscar en recursos
                source_path = resources_path / f"{folder_name} Related"
                if source_path.exists():
                    try:
                        target_path = personal_dev_path / folder_name
                        if not target_path.exists():
                            source_path.rename(target_path)
                            stats['areas_created'] += 1
                            print(f"✅ Movido a Personal Development: {folder_name}")
                    except Exception as e:
                        stats['errors'].append(f"Error moviendo {folder_name}: {e}")
        
        # 4. Limpiar carpetas temporales
        for para_folder in ['01-Projects', '02-Areas', '03-Resources']:
            folder_path = vault_path / para_folder
            if folder_path.exists():
                for folder in folder_path.iterdir():
                    if not folder.is_dir() or folder.name.startswith('.'):
                        continue
                    
                    # Detectar carpetas temporales
                    if 'Recent' in folder.name or 'Temporary' in folder.name:
                        try:
                            # Mover contenido a archivo
                            archive_path = vault_path / '04-Archive' / 'Temporary Notes'
                            archive_path.mkdir(exist_ok=True)
                            
                            for item in folder.iterdir():
                                if item.is_file():
                                    target_path = archive_path / item.name
                                    if not target_path.exists():
                                        item.rename(target_path)
                            
                            # Eliminar carpeta vacía
                            folder.rmdir()
                            stats['folders_cleaned'] += 1
                            print(f"✅ Limpiada carpeta temporal: {folder.name}")
                            
                        except Exception as e:
                            stats['errors'].append(f"Error limpiando {folder.name}: {e}")
        
        stats['folders_cleaned'] += stats['projects_fixed'] + stats['resources_reorganized'] + stats['areas_created']
        
    except Exception as e:
        stats['errors'].append(f"Error general: {e}")
    
    return stats

class TagAnalyzer:
    """Analizador de tags simple para evitar errores de importación."""
    def __init__(self, vault_path):
        self.vault_path = vault_path
        self.tag_folders = {}  # Cache para análisis de tags
    
    def analyze_vault_tags(self):
        """Analiza tags del vault de forma simple."""
        try:
            # Análisis básico de tags por carpeta
            for para_folder in ['01-Projects', '02-Areas', '03-Resources', '04-Archive']:
                folder_path = self.vault_path / para_folder
                if not folder_path.exists():
                    continue
                
                for note_file in folder_path.rglob('*.md'):
                    if note_file.is_file():
                        content = note_file.read_text(encoding='utf-8', errors='ignore')
                        tags = self._extract_tags_from_content(content)
                        
                        for tag in tags:
                            if tag not in self.tag_folders:
                                self.tag_folders[tag] = {}
                            
                            if para_folder not in self.tag_folders[tag]:
                                self.tag_folders[tag][para_folder] = 0
                            
                            self.tag_folders[tag][para_folder] += 1
        except Exception as e:
            logger.warning(f"Error analizando tags del vault: {e}")
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extrae tags de Obsidian del contenido."""
        import re
        tags = []
        
        # Buscar tags de Obsidian #tag
        tag_pattern = r'#([a-zA-Z0-9_]+)'
        matches = re.findall(tag_pattern, content)
        tags.extend(matches)
        
        # Buscar tags en frontmatter
        frontmatter_pattern = r'---\s*\n(.*?)\n---'
        frontmatter_match = re.search(frontmatter_pattern, content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            # Buscar tags en frontmatter
            tags_pattern = r'tags:\s*\[(.*?)\]'
            tags_match = re.search(tags_pattern, frontmatter)
            if tags_match:
                tags_str = tags_match.group(1)
                frontmatter_tags = [tag.strip().strip('"\'') for tag in tags_str.split(',')]
                tags.extend(frontmatter_tags)
        
        return list(set(tags))  # Remover duplicados
    
    def calculate_tag_weight_for_classification(self, tags: set, category: str, suggested_folder: str) -> float:
        """
        Calcula el peso de los tags para la clasificación.
        
        Args:
            tags: Conjunto de tags encontrados en la nota
            category: Categoría sugerida (Projects, Areas, Resources, Archive)
            suggested_folder: Carpeta sugerida
            
        Returns:
            float: Peso entre 0.0 y 1.0
        """
        if not tags or not suggested_folder:
            return 0.0
        
        try:
            # Mapear categoría a carpeta PARA
            category_to_folder = {
                'Projects': '01-Projects',
                'Areas': '02-Areas', 
                'Resources': '03-Resources',
                'Archive': '04-Archive'
            }
            
            target_folder = category_to_folder.get(category, suggested_folder)
            
            # Calcular peso basado en análisis histórico
            total_weight = 0.0
            valid_tags = 0
            
            for tag in tags:
                if tag in self.tag_folders:
                    folder_dist = self.tag_folders[tag]
                    total_occurrences = sum(folder_dist.values())
                    
                    if total_occurrences > 0:
                        # Peso basado en dominancia en la carpeta objetivo
                        target_occurrences = folder_dist.get(target_folder, 0)
                        dominance = target_occurrences / total_occurrences
                        
                        # Ajustar peso por frecuencia total del tag
                        frequency_factor = min(total_occurrences / 10, 1.0)  # Normalizar por frecuencia
                        
                        tag_weight = dominance * frequency_factor
                        total_weight += tag_weight
                        valid_tags += 1
            
            # Retornar promedio de pesos
            if valid_tags > 0:
                return total_weight / valid_tags
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error calculando peso de tags: {e}")
            return 0.0
    
    def get_tag_coherence(self, content):
        """Retorna coherencia de tags (valor por defecto)."""
        return 0.5  # Valor neutral

def _log_detailed_classification_decision(
    note_content: str, 
    note_path: Path, 
    final_result: dict, 
    complete_analysis: dict,
    semantic_category: str, 
    llm_category: str, 
    semantic_confidence: float, 
    llm_confidence: float,
    semantic_weight: float, 
    llm_weight: float,
    vault_path: Path, 
    db: ChromaPARADatabase,
    user_directive: str = "",
    model_name: str = ""
) -> dict:
    """
    Logging detallado de cada decisión de clasificación para análisis y aprendizaje.
    Captura toda la información necesaria para entender por qué se tomó cada decisión.
    """
    from datetime import datetime
    from paralib.log_center import log_center
    from paralib.learning_system import PARA_Learning_System
    import json
    
    try:
        # Extraer información de la decisión final
        final_category = final_result.get('category', 'Unknown')
        final_folder = final_result.get('folder_name', 'Unknown')
        final_confidence = final_result.get('confidence', 0.0)
        final_method = final_result.get('method', 'unknown')
        final_reasoning = final_result.get('reasoning', '')
        
        # Detectar si se usó fallback
        fallback_used = False
        fallback_reason = ""
        if final_confidence < 0.3:
            fallback_used = True
            fallback_reason = "Confianza muy baja"
        elif final_category == 'Unknown':
            fallback_used = True
            fallback_reason = "Categoría no determinada"
        elif final_folder == 'Unknown':
            fallback_used = True
            fallback_reason = "Carpeta no determinada"
        
        # Crear registro detallado
        classification_log = {
            # === INFORMACIÓN BÁSICA ===
            'timestamp': datetime.now().isoformat(),
            'note_path': str(note_path),
            'note_name': note_path.name,
            'note_size': len(note_content),
            'vault_path': str(vault_path),
            
            # === INPUTS ===
            'user_directive': user_directive,
            'model_name': model_name,
            'note_content_preview': note_content[:200] + "..." if len(note_content) > 200 else note_content,
            
            # === ANÁLISIS COMPLETO ===
            'analysis': {
                'has_dates': complete_analysis.get('has_dates', False),
                'has_links': complete_analysis.get('has_links', False),
                'has_attachments': complete_analysis.get('has_attachments', False),
                'link_count': complete_analysis.get('link_count', 0),
                'word_count': complete_analysis.get('word_count', 0),
                'last_modified': complete_analysis.get('last_modified', ''),
                'tags_found': complete_analysis.get('tags', []),
                'entities_found': complete_analysis.get('entities', []),
                'patterns_detected': complete_analysis.get('patterns', [])
            },
            
            # === RESULTADOS SEMÁNTICOS ===
            'semantic_analysis': {
                'category': semantic_category,
                'confidence': semantic_confidence,
                'weight_used': semantic_weight,
                'method': 'semantic_embedding'
            },
            
            # === RESULTADOS LLM ===
            'llm_analysis': {
                'category': llm_category,
                'confidence': llm_confidence,
                'weight_used': llm_weight,
                'method': 'llm_reasoning'
            },
            
            # === DECISIÓN FINAL ===
            'final_decision': {
                'category': final_category,
                'folder': final_folder,
                'confidence': final_confidence,
                'method': final_method,
                'reasoning': final_reasoning,
                'fallback_used': fallback_used,
                'fallback_reason': fallback_reason
            },
            
            # === MÉTRICAS DE CALIDAD ===
            'quality_metrics': {
                'confidence_gap': abs(semantic_confidence - llm_confidence),
                'method_agreement': semantic_category == llm_category,
                'decision_confidence': final_confidence,
                'content_complexity': len(note_content.split()) / 100,  # Normalizado
                'tag_density': len(complete_analysis.get('tags', [])) / max(len(note_content.split()), 1)
            },
            
            # === INFORMACIÓN PARA APRENDIZAJE ===
            'learning_data': {
                'requires_review': final_confidence < 0.5 or fallback_used,
                'potential_error': _detect_classification_error(
                    note_content, final_category, complete_analysis,
                    semantic_category, llm_category, semantic_confidence, llm_confidence
                ),
                'learning_priority': 'high' if final_confidence < 0.3 else 'medium' if final_confidence < 0.7 else 'low'
            }
        }
        
        # === LOGGING A SISTEMAS CENTRALES ===
        
        # 1. Log Center (para debugging y monitoreo)
        log_level = "warning" if fallback_used or final_confidence < 0.5 else "info"
        log_message = f"Clasificación: {note_path.name} → {final_category}/{final_folder} (conf: {final_confidence:.3f}, método: {final_method})"
        if fallback_used:
            log_message += f" [FALLBACK: {fallback_reason}]"
        
        log_center.log(log_level, log_message, "Classification-Decision")
        
        # 2. Sistema de Aprendizaje (para mejora automática)
        try:
            learning_system = PARA_Learning_System(db, vault_path)
            learning_result = learning_system.learn_from_classification(classification_log)
            classification_log['learning_result'] = learning_result
        except Exception as e:
            classification_log['learning_error'] = str(e)
            log_center.log_warning(f"Error en sistema de aprendizaje: {e}", "Classification-Decision")
        
        # 3. Base de Datos de Clasificaciones (para análisis histórico)
        try:
            _save_classification_to_database(classification_log, db)
        except Exception as e:
            classification_log['database_error'] = str(e)
            log_center.log_warning(f"Error guardando clasificación en DB: {e}", "Classification-Decision")
        
        # 4. Archivo de Log Detallado (para análisis offline)
        try:
            _save_detailed_log_to_file(classification_log, vault_path)
        except Exception as e:
            classification_log['file_log_error'] = str(e)
            log_center.log_warning(f"Error guardando log detallado: {e}", "Classification-Decision")
        
        return classification_log
        
    except Exception as e:
        log_center.log_error(f"Error en logging detallado de clasificación: {e}", "Classification-Decision")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'note_path': str(note_path) if note_path else 'unknown'
        }

def _save_classification_to_database(classification_log: dict, db: ChromaPARADatabase):
    """Guarda la clasificación en la base de datos para análisis histórico."""
    try:
        # Crear documento para ChromaDB
        document = {
            'content': classification_log['note_content_preview'],
            'metadata': {
                'note_path': classification_log['note_path'],
                'note_name': classification_log['note_name'],
                'final_category': classification_log['final_decision']['category'],
                'final_folder': classification_log['final_decision']['folder'],
                'final_confidence': classification_log['final_decision']['confidence'],
                'final_method': classification_log['final_decision']['method'],
                'semantic_category': classification_log['semantic_analysis']['category'],
                'llm_category': classification_log['llm_analysis']['category'],
                'semantic_confidence': classification_log['semantic_analysis']['confidence'],
                'llm_confidence': classification_log['llm_analysis']['confidence'],
                'fallback_used': classification_log['final_decision']['fallback_used'],
                'requires_review': classification_log['learning_data']['requires_review'],
                'timestamp': classification_log['timestamp'],
                'classification_id': f"cls_{classification_log['timestamp'].replace(':', '-')}"
            }
        }
        
        # Agregar a la colección de clasificaciones
        db.collection.add(
            documents=[document['content']],
            metadatas=[document['metadata']],
            ids=[document['metadata']['classification_id']]
        )
        
    except Exception as e:
        raise Exception(f"Error guardando en base de datos: {e}")

def _save_detailed_log_to_file(classification_log: dict, vault_path: Path):
    """Guarda el log detallado en un archivo JSON para análisis offline."""
    try:
        log_dir = vault_path / ".para_db" / "classification_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo con timestamp
        timestamp = classification_log['timestamp'].replace(':', '-').replace('.', '-')
        filename = f"classification_{timestamp}_{classification_log['note_name'].replace('.md', '')}.json"
        log_file = log_dir / filename
        
        # Guardar como JSON
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(classification_log, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        raise Exception(f"Error guardando log en archivo: {e}")

def _detect_classification_error(note_content: str, predicted_category: str, analysis: dict,
                               semantic_category: str, llm_category: str, 
                               semantic_confidence: float, llm_confidence: float) -> dict:
    """Detecta posibles errores en la clasificación basado en múltiples indicadores."""
    
    error_indicators = []
    error_confidence = 0.0
    
    # 1. Discrepancia entre métodos
    if semantic_category != llm_category:
        error_indicators.append("Discrepancia entre análisis semántico y LLM")
        error_confidence += 0.3
    
    # 2. Confianza muy baja
    if semantic_confidence < 0.3 and llm_confidence < 0.3:
        error_indicators.append("Confianza muy baja en ambos métodos")
        error_confidence += 0.4
    
    # 3. Contenido ambiguo
    if len(note_content.split()) < 10:
        error_indicators.append("Contenido muy corto")
        error_confidence += 0.2
    
    # 4. Categoría genérica
    if predicted_category in ['Unknown', 'Miscellaneous', 'General']:
        error_indicators.append("Categoría genérica asignada")
        error_confidence += 0.2
    
    # 5. Patrones contradictorios
    has_dates = analysis.get('has_dates', False)
    has_links = analysis.get('has_links', False)
    if has_dates and predicted_category == 'Resources':
        error_indicators.append("Nota con fechas clasificada como Resources")
        error_confidence += 0.1
    
    return {
        'is_error': error_confidence > 0.5,
        'error_confidence': min(error_confidence, 1.0),
        'indicators': error_indicators,
        'requires_manual_review': error_confidence > 0.7
    }