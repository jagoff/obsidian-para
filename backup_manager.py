"""
backup_manager.py

Gestiona la creación de copias de seguridad del vault de Obsidian.
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
import sys
import os
from pathlib import Path
import shutil
from datetime import datetime
import argparse
from paralib.logger import logger
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

BACKUP_DIR = Path.cwd() / "backups"

# Decorador para loguear errores automáticamente
def log_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper

# Captura global de excepciones no manejadas
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Excepción no capturada", exc_info=(exc_type, exc_value, exc_traceback))
    print(f"[red]Excepción no capturada: {exc_value}[/red]")
sys.excepthook = handle_exception

def create_backup(vault_path: Path, reason: str = "pre-organization") -> Path | None:
    """Creates a timestamped zip backup of the vault."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_vault_name = "".join(c for c in vault_path.name if c.isalnum() or c in (' ', '_')).rstrip()
    backup_filename = f"backup_{safe_vault_name}_{timestamp}_{reason}.zip"
    backup_path = BACKUP_DIR / backup_filename
    console.print(Panel(f"🔒 Creando backup para vault: [cyan]{vault_path.name}[/cyan]", title="Backup Vault", style="bold blue", box=box.SIMPLE))
    try:
        shutil.make_archive(str(backup_path.with_suffix('')), 'zip', str(vault_path))
        console.print(Panel(f"✅ Backup exitoso: [yellow]{backup_path}[/yellow]", title="Backup OK", style="bold green", box=box.SIMPLE))
        return backup_path
    except Exception as e:
        console.print(Panel(f"❌ Backup fallido: {e}", title="Backup Error", style="bold red", box=box.SIMPLE))
        return None

def list_backups():
    """Lists available backups."""
    if not BACKUP_DIR.exists() or not any(BACKUP_DIR.glob('*.zip')):
        console.print(Panel("⚠️ No se encontraron backups.", style="bold yellow", box=box.SIMPLE))
        return []
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=os.path.getmtime, reverse=True)
    table = Table(title="Available Backups", show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("#", style="dim", width=3)
    table.add_column("Backup File", style="cyan")
    table.add_column("Date Created", style="green")
    table.add_column("Size (MB)", style="yellow", justify="right")
    for i, backup_file in enumerate(backups, 1):
        created_time = datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        size_mb = f"{backup_file.stat().st_size / (1024*1024):.2f}"
        table.add_row(str(i), backup_file.name, created_time, size_mb)
    console.print(table)
    return backups

def restore_backup(vault_path: Path):
    """Restores a vault from a selected backup."""
    console.print(Panel(f"🔄 Iniciando restauración para vault: [cyan]{vault_path.name}[/cyan]", title="Restaurar Vault", style="bold blue", box=box.SIMPLE))
    backups = list_backups()
    if not backups:
        return
    choice = Prompt.ask("Número de backup para restaurar", choices=[str(i) for i in range(1, len(backups) + 1)])
    backup_to_restore = backups[int(choice) - 1]
    console.print(Panel(f"⚠️ [bold yellow]¡Esto sobrescribirá completamente el contenido de '{vault_path.name}'![/bold yellow]", title="Advertencia", style="bold yellow", box=box.SIMPLE))
    if not Confirm.ask(f"¿Seguro que quieres restaurar desde '{backup_to_restore.name}'?", default=False):
        console.print(Panel("❌ Restauración cancelada por el usuario.", style="bold red", box=box.SIMPLE))
        return
    console.print(Panel("Creando backup de seguridad antes de restaurar...", style="bold blue", box=box.SIMPLE))
    safety_backup_path = create_backup(vault_path, reason="pre-restore")
    if not safety_backup_path:
        console.print(Panel("❌ No se pudo crear backup de seguridad. Abortando.", style="bold red", box=box.SIMPLE))
        return
    console.print(Panel(f"✅ Backup de seguridad creado en {safety_backup_path}", style="bold green", box=box.SIMPLE))
    try:
        console.print(Panel(f"Restaurando desde {backup_to_restore.name}...", style="bold blue", box=box.SIMPLE))
        with console.status("[bold red]Vaciando vault actual...[/bold]", spinner="dots"):
            for item in vault_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        with console.status(f"[bold green]Descomprimiendo {backup_to_restore.name}...[/bold]", spinner="earth"):
            shutil.unpack_archive(str(backup_to_restore), str(vault_path), 'zip')
        console.print(Panel("✅ [bold green]Restauración completa![/bold green]", style="bold green", box=box.SIMPLE))
    except Exception as e:
        console.print(Panel(f"❌ Error durante la restauración: {e}", style="bold red", box=box.SIMPLE))
        console.print(Panel(f"Tu vault puede estar en estado inconsistente. Puedes restaurar manualmente desde '{backup_to_restore}' o el backup de seguridad en '{safety_backup_path}'.", style="bold yellow", box=box.SIMPLE))

@log_exceptions
def main():
    parser = argparse.ArgumentParser(description="Backup and Restore manager for the PARA Organizer.")
    parser.add_argument('--action', choices=['backup', 'list', 'restore'], required=True, help='Acción a realizar')
    parser.add_argument('--vault-path', required=True, help='Ruta al vault de Obsidian')
    parser.add_argument('--backup-file', help='Archivo de backup para restaurar (solo para restore)')
    args = parser.parse_args()

    vault_path = Path(args.vault_path)

    if args.action == 'backup':
        backup = create_backup(vault_path)
        if backup:
            print(f"Backup creado exitosamente: {backup}")
        else:
            print("Error al crear el backup.")
    elif args.action == 'list':
        list_backups()
    elif args.action == 'restore':
        if not args.backup_file:
            print("Debes especificar --backup-file para restaurar.")
            return
        restore_backup(vault_path)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt):
        console.print(f"\n[bold red]Operation cancelled by user.[/bold red]")
        sys.exit(0)
