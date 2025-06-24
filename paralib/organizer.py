"""
paralib/organizer.py

Organizador principal del sistema PARA.
Coordina la clasificación, reclasificación y organización de notas usando IA.
"""
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.panel import Panel

from .db import ChromaPARADatabase
from .config import load_config
from .vault import load_para_config
from .vault_selector import vault_selector
from .analyze_manager import AnalyzeManager
from .logger import logger
import ollama
from paralib.ai_engine import AIEngine

console = Console()

CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources, Archive) system organizer with deep understanding of productivity and knowledge management. Your task is to classify a given note into one of the four PARA categories with maximum precision.

CRITICAL CONTEXT: You are working alongside a ChromaDB semantic analysis system. Your classification will be combined with semantic analysis for optimal accuracy.

PARA CATEGORIES - PRECISE DEFINITIONS:

**PROJECTS** - A series of tasks linked to a goal with a deadline:
- MUST HAVE: Specific outcomes, deadlines, action items
- EXAMPLES: "Develop New App by Q2", "Plan Vacation for March", "Complete Q3 Report by Friday"
- INDICATORS: Action verbs (develop, plan, complete), dates, task lists, milestones, OKRs
- TIME-BOUND with clear completion criteria

**AREAS** - A sphere of activity with a standard to be maintained over time:
- MUST HAVE: Ongoing maintenance, continuous improvement, no specific end date
- EXAMPLES: "Health & Fitness", "Finances", "Career Development", "Team Management"
- INDICATORS: Standards, habits, regular reviews, continuous improvement, quarterly goals
- NO specific end date, but requires regular attention

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

CLASSIFICATION STRATEGY:
1. Analyze the note's PURPOSE and CONTENT TYPE
2. Look for SPECIFIC INDICATORS (dates, action items, references)
3. Consider the NOTE'S CONTEXT and INTENDED USE
4. If unclear or too generic, classify as "Archive" for manual review

Output ONLY a JSON object with this structure:
{"category": "Projects" | "Areas" | "Resources" | "Archive", "folder_name": "Suggested Folder Name", "reasoning": "Brief explanation of classification decision"}

- The "folder_name" should be a short, descriptive name (2-4 words max)
- The "reasoning" should explain your classification logic
- If the note doesn't clearly fit any category, classify as "Archive"
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
- EXAMPLES: "Health & Fitness", "Finances", "Career Development", "Team Management"
- INDICATORS: Standards, habits, regular reviews, continuous improvement, quarterly goals
- NO specific end date, but requires regular attention

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
    """
    engine = AIEngine(model_name=model_name)
    result = engine.classify_note_with_llm(note_content, user_directive, system_prompt)
    return result

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
    # Base weights
    base_semantic = 0.6
    base_llm = 0.4
    
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
        
        # Calcular confianza combinada
        combined_confidence = (semantic_confidence * semantic_weight) + (0.8 * llm_weight)
        
        return {
            'category': semantic_category,
            'folder_name': folder_name,
            'confidence': combined_confidence,
            'method': 'consensus',
            'semantic_score': semantic_confidence,
            'llm_score': 0.8,
            'reasoning': f"Consenso entre ChromaDB y IA. {semantic_reasoning}"
        }
    
    # Caso 2: Sistemas discrepan - usar pesos dinámicos
    console.print(f"🔄 [yellow]DISCREPANCIA: ChromaDB={semantic_category} vs IA={llm_category}[/yellow]")
    
    # Calcular scores ponderados
    semantic_score = semantic_confidence * semantic_weight
    llm_score = 0.8 * llm_weight  # Asumimos confianza media de IA
    
    if semantic_score > llm_score:
        final_category = semantic_category
        final_folder = _generate_folder_name_from_content(note_content, semantic_category)
        method = 'chromadb_weighted'
        reasoning = f"ChromaDB prevalece por peso ({semantic_weight:.2f}). {semantic_reasoning}"
    else:
        final_category = llm_category
        final_folder = llm_folder if llm_folder != 'Unknown' else _generate_folder_name_from_content(note_content, llm_category)
        method = 'llm_weighted'
        reasoning = f"IA prevalece por peso ({llm_weight:.2f}). Razonamiento: {llm_result.get('reasoning', 'Análisis de IA')}"
    
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

def classify_note_with_enhanced_analysis(note_content: str, note_path: Path, user_directive: str, model_name: str, system_prompt: str, db: ChromaPARADatabase, vault_path: Path) -> dict | None:
    """
    Clasificación potenciada con ChromaDB usando análisis completo de la nota.
    """
    # Usar el sistema de análisis completo
    return classify_note_with_complete_analysis(note_content, note_path, user_directive, model_name, system_prompt, db, vault_path)

def _generate_folder_name_from_content(content: str, category: str) -> str:
    """
    Genera un nombre de carpeta basado en el contenido y categoría.
    """
    import re
    
    # Extraer título del contenido (primera línea no vacía)
    lines = content.strip().split('\n')
    title = ""
    for line in lines:
        if line.strip() and not line.strip().startswith('#'):
            title = line.strip()
            break
    
    if not title:
        title = "Untitled"
    
    # Limpiar y normalizar título
    title = re.sub(r'[^\w\s-]', '', title)  # Remover caracteres especiales
    title = re.sub(r'\s+', ' ', title).strip()  # Normalizar espacios
    
    # Acortar si es muy largo
    if len(title) > 30:
        words = title.split()
        title = ' '.join(words[:3])  # Primeras 3 palabras
    
    # Asegurar que no esté vacío
    if not title:
        title = f"New {category[:-1]}"  # "New Project", "New Area", etc.
    
    return title

def _process_notes_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, source_folder_name: str, system_prompt: str, excluded_paths: list[str] = None):
    """
    Función interna para procesar clasificación de notas (usada por inbox y archive).
    POTENCIADA CON CHROMADB para mejor precisión.
    """
    if not check_ollama_model(model_name):
        return

    source_path = vault_path / source_folder_name
    if not source_path.is_dir():
        console.print(f"[yellow]⚠️ No se encontró la carpeta '{source_folder_name}' en el vault.[/yellow]")
        console.print(f"[dim]Ruta buscada: {source_path}[/dim]")
        
        # Mostrar estructura de carpetas disponibles
        console.print(f"\n[bold]📁 Estructura de carpetas disponible en el vault:[/bold]")
        try:
            vault_folders = [f.name for f in vault_path.iterdir() if f.is_dir()]
            if vault_folders:
                for folder in sorted(vault_folders):
                    console.print(f"  • {folder}")
            else:
                console.print("  • No se encontraron carpetas en el vault")
        except Exception as e:
            console.print(f"  • Error al listar carpetas: {e}")
        
        console.print(f"\n[bold]💡 Sugerencias:[/bold]")
        console.print(f"  • Verifica que la carpeta '{source_folder_name}' existe")
        console.print(f"  • Usa 'python para_cli.py vault' para ver la configuración actual")
        console.print(f"  • Crea la carpeta si es necesaria para el sistema PARA")
        
        return

    all_notes_in_source = list(source_path.rglob("*.md"))
    if excluded_paths:
        notes_to_process = [
            note for note in all_notes_in_source 
            if not any(str(note.resolve()).startswith(excluded) for excluded in excluded_paths)
        ]
    else:
        notes_to_process = all_notes_in_source

    console.print(f"\n[bold]🤖 Encontradas {len(notes_to_process)} notas para procesar en '{source_folder_name}'.[/bold]")
    if not notes_to_process:
        console.print(f"[yellow]No hay notas para procesar en '{source_folder_name}'.[/yellow]")
        console.print(f"[dim]Esto puede ser normal si la carpeta está vacía o no contiene archivos .md[/dim]")
        return
        
    if execute:
        mode_text = "EXECUTE"
        progress_title = "[green]Procesando y moviendo notas..."
    else:
        mode_text = "SIMULATION"
        progress_title = "[yellow]Simulando procesamiento..."
        console.print("\n[yellow][bold]MODO SIMULACIÓN ACTIVADO: No se aplicarán cambios permanentes.[/bold][/yellow]")

    console.print(f"🤖 Usando modelo de IA: [bold cyan]{model_name}[/bold cyan]")
    console.print(f"🔍 [bold]POTENCIADO CON CHROMADB[/bold] para análisis semántico avanzado")
    console.print(f"\n[bold]Modo {mode_text} activado. Directiva del usuario:[/bold] [italic]'{extra_prompt}'[/italic]")

    # Mostrar distribución actual de categorías
    console.print(f"\n[bold]📊 Distribución actual de categorías:[/bold]")
    category_distribution = db.get_category_distribution()
    if category_distribution:
        for category, count in category_distribution.items():
            console.print(f"  • {category}: {count} notas")
    else:
        console.print("  • Base de datos vacía - primera ejecución")

    # Tabla de resultados
    results_table = Table(title=f"Resultados de Clasificación - {mode_text}")
    results_table.add_column("Nota", style="cyan")
    results_table.add_column("Categoría", style="green")
    results_table.add_column("Carpeta", style="yellow")
    results_table.add_column("Confianza", style="blue")
    results_table.add_column("Método", style="magenta")
    results_table.add_column("Tags", style="cyan")
    results_table.add_column("Patrones", style="yellow")

    with Progress() as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        
        for note_path in notes_to_process:
            try:
                note_content = note_path.read_text(encoding='utf-8')
                
                # Usar clasificación potenciada con ChromaDB
                result = classify_note_with_enhanced_analysis(
                    note_content, note_path, extra_prompt, model_name, 
                    system_prompt, db, vault_path
                )
                
                if result:
                    category = result.get('category', 'Unknown')
                    folder_name = result.get('folder_name', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    method = result.get('method', 'unknown')
                    analysis = result.get('analysis', {})
                    
                    # Mostrar método de clasificación
                    method_display = {
                        'consensus': '✅ Consenso',
                        'chromadb_weighted': '🔍 ChromaDB',
                        'llm_weighted': '🤖 IA',
                        'chromadb_only': '🔍 Solo ChromaDB',
                        'llm_only': '🤖 Solo IA'
                    }.get(method, method)
                    
                    # Información de tags
                    tags = analysis.get('tags', [])
                    obsidian_tags = analysis.get('obsidian_tags', [])
                    tags_display = []
                    if obsidian_tags:
                        tags_display.extend(obsidian_tags)
                    tags_display.extend([t for t in tags[:3] if t not in obsidian_tags])
                    tags_text = ', '.join(tags_display[:5]) if tags_display else "N/A"
                    
                    # Información de patrones
                    patterns = []
                    if analysis.get('has_todos'):
                        patterns.append(f"📝{analysis.get('todo_count', 0)}")
                    if analysis.get('has_dates'):
                        patterns.append("📅")
                    if analysis.get('has_links'):
                        patterns.append(f"🔗{analysis.get('link_count', 0)}")
                    if analysis.get('has_attachments'):
                        patterns.append("📎")
                    
                    patterns_text = ' '.join(patterns) if patterns else "N/A"
                    
                    results_table.add_row(
                        note_path.name,
                        category,
                        folder_name,
                        f"{confidence:.3f}",
                        method_display,
                        tags_text,
                        patterns_text
                    )
                    
                    if execute:
                        # Asegurar que la categoría tenga el número correcto
                        category_mapping = {
                            'Projects': '01-Projects',
                            'Areas': '02-Areas', 
                            'Resources': '03-Resources',
                            'Archive': '04-Archive',
                            'Inbox': '00-Inbox'
                        }
                        
                        target_category = category_mapping.get(category, category)
                        target_folder = vault_path / target_category / folder_name
                        target_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Extraer scores del resultado
                        semantic_score = result.get('semantic_score', 0.0)
                        ai_score = result.get('ai_score', 0.0)
                        
                        # Registrar la creación de carpeta para el sistema de aprendizaje
                        register_folder_creation(
                            folder_name=folder_name,
                            category=category,
                            note_content=note_content,
                            note_path=note_path,
                            confidence=confidence,
                            method_used=method_display,
                            semantic_score=semantic_score,
                            ai_score=ai_score,
                            vault_path=vault_path,
                            db=db
                        )
                        
                        target_path = target_folder / note_path.name
                        if target_path.exists():
                            # Generar nombre único
                            counter = 1
                            while target_path.exists():
                                name_parts = note_path.stem, f"_{counter}", note_path.suffix
                                target_path = target_folder / "".join(name_parts)
                                counter += 1
                        
                        shutil.move(str(note_path), str(target_path))
                        
                        # Actualizar en ChromaDB
                        db.update_note_category(target_path, target_category, folder_name)
                        
                        console.print(f"✅ [green]Movido: {note_path.name} → {target_category}/{folder_name}/[/green]")
                    else:
                        console.print(f"📋 [dim]Simulación: {note_path.name} → {category}/{folder_name}/[/dim]")
                else:
                    console.print(f"❌ [red]Error al clasificar: {note_path.name}[/red]")
                    results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
                
            except Exception as e:
                console.print(f"❌ [red]Error procesando {note_path.name}: {e}[/red]")
                results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
            
            progress.advance(task)

    console.print(f"\n[bold]📊 Resumen de clasificación:[/bold]")
    console.print(results_table)
    
    # Mostrar estadísticas finales
    if execute:
        console.print(f"\n[bold]🎯 Estadísticas finales:[/bold]")
        final_distribution = db.get_category_distribution()
        for category, count in final_distribution.items():
            console.print(f"  • {category}: {count} notas")

def run_inbox_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Procesa notas del Inbox usando clasificación potenciada con ChromaDB.
    """
    # Usar el nuevo sistema de planificación
    run_inbox_classification_with_plan(vault_path, db, extra_prompt, model_name, execute)

