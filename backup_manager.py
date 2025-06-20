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

# Use rich for better UI, but handle if it's not installed, since this can be a standalone script.
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich' for a better UI experience.")
    # Create dummy classes to avoid crashing if rich is not installed
    class Console:
        def print(self, *args, **kwargs): print(*args)
    class Prompt:
        @staticmethod
        def ask(prompt, **kwargs): return input(prompt)
    class Confirm:
        @staticmethod
        def ask(prompt, **kwargs):
            response = input(f"{prompt} [y/n]: ").lower()
            return response == 'y'

console = Console()

BACKUP_DIR = Path.cwd() / "backups"

def create_backup(vault_path: Path, reason: str = "pre-organization") -> Path | None:
    """Creates a timestamped zip backup of the vault."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize vault name for filename
    safe_vault_name = "".join(c for c in vault_path.name if c.isalnum() or c in (' ', '_')).rstrip()
    backup_filename = f"backup_{safe_vault_name}_{timestamp}_{reason}.zip"
    backup_path = BACKUP_DIR / backup_filename
    
    console.print(f"\n🔒 [bold]Creating backup for vault:[/bold] [cyan]{vault_path.name}[/cyan]")
    
    try:
        shutil.make_archive(str(backup_path.with_suffix('')), 'zip', str(vault_path))
        console.print(f"✅ [bold green]Backup successful:[/bold green] [yellow]{backup_path}[/yellow]")
        return backup_path
    except Exception as e:
        console.print(f"[bold red]Backup failed: {e}[/bold red]")
        return None

def list_backups():
    """Lists available backups."""
    if not BACKUP_DIR.exists() or not any(BACKUP_DIR.glob('*.zip')):
        console.print("[yellow]No backups found.[/yellow]")
        return []

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=os.path.getmtime, reverse=True)
    
    table = Table(title="Available Backups", show_header=True, header_style="bold magenta")
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
    console.print(f"\n🔄 [bold]Starting restore process for vault:[/bold] [cyan]{vault_path.name}[/cyan]")
    backups = list_backups()
    if not backups:
        return

    choice = Prompt.ask("Enter the number of the backup to restore", choices=[str(i) for i in range(1, len(backups) + 1)])
    backup_to_restore = backups[int(choice) - 1]

    console.print(f"[bold yellow]WARNING: This will completely overwrite the contents of '{vault_path.name}'.[/bold yellow]")
    if not Confirm.ask(f"Are you sure you want to restore from '{backup_to_restore.name}'?", default=False):
        console.print("[bold]Restore cancelled by user.[/bold]")
        return

    # Create a backup of the current state before restoring
    console.print("Creating a safety backup of the current state before restoring...")
    safety_backup_path = create_backup(vault_path, reason="pre-restore")
    if not safety_backup_path:
        console.print("[bold red]Could not create safety backup. Aborting restore.[/bold red]")
        return
    
    console.print(f"✅ Safety backup created at {safety_backup_path}")

    try:
        console.print(f"Restoring from {backup_to_restore.name}...")
        # Empty the vault directory
        with console.status("[bold red]Emptying current vault directory...[/bold]", spinner="dots"):
             for item in vault_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Unzip the backup
        with console.status(f"[bold green]Unzipping {backup_to_restore.name}...[/bold]", spinner="earth"):
            shutil.unpack_archive(str(backup_to_restore), str(vault_path), 'zip')
        
        console.print("\n✅ [bold green]Restore complete![/bold green]")

    except Exception as e:
        console.print(f"[bold red]An error occurred during restore: {e}[/bold red]")
        console.print(f"Your vault may be in an inconsistent state. You can manually restore from '{backup_to_restore}' or the safety backup at '{safety_backup_path}'.")

def main():
    parser = argparse.ArgumentParser(description="Backup and Restore manager for the PARA Organizer.")
    parser.add_argument("--action", choices=['list', 'restore'], required=True, help="Action to perform.")
    parser.add_argument("--vault-path", required=True, help="Path to the Obsidian vault.")
    args = parser.parse_args()
    
    vault_path = Path(args.vault_path).expanduser().resolve()
    if not vault_path.is_dir():
        console.print(f"[bold red]Error: Path '{vault_path}' is not a valid directory.[/bold red]")
        sys.exit(1)
        
    if args.action == 'list':
        list_backups()
    elif args.action == 'restore':
        restore_backup(vault_path)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt):
        console.print(f"\n[bold red]Operation cancelled by user.[/bold red]")
        sys.exit(0)
