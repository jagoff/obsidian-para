import os
from pathlib import Path
from rich.panel import Panel
from rich import box
import functools
import typer
import json
import importlib.util

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

def auto_backup_if_needed(vault_path=None, reason="pre-action"):
    """
    Realiza un backup automático si está activado en la configuración.
    Si vault_path es None, intenta cargarlo de la configuración.
    Devuelve True si el backup fue exitoso o no era necesario, False si falló.
    """
    config_path = Path("para_config.json")
    if not config_path.exists():
        config_path = Path("para_config.default.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    auto_backup = config.get("auto_backup", True)
    if not auto_backup:
        return True  # No se requiere backup
    if not vault_path:
        vault_path = config.get("vault_path")
    if not vault_path:
        print("[CRITICAL] No se pudo determinar la ruta del vault para el backup automático.")
        return False
    vault_path = Path(vault_path)
    # Importar create_backup dinámicamente para evitar dependencias circulares
    backup_manager_path = Path("backup_manager.py")
    if not backup_manager_path.exists():
        print("[CRITICAL] No se encontró backup_manager.py para realizar el backup.")
        return False
    spec = importlib.util.spec_from_file_location("backup_manager", str(backup_manager_path))
    backup_manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup_manager)
    backup_path = backup_manager.create_backup(vault_path, reason=reason)
    if not backup_path:
        print("[CRITICAL] El backup automático falló. Abortando acción para proteger tus datos.")
        return False
    return True

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
        # --- NUEVO: Backup automático antes de acciones destructivas ---
        # Detectar si el comando es de organización (classify, refactor, clean, reset, etc.)
        import inspect
        destructive_commands = {"classify", "refactor", "clean", "reset"}
        command_name = func.__name__
        if command_name in destructive_commands:
            # Intentar obtener vault_path del primer argumento o de kwargs
            vault_path = None
            if "vault_path" in kwargs:
                vault_path = kwargs["vault_path"]
            elif len(args) > 0:
                # Buscar si el primer argumento es vault_path
                vault_path = args[0] if isinstance(args[0], (str, Path)) else None
            if not auto_backup_if_needed(vault_path):
                print("[CRITICAL] Acción abortada por fallo en el backup automático.")
                raise typer.Exit(1)
        # --- FIN NUEVO ---
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            # typer.Exit es una salida controlada, no un error
            raise
        except Exception as e:
            print(f"[CRITICAL] Error inesperado: {e}\nSugerencia: ejecuta 'python para_cli.py doctor' para limpiar y diagnosticar.")
            raise
    return wrapper 