def run_archive_refactor(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, excluded_paths: list[str]):
    """
    Refactoriza notas del Archive usando clasificación potenciada con ChromaDB.
    """
    # Usar el nuevo sistema de planificación
    run_archive_refactor_with_plan(vault_path, db, extra_prompt, model_name, execute, excluded_paths)

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
    """
    console.print(f"🔍 [bold]Análisis completo de nota activado[/bold]")
    console.print(f"📄 [dim]Analizando: {note_path.name}[/dim]")
    
    # 1. ANÁLISIS COMPLETO DE LA NOTA
    complete_analysis = analyze_note_completely(note_path, note_content, user_directive)
    
    # Mostrar información del análisis
    console.print(f"📊 [dim]Tags: {', '.join(complete_analysis['tags'][:5])}...[/dim]")
    console.print(f"📅 [dim]Última modificación: {complete_analysis['last_modified']}[/dim]")
    console.print(f"📝 [dim]Palabras: {complete_analysis['word_count']}[/dim]")
    
    # 2. ANÁLISIS SEMÁNTICO CON CHROMADB
    analyze_manager = AnalyzeManager(vault_path, db_path=Path(db.db_path).parent)
    enhanced_suggestion = analyze_manager.get_enhanced_classification_suggestion(note_path, note_content)
    
    semantic_category = enhanced_suggestion['suggested_category']
    semantic_confidence = enhanced_suggestion['confidence_score']
    semantic_reasoning = enhanced_suggestion['reasoning']
    
    console.print(f"🔍 [dim]ChromaDB: {semantic_category} (confianza: {semantic_confidence:.3f})[/dim]")
    
    # 3. PROMPT ENRIQUECIDO CON ANÁLISIS COMPLETO
    enriched_prompt = create_enriched_prompt(complete_analysis, user_directive)
    
    # 4. ANÁLISIS CON IA USANDO PROMPT ENRIQUECIDO
    console.print(f"🤖 [dim]Consultando IA con análisis completo...[/dim]")
    llm_result = classify_note_with_llm(note_content, enriched_prompt, model_name, system_prompt)
    
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
            'reasoning': semantic_reasoning,
            'analysis': complete_analysis
        }
    
    llm_category = llm_result.get('category', 'Unknown')
    llm_folder = llm_result.get('folder_name', 'Unknown')
    
    console.print(f"🤖 [dim]IA: {llm_category} → {llm_folder}[/dim]")
    
    # 5. CÁLCULO DE PESOS DINÁMICOS CON ANÁLISIS COMPLETO
    weights = _calculate_dynamic_weights_with_analysis(semantic_confidence, complete_analysis, db, vault_path)
    semantic_weight = weights['semantic']
    llm_weight = weights['llm']
    
    console.print(f"⚖️ [dim]Pesos dinámicos: ChromaDB={semantic_weight:.2f}, IA={llm_weight:.2f}[/dim]")
    
    # 6. DECISIÓN HÍBRIDA INTELIGENTE
    final_decision = _make_hybrid_decision_with_analysis(
        semantic_category, semantic_confidence, semantic_reasoning,
        llm_category, llm_folder, llm_result,
        semantic_weight, llm_weight,
        complete_analysis, user_directive
    )
    
    # Agregar análisis completo al resultado
    final_decision['analysis'] = complete_analysis
    
    return final_decision

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

def _calculate_dynamic_weights_with_analysis(semantic_confidence: float, analysis: dict, db: ChromaPARADatabase, vault_path: Path) -> dict:
    """
    Calcula pesos dinámicos considerando el análisis completo de la nota.
    Factores mejorados para máxima precisión.
    """
    # Base weights
    base_semantic = 0.6
    base_llm = 0.4
    
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
    
    # Factor 3: Tags de Obsidian (CRÍTICO)
    obsidian_tags = analysis.get('obsidian_tags', [])
    if obsidian_tags:
        # Si tiene tags específicos de PARA, boost muy significativo
        semantic_boost += 0.4
        llm_penalty += 0.2
        
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

def _make_hybrid_decision_with_analysis(semantic_category: str, semantic_confidence: float, semantic_reasoning: str,
                                       llm_category: str, llm_folder: str, llm_result: dict,
                                       semantic_weight: float, llm_weight: float,
                                       analysis: dict, user_directive: str) -> dict:
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
            folder_name = _generate_folder_name_from_content(analysis['content'], semantic_category)
        
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
    
    if semantic_score > llm_score:
        final_category = semantic_category
        final_folder = _generate_folder_name_from_content(analysis['content'], semantic_category)
        method = 'chromadb_weighted'
        reasoning = f"ChromaDB prevalece por peso ({semantic_weight:.2f}). {semantic_reasoning}"
    else:
        final_category = llm_category
        final_folder = llm_folder if llm_folder != 'Unknown' else _generate_folder_name_from_content(analysis['content'], llm_category)
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

def _generate_folder_name_from_content(content: str, category: str) -> str:
    """
    Genera un nombre de carpeta basado en el contenido y categoría.
    Asegura que siempre use la estructura numerada correcta.
    """
    import re
    
    # Mapeo de categorías a números correctos
    category_mapping = {
        'Projects': '01-Projects',
        'Areas': '02-Areas', 
        'Resources': '03-Resources',
        'Archive': '04-Archive',
        'Inbox': '00-Inbox'
    }
    
    # Asegurar que la categoría tenga el número correcto
    if category in category_mapping:
        category = category_mapping[category]
    
    # Extraer palabras clave del contenido
    lines = content.split('\n')
    title = ""
    
    # Buscar título en encabezados
    for line in lines[:10]:  # Solo las primeras 10 líneas
        if line.strip().startswith('# '):
            title = line.strip()[2:].strip()
            break
        elif line.strip().startswith('## '):
            title = line.strip()[3:].strip()
            break
    
    # Si no hay título, usar primera línea no vacía
    if not title:
        for line in lines:
            if line.strip() and not line.strip().startswith('---'):
                title = line.strip()
                break
    
    # Limpiar y procesar el título
    if title:
        # Remover caracteres especiales y tags
        title = re.sub(r'#\w+', '', title)  # Remover tags
        title = re.sub(r'[^\w\s\-]', '', title)  # Solo letras, números, espacios y guiones
        title = title.strip()
        
        # Limitar longitud
        if len(title) > 50:
            title = title[:47] + "..."
        
        # Si el título está vacío después de limpiar, usar categoría
        if not title:
            title = category.split('-')[1] if '-' in category else category
    
    # Si aún no hay título, usar categoría
    if not title:
        title = category.split('-')[1] if '-' in category else category
    
    return title

def _ensure_correct_para_structure(vault_path: Path) -> None:
    """
    Asegura que la estructura PARA tenga los números correctos.
    """
    correct_structure = {
        '00-Inbox': 'Inbox',
        '01-Projects': 'Projects', 
        '02-Areas': 'Areas',
        '03-Resources': 'Resources',
        '04-Archive': 'Archive'
    }
    
    for numbered_name, simple_name in correct_structure.items():
        numbered_path = vault_path / numbered_name
        simple_path = vault_path / simple_name
        
        # Si existe la carpeta sin número, renombrarla
        if simple_path.exists() and not numbered_path.exists():
            try:
                simple_path.rename(numbered_path)
                console.print(f"✅ [green]Renombrado: {simple_name} → {numbered_name}[/green]")
            except Exception as e:
                console.print(f"❌ [red]Error renombrando {simple_name}: {e}[/red]")
        
        # Si no existe ninguna, crear la numerada
        elif not numbered_path.exists() and not simple_path.exists():
            try:
                numbered_path.mkdir(parents=True, exist_ok=True)
                console.print(f"✅ [green]Creado: {numbered_name}[/green]")
            except Exception as e:
                console.print(f"❌ [red]Error creando {numbered_name}: {e}[/red]")

def _process_notes_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, source_folder_name: str, system_prompt: str, excluded_paths: list[str] = None):
    """
    Procesa la clasificación de notas con estructura PARA correcta.
    """
    # Asegurar estructura correcta antes de procesar
    _ensure_correct_para_structure(vault_path)
    
    # Resto del código existente...
    mode_text = "EXECUTE" if execute else "SIMULACIÓN"
    progress_title = "Procesando y moviendo notas..." if execute else "Simulando clasificación..."
    
    # Encontrar notas a procesar
    source_folder = vault_path / source_folder_name
    if not source_folder.exists():
        console.print(f"❌ [red]Carpeta fuente no encontrada: {source_folder_name}[/red]")
        return
    
    notes_to_process = []
    for note_path in source_folder.glob("*.md"):
        if excluded_paths and any(excluded in str(note_path) for excluded in excluded_paths):
            continue
        notes_to_process.append(note_path)
    
    if not notes_to_process:
        console.print(f"No hay notas para procesar en '{source_folder_name}'.")
        console.print("Esto puede ser normal si la carpeta está vacía o no contiene archivos .md")
        return
    
    console.print(f"🤖 Encontradas {len(notes_to_process)} notas para procesar en '{source_folder_name}'.")
    console.print(f"🤖 Usando modelo de IA: {model_name}")
    console.print(f"🔍 POTENCIADO CON CHROMADB para análisis semántico avanzado")
    console.print()
    
    if execute:
        console.print("Modo EXECUTE activado. Directiva del usuario: '{}'".format(extra_prompt))
    else:
        console.print("Modo SIMULACIÓN activado. Directiva del usuario: '{}'".format(extra_prompt))
    
    # Mostrar distribución actual
    console.print(f"\n📊 Distribución actual de categorías:")
    current_distribution = db.get_category_distribution()
    for category, count in current_distribution.items():
        console.print(f"  • {category}: {count} notas")
    
    # Tabla de resultados
    results_table = Table(title=f"Resultados de Clasificación - {mode_text}")
    results_table.add_column("Nota", style="cyan")
    results_table.add_column("Categoría", style="green")
    results_table.add_column("Carpeta", style="yellow")
    results_table.add_column("Confianza", style="blue")
    results_table.add_column("Método", style="magenta")
    results_table.add_column("Tags", style="cyan")
    results_table.add_column("Patrones", style="yellow")

    with Progress() as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        
        for note_path in notes_to_process:
            try:
                note_content = note_path.read_text(encoding='utf-8')
                
                # Usar clasificación potenciada con ChromaDB
                result = classify_note_with_enhanced_analysis(
                    note_content, note_path, extra_prompt, model_name, 
                    system_prompt, db, vault_path
                )
                
                if result:
                    category = result.get('category', 'Unknown')
                    folder_name = result.get('folder_name', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    method = result.get('method', 'unknown')
                    analysis = result.get('analysis', {})
                    
                    # Mostrar método de clasificación
                    method_display = {
                        'consensus': '✅ Consenso',
                        'chromadb_weighted': '🔍 ChromaDB',
                        'llm_weighted': '🤖 IA',
                        'chromadb_only': '🔍 Solo ChromaDB',
                        'llm_only': '🤖 Solo IA'
                    }.get(method, method)
                    
                    # Información de tags
                    tags = analysis.get('tags', [])
                    obsidian_tags = analysis.get('obsidian_tags', [])
                    tags_display = []
                    if obsidian_tags:
                        tags_display.extend(obsidian_tags)
                    tags_display.extend([t for t in tags[:3] if t not in obsidian_tags])
                    tags_text = ', '.join(tags_display[:5]) if tags_display else "N/A"
                    
                    # Información de patrones
                    patterns = []
                    if analysis.get('has_todos'):
                        patterns.append(f"📝{analysis.get('todo_count', 0)}")
                    if analysis.get('has_dates'):
                        patterns.append("📅")
                    if analysis.get('has_links'):
                        patterns.append(f"🔗{analysis.get('link_count', 0)}")
                    if analysis.get('has_attachments'):
                        patterns.append("📎")
                    
                    patterns_text = ' '.join(patterns) if patterns else "N/A"
                    
                    results_table.add_row(
                        note_path.name,
                        category,
                        folder_name,
                        f"{confidence:.3f}",
                        method_display,
                        tags_text,
                        patterns_text
                    )
                    
                    if execute:
                        # Asegurar que la categoría tenga el número correcto
                        category_mapping = {
                            'Projects': '01-Projects',
                            'Areas': '02-Areas', 
                            'Resources': '03-Resources',
                            'Archive': '04-Archive',
                            'Inbox': '00-Inbox'
                        }
                        
                        target_category = category_mapping.get(category, category)
                        target_folder = vault_path / target_category / folder_name
                        target_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Extraer scores del resultado
                        semantic_score = result.get('semantic_score', 0.0)
                        ai_score = result.get('ai_score', 0.0)
                        
                        # Registrar la creación de carpeta para el sistema de aprendizaje
                        register_folder_creation(
                            folder_name=folder_name,
                            category=category,
                            note_content=note_content,
                            note_path=note_path,
                            confidence=confidence,
                            method_used=method_display,
                            semantic_score=semantic_score,
                            ai_score=ai_score,
                            vault_path=vault_path,
                            db=db
                        )
                        
                        target_path = target_folder / note_path.name
                        if target_path.exists():
                            # Generar nombre único
                            counter = 1
                            while target_path.exists():
                                name_parts = note_path.stem, f"_{counter}", note_path.suffix
                                target_path = target_folder / "".join(name_parts)
                                counter += 1
                        
                        shutil.move(str(note_path), str(target_path))
                        
                        # Actualizar en ChromaDB
                        db.update_note_category(target_path, target_category, folder_name)
                        
                        console.print(f"✅ [green]Movido: {note_path.name} → {target_category}/{folder_name}/[/green]")
                    else:
                        console.print(f"📋 [dim]Simulación: {note_path.name} → {category}/{folder_name}/[/dim]")
                else:
                    console.print(f"❌ [red]Error al clasificar: {note_path.name}[/red]")
                    results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
                
            except Exception as e:
                console.print(f"❌ [red]Error procesando {note_path.name}: {e}[/red]")
                results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
            
            progress.advance(task)

    console.print(f"\n[bold]📊 Resumen de clasificación:[/bold]")
    console.print(results_table)
    
    # Mostrar estadísticas finales
    if execute:
        console.print(f"\n[bold]🎯 Estadísticas finales:[/bold]")
        final_distribution = db.get_category_distribution()
        for category, count in final_distribution.items():
            console.print(f"  • {category}: {count} notas")

def create_classification_plan(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, source_folder_name: str, system_prompt: str, excluded_paths: list[str] = None) -> dict:
    """
    Crea un plan detallado de clasificación antes de ejecutar.
    Analiza todas las notas y genera un reporte completo.
    """
    console.print(f"\n{'='*80}")
    console.print(f"[bold blue]📋 PLAN DE CLASIFICACIÓN - ANÁLISIS COMPLETO[/bold blue]")
    console.print(f"{'='*80}")
    
    # Asegurar estructura correcta
    _ensure_correct_para_structure(vault_path)
    
    # Encontrar notas a procesar
    source_folder = vault_path / source_folder_name
    if not source_folder.exists():
        console.print(f"❌ [red]Carpeta fuente no encontrada: {source_folder_name}[/red]")
        return {}
    
    notes_to_process = []
    for note_path in source_folder.glob("*.md"):
        if excluded_paths and any(excluded in str(note_path) for excluded in excluded_paths):
            continue
        notes_to_process.append(note_path)
    
    if not notes_to_process:
        console.print(f"📭 [yellow]No hay notas para procesar en '{source_folder_name}'.[/yellow]")
        return {}
    
    console.print(f"🔍 [bold]Analizando {len(notes_to_process)} notas para crear plan...[/bold]")
    console.print(f"🤖 [dim]Modelo de IA: {model_name}[/dim]")
    console.print(f"📝 [dim]Directiva: {extra_prompt}[/dim]")
    
    # Análisis completo de todas las notas
    analysis_results = []
    total_analysis = {
        'total_notes': len(notes_to_process),
        'by_category': {},
        'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
        'by_method': {'consensus': 0, 'chromadb': 0, 'llm': 0},
        'tags_found': set(),
        'patterns_found': {'todos': 0, 'dates': 0, 'links': 0, 'attachments': 0},
        'recent_notes': 0,
        'old_notes': 0,
        'complex_notes': 0,
        'simple_notes': 0
    }
    
    with Progress() as progress:
        task = progress.add_task("Analizando notas...", total=len(notes_to_process))
        
        for note_path in notes_to_process:
            try:
                note_content = note_path.read_text(encoding='utf-8')
                
                # Análisis completo de la nota
                result = classify_note_with_enhanced_analysis(
                    note_content, note_path, extra_prompt, model_name, 
                    system_prompt, db, vault_path
                )
                
                if result:
                    analysis_results.append({
                        'note_path': note_path,
                        'result': result,
                        'content': note_content
                    })
                    
                    # Actualizar estadísticas
                    category = result.get('category', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    method = result.get('method', 'unknown')
                    analysis = result.get('analysis', {})
                    
                    # Categorías
                    if category not in total_analysis['by_category']:
                        total_analysis['by_category'][category] = 0
                    total_analysis['by_category'][category] += 1
                    
                    # Confianza
                    if confidence > 0.7:
                        total_analysis['by_confidence']['high'] += 1
                    elif confidence > 0.4:
                        total_analysis['by_confidence']['medium'] += 1
                    else:
                        total_analysis['by_confidence']['low'] += 1
                    
                    # Método
                    if method == 'consensus':
                        total_analysis['by_method']['consensus'] += 1
                    elif 'chromadb' in method:
                        total_analysis['by_method']['chromadb'] += 1
                    else:
                        total_analysis['by_method']['llm'] += 1
                    
                    # Tags
                    tags = analysis.get('tags', [])
                    obsidian_tags = analysis.get('obsidian_tags', [])
                    total_analysis['tags_found'].update(tags)
                    total_analysis['tags_found'].update(obsidian_tags)
                    
                    # Patrones
                    if analysis.get('has_todos'):
                        total_analysis['patterns_found']['todos'] += 1
                    if analysis.get('has_dates'):
                        total_analysis['patterns_found']['dates'] += 1
                    if analysis.get('has_links'):
                        total_analysis['patterns_found']['links'] += 1
                    if analysis.get('has_attachments'):
                        total_analysis['patterns_found']['attachments'] += 1
                    
                    # Análisis temporal
                    recency = analysis.get('recency', 'moderate')
                    if recency in ['very_recent', 'recent']:
                        total_analysis['recent_notes'] += 1
                    elif recency in ['old', 'very_old']:
                        total_analysis['old_notes'] += 1
                    
                    # Complejidad
                    word_count = analysis.get('word_count', 0)
                    if word_count > 500:
                        total_analysis['complex_notes'] += 1
                    elif word_count < 50:
                        total_analysis['simple_notes'] += 1
                
            except Exception as e:
                console.print(f"❌ [red]Error analizando {note_path.name}: {e}[/red]")
            
            progress.advance(task)
    
    # Crear plan detallado
    plan = {
        'summary': total_analysis,
        'notes': analysis_results,
        'recommendations': generate_recommendations(total_analysis),
        'estimated_time': estimate_execution_time(len(notes_to_process)),
        'risk_assessment': assess_risks(total_analysis),
        'backup_recommended': True
    }
    
    # Mostrar plan detallado
    display_classification_plan(plan, source_folder_name)
    
    return plan

def generate_recommendations(analysis: dict) -> list:
    """
    Genera recomendaciones basadas en el análisis.
    """
    recommendations = []
    
    # Análisis de confianza
    low_confidence = analysis['by_confidence']['low']
    total_notes = analysis['total_notes']
    
    if low_confidence > total_notes * 0.3:
        recommendations.append({
            'type': 'warning',
            'message': f"⚠️ {low_confidence} notas tienen baja confianza. Considera revisar manualmente.",
            'action': 'review_low_confidence'
        })
    
    # Análisis de método
    consensus_count = analysis['by_method']['consensus']
    if consensus_count < total_notes * 0.5:
        recommendations.append({
            'type': 'info',
            'message': f"ℹ️ Solo {consensus_count}/{total_notes} notas tienen consenso entre sistemas.",
            'action': 'monitor_decisions'
        })
    
    # Análisis de patrones
    if analysis['patterns_found']['todos'] > 0:
        recommendations.append({
            'type': 'success',
            'message': f"✅ {analysis['patterns_found']['todos']} notas contienen TO-DOs (patrón fuerte de proyecto).",
            'action': 'none'
        })
    
    # Análisis temporal
    if analysis['recent_notes'] > total_notes * 0.7:
        recommendations.append({
            'type': 'info',
            'message': f"📅 {analysis['recent_notes']} notas son recientes (≤30 días).",
            'action': 'none'
        })
    
    return recommendations

def estimate_execution_time(notes_count: int) -> str:
    """
    Estima el tiempo de ejecución basado en el número de notas.
    """
    if notes_count < 10:
        return "1-2 minutos"
    elif notes_count < 50:
        return "3-5 minutos"
    elif notes_count < 100:
        return "5-10 minutos"
    else:
        return "10-15 minutos"

def assess_risks(analysis: dict) -> dict:
    """
    Evalúa los riesgos de la clasificación.
    """
    risks = {
        'level': 'low',
        'factors': []
    }
    
    total_notes = analysis['total_notes']
    
    # Riesgo por baja confianza
    low_confidence_ratio = analysis['by_confidence']['low'] / total_notes
    if low_confidence_ratio > 0.5:
        risks['level'] = 'high'
        risks['factors'].append(f"50%+ de notas con baja confianza ({low_confidence_ratio:.1%})")
    elif low_confidence_ratio > 0.3:
        risks['level'] = 'medium'
        risks['factors'].append(f"30%+ de notas con baja confianza ({low_confidence_ratio:.1%})")
    
    # Riesgo por falta de consenso
    consensus_ratio = analysis['by_method']['consensus'] / total_notes
    if consensus_ratio < 0.3:
        risks['level'] = 'high'
        risks['factors'].append(f"Poco consenso entre sistemas ({consensus_ratio:.1%})")
    
    # Riesgo por notas complejas
    complex_ratio = analysis['complex_notes'] / total_notes
    if complex_ratio > 0.7:
        risks['factors'].append(f"Muchas notas complejas ({complex_ratio:.1%})")
    
    return risks

def display_classification_plan(plan: dict, source_folder: str):
    """
    Muestra el plan de clasificación de forma detallada.
    """
    analysis = plan['summary']
    
    # Resumen ejecutivo
    console.print(f"\n[bold blue]📊 RESUMEN EJECUTIVO[/bold blue]")
    console.print(f"📁 Carpeta fuente: {source_folder}")
    console.print(f"📄 Total de notas: {analysis['total_notes']}")
    console.print(f"⏱️ Tiempo estimado: {plan['estimated_time']}")
    console.print(f"⚠️ Nivel de riesgo: {plan['risk_assessment']['level'].upper()}")
    
    # Distribución por categorías
    console.print(f"\n[bold green]📂 DISTRIBUCIÓN POR CATEGORÍAS[/bold green]")
    category_table = Table(show_header=True, header_style="bold magenta")
    category_table.add_column("Categoría", style="cyan")
    category_table.add_column("Cantidad", style="green")
    category_table.add_column("Porcentaje", style="yellow")
    
    for category, count in analysis['by_category'].items():
        percentage = (count / analysis['total_notes']) * 100
        category_table.add_row(category, str(count), f"{percentage:.1f}%")
    
    console.print(category_table)
    
    # Análisis de confianza
    console.print(f"\n[bold yellow]🎯 ANÁLISIS DE CONFIANZA[/bold yellow]")
    confidence_table = Table(show_header=True, header_style="bold magenta")
    confidence_table.add_column("Nivel", style="cyan")
    confidence_table.add_column("Cantidad", style="green")
    confidence_table.add_column("Porcentaje", style="yellow")
    
    for level, count in analysis['by_confidence'].items():
        percentage = (count / analysis['total_notes']) * 100
        level_display = {'high': 'Alta (>0.7)', 'medium': 'Media (0.4-0.7)', 'low': 'Baja (<0.4)'}[level]
        confidence_table.add_row(level_display, str(count), f"{percentage:.1f}%")
    
    console.print(confidence_table)
    
    # Métodos de clasificación
    console.print(f"\n[bold purple]🤖 MÉTODOS DE CLASIFICACIÓN[/bold purple]")
    method_table = Table(show_header=True, header_style="bold magenta")
    method_table.add_column("Método", style="cyan")
    method_table.add_column("Cantidad", style="green")
    method_table.add_column("Porcentaje", style="yellow")
    
    for method, count in analysis['by_method'].items():
        percentage = (count / analysis['total_notes']) * 100
        method_display = {
            'consensus': '✅ Consenso',
            'chromadb': '🔍 ChromaDB',
            'llm': '🤖 IA'
        }[method]
        method_table.add_row(method_display, str(count), f"{percentage:.1f}%")
    
    console.print(method_table)
    
    # Patrones detectados
    console.print(f"\n[bold orange]🔍 PATRONES DETECTADOS[/bold orange]")
    patterns_table = Table(show_header=True, header_style="bold magenta")
    patterns_table.add_column("Patrón", style="cyan")
    patterns_table.add_column("Cantidad", style="green")
    patterns_table.add_column("Porcentaje", style="yellow")
    
    for pattern, count in analysis['patterns_found'].items():
        percentage = (count / analysis['total_notes']) * 100
        pattern_display = {
            'todos': '📝 TO-DOs',
            'dates': '📅 Fechas',
            'links': '🔗 Enlaces',
            'attachments': '📎 Adjuntos'
        }[pattern]
        patterns_table.add_row(pattern_display, str(count), f"{percentage:.1f}%")
    
    console.print(patterns_table)
    
    # Tags más comunes
    if analysis['tags_found']:
        console.print(f"\n[bold cyan]🏷️ TAGS MÁS COMUNES[/bold cyan]")
        tags_list = list(analysis['tags_found'])[:10]  # Top 10
        console.print(f"  {', '.join(tags_list)}")
    
    # Análisis temporal
    console.print(f"\n[bold blue]📅 ANÁLISIS TEMPORAL[/bold blue]")
    console.print(f"  📅 Notas recientes (≤30 días): {analysis['recent_notes']}")
    console.print(f"  📅 Notas antiguas (>90 días): {analysis['old_notes']}")
    console.print(f"  📝 Notas complejas (>500 palabras): {analysis['complex_notes']}")
    console.print(f"  📝 Notas simples (<50 palabras): {analysis['simple_notes']}")
    
    # Recomendaciones
    if plan['recommendations']:
        console.print(f"\n[bold green]💡 RECOMENDACIONES[/bold green]")
        for rec in plan['recommendations']:
            icon = {'warning': '⚠️', 'info': 'ℹ️', 'success': '✅'}[rec['type']]
            console.print(f"  {icon} {rec['message']}")
    
    # Evaluación de riesgos
    if plan['risk_assessment']['factors']:
        console.print(f"\n[bold red]⚠️ EVALUACIÓN DE RIESGOS[/bold red]")
        risk_level = plan['risk_assessment']['level']
        risk_color = {'low': 'green', 'medium': 'yellow', 'high': 'red'}[risk_level]
        console.print(f"  Nivel: [{risk_color}]{risk_level.upper()}[/{risk_color}]")
        for factor in plan['risk_assessment']['factors']:
            console.print(f"  • {factor}")
    
    # Backup recomendado
    if plan['backup_recommended']:
        console.print(f"\n[bold blue]💾 BACKUP[/bold blue]")
        console.print(f"  🔒 Se recomienda crear backup antes de ejecutar")
        console.print(f"  📁 Los backups se guardan en ./backups/")

def execute_classification_plan(plan: dict, vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, source_folder_name: str, system_prompt: str) -> bool:
    """
    Ejecuta el plan de clasificación con backup automático.
    """
    from paralib.utils import auto_backup_if_needed
    
    logger.info(f"[EXECUTE-PLAN] Iniciando ejecución de plan de clasificación")
    logger.info(f"[EXECUTE-PLAN] Vault: {vault_path}, Notas: {plan['summary']['total_notes']}, Riesgo: {plan['risk_assessment']['level']}")
    
    console.print(f"\n{'='*80}")
    console.print(f"[bold green]🚀 EJECUTANDO PLAN DE CLASIFICACIÓN[/bold green]")
    console.print(f"{'='*80}")
    
    # Crear backup automático
    backup_reason = f"pre-classification-{source_folder_name}" if source_folder_name else "pre-full-reclassification"
    console.print(f"🔒 [bold]Creando backup automático...[/bold]")
    backup_success = auto_backup_if_needed(vault_path, reason=backup_reason)
    
    if not backup_success:
        logger.error(f"[EXECUTE-PLAN] Error al crear backup: {backup_reason}")
        console.print(f"❌ [red]Error al crear backup. ¿Deseas continuar?[/red]")
        if not Confirm.ask("¿Continuar sin backup?", default=False):
            logger.warning(f"[EXECUTE-PLAN] Ejecución cancelada por el usuario (sin backup)")
            console.print(f"❌ [red]Ejecución cancelada por el usuario.[/red]")
            return False
    
    # Confirmar ejecución
    console.print(f"\n[bold yellow]⚠️ CONFIRMACIÓN FINAL[/bold yellow]")
    console.print(f"📄 Notas a procesar: {plan['summary']['total_notes']}")
    console.print(f"⏱️ Tiempo estimado: {plan['estimated_time']}")
    console.print(f"⚠️ Nivel de riesgo: {plan['risk_assessment']['level'].upper()}")
    
    try:
        if not Confirm.ask("¿Ejecutar la clasificación?", default=False):
            logger.warning(f"[EXECUTE-PLAN] Ejecución cancelada por el usuario")
            console.print(f"❌ [red]Ejecución cancelada por el usuario.[/red]")
            return False
    except Exception as e:
        logger.error(f"[EXECUTE-PLAN] Error en la confirmación: {e}")
        console.print(f"❌ [red]Error en la confirmación: {e}[/red]")
        console.print(f"❌ [red]Ejecución cancelada.[/red]")
        return False
    
    # Ejecutar clasificación
    logger.info(f"[EXECUTE-PLAN] Confirmación aceptada, iniciando clasificación")
    console.print(f"\n[bold green]✅ Ejecutando clasificación...[/bold green]")
    
    # Si es re-clasificación total (source_folder_name vacío), procesar todas las notas del plan
    if not source_folder_name:
        logger.info(f"[EXECUTE-PLAN] Modo re-clasificación total, procesando {len(plan['notes'])} notas")
        # Procesar las notas del plan directamente
        notes_to_process = [note_data['note_path'] for note_data in plan['notes']]
        
        # Usar la lógica de procesamiento pero con la lista de notas del plan
        _process_notes_from_list(
            vault_path=vault_path,
            db=db,
            extra_prompt=extra_prompt,
            model_name=model_name,
            execute=True,
            notes_to_process=notes_to_process,
            system_prompt=system_prompt
        )
    else:
        logger.info(f"[EXECUTE-PLAN] Modo carpeta específica: {source_folder_name}")
        # Usar la función existente para carpeta específica
        _process_notes_classification(
            vault_path=vault_path,
            db=db,
            extra_prompt=extra_prompt,
            model_name=model_name,
            execute=True,
            source_folder_name=source_folder_name,
            system_prompt=system_prompt
        )
    
    logger.info(f"[EXECUTE-PLAN] Clasificación completada exitosamente")
    console.print(f"\n[bold green]🎉 ¡Clasificación completada exitosamente![/bold green]")
    console.print(f"💾 Backup disponible en ./backups/ si fue necesario")
    
    return True

def run_inbox_classification_with_plan(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Procesa notas del Inbox con plan detallado antes de ejecutar.
    """
    console.print(f"\n{'='*60}")
    console.print(f"[bold blue]📥 PROCESAMIENTO DE INBOX CON PLAN DETALLADO[/bold blue]")
    console.print(f"{'='*60}")
    
    # Crear plan detallado
    plan = create_classification_plan(
        vault_path=vault_path,
        db=db,
        extra_prompt=extra_prompt,
        model_name=model_name,
        source_folder_name="00-Inbox",
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT
    )
    
    if not plan:
        console.print(f"❌ [red]No se pudo crear el plan de clasificación.[/red]")
        return
    
    # Si es modo execute, ejecutar el plan
    if execute:
        execute_classification_plan(
            plan=plan,
            vault_path=vault_path,
            db=db,
            extra_prompt=extra_prompt,
            model_name=model_name,
            source_folder_name="00-Inbox",
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT
        )
    else:
        console.print(f"\n[bold yellow]📋 MODO SIMULACIÓN: Plan mostrado, no se ejecutaron cambios.[/bold yellow]")
        console.print(f"💡 Usa --execute para aplicar los cambios.")

