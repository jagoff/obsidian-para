#!/usr/bin/env python3
"""
para.py

Punto de entrada unificado para el sistema PARA.
Permite instalar dependencias, lanzar dashboard, CLI y tareas comunes desde un solo menú.
"""
import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

console = Console()

VENV_DIR = Path('venv')
PYTHON = sys.executable

# ----------------------
# Funciones de utilidades
# ----------------------
def check_python():
    if not shutil.which('python3'):
        console.print("[red]❌ Python 3 no está instalado.[/red]")
        sys.exit(1)
    return shutil.which('python3')

def check_venv():
    if not VENV_DIR.exists():
        console.print("[yellow]Creando entorno virtual...[/yellow]")
        subprocess.run([PYTHON, '-m', 'venv', 'venv'], check=True)
        console.print("[green]Entorno virtual creado.[/green]")
    else:
        console.print("[green]Entorno virtual ya existe.[/green]")

def run_in_venv(cmd, check=True):
    activate = str(VENV_DIR / 'bin' / 'activate')
    full_cmd = f"source {activate} && {cmd}"
    return subprocess.run(full_cmd, shell=True, check=check, executable='/bin/bash')

def install_dependencies():
    check_venv()
    console.print("[yellow]Instalando dependencias...[/yellow]")
    run_in_venv("pip install --upgrade pip", check=True)
    run_in_venv("pip install -r requirements.txt", check=True)
    console.print("[green]Dependencias instaladas.[/green]")

def check_ollama():
    if not shutil.which('ollama'):
        console.print("[yellow]Ollama no encontrado. Instalando...[/yellow]")
        if sys.platform == 'darwin':
            subprocess.run("curl -fsSL https://ollama.ai/install.sh | sh", shell=True, check=True)
        else:
            console.print("[red]Por favor instala Ollama manualmente desde https://ollama.ai[/red]")
            sys.exit(1)
    else:
        console.print(f"[green]Ollama encontrado: {shutil.which('ollama')}[/green]")

def start_ollama():
    # Verifica si Ollama está corriendo
    import socket
    s = socket.socket()
    try:
        s.connect(('localhost', 11434))
        s.close()
        console.print("[green]Ollama ya está corriendo.[/green]")
        return
    except Exception:
        pass
    console.print("[yellow]Iniciando Ollama...[/yellow]")
    subprocess.Popen(['ollama', 'serve'])
    time.sleep(5)
    console.print("[green]Ollama iniciado.[/green]")

def download_ollama_model():
    model = "llama3.2:3b"
    console.print(f"[yellow]Descargando modelo Ollama: {model}...[/yellow]")
    subprocess.run(["ollama", "pull", model], check=True)
    console.print("[green]Modelo descargado.[/green]")

def create_config():
    config_path = Path('para_config.json')
    if not config_path.exists():
        config = '{\n    "vault_path": "",\n    "chroma_db_path": "./para_chroma_db",\n    "ollama_host": "http://localhost:11434",\n    "ollama_model": "llama3.2:3b",\n    "dashboard_port": 7860,\n    "auto_backup": true,\n    "backup_path": "./backups"\n}\n'
        config_path.write_text(config)
        console.print("[green]Archivo de configuración creado.[/green]")
    else:
        console.print("[green]Archivo de configuración ya existe.[/green]")

def install_all():
    check_python()
    install_dependencies()
    check_ollama()
    start_ollama()
    download_ollama_model()
    create_config()
    Path('backups').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    console.print("[bold green]✅ Instalación completa![/bold green]")

def launch_dashboard():
    check_venv()
    start_ollama()
    port = Prompt.ask("Puerto para dashboard", default="8501")
    run_in_venv(f"streamlit run para_backend_dashboard.py --server.port {port} --server.headless true --server.runOnSave true", check=False)

def launch_cli():
    check_venv()
    run_in_venv("python para_cli.py", check=False)

def show_logs():
    log_path = Path('logs/para.log')
    if log_path.exists():
        os.system(f"tail -n 40 {log_path}")
    else:
        console.print("[yellow]No se encontró logs/para.log[/yellow]")

def backup():
    check_venv()
    run_in_venv("python para_cli.py backup", check=False)

def restore_backup():
    check_venv()
    run_in_venv("python para_cli.py restore-backup", check=False)

def main_menu():
    while True:
        console.print(Panel("[bold blue]PARA System - Menú Principal[/bold blue]", expand=False))
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Opción", style="cyan")
        table.add_column("Acción", style="white")
        table.add_row("1", "Instalar/Actualizar sistema completo")
        table.add_row("2", "Lanzar Dashboard web")
        table.add_row("3", "Lanzar CLI interactiva")
        table.add_row("4", "Backup del vault")
        table.add_row("5", "Restaurar backup")
        table.add_row("6", "Ver logs recientes")
        table.add_row("0", "Salir")
        console.print(table)
        opt = Prompt.ask("Selecciona una opción", choices=["1","2","3","4","5","6","0"], default="3")
        if opt == "1":
            install_all()
        elif opt == "2":
            launch_dashboard()
        elif opt == "3":
            launch_cli()
        elif opt == "4":
            backup()
        elif opt == "5":
            restore_backup()
        elif opt == "6":
            show_logs()
        elif opt == "0":
            console.print("[bold green]¡Hasta luego![/bold green]")
            break

if __name__ == "__main__":
    main_menu() 