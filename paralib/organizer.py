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

console = Console()

CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources) system organizer. Your task is to classify a given NEW, UNPROCESSED note from an Inbox into one of the three active PARA categories and suggest a folder name for it.

Here are the definitions:
- **Projects:** A series of tasks linked to a goal with a deadline. (e.g., "Develop New App", "Plan Vacation", "Complete Q3 Report").
- **Areas:** A sphere of activity with a standard to be maintained over time. (e.g., "Health & Fitness", "Finances", "Apartment").
- **Resources:** A topic of ongoing interest. (e.g., "AI Prompts", "Stoicism", "Cooking Recipes").

The user will provide a high-level directive and the content of a note.
Based on BOTH the directive and the note content, you must output ONLY a JSON object with the following structure:
{"category": "Projects" | "Areas" | "Resources", "folder_name": "Suggested Folder Name"}

- The "folder_name" should be a short, descriptive name for the project, area, or resource.
- If the note doesn't seem to fit any category or is too generic, classify it as "Inbox" and the folder_name as "Inbox". This means it will remain in the Inbox for now.
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

REFACTOR_SYSTEM_PROMPT = """
You are an expert PARA (Projects, Areas, Resources, Archives) system archivist. Your task is to re-evaluate a note that is CURRENTLY IN THE ARCHIVE and decide if it has become relevant again for an active Project, Area, or Resource.

Here are the definitions:
- **Projects:** A series of tasks linked to a goal with a deadline.
- **Areas:** A sphere of activity with a standard to be maintained over time.
- **Resources:** A topic of ongoing interest.
- **Archive:** Inactive items. This is the note's current location.

The user will provide a high-level directive and the content of the note.
Based on BOTH the directive and the note content, you must output ONLY a JSON object with the following structure:
{"category": "Projects" | "Areas" | "Resources" | "Archive", "folder_name": "Suggested Folder Name"}

- If the note is now relevant to an active category, choose "Projects", "Areas", or "Resources" and provide a folder name.
- If the note is still inactive and should remain in the archive, you MUST return "category": "Archive". In this case, the folder_name is irrelevant (you can use "Archive").
- Do not add any explanation or introductory text. ONLY the JSON object.
"""

def classify_note_with_llm(note_content: str, user_directive: str, model_name: str, system_prompt: str) -> dict | None:
    """
    Usa un LLM local a través de Ollama para clasificar una nota.
    """
    prompt = f"""High-level directive: "{user_directive}"\n\nNote content:\n---\n{note_content[:4000]}"""
    try:
        response = ollama.chat(
            # Modelo recomendado: llama3:8b por su excelente balance entre rendimiento y calidad de instrucción.
            # Alternativas: 'mistral:7b' (más rápido), 'llama3:70b' (mayor calidad, más lento).
            model=model_name, 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
            options={'temperature': 0.0}
        )
        content = response['message']['content']
        # Limpiar el contenido en caso de que el LLM añada markdown de código
        if content.startswith("```json"):
            content = content.strip("```json\n").strip("`")
        return json.loads(content)
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

