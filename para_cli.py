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
import sqlite3

# Importamos la lógica del núcleo desde la nueva librería
from paralib.db import ChromaPARADatabase
from paralib.organizer import (run_archive_refactor, run_inbox_classification, get_keywords, get_rules, get_profile)
from paralib.ui import (display_search_results, run_monitor_dashboard,
                        select_folders_to_exclude, select_ollama_model, interactive_note_review_loop)
from paralib.vault import load_para_config, save_para_config, extract_frontmatter, extract_links_and_backlinks, get_notes_modification_times, detect_tasks_in_notes, extract_structured_features_from_note, score_para_classification
from paralib.logger import logger
from paralib.classification_log import export_finetune_dataset, get_feedback_notes, get_classification_history, log_feedback
from paralib.feedback_manager import (analyze_feedback_quality, run_feedback_review_interactive, 
                                     compare_classification_quality, auto_adjust_classification_parameters,
                                     test_classification_improvements, suggest_improvements,
                                     create_sample_feedback, export_quality_report)
from paralib.learning_system import PARA_Learning_System
from paralib.learning_dashboard import create_learning_dashboard
from paralib.utils import shorten_path, check_recent_errors, pre_command_checks
from paralib.vault_cli import select_vault_interactive, get_vault_path

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

def check_exit(value):
    if isinstance(value, str) and value.strip().lower() == 'q':
        print(' ' * 80, end='\r', flush=True)
        console.print("[cyan]👋 Saliste del flujo actual. ¡Hasta la próxima![/cyan]")
        sys.exit(0)

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
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
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
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
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
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
        
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    search_results = db.search_similar_notes(query, n_results=results)
    
    display_search_results(search_results, vault_path_obj)