def run_archive_refactor_with_plan(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, excluded_paths: list[str]):
    """
    Refactoriza notas del Archive con plan detallado antes de ejecutar.
    """
    console.print(f"\n{'='*60}")
    console.print(f"[bold blue]📦 REFACTORIZACIÓN DE ARCHIVE CON PLAN DETALLADO[/bold blue]")
    console.print(f"{'='*60}")
    
    # Crear plan detallado
    plan = create_classification_plan(
        vault_path=vault_path,
        db=db,
        extra_prompt=extra_prompt,
        model_name=model_name,
        source_folder_name="04-Archive",
        system_prompt=REFACTOR_SYSTEM_PROMPT,
        excluded_paths=excluded_paths
    )
    
    if not plan:
        console.print(f"❌ [red]No se pudo crear el plan de clasificación.[/red]")
        return
    
    # Si es modo execute, ejecutar el plan
    if execute:
        execute_classification_plan(
            plan=plan,
            vault_path=vault_path,
            db=db,
            extra_prompt=extra_prompt,
            model_name=model_name,
            source_folder_name="04-Archive",
            system_prompt=REFACTOR_SYSTEM_PROMPT
        )
    else:
        console.print(f"\n[bold yellow]📋 MODO SIMULACIÓN: Plan mostrado, no se ejecutaron cambios.[/bold yellow]")
        console.print(f"💡 Usa --execute para aplicar los cambios.") 

