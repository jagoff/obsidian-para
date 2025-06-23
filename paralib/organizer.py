"""
paralib/organizer.py

Contiene la lógica principal para el proceso de organización de notas.
"""
#
# MIT License
#
# Copyright (c) 2024 Fernando Ferrari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from .db import ChromaPARADatabase
import ollama
import json
import shutil
from paralib.similarity import normalize_name
from paralib.vault import (
    extract_structured_features_from_note, 
    score_para_classification, 
    load_para_config
)
from paralib.analyze_manager import AnalyzeManager
from rich.table import Table
from rich import box

console = Console()

CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources) system organizer with deep understanding of productivity and knowledge management. Your task is to classify a given NEW, UNPROCESSED note from an Inbox into one of the three active PARA categories and suggest a folder name for it.

Here are the detailed definitions with examples:

**PROJECTS** - A series of tasks linked to a goal with a deadline:
- Examples: "Develop New App", "Plan Vacation", "Complete Q3 Report", "Renovate Kitchen", "Write Book", "Launch Website"
- Key indicators: Action verbs, deadlines, specific outcomes, task lists, milestones
- Time-bound with clear completion criteria

**AREAS** - A sphere of activity with a standard to be maintained over time:
- Examples: "Health & Fitness", "Finances", "Apartment Maintenance", "Career Development", "Relationships", "Learning"
- Key indicators: Ongoing maintenance, standards, habits, continuous improvement
- No specific end date, but requires regular attention

**RESOURCES** - A topic of ongoing interest or reference material:
- Examples: "AI Prompts", "Stoicism", "Cooking Recipes", "Programming Tips", "Travel Guides", "Book Notes"
- Key indicators: Reference material, learning resources, collections, knowledge bases
- Useful for future reference and learning

**INBOX** - For notes that are too generic, unclear, or need more processing:
- Examples: Quick thoughts, incomplete ideas, unclear purpose, temporary notes
- Should remain in Inbox for manual review

The user will provide a high-level directive and the content of a note.
Based on BOTH the directive and the note content, analyze the note's purpose, content type, and context.

Output ONLY a JSON object with this structure:
{"category": "Projects" | "Areas" | "Resources" | "Inbox", "folder_name": "Suggested Folder Name"}

- The "folder_name" should be a short, descriptive name (2-4 words max)
- If the note doesn't clearly fit any category or is too generic, classify as "Inbox"
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

REFACTOR_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources, Archives) system archivist with deep understanding of productivity and knowledge management. Your task is to re-evaluate a note that is CURRENTLY IN THE ARCHIVE and decide if it has become relevant again for an active Project, Area, or Resource.

Here are the detailed definitions with examples:

**PROJECTS** - A series of tasks linked to a goal with a deadline:
- Examples: "Develop New App", "Plan Vacation", "Complete Q3 Report", "Renovate Kitchen"
- Key indicators: Action verbs, deadlines, specific outcomes, task lists

**AREAS** - A sphere of activity with a standard to be maintained over time:
- Examples: "Health & Fitness", "Finances", "Apartment Maintenance", "Career Development"
- Key indicators: Ongoing maintenance, standards, habits, continuous improvement

**RESOURCES** - A topic of ongoing interest or reference material:
- Examples: "AI Prompts", "Stoicism", "Cooking Recipes", "Programming Tips"
- Key indicators: Reference material, learning resources, collections, knowledge bases

**ARCHIVE** - Inactive items that should remain archived:
- Examples: Completed projects, outdated information, irrelevant content
- Should remain in Archive if still inactive or no longer relevant

The user will provide a high-level directive and the content of the note.
Based on BOTH the directive and the note content, determine if this archived note is now relevant to active work.

Output ONLY a JSON object with this structure:
{"category": "Projects" | "Areas" | "Resources" | "Archive", "folder_name": "Suggested Folder Name"}

- If the note is now relevant to an active category, choose "Projects", "Areas", or "Resources"
- If the note is still inactive and should remain archived, return "category": "Archive"
- The "folder_name" should be a short, descriptive name (2-4 words max)
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