@app.command()
def chroma(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    insights: bool = typer.Option(False, "--insights", help="Mostrar insights detallados de categorías."),
    distribution: bool = typer.Option(False, "--distribution", help="Mostrar distribución de categorías."),
    patterns: bool = typer.Option(False, "--patterns", help="Mostrar patrones de proyectos."),
    recent: int = typer.Option(7, "--recent", help="Mostrar notas recientes (días)."),
):
    """
    Análisis semántico y capacidades de ChromaDB para mejorar la precisión de PARA.
    """
    console.print(f"\n[bold blue]🔍 ANÁLISIS SEMÁNTICO CON CHROMADB[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
        
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    # Inicializar analyze manager
    from paralib.analyze_manager import AnalyzeManager
    analyze_manager = AnalyzeManager(vault_path_obj, db_path=Path(db_path).parent)
    
    # Mostrar información por defecto si no se especifican opciones
    if not any([insights, distribution, patterns]):
        distribution = True
        patterns = True
    
    if distribution:
        console.print(f"\n[bold]📊 Distribución de Categorías:[/bold]", markup=SUPPORTS_COLOR)
        category_dist = db.get_category_distribution()
        if category_dist:
            total_notes = sum(category_dist.values())
            for category, count in category_dist.items():
                percentage = (count / total_notes) * 100
                console.print(f"  • {category}: {count} notas ({percentage:.1f}%)", markup=SUPPORTS_COLOR)
        else:
            console.print("  • Base de datos vacía - ejecuta 'classify' primero", markup=SUPPORTS_COLOR)
    
    if patterns:
        console.print(f"\n[bold]🎯 Patrones de Proyectos:[/bold]", markup=SUPPORTS_COLOR)
        project_patterns = db.get_project_patterns()
        if project_patterns['total_projects'] > 0:
            console.print(f"  • Total de proyectos: {project_patterns['total_projects']}", markup=SUPPORTS_COLOR)
            console.print(f"  • Proyectos activos (30 días): {len(project_patterns['recent_projects'])}", markup=SUPPORTS_COLOR)
            if project_patterns['project_names']:
                console.print(f"  • Nombres de proyectos: {', '.join(project_patterns['project_names'][:5])}", markup=SUPPORTS_COLOR)
        else:
            console.print("  • No hay proyectos en la base de datos", markup=SUPPORTS_COLOR)
    
    if insights:
        console.print(f"\n[bold]💡 Insights Detallados:[/bold]", markup=SUPPORTS_COLOR)
        category_insights = analyze_manager.get_category_insights()
        for category, insight in category_insights.items():
            console.print(f"\n  [bold]{category}:[/bold]", markup=SUPPORTS_COLOR)
            console.print(f"    • Total de notas: {insight['total_notes']}", markup=SUPPORTS_COLOR)
            if category == "Projects" and insight.get('active_projects'):
                console.print(f"    • Proyectos activos: {insight['active_projects']}", markup=SUPPORTS_COLOR)
            if insight.get('patterns', {}).get('content_patterns', {}).get('top_keywords'):
                keywords = insight['patterns']['content_patterns']['top_keywords'][:5]
                console.print(f"    • Palabras clave: {', '.join(keywords)}", markup=SUPPORTS_COLOR)
    
    # Mostrar notas recientes
    console.print(f"\n[bold]📅 Notas Recientes ({recent} días):[/bold]", markup=SUPPORTS_COLOR)
    recent_notes = db.get_recent_notes(days=recent)
    if recent_notes:
        for note in recent_notes[:10]:  # Mostrar solo las 10 más recientes
            path = note.get('path', 'Unknown')
            category = note.get('category', 'Unknown')
            filename = note.get('filename', 'Unknown')
            console.print(f"  • {filename} → {category}", markup=SUPPORTS_COLOR)
    else:
        console.print("  • No hay notas recientes", markup=SUPPORTS_COLOR)
    
    console.print(f"\n[bold green]✅ Análisis semántico completado[/bold green]", markup=SUPPORTS_COLOR)

@app.command()
def monitor(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian a monitorear."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
):
    """
    Muestra un dashboard interactivo de tu vault que se actualiza en tiempo real.
    """
    console.print("[bold green]Iniciando monitor...[/bold green]", markup=SUPPORTS_COLOR)
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
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
    from rich.panel import Panel
    from rich import box
    # Inicio
    console.print("[bold blue]🩺 Diagnóstico y QA completo del sistema[/bold blue]\n")
    logger.info("[DOCTOR] Iniciando diagnóstico y QA completo...")
    # Limpiar logs si se solicita
    log_path = Path("logs/para.log")
    if clean_logs and log_path.exists():
        with open(log_path, "w") as f:
            f.write("")
        console.print("[green]✔ Log de errores limpiado.[/green]\n")
        logger.info("[DOCTOR] Log de errores limpiado.")
    if only_tests:
        console.print("[yellow]🧪 Ejecutando solo tests unitarios...[/yellow]\n")
        logger.info("[DOCTOR] Ejecutando solo tests unitarios...")
    if not only_tests:
        # Diagnóstico completo (antes: autoheal)
        # 1. Verificar integridad de archivos clave
        files_ok = True
        required_files = ["requirements.txt", "para_config.json", "para_cli.py", "paralib/__init__.py"]
        missing_files = []
        for f in required_files:
            if not Path(f).exists():
                missing_files.append(f)
                logger.critical(f"[DOCTOR] Archivo clave faltante: {f}")
                files_ok = False
        if not files_ok:
            console.print(f"[red]❌ Faltan archivos clave:[/red] {', '.join(missing_files)}\n[red]Intenta restaurar desde backup o clona de nuevo el repositorio.[/red]\n")
            logger.critical("[DOCTOR] Faltan archivos clave. Intenta restaurar desde backup o clona de nuevo el repositorio.")
            return
        # 2. Reparar base de datos corrupta
        db_path = Path("para_chroma_db")
        if db_path.exists() and db_path.stat().st_size < 1024:
            console.print("[yellow]⚠️  Base de datos corrupta detectada. Eliminando...[/yellow]")
            logger.warning("[DOCTOR] Base de datos corrupta detectada. Eliminando...")
            import shutil
            shutil.rmtree(db_path)
            console.print("[green]✔ Base de datos eliminada. Se recreará en el próximo uso.[/green]\n")
            logger.info("[DOCTOR] Base de datos eliminada. Se recreará en el próximo uso.")
        # 3. Reparar errores de schema en ChromaDB
        chroma_db_file = db_path / "chroma.sqlite3"
        if chroma_db_file.exists():
            with open(chroma_db_file, 'rb') as f:
                content = f.read(100)
                if b'sqlite' not in content:
                    console.print("[yellow]⚠️  Archivo de base de datos ChromaDB corrupto. Renombrando para recreación...[/yellow]")
                    logger.warning("[DOCTOR] Archivo de base de datos ChromaDB corrupto. Renombrando para recreación...")
                    import shutil
                    shutil.move(str(chroma_db_file), str(chroma_db_file) + ".bak_autofix")
                    console.print(f"[green]✔ Base renombrada a {chroma_db_file}.bak_autofix[/green]\n")
                    logger.info(f"[DOCTOR] Base renombrada a {chroma_db_file}.bak_autofix")
        # 4. Backup automático si no existe
        backups_dir = Path("backups")
        backups = sorted(backups_dir.glob("*.zip"), reverse=True) if backups_dir.exists() else []
        if not backups:
            console.print("[yellow]⚠️  No se encontró backup. Creando backup automático...[/yellow]")
            logger.warning("[DOCTOR] No se encontró backup. Creando backup automático...")
            try:
                from paralib.utils import auto_backup_if_needed
                auto_backup_if_needed()
                console.print("[green]✔ Backup automático creado.[/green]\n")
                logger.info("[DOCTOR] Backup automático creado.")
            except Exception as e:
                console.print(f"[red]❌ No se pudo crear backup automático:[/red] {e}\n")
                logger.critical(f"[DOCTOR] No se pudo crear backup automático: {e}")
        else:
            console.print(f"[green]✔ Backup más reciente encontrado:[/green] [yellow]{backups[0]}[/yellow]")
            logger.info(f"[DOCTOR] Backup más reciente encontrado: {backups[0]}")
            console.print("[blue]ℹ️  Puedes restaurar manualmente usando:[/blue] [cyan]python backup_manager.py --action restore --vault-path <ruta> --backup-file <archivo>[/cyan]\n")
            logger.info("[DOCTOR] Puedes restaurar manualmente usando: python backup_manager.py --action restore --vault-path <ruta> --backup-file <archivo>")
        # 5. Analizar y autocorregir errores recientes en logs
        try:
            from paralib.log_analyzer import analyze_and_fix_log
            console.print("[magenta]🪛  Analizando logs y aplicando fixes automáticos...[/magenta]")
            logger.info("[DOCTOR] Analizando logs y aplicando fixes automáticos...")
            analyze_and_fix_log()
        except Exception as e:
            console.print(f"[red]❌  No se pudo analizar el log automáticamente:[/red] {e}\n")
            logger.error(f"[DOCTOR] No se pudo analizar el log automáticamente: {e}")
    # 6. Ejecutar tests unitarios
    console.print("[yellow]🧪  Ejecutando tests unitarios...[/yellow]")
    logger.info("[DOCTOR] Ejecutando tests unitarios...")
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', 'paralib/tests/', '--maxfail=3', '--disable-warnings', '-v'],
                               env={**os.environ, 'PYTHONPATH': '.'},
                               capture_output=True, text=True)
        console.print(f"[blue]🧪  Resultado de tests:[/blue]\n{result.stdout}")
        logger.info(result.stdout)
        if result.returncode == 0:
            console.print("[green]✔ Todos los tests pasaron correctamente.[/green]\n")
            logger.info("[DOCTOR] Todos los tests pasaron correctamente.")
        else:
            console.print("[red]❌  Algunos tests fallaron. Revisa la salida anterior para detalles.[/red]\n")
            logger.warning("[DOCTOR] Algunos tests fallaron. Revisa la salida anterior para detalles.")
    except Exception as e:
        console.print(f"[red]❌  No se pudieron ejecutar los tests:[/red] {e}\n")
        logger.error(f"[DOCTOR] No se pudieron ejecutar los tests: {e}")
    console.print("[bold green]✅  Diagnóstico y QA completados.[/bold green]\n")
    logger.info("[DOCTOR] Diagnóstico y QA completados.")