def register_folder_creation(folder_name: str, category: str, note_content: str, note_path: Path, 
                           confidence: float, method_used: str, semantic_score: float, ai_score: float,
                           vault_path: Path, db: ChromaPARADatabase):
    """
    Registra la creación de una carpeta para el sistema de aprendizaje.
    """
    try:
        # Extraer información de la nota
        note_tags = []
        note_patterns = {}
        
        # Extraer tags del contenido
        import re
        content_tags = re.findall(r'#([a-zA-Z0-9_]+)', note_content)
        note_tags.extend(content_tags)
        
        # Extraer patrones básicos
        note_patterns = {
            'todos': bool(re.search(r'- \[ \].*|#todo|#TODO|TODO:|todo:', note_content, re.IGNORECASE)),
            'dates': bool(re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', note_content)),
            'links': bool(re.search(r'\[\[([^\]]+)\]\]', note_content)),
            'attachments': bool(re.search(r'!\[.*?\]\(([^)]+)\)', note_content)),
            'headers': bool(re.search(r'^#{1,6}\s+', note_content, re.MULTILINE)),
            'lists': bool(re.search(r'^[-*+]\s+', note_content, re.MULTILINE)),
            'code_blocks': bool(re.search(r'```', note_content)),
            'tables': bool(re.search(r'\|.*\|', note_content)),
            'quotes': bool(re.search(r'^>\s+', note_content, re.MULTILINE)),
            'emphasis': bool(re.search(r'\*\*.*\*\*|__.*__', note_content)),
            'strikethroughs': bool(re.search(r'~~.*~~', note_content)),
            'footnotes': bool(re.search(r'\[\^.*\]', note_content))
        }
        
        # Crear información de carpeta
        folder_info = {
            'folder_name': folder_name,
            'category': category,
            'note_content': note_content[:500],  # Primeros 500 caracteres
            'note_tags': note_tags,
            'note_patterns': note_patterns,
            'confidence': confidence,
            'method_used': method_used,
            'semantic_score': semantic_score,
            'ai_score': ai_score
        }
        
        # Inicializar sistema de aprendizaje si no existe
        learning_system = PARA_Learning_System(db, vault_path)
        
        # Registrar la creación de carpeta (sin feedback del usuario por ahora)
        # El feedback se puede agregar después usando el comando folder_feedback
        learning_system._save_folder_feedback(folder_info, "pending", "Carpeta creada automáticamente")
        
        console.print(f"[dim]📁 Carpeta '{folder_name}' registrada para aprendizaje[/dim]")
        
    except Exception as e:
        console.print(f"[dim]Error registrando carpeta para aprendizaje: {e}[/dim]")

def run_full_reclassification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Reclasifica todas las notas del vault usando el sistema híbrido y de aprendizaje.
    Sigue exactamente la misma lógica, experiencia de usuario y robustez que el flujo de clasificación inicial.
    """
    logger.info(f"[RECLASSIFY-ALL] Iniciando re-clasificación total del vault: {vault_path}")
    logger.info(f"[RECLASSIFY-ALL] Modelo: {model_name}, Directiva: {extra_prompt}, Execute: {execute}")
    
    console.print(f"\n{'='*60}")
    console.print(f"[bold blue]🔄 RECLASIFICACIÓN TOTAL DEL VAULT[/bold blue]")
    console.print(f"{'='*60}")
    
    # Asegurar estructura correcta
    _ensure_correct_para_structure(vault_path)
    
    # Recorrer todas las notas del vault
    all_notes = list(vault_path.rglob("*.md"))
    if not all_notes:
        console.print("[yellow]No se encontraron notas en el vault.[/yellow]")
        return
    
    console.print(f"🔍 [bold]Analizando {len(all_notes)} notas para crear plan de reclasificación...[/bold]")
    console.print(f"🤖 [dim]Modelo de IA: {model_name}[/dim]")
    console.print(f"📝 [dim]Directiva: {extra_prompt}[/dim]")
    
    # Procesar cada nota: archivar diarias vacías primero
    notes_to_process = []
    archived_dailies = 0
    
    for note_path in all_notes:
        try:
            content = note_path.read_text(encoding="utf-8").strip()
            is_daily = note_path.name.startswith("20") and note_path.name.endswith(".md")
            
            if is_daily and (not content or len(content) < 10):
                # Archivar automáticamente
                target_folder = vault_path / "04-Archive" / "Daily Notes"
                target_folder.mkdir(parents=True, exist_ok=True)
                target_path = target_folder / note_path.name
                note_path.replace(target_path)
                db.update_note_category(target_path, "04-Archive", "Daily Notes")
                console.print(f"[dim]🗃️ Nota diaria vacía archivada: {note_path.name}[/dim]")
                archived_dailies += 1
                continue
            
            notes_to_process.append(note_path)
            
        except Exception as e:
            console.print(f"[red]Error leyendo {note_path}: {e}[/red]")
            continue
    
    if archived_dailies > 0:
        console.print(f"[green]✅ {archived_dailies} notas diarias vacías archivadas automáticamente.[/green]")
    
    if not notes_to_process:
        console.print("[yellow]No hay notas para reclasificar después del filtrado.[/yellow]")
        return
    
    # Análisis completo de todas las notas para crear plan
    analysis_results = []
    total_analysis = {
        'total_notes': len(notes_to_process),
        'by_category': {},
        'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
        'by_method': {'consensus': 0, 'chromadb': 0, 'llm': 0},
        'tags_found': set(),
        'patterns_found': {'todos': 0, 'dates': 0, 'links': 0, 'attachments': 0},
        'recent_notes': 0,
        'old_notes': 0,
        'complex_notes': 0,
        'simple_notes': 0
    }
    
    system_prompt = get_profile()
    
    with Progress() as progress:
        task = progress.add_task("Analizando notas...", total=len(notes_to_process))
        
        for note_path in notes_to_process:
            try:
                note_content = note_path.read_text(encoding='utf-8')
                
                # Análisis completo de la nota
                result = classify_note_with_enhanced_analysis(
                    note_content, note_path, extra_prompt, model_name, 
                    system_prompt, db, vault_path
                )
                
                if result:
                    analysis_results.append({
                        'note_path': note_path,
                        'result': result,
                        'content': note_content
                    })
                    
                    # Actualizar estadísticas
                    category = result.get('category', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    method = result.get('method', 'unknown')
                    analysis = result.get('analysis', {})
                    
                    # Categorías
                    if category not in total_analysis['by_category']:
                        total_analysis['by_category'][category] = 0
                    total_analysis['by_category'][category] += 1
                    
                    # Confianza
                    if confidence > 0.7:
                        total_analysis['by_confidence']['high'] += 1
                    elif confidence > 0.4:
                        total_analysis['by_confidence']['medium'] += 1
                    else:
                        total_analysis['by_confidence']['low'] += 1
                    
                    # Método
                    if method == 'consensus':
                        total_analysis['by_method']['consensus'] += 1
                    elif 'chromadb' in method:
                        total_analysis['by_method']['chromadb'] += 1
                    else:
                        total_analysis['by_method']['llm'] += 1
                    
                    # Tags
                    tags = analysis.get('tags', [])
                    obsidian_tags = analysis.get('obsidian_tags', [])
                    total_analysis['tags_found'].update(tags)
                    total_analysis['tags_found'].update(obsidian_tags)
                    
                    # Patrones
                    if analysis.get('has_todos'):
                        total_analysis['patterns_found']['todos'] += 1
                    if analysis.get('has_dates'):
                        total_analysis['patterns_found']['dates'] += 1
                    if analysis.get('has_links'):
                        total_analysis['patterns_found']['links'] += 1
                    if analysis.get('has_attachments'):
                        total_analysis['patterns_found']['attachments'] += 1
                    
                    # Análisis temporal
                    recency = analysis.get('recency', 'moderate')
                    if recency in ['very_recent', 'recent']:
                        total_analysis['recent_notes'] += 1
                    elif recency in ['old', 'very_old']:
                        total_analysis['old_notes'] += 1
                    
                    # Complejidad
                    word_count = analysis.get('word_count', 0)
                    if word_count > 500:
                        total_analysis['complex_notes'] += 1
                    elif word_count < 50:
                        total_analysis['simple_notes'] += 1
                
            except Exception as e:
                console.print(f"❌ [red]Error analizando {note_path.name}: {e}[/red]")
            
            progress.advance(task)
    
    # Crear plan detallado
    plan = {
        'summary': total_analysis,
        'notes': analysis_results,
        'recommendations': generate_recommendations(total_analysis),
        'estimated_time': estimate_execution_time(len(notes_to_process)),
        'risk_assessment': assess_risks(total_analysis),
        'backup_recommended': True
    }
    
    # Mostrar plan detallado
    display_classification_plan(plan, "TODO EL VAULT")
    
    # Ejecutar plan con confirmación (igual que en classify)
    if execute:
        success = execute_classification_plan(
            plan=plan,
            vault_path=vault_path,
            db=db,
            extra_prompt=extra_prompt,
            model_name=model_name,
            source_folder_name="",  # Vacío para procesar todo el vault
            system_prompt=system_prompt
        )
        
        if success:
            console.print("[green]✅ Reclasificación completa. Puedes ver la evolución en el panel de aprendizaje con:[/green]")
            console.print("[bold cyan]python para_cli.py learn --dashboard[/bold cyan]")
        else:
            console.print("[red]❌ Reclasificación cancelada o falló.[/red]")
            return False
    else:
        console.print("[yellow]Modo simulación: No se aplicaron cambios permanentes.[/yellow]")
        console.print("[green]Para aplicar los cambios, ejecuta con --execute[/green]")
    
    return True

def _process_notes_from_list(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, notes_to_process: list[Path], system_prompt: str):
    """
    Procesa una lista específica de notas usando la misma lógica que _process_notes_classification.
    """
    logger.info(f"[PROCESS-LIST] Iniciando procesamiento de {len(notes_to_process)} notas")
    logger.info(f"[PROCESS-LIST] Vault: {vault_path}, Modelo: {model_name}, Execute: {execute}")
    
    if not check_ollama_model(model_name):
        logger.error(f"[PROCESS-LIST] Modelo de IA no disponible: {model_name}")
        return

    mode_text = "EXECUTE" if execute else "SIMULACIÓN"
    progress_title = "Procesando y moviendo notas..." if execute else "Simulando clasificación..."
    
    if not notes_to_process:
        logger.warning(f"[PROCESS-LIST] No hay notas para procesar")
        console.print(f"No hay notas para procesar.")
        return
    
    console.print(f"🤖 Encontradas {len(notes_to_process)} notas para procesar.")
    console.print(f"🤖 Usando modelo de IA: {model_name}")
    console.print(f"🔍 POTENCIADO CON CHROMADB para análisis semántico avanzado")
    console.print()
    
    if execute:
        console.print("Modo EXECUTE activado. Directiva del usuario: '{}'".format(extra_prompt))
    else:
        console.print("Modo SIMULACIÓN activado. Directiva del usuario: '{}'".format(extra_prompt))
    
    # Mostrar distribución actual
    console.print(f"\n📊 Distribución actual de categorías:")
    current_distribution = db.get_category_distribution()
    for category, count in current_distribution.items():
        console.print(f"  • {category}: {count} notas")
    
    # Tabla de resultados
    results_table = Table(title=f"Resultados de Clasificación - {mode_text}")
    results_table.add_column("Nota", style="cyan")
    results_table.add_column("Categoría", style="green")
    results_table.add_column("Carpeta", style="yellow")
    results_table.add_column("Confianza", style="blue")
    results_table.add_column("Método", style="magenta")
    results_table.add_column("Tags", style="cyan")
    results_table.add_column("Patrones", style="yellow")

    processed_count = 0
    error_count = 0

    with Progress() as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        
        for note_path in notes_to_process:
            try:
                note_content = note_path.read_text(encoding='utf-8')
                
                # Usar clasificación potenciada con ChromaDB
                result = classify_note_with_enhanced_analysis(
                    note_content, note_path, extra_prompt, model_name, 
                    system_prompt, db, vault_path
                )
                
                if result:
                    category = result.get('category', 'Unknown')
                    folder_name = result.get('folder_name', 'Unknown')
                    confidence = result.get('confidence', 0.0)
                    method = result.get('method', 'unknown')
                    analysis = result.get('analysis', {})
                    
                    logger.debug(f"[PROCESS-LIST] Clasificado: {note_path.name} -> {category}/{folder_name} (conf: {confidence:.3f})")
                    
                    # Mostrar método de clasificación
                    method_display = {
                        'consensus': '✅ Consenso',
                        'chromadb_weighted': '🔍 ChromaDB',
                        'llm_weighted': '🤖 IA',
                        'chromadb_only': '🔍 Solo ChromaDB',
                        'llm_only': '🤖 Solo IA'
                    }.get(method, method)
                    
                    # Información de tags
                    tags = analysis.get('tags', [])
                    obsidian_tags = analysis.get('obsidian_tags', [])
                    tags_display = []
                    if obsidian_tags:
                        tags_display.extend(obsidian_tags)
                    tags_display.extend([t for t in tags[:3] if t not in obsidian_tags])
                    tags_text = ', '.join(tags_display[:5]) if tags_display else "N/A"
                    
                    # Información de patrones
                    patterns = []
                    if analysis.get('has_todos'):
                        patterns.append(f"📝{analysis.get('todo_count', 0)}")
                    if analysis.get('has_dates'):
                        patterns.append("📅")
                    if analysis.get('has_links'):
                        patterns.append(f"🔗{analysis.get('link_count', 0)}")
                    if analysis.get('has_attachments'):
                        patterns.append("📎")
                    
                    patterns_text = ' '.join(patterns) if patterns else "N/A"
                    
                    results_table.add_row(
                        note_path.name,
                        category,
                        folder_name,
                        f"{confidence:.3f}",
                        method_display,
                        tags_text,
                        patterns_text
                    )
                    
                    if execute:
                        # Asegurar que la categoría tenga el número correcto
                        category_mapping = {
                            'Projects': '01-Projects',
                            'Areas': '02-Areas', 
                            'Resources': '03-Resources',
                            'Archive': '04-Archive',
                            'Inbox': '00-Inbox'
                        }
                        
                        target_category = category_mapping.get(category, category)
                        target_folder = vault_path / target_category / folder_name
                        target_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Extraer scores del resultado
                        semantic_score = result.get('semantic_score', 0.0)
                        ai_score = result.get('ai_score', 0.0)
                        
                        # Registrar la creación de carpeta para el sistema de aprendizaje
                        register_folder_creation(
                            folder_name=folder_name,
                            category=category,
                            note_content=note_content,
                            note_path=note_path,
                            confidence=confidence,
                            method_used=method_display,
                            semantic_score=semantic_score,
                            ai_score=ai_score,
                            vault_path=vault_path,
                            db=db
                        )
                        
                        target_path = target_folder / note_path.name
                        if target_path.exists():
                            # Generar nombre único
                            counter = 1
                            while target_path.exists():
                                name_parts = note_path.stem, f"_{counter}", note_path.suffix
                                target_path = target_folder / "".join(name_parts)
                                counter += 1
                        
                        shutil.move(str(note_path), str(target_path))
                        
                        # Actualizar en ChromaDB
                        db.update_note_category(target_path, target_category, folder_name)
                        
                        logger.info(f"[PROCESS-LIST] Movido: {note_path.name} -> {target_category}/{folder_name}/")
                        console.print(f"✅ [green]Movido: {note_path.name} → {target_category}/{folder_name}/[/green]")
                    else:
                        console.print(f"📋 [dim]Simulación: {note_path.name} → {category}/{folder_name}/[/dim]")
                    
                    processed_count += 1
                else:
                    logger.error(f"[PROCESS-LIST] Error al clasificar: {note_path.name}")
                    console.print(f"❌ [red]Error al clasificar: {note_path.name}[/red]")
                    results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
                    error_count += 1
                
            except Exception as e:
                logger.error(f"[PROCESS-LIST] Error procesando {note_path.name}: {e}")
                console.print(f"❌ [red]Error procesando {note_path.name}: {e}[/red]")
                results_table.add_row(note_path.name, "ERROR", "ERROR", "0.000", "ERROR", "N/A", "N/A")
                error_count += 1
            
            progress.advance(task)

    logger.info(f"[PROCESS-LIST] Procesamiento completado. Procesadas: {processed_count}, Errores: {error_count}")
    console.print(f"\n[bold]📊 Resumen de clasificación:[/bold]")
    console.print(results_table)
    
    # Mostrar estadísticas finales
    if execute:
        console.print(f"\n[bold]🎯 Estadísticas finales:[/bold]")
        final_distribution = db.get_category_distribution()
        for category, count in final_distribution.items():
            console.print(f"  • {category}: {count} notas")
        
        logger.info(f"[PROCESS-LIST] Distribución final: {final_distribution}")

class PARAOrganizer:
    """Organizador principal de PARA que coordina todas las operaciones."""
    
    def __init__(self):
        self.config = load_config("para_config.default.json")
        self.model_name = self.config.get("model_name", "llama3.2:3b")
        # Inicializar ChromaDB sin db_path específico (usará el por defecto)
        try:
            self.db = ChromaPARADatabase()
        except TypeError:
            # Si requiere db_path, usar el por defecto
            from paralib.vault import find_vault
            vault = find_vault()
            if vault:
                db_path = vault / ".para_db" / "chroma"
                self.db = ChromaPARADatabase(db_path=str(db_path))
            else:
                # Fallback a directorio temporal
                import tempfile
                temp_dir = Path(tempfile.gettempdir()) / "para_chroma"
                self.db = ChromaPARADatabase(db_path=str(temp_dir))
    
    def reclassify_all_notes(self, vault_path: str = None, create_backup: bool = True, auto_confirm: bool = False):
        """Reclasifica todas las notas del vault usando el sistema híbrido y de aprendizaje."""
        
        # Obtener vault usando el nuevo sistema centralizado
        vault = vault_selector.get_vault(vault_path)
        if not vault:
            console.print("[red]❌ No se encontró ningún vault de Obsidian.[/red]")
            return False
        
        vault_path = Path(vault)
        
        # Crear backup si se solicita
        if create_backup:
            from paralib.utils import auto_backup_if_needed
            if not auto_backup_if_needed(vault_path, "pre-reclassification"):
                console.print("[yellow]⚠️ No se pudo crear backup automático. ¿Continuar?[/yellow]")
                if not Confirm.ask("¿Continuar sin backup?"):
                    return False
        
        # Configurar confirmación automática si se solicita
        if auto_confirm:
            # Modificar temporalmente la función Confirm.ask para que siempre devuelva True
            import paralib.organizer
            original_ask = paralib.organizer.Confirm.ask
            paralib.organizer.Confirm.ask = lambda *args, **kwargs: True
        
        try:
            # Usar la función existente run_full_reclassification que procesa TODAS las notas
            success = run_full_reclassification(
                vault_path=vault_path,
                db=self.db,
                extra_prompt="Reclasificar todas las notas del vault usando el sistema híbrido completo",
                model_name=self.model_name,
                execute=True
            )
            
            if success:
                console.print("[green]✅ Reclasificación completa exitosa![/green]")
                return True
            else:
                console.print("[red]❌ Reclasificación falló o fue cancelada.[/red]")
                return False
                
        except Exception as e:
            logger.error(f"Error en reclassify_all_notes: {e}")
            console.print(f"[red]❌ Error durante la reclasificación: {e}[/red]")
            return False
        finally:
            # Restaurar Confirm.ask si se modificó
            if auto_confirm:
                paralib.organizer.Confirm.ask = original_ask
    
    def classify_note(self, note_path: str, auto_confirm: bool = False, create_backup: bool = True):
        """Clasifica una nota específica."""
        
        # Obtener vault usando el nuevo sistema centralizado
        vault = vault_selector.get_vault()
        if not vault:
            console.print("[red]❌ No se encontró ningún vault de Obsidian.[/red]")
            return False
        
        vault_path = Path(vault)
        note_path = Path(note_path)
        
        # Crear backup si se solicita
        if create_backup:
            from paralib.utils import auto_backup_if_needed
            if not auto_backup_if_needed(vault_path, "pre-classification"):
                console.print("[yellow]⚠️ No se pudo crear backup automático. ¿Continuar?[/yellow]")
                if not Confirm.ask("¿Continuar sin backup?"):
                    return False
        
        # Usar la función existente para clasificar una nota
        system_prompt = get_profile()
        result = classify_note_with_enhanced_analysis(
            note_path.read_text(encoding='utf-8'),
            note_path,
            "Clasificar esta nota usando el sistema híbrido",
            self.model_name,
            system_prompt,
            self.db,
            vault_path
        )
        
        if result:
            console.print(f"[green]✅ Nota clasificada: {result.get('category')}/{result.get('folder_name')}[/green]")
            return True
        else:
            console.print("[red]❌ Error clasificando la nota.[/red]")
            return False
    
    def plan_classification(self, path: str):
        """Genera un plan de clasificación para una nota o carpeta."""
        
        # Obtener vault usando el nuevo sistema centralizado
        vault = vault_selector.get_vault()
        if not vault:
            console.print("[red]❌ No se encontró ningún vault de Obsidian.[/red]")
            return False
        
        vault_path = Path(vault)
        path = Path(path)
        
        # Usar la función existente para crear plan
        system_prompt = get_profile()
        plan = create_classification_plan(
            vault_path=vault_path,
            db=self.db,
            extra_prompt="Crear plan de clasificación",
            model_name=self.model_name,
            source_folder_name=path.name if path.is_dir() else "",
            system_prompt=system_prompt
        )
        
        return plan