def classify_note_with_llm(note_content: str, user_directive: str, model_name: str, system_prompt: str) -> dict | None:
    """
    Usa un LLM local a través de Ollama para clasificar una nota.
    """
    console.print(f"🤖 [dim]Consultando IA ({model_name}) para clasificación...[/dim]")
    prompt = f"""High-level directive: "{user_directive}"\n\nNote content:\n---\n{note_content[:4000]}"""
    try:
        response = ollama.chat(
            model=model_name, 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
            options={'temperature': 0.0}
        )
        content = response['message']['content']
        if content.startswith("```json"):
            content = content.strip("```json\n").strip("`")
        result = json.loads(content)
        console.print(f"✅ [dim]IA clasificó como: {result.get('category', 'Unknown')} -> {result.get('folder_name', 'Unknown')}[/dim]")
        return result
    except json.JSONDecodeError:
        console.print("[bold red]Error: El LLM no devolvió un JSON válido.[/bold red]")
        return None
    except Exception as e:
        if "model" in str(e) and "not found" in str(e):
             console.print(f"[bold red]Error: Modelo de IA '{model_name}' no encontrado. Asegurate de que Ollama esté corriendo y hayas ejecutado 'ollama pull {model_name}'.[/bold red]")
        else:
            console.print(f"[bold red]Error al contactar con Ollama: {e}[/bold red]")
        return None

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