@app.command("clean-manager")
def clean_manager(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian a limpiar."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
):
    """
    Limpieza interactiva y exhaustiva de notas: duplicados, vacíos, no Markdown, corruptos, etc.
    """
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    from paralib.clean_manager import run_clean_manager
    run_clean_manager(vault_path_obj)

@app.command()
def vault(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_detect: bool = typer.Option(False, "--force", help="Forzar detección automática, ignorando caché y config."),
    show_only: bool = typer.Option(False, "--show", help="Solo mostrar el vault actual sin modificar nada."),
):
    """Muestra o detecta el vault de Obsidian usando el Vault Manager."""
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
    vault = select_vault_interactive(vault_path, force_cache=not force_detect)
    if vault:
        pass
    else:
        rprint("[red]No se pudo detectar ningún vault automáticamente.[/red]")

@app.command()
def update_model(
    model: str = typer.Option("llama3.1:8b", "--model", "-m", help="Modelo de IA a actualizar."),
    force: bool = typer.Option(False, "--force", help="Forzar actualización incluso si el modelo ya existe."),
):
    """
    Actualiza y verifica el modelo de IA para mejorar la precisión de clasificación.
    """
    console.print(f"\n[bold blue]🤖 ACTUALIZACIÓN DE MODELO DE IA[/bold blue]", markup=SUPPORTS_COLOR)
    console.print(f"Modelo objetivo: [bold cyan]{model}[/bold cyan]", markup=SUPPORTS_COLOR)
    
    import subprocess
    import sys
    
    try:
        # Verificar si el modelo existe
        console.print(f"\n[dim]Verificando modelo actual...[/dim]", markup=SUPPORTS_COLOR)
        result = subprocess.run(['ollama', 'show', model], capture_output=True, text=True)
        
        if result.returncode == 0 and not force:
            console.print(f"[green]✅ Modelo {model} ya está instalado y actualizado.[/green]", markup=SUPPORTS_COLOR)
            console.print(f"[dim]Usa --force para forzar una nueva descarga.[/dim]", markup=SUPPORTS_COLOR)
            return
        else:
            console.print(f"[yellow]📥 Descargando modelo {model}...[/yellow]", markup=SUPPORTS_COLOR)
        
        # Descargar/actualizar el modelo
        with console.status(f"[bold green]Descargando {model}...[/bold green]", spinner="dots"):
            result = subprocess.run(['ollama', 'pull', model], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print(f"[green]✅ Modelo {model} actualizado exitosamente.[/green]", markup=SUPPORTS_COLOR)
            
            # Verificar el modelo
            console.print(f"\n[dim]Verificando funcionalidad del modelo...[/dim]", markup=SUPPORTS_COLOR)
            test_result = subprocess.run(['ollama', 'show', model], capture_output=True, text=True)
            
            if test_result.returncode == 0:
                console.print(f"[green]✅ Modelo {model} verificado y listo para usar.[/green]", markup=SUPPORTS_COLOR)
                console.print(f"[dim]Ahora puedes usar: python para_cli.py classify --model {model}[/dim]", markup=SUPPORTS_COLOR)
            else:
                console.print(f"[red]❌ Error al verificar el modelo.[/red]", markup=SUPPORTS_COLOR)
        else:
            console.print(f"[red]❌ Error al descargar el modelo:[/red]", markup=SUPPORTS_COLOR)
            console.print(f"[red]{result.stderr}[/red]", markup=SUPPORTS_COLOR)
            
    except FileNotFoundError:
        console.print(f"[red]❌ Ollama no está instalado o no está en el PATH.[/red]", markup=SUPPORTS_COLOR)
        console.print(f"[yellow]Instala Ollama desde: https://ollama.ai[/yellow]", markup=SUPPORTS_COLOR)
    except Exception as e:
        console.print(f"[red]❌ Error inesperado: {e}[/red]", markup=SUPPORTS_COLOR)

@app.command()
def model_info(
    model: str = typer.Option("llama3.1:8b", "--model", "-m", help="Modelo de IA a verificar."),
):
    """
    Verifica información detallada de un modelo de IA local.
    """
    console.print(f"[bold blue]🔍 Verificando modelo: {model}[/bold blue]", markup=SUPPORTS_COLOR)
    try:
        client = ollama.Client()
        model_info = client.show(model)
        console.print(f"[green]✅ Modelo encontrado[/green]", markup=SUPPORTS_COLOR)
        console.print(f"Nombre: {model_info['name']}")
        console.print(f"Tamaño: {model_info.get('size', 'N/A')}")
        console.print(f"Familia: {model_info.get('family', 'N/A')}")
        console.print(f"Parámetros: {model_info.get('parameter_size', 'N/A')}")
        console.print(f"Última modificación: {model_info.get('modified_at', 'N/A')}")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]", markup=SUPPORTS_COLOR)
        console.print("[yellow]💡 Sugerencia: Usa 'para update-model' para descargar el modelo[/yellow]", markup=SUPPORTS_COLOR)

