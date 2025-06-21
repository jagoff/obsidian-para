import os
from pathlib import Path
from rich.panel import Panel
from rich import box
import functools

def shorten_path(path, n=3):
    parts = os.path.normpath(str(path)).split(os.sep)
    if 'Obsidian' in parts:
        idx = parts.index('Obsidian')
        if idx > 0 and parts[idx-1] == 'Mi unidad':
            return 'Mi unidad/Obsidian'
        return 'Obsidian'
    return parts[-1]

def check_recent_errors(console, supports_color):
    import re
    log_path = os.path.join(os.path.dirname(__file__), '../logs/para.log')
    marker_path = os.path.join(os.path.dirname(__file__), '../logs/.last_clean_marker')
    if not os.path.exists(log_path):
        return
    last_clean = 0
    if os.path.exists(marker_path):
        with open(marker_path, 'r') as m:
            try:
                last_clean = float(m.read().strip())
            except Exception:
                last_clean = 0
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-100:]
    error_lines = []
    for l in lines:
        match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', l)
        if match:
            import time, datetime
            ts = time.mktime(datetime.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").timetuple())
            if ts > last_clean:
                if 'ERROR' in l or 'CRITICAL' in l:
                    error_lines.append(l)
    if error_lines:
        console.print("[bold red]Se detectaron errores recientes en el sistema:[/bold red]", markup=supports_color)
        for l in error_lines[-5:]:
            console.print(f"[red]{l.strip()}[/red]", markup=supports_color)
        console.print("[yellow]Revisa el archivo logs/para.log para más detalles o ejecuta 'para doctor' para sugerencias automáticas.[/yellow]", markup=supports_color)

def pre_command_checks(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log_path = Path("logs/para.log")
        if log_path.exists():
            with open(log_path, "w") as f:
                f.write("")
        chroma_db_path = Path.home() / "Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian/.para_db/chroma/chroma.sqlite3"
        if chroma_db_path.exists() and chroma_db_path.stat().st_size < 1024:
            print("[CRITICAL] La base de datos ChromaDB parece corrupta o vacía. Ejecuta 'doctor' o 'autoheal'.")
        backups_dir = Path("backups")
        if not backups_dir.exists() or not any(backups_dir.glob("*.zip")):
            print("[ADVERTENCIA] No se encontró backup reciente. Se recomienda ejecutar un backup antes de organizar.")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[CRITICAL] Error inesperado: {e}\nSugerencia: ejecuta 'python para_cli.py doctor' para limpiar y diagnosticar.")
            raise
    return wrapper 