def _process_notes_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, source_folder_name: str, system_prompt: str, excluded_paths: list[str] = None):
    """
    Función interna para procesar clasificación de notas (usada por inbox y archive).
    """
    if not check_ollama_model(model_name):
        return

    source_path = vault_path / source_folder_name
    if not source_path.is_dir():
        console.print(f"[yellow]No se encontró la carpeta '{source_folder_name}'. No hay nada que procesar.[/yellow]")
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
        return
        
    if execute:
        mode_text = "EXECUTE"
        progress_title = "[green]Procesando y moviendo notas..."
    else:
        mode_text = "SIMULATION"
        progress_title = "[yellow]Simulando procesamiento..."
        console.print("\n[yellow][bold]MODO SIMULACIÓN ACTIVADO: No se aplicarán cambios permanentes.[/bold][/yellow]")

    console.print(f"🤖 Usando modelo de IA: [bold cyan]{model_name}[/bold cyan]")
    console.print(f"\n[bold]Modo {mode_text} activado. Directiva del usuario:[/bold] [italic]'{extra_prompt}'[/italic]")

    try:
        with open("para_factor_weights.json", "r", encoding="utf-8") as f:
            category_weights = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        console.print("[bold red]Error: No se pudo cargar 'para_factor_weights.json'. Asegúrate de que existe y es un JSON válido.[/bold red]")
        return

    # Instanciar AnalyzeManager una sola vez
    analyze_manager = AnalyzeManager(vault_path)

    with Progress(console=console) as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        for note in notes_to_process:
            content = note.read_text(encoding='utf-8')
            if not content.strip():
                progress.update(task, advance=1, description=f"[dim]Omitiendo nota vacía: {note.name}[/dim]")
                continue

            # 1. Obtener predicción del LLM
            llm_classification = classify_note_with_llm(content, extra_prompt, model_name, system_prompt)
            llm_category = llm_classification.get('category') if llm_classification else source_folder_name

            # 2. Extraer features y añadir predicción LLM
            features = extract_structured_features_from_note(content, note_path=str(note), db=db)
            feature_values = {k: v['value'] for k, v in features.items()}
            feature_values['llm_prediction'] = llm_category
            # 2b. Agregar features de AnalyzeManager
            analyze_features = analyze_manager.get_features_for_note(note)
            feature_values.update(analyze_features)
            # También agregarlos al breakdown de features
            for k, v in analyze_features.items():
                features[k] = {'value': v, 'explanation': f'Feature estadístico de AnalyzeManager: {k}'}

            # 3. Puntuar con la matriz
            final_category, final_score, score_breakdown = score_para_classification(feature_values, category_weights)
            
            progress.update(task, advance=1)
            
            # --- Mostrar resultados con transparencia ---
            console.print(f"\n[bold]📄 Nota Analizada: [cyan]{note.name}[/cyan][/bold]")
            
            # Mostrar la predicción del LLM de forma destacada
            if llm_classification:
                console.print(f"🤖 [bold]Predicción IA:[/bold] [blue]{llm_classification.get('category', 'Unknown')}[/blue] -> [cyan]{llm_classification.get('folder_name', 'Unknown')}[/cyan]")
            else:
                console.print(f"🤖 [bold]Predicción IA:[/bold] [red]Falló[/red] -> Usando '{source_folder_name}' como fallback")
            
            # Determinar el nombre de la carpeta final
            if final_category == source_folder_name:
                final_folder = source_folder_name
            elif llm_classification and final_category == llm_classification.get('category'):
                final_folder = normalize_name(llm_classification.get('folder_name', note.stem))
            else:
                final_folder = normalize_name(note.stem)
            
            console.print(f"🏆 [bold]Decisión Final (Matriz + IA):[/bold] Clasificar como [green]{final_category}/{final_folder}[/green] (Puntaje: {final_score})")

            # Crear y mostrar la tabla de desglose
            table = Table(title="[bold blue]Desglose de Puntuación[/bold blue]", box=box.ROUNDED, show_header=True, header_style="bold magenta")
            table.add_column("Factor", style="cyan")
            table.add_column("Aporte", style="bold green", justify="right")
            
            for factor, contribution in sorted(score_breakdown.items(), key=lambda item: abs(float(item[1])), reverse=True):
                table.add_row(factor, str(contribution))
            
            console.print(table)

            # --- Bloque de Features Detallados ---
            features_table = Table(title="[bold]Análisis de Features[/bold]", show_header=True, header_style="bold blue", box=box.SIMPLE)
            features_table.add_column("Feature", style="cyan", no_wrap=True)
            features_table.add_column("Valor Detectado", style="magenta")
            
            for feature_name, feature_data in sorted(features.items()):
                value = feature_data.get('value')
                
                if isinstance(value, bool):
                    display_value = "✅ Sí" if value else "[dim]No[/dim]"
                elif isinstance(value, list) and len(value) > 3:
                    display_value = f"[{', '.join(map(str, value[:3]))}, ... ({len(value)} total)]"
                elif not value:
                    display_value = "[dim]N/A[/dim]"
                else:
                    display_value = str(value)
                    
                features_table.add_row(feature_name, display_value)
            
            console.print(features_table)

            if final_category == source_folder_name:
                console.print(f"  - ➡️ [dim]{note.name} -> se mantiene en '{source_folder_name}'.[/dim]")
                continue

            para_map = {"Projects": "01-Projects", "Areas": "02-Areas", "Resources": "03-Resources"}
            target_dir_name = para_map.get(final_category)

            if not target_dir_name:
                continue

            if execute:
                console.print(f"  - 🚀 [cyan]{note.name}[/cyan] -> Moviendo a [green]{final_category}/{final_folder}[/green]")
                target_path = vault_path / target_dir_name / final_folder
                target_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(note), str(target_path / note.name))
                db.add_or_update_note(target_path / note.name, content, final_category, final_folder)
            else:
                console.print(f"  - simulating: [cyan]{note.name}[/cyan] -> Movería a [yellow]{final_category}/{final_folder}[/yellow]")

    if not execute:
        console.print(f"\n[yellow][bold]FIN DE LA SIMULACIÓN: No se movió ningún archivo ni se modificó la base de datos.[/bold][/yellow]")
    console.print(f"\n[bold]✅ Proceso de procesamiento finalizado.[/bold]")

def run_inbox_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Clasifica y organiza notas desde la carpeta 00-Inbox usando la matriz de factores.
    """
    _process_notes_classification(
        vault_path, db, extra_prompt, model_name, execute, 
        "00-Inbox", CLASSIFICATION_SYSTEM_PROMPT
    )

def run_archive_refactor(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, excluded_paths: list[str]):
    """
    Re-evalúa y organiza notas desde la carpeta de Archivos usando la matriz de factores.
    """
    _process_notes_classification(
        vault_path, db, extra_prompt, model_name, execute, 
        "04-Archive", REFACTOR_SYSTEM_PROMPT, excluded_paths
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