#!/usr/bin/env python3
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
import logging
import sys
import re
from rich.syntax import Syntax
from rich.panel import Panel
import shutil
import ollama
from paralib.similarity import find_similar_classification, register_project_alias
import json
from rich.table import Table
from rich.progress import Progress as RichProgress, BarColumn, TextColumn
import hashlib
from rich import box
import subprocess
import os
import functools

# Importamos la lógica del núcleo desde la nueva librería
from paralib.db import ChromaPARADatabase
from paralib.organizer import (run_archive_refactor, run_inbox_classification, get_keywords, get_rules, get_profile)
from paralib.ui import (display_search_results, run_monitor_dashboard,
                        select_folders_to_exclude, select_ollama_model, interactive_note_review_loop)
from paralib.vault import find_vault, extract_frontmatter, save_para_config, load_para_config, extract_links_and_backlinks, get_notes_modification_times, detect_tasks_in_notes, extract_structured_features_from_note, score_para_classification
from paralib.logger import logger
from paralib.classification_log import export_finetune_dataset, get_feedback_notes, get_classification_history, log_feedback
from paralib.utils import shorten_path, check_recent_errors, pre_command_checks

app = typer.Typer(
    help="PARA CLI: Un asistente inteligente para organizar y buscar en tu vault de Obsidian.",
    rich_markup_mode="markdown"
)
console = Console()
SUPPORTS_COLOR = console.is_terminal or sys.stdout.isatty()

# Funciones utilitarias globales para clasificación avanzada

def get_semantic_neighbors(note_text, db, n=5):
    results = db.search_similar_notes(note_text, n_results=n)
    neighbors = []
    for meta, _ in results:
        neighbors.append({
            'text': meta.get('content', meta.get('filename', '')),
            'category': meta.get('category', 'Unknown')
        })
    return neighbors

def build_enriched_prompt(note_text, neighbors, keywords, rules, profile):
    prompt = """
Eres un asistente experto en organización de notas según el método PARA (Projects, Areas, Resources, Archive).
"""
    if profile:
        prompt += f"\nPerfil de organización: {profile}"
    if keywords:
        prompt += f"\nContexto de la vault: {', '.join(keywords)}"
    if rules:
        prompt += "\nReglas personalizadas:\n"
        for rule in rules:
            prompt += f"- Si la nota contiene '{rule['contains']}', clasifícala como '{rule['category']}'.\n"
    if neighbors:
        prompt += "\nNotas similares encontradas:\n"
        for n in neighbors:
            prompt += f"- \"{n['text'][:60]}...\" ({n['category']})\n"
    prompt += f"\nNota a clasificar:\n\"{note_text}\"\n"
    prompt += "\nClasifica la nota en Projects, Areas, Resources o Archive. Explica tu decisión.\n"
    prompt += "\nFormato de respuesta:\nClasificación: <categoría>\nExplicación: <explicación>\n"
    return prompt

def get_recent_notes(vault_path_obj, n=10):
    from pathlib import Path
    import os
    import datetime
    notes = list(Path(vault_path_obj).rglob("*.md"))
    notes = [(str(n), n.stat().st_mtime) for n in notes]
    notes = sorted(notes, key=lambda x: x[1], reverse=True)[:n]
    result = []
    for note_path, ts in notes:
        name = os.path.basename(note_path)
        fecha = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        # Intentar extraer status del nombre o dejar vacío
        status = ""
        if "Backlog" in name:
            status = "Backlog"
        elif "Done" in name:
            status = "Done"
        elif "Archive" in name:
            status = "Archive"
        result.append((name, fecha, status))
    return result

@app.command()
@pre_command_checks
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
    check_recent_errors(console, SUPPORTS_COLOR)
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"🤖  Iniciando clasificación de notas nuevas...")
    from paralib.vault import find_vault
    vault_path_obj = find_vault(vault_path, force_cache)
    if vault_path_obj:
        print(f"🗄️  Vault detectado: {shorten_path(str(vault_path_obj), 3)}")
    if not vault_path_obj:
        raise typer.Exit(1)
    console.print(Panel(f"🗄️  Vault detectado: [cyan]{shorten_path(str(vault_path_obj), 3)}[/cyan]", style="bold blue", box=box.SIMPLE), markup=SUPPORTS_COLOR)
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    if not model:
        from paralib.vault import load_para_config
        config = load_para_config()
        model = config.get('ollama_model') or 'llama3.2:3b'
    # Mensaje de modo
    if execute:
        console.print("[bold green]MODO EJECUCIÓN: Los cambios se aplicarán en el vault.[/bold green]", markup=SUPPORTS_COLOR)
    else:
        console.print("[yellow][bold]MODO SIMULACIÓN: No se aplicarán cambios permanentes.[/bold][/yellow]", markup=SUPPORTS_COLOR)
    run_inbox_classification(vault_path_obj, db, extra_prompt, model, execute)
    console.print("[bold blue]✅ Clasificación finalizada. Revisa el resumen arriba y los logs para detalles.[/bold blue]", markup=SUPPORTS_COLOR)

