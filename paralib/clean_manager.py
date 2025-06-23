#!/usr/bin/env python3
"""
paralib/clean_manager.py

Limpieza interactiva y exhaustiva de notas: duplicados, vacíos, no Markdown, corruptos, etc.
UI/UX consistente con el resto del sistema (Rich, prompts, paneles).
"""
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box
import os
import shutil
from paralib.logger import logger

console = Console()


def find_duplicates(note_paths):
    """Devuelve un dict: nombre -> lista de rutas con ese nombre (si hay más de una)."""
    from collections import defaultdict
    name_map = defaultdict(list)
    for p in note_paths:
        name_map[p.name].append(p)
    return {k: v for k, v in name_map.items() if len(v) > 1}

def find_empty_files(note_paths):
    return [p for p in note_paths if p.stat().st_size == 0]

def find_non_md_files(all_paths):
    return [p for p in all_paths if p.is_file() and p.suffix.lower() != ".md"]

def find_corrupt_or_unreadable(note_paths):
    corrupt = []
    for p in note_paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                f.read(100)
        except Exception:
            corrupt.append(p)
    return corrupt

def log_action(action, details):
    logger.info(f"[CLEAN-MANAGER] {action}: {details}")

def run_clean_manager(vault_path: Path):
    """
    Flujo interactivo de limpieza de notas en el vault.
    """
    console.print(Panel(f"[bold blue]🔍 Iniciando limpieza interactiva en:[/bold blue]\n[yellow]{vault_path}[/yellow]", title="Clean Manager", style="bold blue", box=box.SIMPLE))
    # Recorrer recursivo
    all_files = list(vault_path.rglob("*"))
    note_paths = [p for p in all_files if p.is_file() and p.suffix.lower() == ".md"]
    # 1. Duplicados
    duplicates = find_duplicates(note_paths)
    if duplicates:
        console.print(Panel(f"[yellow]Se encontraron {len(duplicates)} nombres de nota duplicados.[/yellow]", title="Duplicados", style="yellow", box=box.SIMPLE))
        for name, paths in duplicates.items():
            table = Table(title=f"'{name}'", box=box.MINIMAL)
            table.add_column("Ruta", style="cyan")
            for p in paths:
                table.add_row(str(p.relative_to(vault_path)))
            console.print(table)
        action = Prompt.ask("¿Qué hacer con los duplicados?", choices=["renombrar", "mover", "saltar"], default="renombrar")
        for name, paths in duplicates.items():
            for i, p in enumerate(paths):
                if action == "renombrar":
                    new_name = f"{p.stem}_{i+1}{p.suffix}"
                    new_path = p.with_name(new_name)
                    p.rename(new_path)
                    log_action("renombrado duplicado", f"{p} -> {new_path}")
                elif action == "mover":
                    target = vault_path / "_Duplicados" / p.name
                    target.parent.mkdir(exist_ok=True)
                    shutil.move(str(p), str(target))
                    log_action("mover duplicado", f"{p} -> {target}")
                elif action == "saltar":
                    log_action("saltar duplicado", str(p))
    else:
        console.print(Panel("[green]No se encontraron notas duplicadas.[/green]", title="Duplicados", style="green", box=box.SIMPLE))
    # 2. Vacíos
    empties = find_empty_files(note_paths)
    if empties:
        console.print(Panel(f"[yellow]Se encontraron {len(empties)} archivos vacíos.[/yellow]", title="Vacíos", style="yellow", box=box.SIMPLE))
        if Confirm.ask("¿Eliminar todos los archivos vacíos?", default=True):
            for p in empties:
                p.unlink()
                log_action("eliminar vacío", str(p))
    else:
        console.print(Panel("[green]No se encontraron archivos vacíos.[/green]", title="Vacíos", style="green", box=box.SIMPLE))
    # 3. No Markdown
    non_md = find_non_md_files(all_files)
    if non_md:
        console.print(Panel(f"[yellow]Se encontraron {len(non_md)} archivos no Markdown.[/yellow]", title="No Markdown", style="yellow", box=box.SIMPLE))
        if Confirm.ask("¿Mover todos los archivos no Markdown a '_NonMarkdown'?", default=True):
            target_dir = vault_path / "_NonMarkdown"
            target_dir.mkdir(exist_ok=True)
            for p in non_md:
                shutil.move(str(p), str(target_dir / p.name))
                log_action("mover no-md", f"{p} -> {target_dir / p.name}")
    else:
        console.print(Panel("[green]No se encontraron archivos no Markdown.[/green]", title="No Markdown", style="green", box=box.SIMPLE))
    # 4. Corruptos o no legibles
    corrupt = find_corrupt_or_unreadable(note_paths)
    if corrupt:
        console.print(Panel(f"[red]Se encontraron {len(corrupt)} archivos corruptos o no legibles.[/red]", title="Corruptos", style="red", box=box.SIMPLE))
        if Confirm.ask("¿Eliminar todos los archivos corruptos?", default=False):
            for p in corrupt:
                p.unlink()
                log_action("eliminar corrupto", str(p))
    else:
        console.print(Panel("[green]No se encontraron archivos corruptos o ilegibles.[/green]", title="Corruptos", style="green", box=box.SIMPLE))
    # Resumen final
    console.print(Panel("[bold green]✅ Limpieza completada. Todas las acciones han sido registradas en logs/para.log[/bold green]", title="Resumen", style="bold green", box=box.SIMPLE)) 