def run_inbox_classification(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool):
    """
    Clasifica y organiza notas desde la carpeta 00-Inbox.
    """
    if not check_ollama_model(model_name):
        return

    source_folder_name = "00-Inbox"
    source_path = vault_path / source_folder_name
    if not source_path.is_dir():
        console.print(f"[yellow]No se encontró la carpeta '{source_folder_name}'. No hay nada que clasificar.[/yellow]")
        return

    notes_to_classify = list(source_path.rglob("*.md"))
    
    console.print(f"\n[bold]🤖 Encontradas {len(notes_to_classify)} notas para clasificar en '{source_folder_name}'.[/bold]")
    if not notes_to_classify:
        return
        
    if execute:
        mode_text = "EXECUTE"
        progress_title = "[green]Clasificando y moviendo notas..."
    else:
        mode_text = "SIMULATION"
        progress_title = "[yellow]Simulando clasificación..."

    console.print(f"🤖 Usando modelo de IA: [bold cyan]{model_name}[/bold cyan]")
    console.print(f"\n[bold]Modo {mode_text} activado. Directiva del usuario:[/bold] [italic]'{extra_prompt}'[/italic]")

    with Progress(console=console) as progress:
        task = progress.add_task(progress_title, total=len(notes_to_classify))
        for note in notes_to_classify:
            content = note.read_text(encoding='utf-8')
            if not content.strip():
                progress.update(task, advance=1, description=f"[dim]Omitiendo nota vacía: {note.name}[/dim]")
                continue

            classification = classify_note_with_llm(content, extra_prompt, model_name, CLASSIFICATION_SYSTEM_PROMPT)
            progress.update(task, advance=1)
            
            if not classification or classification['category'] == 'Inbox':
                progress.console.print(f"  - 📄 [dim]{note.name} -> se mantiene en '{source_folder_name}'.[/dim]")
                continue
                
            category = classification['category']
            folder_name = classification['folder_name']
            
            para_map = {
                "Projects": "01-Projects", 
                "Areas": "02-Areas", 
                "Resources": "03-Resources"
            }
            target_dir_name = para_map.get(category)
            if not target_dir_name:
                continue

            target_path = vault_path / target_dir_name / folder_name
            
            if execute:
                progress.console.print(f"  - 🚀 [cyan]{note.name}[/cyan] -> Moviendo a [green]{category}/{folder_name}[/green]")
                target_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(note), str(target_path / note.name))
                db.add_or_update_note(target_path / note.name, content, category, folder_name)
            else:
                progress.console.print(f"  -  simulating: [cyan]{note.name}[/cyan] -> Movería a [yellow]{category}/{folder_name}[/yellow]")

    console.print(f"\n[bold]✅ Proceso de clasificación finalizado.[/bold]")


def run_archive_refactor(vault_path: Path, db: ChromaPARADatabase, extra_prompt: str, model_name: str, execute: bool, excluded_paths: list[str]):
    """
    Re-evalúa y organiza notas desde la carpeta de Archivos.
    """
    if not check_ollama_model(model_name):
        return

    source_folder_name = "04-Archive"
    source_path = vault_path / source_folder_name
    if not source_path.is_dir():
        console.print(f"[yellow]No se encontró la carpeta '{source_folder_name}'. No hay nada que re-evaluar.[/yellow]")
        return

    all_notes_in_source = list(source_path.rglob("*.md"))
    
    notes_to_process = [
        note for note in all_notes_in_source 
        if not any(str(note.resolve()).startswith(excluded) for excluded in excluded_paths)
    ]

    console.print(f"\n[bold]🔄 Encontradas {len(notes_to_process)} notas para re-evaluar en '{source_folder_name}' (después de exclusiones).[/bold]")
    if not notes_to_process:
        return
        
    if execute:
        mode_text = "EXECUTE"
        progress_title = "[green]Refactorizando y moviendo notas..."
    else:
        mode_text = "SIMULATION"
        progress_title = "[yellow]Simulando refactorización..."

    console.print(f"🤖 Usando modelo de IA: [bold cyan]{model_name}[/bold cyan]")
    console.print(f"\n[bold]Modo {mode_text} activado. Directiva del usuario:[/bold] [italic]'{extra_prompt}'[/italic]")

    with Progress(console=console) as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        for note in notes_to_process:
            content = note.read_text(encoding='utf-8')
            if not content.strip():
                progress.update(task, advance=1, description=f"[dim]Omitiendo nota vacía: {note.name}[/dim]")
                continue

            classification = classify_note_with_llm(content, extra_prompt, model_name, REFACTOR_SYSTEM_PROMPT)
            progress.update(task, advance=1)
            
            if not classification or classification['category'] == 'Archive':
                progress.console.print(f"  - 📄 [dim]{note.name} -> se mantiene en '{source_folder_name}'.[/dim]")
                continue
                
            category = classification['category']
            folder_name = classification['folder_name']
            
            para_map = {
                "Projects": "01-Projects", 
                "Areas": "02-Areas", 
                "Resources": "03-Resources"
            }
            target_dir_name = para_map.get(category)
            if not target_dir_name:
                continue

            target_path = vault_path / target_dir_name / folder_name
            
            if execute:
                progress.console.print(f"  - 🚀 [cyan]{note.name}[/cyan] -> Moviendo a [green]{category}/{folder_name}[/green]")
                target_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(note), str(target_path / note.name))
                db.add_or_update_note(target_path / note.name, content, category, folder_name)
            else:
                progress.console.print(f"  -  simulating: [cyan]{note.name}[/cyan] -> Movería a [yellow]{category}/{folder_name}[/yellow]")

    console.print(f"\n[bold]✅ Proceso de refactorización finalizado.[/bold]")