@app.command()
def review_feedback(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    interactive: bool = typer.Option(True, "--interactive", "-i", help="Modo interactivo para revisar notas."),
    export: bool = typer.Option(False, "--export", "-e", help="Exportar dataset de feedback para fine-tuning."),
    analyze: bool = typer.Option(False, "--analyze", "-a", help="Analizar calidad del feedback y sugerir mejoras."),
):
    """
    Revisa y gestiona el feedback de clasificaciones para mejorar el sistema.
    """
    console.print("[bold blue]📝 Sistema de Revisión de Feedback[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    if export:
        output_path = vault_path_obj / "feedback_dataset.jsonl"
        export_finetune_dataset(db, str(output_path))
        console.print(f"[green]✅ Dataset exportado a: {output_path}[/green]", markup=SUPPORTS_COLOR)
        return
    
    if analyze:
        analyze_feedback_quality(db, vault_path_obj)
        return
    
    if interactive:
        run_feedback_review_interactive(db, vault_path_obj)

@app.command()
def feedback_quality(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Análisis detallado con métricas avanzadas."),
    compare: bool = typer.Option(False, "--compare", "-c", help="Comparar calidad antes/después de mejoras."),
):
    """
    Analiza la calidad del sistema de clasificación y feedback.
    """
    console.print("[bold blue]📊 Análisis de Calidad del Sistema[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    if compare:
        compare_classification_quality(db, vault_path_obj)
    else:
        analyze_feedback_quality(db, vault_path_obj, detailed)

@app.command()
def improve_classification(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    auto_adjust: bool = typer.Option(False, "--auto-adjust", "-a", help="Ajustar parámetros automáticamente basado en feedback."),
    test_improvements: bool = typer.Option(False, "--test", "-t", help="Probar mejoras en un subconjunto de notas."),
):
    """
    Mejora el sistema de clasificación basado en feedback acumulado.
    """
    console.print("[bold blue]🚀 Mejora Continua del Sistema[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    if auto_adjust:
        auto_adjust_classification_parameters(db, vault_path_obj)
    elif test_improvements:
        test_classification_improvements(db, vault_path_obj)
    else:
        suggest_improvements(db, vault_path_obj)

@app.command()
def sample_feedback(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
):
    """
    Crea feedback de muestra para demostrar el sistema de análisis.
    """
    console.print("[bold blue]🧪 Creación de Feedback de Muestra[/bold blue]")
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    create_sample_feedback(db, vault_path_obj)

@app.command()
def export_report(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    output: str = typer.Option(None, "--output", "-o", help="Ruta del archivo de salida."),
):
    """
    Exporta un reporte completo de calidad del sistema.
    """
    console.print("[bold blue]📊 Exportación de Reporte de Calidad[/bold blue]")
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    
    export_quality_report(db, vault_path_obj, output)

@app.command()
def learn(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    dashboard: bool = typer.Option(False, "--dashboard", "-d", help="Abrir dashboard de aprendizaje."),
    snapshot: bool = typer.Option(False, "--snapshot", "-s", help="Crear snapshot de aprendizaje."),
    progress: int = typer.Option(30, "--progress", "-p", help="Días para análisis de progreso."),
):
    """
    Sistema de Aprendizaje Autónomo - Aprende y mejora automáticamente.
    """
    console.print("[bold blue]🧠 Sistema de Aprendizaje Autónomo PARA[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    learning_system = PARA_Learning_System(db, vault_path_obj)
    
    if dashboard:
        console.print("[green]🚀 Iniciando dashboard de aprendizaje...[/green]", markup=SUPPORTS_COLOR)
        console.print("[yellow]El dashboard se abrirá en tu navegador.[/yellow]", markup=SUPPORTS_COLOR)
        
        # Lanzar dashboard
        import subprocess
        import sys
        
        dashboard_script = str(Path(__file__).parent / "paralib" / "learning_dashboard.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_script, "--", str(vault_path_obj)])
        
    elif snapshot:
        console.print("[blue]📸 Creando snapshot de aprendizaje...[/blue]", markup=SUPPORTS_COLOR)
        snapshot = learning_system.create_learning_snapshot()
        
        # Mostrar métricas principales
        metrics = snapshot['metrics']
        console.print(f"\n[bold]📊 Métricas de Aprendizaje:[/bold]", markup=SUPPORTS_COLOR)
        console.print(f"🎯 Precisión: {metrics['accuracy_rate']:.1f}%")
        console.print(f"🚀 Velocidad de Aprendizaje: {metrics['learning_velocity']:.2f}")
        console.print(f"🎲 Correlación Confianza: {metrics['confidence_correlation']:.3f}")
        console.print(f"📈 Score de Mejora: {metrics['improvement_score']:.2f}")
        console.print(f"🔗 Coherencia Semántica: {metrics['semantic_coherence']:.2f}")
        console.print(f"⚖️ Balance de Categorías: {metrics['category_balance']:.2f}")
        console.print(f"😊 Satisfacción Usuario: {metrics['user_satisfaction']:.2f}")
        
        # Mostrar insights
        if snapshot['learning_insights']:
            console.print(f"\n[bold]💡 Insights:[/bold]", markup=SUPPORTS_COLOR)
            for insight in snapshot['learning_insights']:
                console.print(f"• {insight}")
        
        # Mostrar sugerencias
        if snapshot['improvement_suggestions']:
            console.print(f"\n[bold]🔧 Sugerencias:[/bold]", markup=SUPPORTS_COLOR)
            for suggestion in snapshot['improvement_suggestions']:
                priority = suggestion['priority']
                console.print(f"• [{priority.upper()}] {suggestion['description']}")
        
    else:
        # Análisis de progreso
        console.print(f"[blue]📈 Analizando progreso de {progress} días...[/blue]", markup=SUPPORTS_COLOR)
        progress_data = learning_system.get_learning_progress(progress)
        
        if 'error' in progress_data:
            console.print(f"[red]❌ {progress_data['error']}[/red]", markup=SUPPORTS_COLOR)
            return
        
        # Mostrar resumen de progreso
        improvement = progress_data['overall_improvement']
        console.print(f"\n[bold]📊 Resumen de Progreso ({progress} días):[/bold]", markup=SUPPORTS_COLOR)
        console.print(f"📈 Mejora en Precisión: {improvement['accuracy']:+.1f}%")
        console.print(f"🎲 Mejora en Confianza: {improvement['confidence']:+.3f}")
        console.print(f"🚀 Mejora General: {improvement['overall']:+.2f}")
        console.print(f"📊 Total de snapshots: {progress_data['total_snapshots']}")
        
        # Mostrar tendencias
        if progress_data['accuracy_trend']:
            initial_acc = progress_data['accuracy_trend'][0]
            final_acc = progress_data['accuracy_trend'][-1]
            console.print(f"\n[bold]📈 Tendencias:[/bold]", markup=SUPPORTS_COLOR)
            console.print(f"Precisión: {initial_acc:.1f}% → {final_acc:.1f}% ({final_acc-initial_acc:+.1f}%)")
        
        if progress_data['confidence_trend']:
            initial_conf = progress_data['confidence_trend'][0]
            final_conf = progress_data['confidence_trend'][-1]
            console.print(f"Confianza: {initial_conf:.3f} → {final_conf:.3f} ({final_conf-initial_conf:+.3f})")

@app.command()
def learn_from_classification(
    note_path: str = typer.Argument(..., help="Ruta de la nota a aprender."),
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    actual_category: str = typer.Option(None, "--actual", "-a", help="Categoría real (para aprendizaje supervisado)."),
):
    """
    Aprende de una clasificación específica.
    """
    console.print("[bold blue]🧠 Aprendiendo de Clasificación[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    learning_system = PARA_Learning_System(db, vault_path_obj)
    
    # Obtener clasificación de la nota
    note_path_obj = Path(note_path)
    if not note_path_obj.exists():
        console.print(f"[red]❌ La nota no existe: {note_path}[/red]", markup=SUPPORTS_COLOR)
        raise typer.Exit(1)
    
    # Buscar clasificación en la base de datos
    note_id = db._generate_id(note_path_obj)
    results = db.collection.get(ids=[note_id], include=["metadatas", "documents"])
    
    if not results.get("metadatas"):
        console.print(f"[red]❌ No se encontró clasificación para: {note_path}[/red]", markup=SUPPORTS_COLOR)
        raise typer.Exit(1)
    
    classification_result = {
        **results["metadatas"][0],
        "content": results["documents"][0] if results["documents"] else ""
    }
    
    # Agregar categoría real si se proporciona
    if actual_category:
        classification_result["actual_category"] = actual_category
    
    # Aprender de la clasificación
    learning_result = learning_system.learn_from_classification(classification_result)
    
    # Mostrar resultados
    console.print(f"\n[bold]📝 Nota: {note_path_obj.name}[/bold]", markup=SUPPORTS_COLOR)
    console.print(f"🎯 Categoría Predicha: {classification_result.get('predicted_category', 'Unknown')}")
    
    if actual_category:
        console.print(f"✅ Categoría Real: {actual_category}")
        is_correct = classification_result.get('predicted_category') == actual_category
        console.print(f"📊 Resultado: {'✅ Correcto' if is_correct else '❌ Incorrecto'}")
    
    # Mostrar insights de aprendizaje
    if learning_result['learning_insights']:
        console.print(f"\n[bold]💡 Insights de Aprendizaje:[/bold]", markup=SUPPORTS_COLOR)
        for insight in learning_result['learning_insights']:
            console.print(f"• {insight}")
    
    # Mostrar mejoras sugeridas
    if learning_result['improvements']:
        console.print(f"\n[bold]🔧 Mejoras Aplicadas:[/bold]", markup=SUPPORTS_COLOR)
        for improvement in learning_result['improvements']:
            console.print(f"• {improvement['type']}: {improvement}")

@app.command()
def learning_metrics(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    export: bool = typer.Option(False, "--export", "-e", help="Exportar métricas a JSON."),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Análisis detallado."),
):
    """
    Muestra métricas detalladas del sistema de aprendizaje.
    """
    console.print("[bold blue]📊 Métricas de Aprendizaje[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    learning_system = PARA_Learning_System(db, vault_path_obj)
    
    # Crear snapshot
    snapshot = learning_system.create_learning_snapshot()
    metrics = snapshot['metrics']
    
    # Mostrar métricas principales
    console.print(f"\n[bold]🎯 Métricas Principales:[/bold]", markup=SUPPORTS_COLOR)
    console.print(f"📊 Total Clasificaciones: {metrics['total_classifications']}")
    console.print(f"🎯 Precisión: {metrics['accuracy_rate']:.1f}%")
    console.print(f"🚀 Velocidad de Aprendizaje: {metrics['learning_velocity']:.2f}")
    console.print(f"🎲 Correlación Confianza: {metrics['confidence_correlation']:.3f}")
    console.print(f"📈 Score de Mejora: {metrics['improvement_score']:.2f}")
    
    if detailed:
        console.print(f"\n[bold]🔍 Métricas Detalladas:[/bold]", markup=SUPPORTS_COLOR)
        console.print(f"🔗 Coherencia Semántica: {metrics['semantic_coherence']:.2f}")
        console.print(f"⚖️ Balance de Categorías: {metrics['category_balance']:.2f}")
        console.print(f"😊 Satisfacción Usuario: {metrics['user_satisfaction']:.2f}")
        console.print(f"🔄 Adaptabilidad Sistema: {metrics['system_adaptability']:.2f}")
        
        # Mostrar rendimiento por categoría
        if snapshot['category_performance']:
            console.print(f"\n[bold]📂 Rendimiento por Categoría:[/bold]", markup=SUPPORTS_COLOR)
            for category, perf in snapshot['category_performance'].items():
                console.print(f"• {category}: {perf['accuracy']:.1f}% ({perf['total_notes']} notas)")
        
        # Mostrar rendimiento por modelo
        if snapshot['model_performance']:
            console.print(f"\n[bold]🤖 Rendimiento por Modelo:[/bold]", markup=SUPPORTS_COLOR)
            for model, accuracy in snapshot['model_performance'].items():
                console.print(f"• {model}: {accuracy:.1f}%")
    
    # Exportar si se solicita
    if export:
        output_path = vault_path_obj / "learning_metrics.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        console.print(f"\n[green]✅ Métricas exportadas a: {output_path}[/green]", markup=SUPPORTS_COLOR)

@app.command()
def folder_feedback(
    vault_path: str = typer.Option(None, "--vault", "-v", help="Ruta al vault de Obsidian."),
    force_cache: bool = typer.Option(False, "--force-cache", "-f", help="Usa la ruta del vault en caché sin preguntar."),
    stats: bool = typer.Option(False, "--stats", "-s", help="Mostrar estadísticas de feedback de carpetas."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Modo interactivo para revisar carpetas creadas."),
    suggest: bool = typer.Option(False, "--suggest", help="Sugerir mejoras basadas en feedback."),
    days: int = typer.Option(30, "--days", "-d", help="Días para análisis de feedback."),
):
    """
    Sistema de feedback específico para carpetas creadas por el sistema PARA.
    
    Permite al usuario evaluar si las carpetas creadas (especialmente proyectos) 
    tienen sentido y aprende de estas decisiones para mejorar futuras clasificaciones.
    """
    console.print("[bold blue]📁 Sistema de Feedback de Carpetas PARA[/bold blue]", markup=SUPPORTS_COLOR)
    
    vault_path_obj = select_vault_interactive(vault_path, force_cache)
    if not vault_path_obj:
        raise typer.Exit(1)
    
    db_path = str(vault_path_obj / ".para_db" / "chroma")
    db = ChromaPARADatabase(db_path=db_path)
    learning_system = PARA_Learning_System(db, vault_path_obj)
    
    if stats:
        console.print("\n[bold cyan]📊 Estadísticas de Feedback de Carpetas[/bold cyan]", markup=SUPPORTS_COLOR)
        folder_stats = learning_system.get_folder_creation_stats(days)
        
        if folder_stats['total_folders'] == 0:
            console.print("[yellow]No hay datos de feedback de carpetas en el período especificado.[/yellow]", markup=SUPPORTS_COLOR)
            return
        
        # Mostrar estadísticas generales
        console.print(f"\n[bold]Resumen General:[/bold]")
        console.print(f"  • Total de carpetas evaluadas: {folder_stats['total_folders']}")
        console.print(f"  • Tasa de aprobación: {folder_stats['approval_rate']:.1f}%")
        
        # Mostrar distribución por categoría
        if folder_stats['category_distribution']:
            console.print(f"\n[bold]Distribución por Categoría:[/bold]")
            for category, data in folder_stats['category_distribution'].items():
                status_color = "green" if data['approval_rate'] >= 70 else "yellow" if data['approval_rate'] >= 50 else "red"
                console.print(f"  • {category}: {data['total']} carpetas, {data['approval_rate']:.1f}% aprobación", 
                            style=status_color, markup=SUPPORTS_COLOR)
        
        # Mostrar rendimiento por método
        if folder_stats['method_performance']:
            console.print(f"\n[bold]Rendimiento por Método:[/bold]")
            for method, performance in folder_stats['method_performance'].items():
                status_color = "green" if performance['approval_rate'] >= 70 else "yellow" if performance['approval_rate'] >= 50 else "red"
                console.print(f"  • {method}: {performance['approval_rate']:.1f}% aprobación (confianza: {performance['avg_confidence']:.2f})", 
                            style=status_color, markup=SUPPORTS_COLOR)
        
        # Mostrar análisis de confianza
        if folder_stats['confidence_analysis']:
            conf_analysis = folder_stats['confidence_analysis']
            console.print(f"\n[bold]Análisis de Confianza:[/bold]")
            console.print(f"  • Confianza promedio: {conf_analysis['mean']:.2f}")
            console.print(f"  • Alta confianza (>0.8): {conf_analysis['high_confidence_approval']['high_confidence']:.1f}% aprobación")
            console.print(f"  • Media confianza (0.5-0.8): {conf_analysis['high_confidence_approval']['medium_confidence']:.1f}% aprobación")
            console.print(f"  • Baja confianza (<0.5): {conf_analysis['high_confidence_approval']['low_confidence']:.1f}% aprobación")
        
        # Mostrar patrones más exitosos
        if folder_stats['top_patterns']:
            console.print(f"\n[bold]Patrones Más Exitosos:[/bold]")
            for pattern in folder_stats['top_patterns'][:5]:
                console.print(f"  • '{pattern['pattern']}' ({pattern['category']}): {pattern['success_rate']:.1f}% éxito, usado {pattern['usage_count']} veces")
        
        # Mostrar insights de aprendizaje
        if folder_stats['learning_insights']:
            console.print(f"\n[bold]Insights de Aprendizaje:[/bold]")
            for insight in folder_stats['learning_insights']:
                console.print(f"  • {insight}")
    
    elif suggest:
        console.print("\n[bold cyan]💡 Sugerencias de Mejora[/bold cyan]", markup=SUPPORTS_COLOR)
        suggestions = learning_system.suggest_folder_improvements()
        
        if not suggestions:
            console.print("[yellow]No hay sugerencias disponibles.[/yellow]", markup=SUPPORTS_COLOR)
            return
        
        for suggestion in suggestions:
            priority_color = "red" if suggestion.get('priority') == 'high' else "yellow" if suggestion.get('priority') == 'medium' else "blue"
            console.print(f"\n[bold {priority_color}]{suggestion['message']}[/bold {priority_color}]", markup=SUPPORTS_COLOR)
            if 'suggestion' in suggestion:
                console.print(f"  Sugerencia: {suggestion['suggestion']}")
    
    elif interactive:
        console.print("\n[bold cyan]🔄 Modo Interactivo de Feedback[/bold cyan]", markup=SUPPORTS_COLOR)
        console.print("Este modo te permitirá revisar carpetas creadas recientemente y dar feedback.")
        console.print("El sistema aprenderá de tus decisiones para mejorar futuras clasificaciones.\n")
        
        # Obtener carpetas recientes para feedback
        conn = sqlite3.connect(learning_system.learning_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_name, category, note_content, confidence, method_used, semantic_score, ai_score
            FROM folder_creation_feedback 
            WHERE timestamp >= datetime('now', '-7 days')
            ORDER BY timestamp DESC
        ''')
        
        recent_folders = cursor.fetchall()
        conn.close()
        
        if not recent_folders:
            console.print("[yellow]No hay carpetas recientes para revisar.[/yellow]", markup=SUPPORTS_COLOR)
            return
        
        console.print(f"Encontradas {len(recent_folders)} carpetas creadas en los últimos 7 días.\n")
        
        for i, folder_data in enumerate(recent_folders, 1):
            folder_name, category, note_content, confidence, method_used, semantic_score, ai_score = folder_data
            
            console.print(f"[bold cyan]Carpeta {i}/{len(recent_folders)}:[/bold cyan]", markup=SUPPORTS_COLOR)
            console.print(f"  Nombre: [bold]{folder_name}[/bold]", markup=SUPPORTS_COLOR)
            console.print(f"  Categoría: {category}")
            console.print(f"  Confianza: {confidence:.2f}")
            console.print(f"  Método: {method_used}")
            console.print(f"  Contenido de la nota: {note_content[:100]}...")
            
            # Preguntar por feedback
            while True:
                feedback = input("\n¿Esta carpeta tiene sentido para ti? (si/no/explicación): ").strip().lower()
                
                if feedback in ['si', 'sí', 'yes', 'y', 'no', 'n']:
                    break
                elif feedback.startswith('explicación:') or feedback.startswith('explicacion:'):
                    break
                else:
                    console.print("[yellow]Por favor responde 'si', 'no', o 'explicación: tu explicación'[/yellow]", markup=SUPPORTS_COLOR)
            
            # Extraer explicación si la hay
            feedback_reason = ""
            if feedback.startswith('explicación:') or feedback.startswith('explicacion:'):
                feedback_reason = feedback.split(':', 1)[1].strip()
                feedback = feedback.split(':')[0].strip()
            
            # Crear información de carpeta para el aprendizaje
            folder_info = {
                'folder_name': folder_name,
                'category': category,
                'note_content': note_content,
                'confidence': confidence,
                'method_used': method_used,
                'semantic_score': semantic_score,
                'ai_score': ai_score
            }
            
            # Aprender del feedback
            learning_result = learning_system.learn_from_folder_creation(folder_info, feedback, feedback_reason)
            
            console.print(f"\n[green]✅ Feedback registrado y aprendido.[/green]", markup=SUPPORTS_COLOR)
            
            if learning_result['learning_insights']:
                console.print("Insights de aprendizaje:")
                for insight in learning_result['learning_insights']:
                    console.print(f"  • {insight}")
            
            # Preguntar si continuar
            if i < len(recent_folders):
                continue_review = input(f"\n¿Continuar con la siguiente carpeta? (si/no): ").strip().lower()
                if continue_review not in ['si', 'sí', 'yes', 'y']:
                    break
        
        console.print(f"\n[bold green]✅ Revisión de feedback completada.[/bold green]", markup=SUPPORTS_COLOR)
    
    else:
        console.print("[yellow]Especifica una opción: --stats, --interactive, o --suggest[/yellow]", markup=SUPPORTS_COLOR)

# --- Callback para error de comando faltante ---
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        console.print("[red]❗ Debes especificar un comando.[/red]", style="red")
        console.print("[bold blue]Mostrando ayuda general de la CLI:[/bold blue]\n")
        typer.echo(ctx.get_help())
        raise typer.Exit(1)

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print(' ' * 80, end='\r', flush=True)
        console.print("[cyan]👋 Saliste del flujo actual. ¡Hasta la próxima![/cyan]")
        sys.exit(0) 