@app.command()
@pre_command_checks
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
    console.print("[bold green]🔄 Iniciando refactorización del Archivo con IA...[/bold green]", markup=SUPPORTS_COLOR)
    from paralib.vault import find_vault
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    archive_path = vault_path_obj / "04-Archive"
    if exclude_folders:
        excluded_paths = [str(archive_path / f.strip()) for f in exclude_folders.split(',')]
        console.print("[yellow]Excluyendo carpetas especificadas por parámetro.[/yellow]", markup=SUPPORTS_COLOR)
    else:
        excluded_paths = select_folders_to_exclude(archive_path)
    if excluded_paths:
        console.print("\n[green]Carpetas excluidas del Archivo:[/green]", markup=SUPPORTS_COLOR)
        for s_path in excluded_paths:
            from pathlib import Path
            relative_p = Path(s_path).relative_to(vault_path_obj)
            console.print(f"  - [yellow]{relative_p}[/yellow]", markup=SUPPORTS_COLOR)
    if not model:
        from paralib.vault import load_para_config
        config = load_para_config()
        model = config.get('ollama_model') or 'llama3.2:3b'
    # Mensaje de modo
    if execute:
        console.print("[bold green]MODO EJECUCIÓN: Los cambios se aplicarán en el vault.[/bold green]", markup=SUPPORTS_COLOR)
    else:
        console.print("[yellow][bold]MODO SIMULACIÓN: No se aplicarán cambios permanentes.[/bold][/yellow]", markup=SUPPORTS_COLOR)
    run_archive_refactor(vault_path_obj, db, extra_prompt, model, execute, excluded_paths)
    console.print("[bold blue]✅ Refactorización finalizada. Revisa el resumen arriba y los logs para detalles.[/bold blue]", markup=SUPPORTS_COLOR)

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
    console.print(f"\n[bold green]🧠 Buscando notas similares a:[/bold green] [italic]'{query}'[/italic]", markup=SUPPORTS_COLOR)
    
    from paralib.vault import find_vault
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
    console.print("[bold green]Iniciando monitor...[/bold green]", markup=SUPPORTS_COLOR)
    from paralib.vault import find_vault
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)

    try:
        db_path = str(vault_path_obj / ".para_db" / "chroma")
        db = ChromaPARADatabase(db_path=db_path)
        run_monitor_dashboard(db)
    except Exception as e:
        console.print(f"[bold red]Error al iniciar el monitor: {e}[/bold red]", markup=SUPPORTS_COLOR)
        raise typer.Exit(1)

