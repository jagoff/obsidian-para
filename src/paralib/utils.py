import os
from pathlib import Path
from rich.panel import Panel
from rich import box
import functools
import typer
import json
import importlib.util
from rich.console import Console
import shutil
from datetime import datetime
from paralib.log_manager import PARALogManager

def shorten_path(path, max_len: int = 70):
    """Acorta una ruta para mostrarla de forma legible."""
    if isinstance(path, str):
        path = Path(path)
    path_str = str(path.resolve())
    home = str(Path.home())
    if path_str.startswith(home):
        path_str = "~" + path_str[len(home):]
    if len(path_str) <= max_len:
        return path_str
    parts = path_str.split(os.sep)
    if len(parts) > 4:
        return os.path.join(parts[0], parts[1], "...", *parts[-2:])
    return path_str

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

def auto_backup_if_needed(vault_path=None, reason="pre-action"):
    """
    Realiza un backup automático robusto. Si falla, loguea el error en logs/para.log y con PARALogManager.
    """
    import shutil
    from datetime import datetime
    from paralib.log_manager import PARALogManager
    log_path = Path("logs/para.log")
    log_path.parent.mkdir(exist_ok=True)
    logger = PARALogManager()
    try:
        if not vault_path:
            from paralib.vault import find_vault
            vault_path = find_vault()
        if not vault_path or not Path(vault_path).exists():
            msg = f"[CRITICAL] No se pudo determinar la ruta del vault para el backup automático."
            with open(log_path, "a") as f:
                f.write(msg + "\n")
            logger.analyze_log_file(str(log_path))
            return False
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"vault_backup_{ts}.zip"
        shutil.make_archive(str(backup_path).replace('.zip',''), 'zip', str(vault_path))
        msg = f"[BACKUP] Backup automático creado en {backup_path} ({reason})"
        with open(log_path, "a") as f:
            f.write(msg + "\n")
        logger.analyze_log_file(str(log_path))
        return True
    except Exception as e:
        msg = f"[CRITICAL] Error creando backup automático: {e}"
        with open(log_path, "a") as f:
            f.write(msg + "\n")
        logger.analyze_log_file(str(log_path))
        return False

def pre_command_checks(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from paralib.log_manager import PARALogManager
        log_path = Path("logs/para.log")
        log_path.parent.mkdir(exist_ok=True)
        logger = PARALogManager()
        if log_path.exists():
            with open(log_path, "w") as f:
                f.write("")
        chroma_db_path = Path.home() / "Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian/.para_db/chroma/chroma.sqlite3"
        if chroma_db_path.exists() and chroma_db_path.stat().st_size < 1024:
            msg = "[CRITICAL] La base de datos ChromaDB parece corrupta o vacía. Ejecuta 'doctor' o 'autoheal'."
            print(msg)
            with open(log_path, "a") as f:
                f.write(msg + "\n")
            logger.analyze_log_file(str(log_path))
        backups_dir = Path("backups")
        if not backups_dir.exists() or not any(backups_dir.glob("*.zip")):
            msg = "[ADVERTENCIA] No se encontró backup reciente. Se recomienda ejecutar un backup antes de organizar."
            print(msg)
            with open(log_path, "a") as f:
                f.write(msg + "\n")
            logger.analyze_log_file(str(log_path))
        import inspect
        destructive_commands = {"classify", "refactor", "clean", "reset"}
        command_name = func.__name__
        if command_name in destructive_commands:
            vault_path = None
            if "vault_path" in kwargs:
                vault_path = kwargs["vault_path"]
            elif len(args) > 0:
                vault_path = args[0] if isinstance(args[0], (str, Path)) else None
            from paralib.utils import auto_backup_if_needed
            if not auto_backup_if_needed(vault_path):
                msg = "[CRITICAL] Acción abortada por fallo en el backup automático."
                print(msg)
                with open(log_path, "a") as f:
                    f.write(msg + "\n")
                logger.analyze_log_file(str(log_path))
                raise typer.Exit(1)
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except Exception as e:
            msg = f"[CRITICAL] Error inesperado: {e}\nSugerencia: ejecuta 'python para_cli.py doctor' para limpiar y diagnosticar."
            print(msg)
            with open(log_path, "a") as f:
                f.write(msg + "\n")
            logger.analyze_log_file(str(log_path))
            raise
    return wrapper

def format_vault_found_message(vault_path, color='green'):
    """
    Devuelve un string formateado para mostrar un vault encontrado, usando el acortador y el color adecuado.
    """
    short = shorten_path(vault_path, 60)
    return f"[{color}]✅ Vault encontrado: [cyan]{short}[/cyan][/{color}]" 