def get_para_category(note_path: Path, vault_path: Path) -> tuple[str, str | None]:
    """
    Determina la categoría PARA y el nombre del proyecto de una nota
    basándose en su ruta relativa al vault.
    """
    try:
        relative_path = note_path.relative_to(vault_path)
    except ValueError:
        return "Unknown", None

    parts = relative_path.parts
    if not parts:
        return "Unknown", None

    first_dir = parts[0]
    
    if "01-Projects" in first_dir:
        category = "Projects"
        project_name = parts[1] if len(parts) > 2 else None
        return category, project_name
    elif "02-Areas" in first_dir:
        return "Areas", None
    elif "03-Resources" in first_dir:
        return "Resources", None
    elif "04-Archive" in first_dir:
        return "Archives", None
    elif "00-Inbox" in first_dir:
        return "Inbox", None
    
    return "Inbox", None


def run_organization(vault_path: Path, excluded_paths: list[str], db: ChromaPARADatabase, execute: bool):
    """
    Función principal que orquesta el proceso de indexado de notas.
    Escanea archivos, los clasifica y los añade (o simula añadir) a la base de datos.
    """
    console.print(f"\n[bold]🔍 Iniciando escaneo del vault en:[/bold] [cyan]{vault_path}[/cyan]")

    all_notes = list(vault_path.rglob("*.md"))
    
    notes_to_process = [
        note for note in all_notes 
        if not any(str(note.resolve()).startswith(excluded) for excluded in excluded_paths)
    ]

    console.print(f"Se encontraron {len(all_notes)} notas en total.")
    console.print(f"Se procesarán {len(notes_to_process)} notas (después de exclusiones).")
    
    # Configuración de la UI según el modo
    if execute:
        mode_color = "green"
        mode_text = "EXECUTE"
        progress_title = "[green]Indexando en BD..."
        final_message = "procesadas y añadidas/actualizadas en la base de datos."
    else:
        mode_color = "yellow"
        mode_text = "SIMULATION"
        progress_title = "[yellow]Simulando indexado..."
        final_message = "habrían sido procesadas (simulación)."

    console.print(f"\n[bold {mode_color}]Modo {mode_text} activado.[/bold {mode_color}]")
    if not execute:
         console.print("[dim]No se escribirá en la base de datos. Usá --execute para aplicar cambios.[/dim]")

    processed_count = 0
    with Progress(console=console) as progress:
        task = progress.add_task(progress_title, total=len(notes_to_process))
        
        for note in notes_to_process:
            try:
                content = note.read_text(encoding="utf-8")
                if not content.strip():
                    progress.update(task, advance=1, description=f"[dim]Omitiría nota vacía: {note.name}[/dim]")
                    continue
                
                category, project_name = get_para_category(note, vault_path)
                
                if execute:
                    db.add_or_update_note(
                        note_path=note,
                        content=content,
                        category=category,
                        project_name=project_name
                    )
                
                processed_count += 1
                description = f"[cyan]Analizando: {note.name}[/cyan] ({category})"
                progress.update(task, advance=1, description=description)
            except Exception as e:
                progress.update(task, advance=1, description=f"[red]Error en {note.name}: {e}[/red]")

    console.print(f"\n[bold]✅ Proceso finalizado.[/bold]")
    console.print(f"  - [green]{processed_count} notas[/green] {final_message}") 