@app.command()
def doctor(
    clean_logs: bool = typer.Option(False, "--clean-logs", help="Limpiar logs antes del diagnóstico."),
    only_tests: bool = typer.Option(False, "--only-tests", help="Ejecutar solo los tests unitarios."),
    full: bool = typer.Option(False, "--full", help="Diagnóstico completo: backup, reparación, logs, tests."),
):
    """Diagnóstico y QA completo del sistema PARA: backup, reparación, logs, tests. Punto único de salud del sistema."""
    import subprocess
    import sys
    from pathlib import Path
    from paralib.logger import logger
    print("[DOCTOR] Iniciando diagnóstico y QA completo...")
    logger.info("[DOCTOR] Iniciando diagnóstico y QA completo...")
    # Limpiar logs si se solicita
    log_path = Path("logs/para.log")
    if clean_logs and log_path.exists():
        with open(log_path, "w") as f:
            f.write("")
        print("[DOCTOR] Log de errores limpiado.")
        logger.info("[DOCTOR] Log de errores limpiado.")
    if only_tests:
        print("[DOCTOR] Ejecutando solo tests unitarios...")
        logger.info("[DOCTOR] Ejecutando solo tests unitarios...")
    if not only_tests:
        # Diagnóstico completo (antes: autoheal)
        # 1. Verificar integridad de archivos clave
        files_ok = True
        required_files = ["requirements.txt", "para_config.json", "para_cli.py", "paralib/__init__.py"]
        for f in required_files:
            if not Path(f).exists():
                msg = f"[DOCTOR] Archivo clave faltante: {f}"
                print(msg)
                logger.critical(msg)
                files_ok = False
        if not files_ok:
            msg = "[DOCTOR] Faltan archivos clave. Intenta restaurar desde backup o clona de nuevo el repositorio."
            print(msg)
            logger.critical(msg)
            return
        # 2. Reparar base de datos corrupta
        db_path = Path("para_chroma_db")
        if db_path.exists() and db_path.stat().st_size < 1024:
            msg = "[DOCTOR] Base de datos corrupta detectada. Eliminando..."
            print(msg)
            logger.warning(msg)
            import shutil
            shutil.rmtree(db_path)
            msg = "[DOCTOR] Base de datos eliminada. Se recreará en el próximo uso."
            print(msg)
            logger.info(msg)
        # 3. Reparar errores de schema en ChromaDB
        chroma_db_file = db_path / "chroma.sqlite3"
        if chroma_db_file.exists():
            with open(chroma_db_file, 'rb') as f:
                content = f.read(100)
                if b'sqlite' not in content:
                    msg = "[DOCTOR] Archivo de base de datos ChromaDB corrupto. Renombrando para recreación..."
                    print(msg)
                    logger.warning(msg)
                    import shutil
                    shutil.move(str(chroma_db_file), str(chroma_db_file) + ".bak_autofix")
                    msg = f"[DOCTOR] Base renombrada a {chroma_db_file}.bak_autofix"
                    print(msg)
                    logger.info(msg)
        # 4. Backup automático si no existe
        backups_dir = Path("backups")
        backups = sorted(backups_dir.glob("*.zip"), reverse=True) if backups_dir.exists() else []
        if not backups:
            msg = "[DOCTOR] No se encontró backup. Creando backup automático..."
            print(msg)
            logger.warning(msg)
            try:
                from paralib.utils import auto_backup_if_needed
                auto_backup_if_needed()
                msg = "[DOCTOR] Backup automático creado."
                print(msg)
                logger.info(msg)
            except Exception as e:
                msg = f"[DOCTOR] No se pudo crear backup automático: {e}"
                print(msg)
                logger.critical(msg)
        else:
            msg = f"[DOCTOR] Backup más reciente encontrado: {backups[0]}"
            print(msg)
            logger.info(msg)
            msg = "[DOCTOR] Puedes restaurar manualmente usando: python backup_manager.py --action restore --vault-path <ruta> --backup-file <archivo>"
            print(msg)
            logger.info(msg)
        # 5. Analizar y autocorregir errores recientes en logs
        try:
            from paralib.log_analyzer import analyze_and_fix_log
            msg = "[DOCTOR] Analizando logs y aplicando fixes automáticos..."
            print(msg)
            logger.info(msg)
            analyze_and_fix_log()
        except Exception as e:
            msg = f"[DOCTOR] No se pudo analizar el log automáticamente: {e}"
            print(msg)
            logger.error(msg)
    # 6. Ejecutar tests unitarios
    print("[DOCTOR] Ejecutando tests unitarios...")
    logger.info("[DOCTOR] Ejecutando tests unitarios...")
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', 'paralib/tests/', '--maxfail=3', '--disable-warnings', '-v'],
                               env={**os.environ, 'PYTHONPATH': '.'},
                               capture_output=True, text=True)
        print(result.stdout)
        logger.info(result.stdout)
        if result.returncode == 0:
            print("[DOCTOR] Todos los tests pasaron correctamente.")
            logger.info("[DOCTOR] Todos los tests pasaron correctamente.")
        else:
            print("[DOCTOR] Algunos tests fallaron. Revisa la salida anterior para detalles.")
            logger.warning("[DOCTOR] Algunos tests fallaron. Revisa la salida anterior para detalles.")
    except Exception as e:
        print(f"[DOCTOR] No se pudieron ejecutar los tests: {e}")
        logger.error(f"[DOCTOR] No se pudieron ejecutar los tests: {e}")
    print("[DOCTOR] Diagnóstico y QA completados.")
    logger.info("[DOCTOR] Diagnóstico y QA completados.")

@app.command("clean-manager")
def clean_manager(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian a limpiar."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
):
    """
    Limpieza interactiva y exhaustiva de notas: duplicados, vacíos, no Markdown, corruptos, etc.
    """
    from paralib.vault import find_vault
    from paralib.clean_manager import run_clean_manager
    vault_path_obj = find_vault(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    run_clean_manager(vault_path_obj)

@app.command()
def vault(
    force_detect: bool = typer.Option(False, "--force", help="Forzar detección automática, ignorando caché y config."),
    show_only: bool = typer.Option(False, "--show", help="Solo mostrar el vault actual sin modificar nada."),
):
    """Muestra o detecta el vault de Obsidian usando el Vault Manager."""
    from paralib.vault import find_vault
    from rich import print as rprint
    if show_only:
        from paralib.vault import load_para_config
        config = load_para_config()
        vault_path = config.get("vault_path", None)
        if vault_path:
            rprint(f"[bold green]Vault actual:[/bold green] [cyan]{vault_path}[/cyan]")
        else:
            rprint("[yellow]No hay vault configurado en para_config.json.[/yellow]")
        return
    vault = find_vault(force_cache=not force_detect)
    if vault:
        rprint(f"[bold green]Vault detectado:[/bold green] [cyan]{vault}[/cyan]")
    else:
        rprint("[red]No se pudo detectar ningún vault automáticamente.[/red]")

if __name__ == "__main__":
    app() 