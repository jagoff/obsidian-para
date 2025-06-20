"""
para_cli.py

Interfaz de Línea de Comandos (CLI) para el sistema de organización PARA.
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
import typer
from rich.console import Console
from pathlib import Path

# Importamos la lógica del núcleo desde la nueva librería
from paralib.db import ChromaPARADatabase
from paralib.organizer import (run_archive_refactor, run_inbox_classification,
                                run_organization)
from paralib.ui import (display_search_results, run_monitor_dashboard,
                        select_folders_to_exclude, select_ollama_model)
from paralib.vault import find_vault

app = typer.Typer(
    help="PARA CLI: Un asistente inteligente para organizar y buscar en tu vault de Obsidian.",
    rich_markup_mode="markdown"
)
console = Console()

@app.command(name="index")
def index_command(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    exclude_folders: str = typer.Option(None, "--exclude", "-e", help="Lista de carpetas a excluir, separadas por comas."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    execute: bool = typer.Option(False, "--execute", help="Escribe los cambios en la base de datos (simulación por defecto)."),
):
    """
    Escanea todo el vault y (re)indexa todas las notas en la base de datos.
    """
    console.print("[bold green]Iniciando proceso de indexado total...[/bold green]")
    
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)

    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
        
    excluded_paths = []
    if exclude_folders:
        excluded_paths = [
            str(vault_path_obj / f.strip()) for f in exclude_folders.split(',')
        ]
        console.print("[yellow]Excluyendo carpetas especificadas por parámetro.[/yellow]")
    else:
        excluded_paths = select_folders_to_exclude(vault_path_obj)

    if excluded_paths:
        console.print("\n[green]Carpetas excluidas:[/green]")
        for s_path in excluded_paths:
            relative_p = Path(s_path).relative_to(vault_path_obj)
            console.print(f"  - [yellow]{relative_p}[/yellow]")
    
    run_organization(vault_path_obj, excluded_paths, db, execute)

@app.command()
def classify(
    extra_prompt: str = typer.Option("General", "--prompt", "-p", help="Directiva para guiar al clasificador de IA."),
    model: str = typer.Option(None, "--model", "-m", help="El modelo de IA a utilizar (vía Ollama). Si no se especifica, se sugerirá el mejor modelo local."),
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    execute: bool = typer.Option(False, "--execute", help="Aplica los cambios moviendo archivos (simulación por defecto)."),
):
    """
    Clasifica notas de '00-Inbox' usando IA y las organiza en carpetas PARA.
    """
    console.print("[bold green]🤖 Iniciando clasificación de notas nuevas desde el Inbox...[/bold green]")
    
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
        
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    # Selección automática de modelo si no se especifica
    chosen_model = model or select_ollama_model()
    run_inbox_classification(vault_path_obj, db, extra_prompt, chosen_model, execute)

@app.command()
def refactor(
    extra_prompt: str = typer.Option("General", "--prompt", "-p", help="Directiva para guiar al clasificador de IA."),
    model: str = typer.Option(None, "--model", "-m", help="El modelo de IA a utilizar (vía Ollama). Si no se especifica, se sugerirá el mejor modelo local."),
    exclude_folders: str = typer.Option(None, "--exclude", "-e", help="Lista de carpetas a excluir, separadas por comas."),
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    execute: bool = typer.Option(False, "--execute", help="Aplica los cambios moviendo archivos (simulación por defecto)."),
):
    """
    Re-evalúa notas de '04-Archive' para moverlas a categorías activas si es necesario.
    """
    console.print("[bold green]🔄 Iniciando refactorización del Archivo con IA...[/bold green]")
    
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
        
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)

    excluded_paths = []
    archive_path = vault_path_obj / "04-Archive"
    if exclude_folders:
        excluded_paths = [
            str(archive_path / f.strip()) for f in exclude_folders.split(',')
        ]
        console.print("[yellow]Excluyendo carpetas especificadas por parámetro.[/yellow]")
    else:
        excluded_paths = select_folders_to_exclude(archive_path)

    if excluded_paths:
        console.print("\n[green]Carpetas excluidas del Archivo:[/green]")
        for s_path in excluded_paths:
            relative_p = Path(s_path).relative_to(vault_path_obj)
            console.print(f"  - [yellow]{relative_p}[/yellow]")
    
    # Selección automática de modelo si no se especifica
    chosen_model = model or select_ollama_model()
    run_archive_refactor(vault_path_obj, db, extra_prompt, chosen_model, execute, excluded_paths)

@app.command()
def search(
    query: str = typer.Argument(..., help="El texto a buscar. La búsqueda es semántica, no por palabra clave."),
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian a organizar."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    results: int = typer.Option(5, "--results", "-n", help="Número de resultados a mostrar."),
):
    """
    Busca notas en tu vault por significado semántico.
    """
    console.print(f"\n[bold green]🧠 Buscando notas similares a:[/bold green] [italic]'{query}'[/italic]")
    
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
        
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    search_results = db.search_similar_notes(query, n_results=results)
    
    display_search_results(search_results, vault_path_obj)

@app.command()
def monitor(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian a monitorear."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
):
    """
    Muestra un dashboard interactivo de tu vault que se actualiza en tiempo real.
    """
    console.print("[bold green]Iniciando monitor...[/bold green]")
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)

    try:
        db_path = str(vault_path_obj / ".para_db" / "chroma")
        db = ChromaPARADatabase(db_path=db_path)
        run_monitor_dashboard(db)
    except Exception as e:
        console.print(f"[bold red]Error al iniciar el monitor: {e}[/bold red]")
        raise typer.Exit(1)

@app.command(hidden=True)
def dashboard():
    """Comando obsoleto. Usar 'monitor'."""
    console.print("[bold yellow]Este comando es obsoleto. Usá 'monitor' para ver el dashboard interactivo.[/bold yellow]")

if __name__ == "__main__":
    app() 