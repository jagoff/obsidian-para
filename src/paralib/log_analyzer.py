"""
paralib/log_analyzer.py

Analiza el archivo de log para detectar errores y sugiere o aplica soluciones automáticas, incluyendo autocorrección de código con IA (Ollama).
Registra los bugs resueltos en ChromaDB y marca el código con un comentario de tilde y descripción.
"""
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
import shutil
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    RICH = True
except ImportError:
    RICH = False

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'para.log')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'autofix_backups')

# ChromaDB para historial de bugs autocorregidos
try:
    from paralib.db import ChromaPARADatabase
    # chroma_db = ChromaPARADatabase()  # COMENTADO: No instanciar sin parámetros
    chroma_db = None
except Exception:
    chroma_db = None

SUGGESTIONS = {
    'OSError': 'Verifica permisos de archivos y rutas configuradas.',
    'FileNotFoundError': 'Revisa que las rutas de vault y backups existan.',
    'ModuleNotFoundError': 'Faltan dependencias. Ejecutando: pip install -r requirements.txt',
    'ConnectionRefusedError': 'El servicio Ollama o ChromaDB no está corriendo. Intentando iniciar servicios...',
    'PermissionError': 'Permisos insuficientes. Intentando ajustar permisos...'
}

ACTIONS = {
    'ModuleNotFoundError': lambda: subprocess.run(['pip', 'install', '-r', 'requirements.txt']),
    'ConnectionRefusedError': lambda: subprocess.run(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
    'PermissionError': lambda: subprocess.run(['chmod', '-R', '755', '.']),
}

def already_fixed_bug(file_path, line_num, error_signature):
    """Consulta ChromaDB para saber si este bug ya fue autocorregido."""
    if not chroma_db:
        return False
    results = chroma_db.search_similar_notes(f"{file_path}:{line_num}:{error_signature}")
    return bool(results and results.get('documents'))

def register_fixed_bug(file_path, line_num, error_signature, description):
    """Registra el bug autocorregido en ChromaDB."""
    if not chroma_db:
        return
    try:
        chroma_db.add_or_update_note(
            note_path=Path(f"autofix_{file_path.replace('/', '_')}_{line_num}"),
            content=f"Auto-fix: {error_signature}",
            category="auto-fix",
            project_name="PARA"
        )
    except Exception:
        pass  # Continuar sin fallar si ChromaDB tiene problemas

def call_ollama_fix(file_path, line_num, error_message, code_context):
    """Llama a Ollama local para sugerir y aplicar un parche automático, marcando el fix."""
    import ollama
    with open(file_path, 'r', encoding='utf-8') as f:
        original_code = f.readlines()
    error_signature = error_message.strip().split('\n')[-1][:120]
    if already_fixed_bug(file_path, line_num, error_signature):
        print(f"[✓] Bug ya autocorregido previamente en {file_path}:{line_num}")
        return
    prompt = f"""
Corrige el siguiente error de Python en el archivo {os.path.basename(file_path)}:

Error:
{error_message}

Código relevante:
{code_context}

Devuelve solo el código corregido, pero en la línea corregida agrega un comentario así:
# ✓ [AUTO-FIXED] Bug: {error_signature} - corregido el {datetime.now().date()} por IA
"""
    response = ollama.chat(model='llama3', messages=[{"role": "user", "content": prompt}])
    fixed_code = response['message']['content']
    # Backup antes de modificar
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f"{os.path.basename(file_path)}_{timestamp}.bak")
    shutil.copy2(file_path, backup_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    print(f"[OK] Parche automático aplicado a {file_path}. Backup en {backup_path}")
    register_fixed_bug(file_path, line_num, error_signature, error_message)

def analyze_and_fix_log():
    if not os.path.exists(LOG_PATH):
        if RICH:
            Console().print(Panel("No se encontró el archivo de log para analizar.", title="[red]Sin log[/red]"))
        else:
            print("No se encontró el archivo de log para analizar.")
        return
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-500:]
    error_lines = [l for l in lines if 'ERROR' in l or 'CRITICAL' in l]
    if not error_lines:
        if RICH:
            Console().print(Panel("No se detectaron errores recientes.", title="[green]Sin errores[/green]"))
        else:
            print("No se detectaron errores recientes.")
        return
    # --- Errores actuales ---
    current_errors = []
    error_types = []
    tracebacks = []
    for l in error_lines:
        match = re.search(r'([A-Za-z]+Error)', l)
        if match:
            error_types.append(match.group(1))
        # Agrupar tracebacks
        if 'Traceback' in l or l.strip().startswith('File '):
            tracebacks.append(l)
        else:
            current_errors.append(l.strip())
    # Mostrar errores actuales
    if RICH:
        console = Console()
        if current_errors:
            error_panel = Panel('\n'.join(current_errors[-5:]), title="[red]Errores detectados[/red]", border_style="red")
            console.print(error_panel)
        else:
            console.print(Panel("No se detectaron errores recientes.", title="[green]Sin errores[/green]", border_style="green"))
        if tracebacks:
            tb_panel = Panel(Syntax(''.join(tracebacks[-20:]), 'python', theme='ansi_dark', line_numbers=False), title="[yellow]Traceback[/yellow]", border_style="yellow")
            console.print(tb_panel)
    else:
        print("\n[Errores detectados]")
        for l in current_errors[-5:]:
            print(l)
        if tracebacks:
            print("\n[Traceback]")
            print(''.join(tracebacks[-20:]))
    # --- Sugerencias y fixes ---
    counter = Counter(error_types)
    fixes = []
    for l in error_lines:
        # Detectar tracebacks de Python y autocorregir
        tb_match = re.search(r'File "([^"]+)", line (\d+)', l)
        if tb_match:
            file_path, line_num = tb_match.group(1), int(tb_match.group(2))
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_lines = f.readlines()
                start = max(0, line_num-6)
                end = min(len(code_lines), line_num+5)
                code_context = ''.join(code_lines[start:end])
                if RICH:
                    console.print(f"[yellow]Intentando autocorregir {file_path} línea {line_num} con IA...[/yellow]")
                else:
                    print(f"Intentando autocorregir {file_path} línea {line_num} con IA...")
                call_ollama_fix(file_path, line_num, l, code_context)
    for err, count in counter.most_common():
        # Ejecutar acción automática si está definida
        if err in ACTIONS:
            try:
                ACTIONS[err]()
                fixes.append(f"[OK] Acción automática ejecutada para {err}.")
            except Exception as e:
                fixes.append(f"[FALLO] No se pudo resolver {err} automáticamente: {e}")
    # Mostrar fixes aplicados
    if RICH and fixes:
        console.print(Panel('\n'.join(fixes), title="[green]Fixes aplicados[/green]", border_style="green"))
    elif fixes:
        print("\n[Fixes aplicados]")
        for f in fixes:
            print(f)
    # --- Bugs resueltos (solo una línea por bug, al final) ---
    if chroma_db:
        resolved = chroma_db.get_all_notes_metadata()
        if resolved:
            unique_bugs = {}
            for note in resolved:
                key = note['content'].split(':')[0:3]  # file:line:error_signature
                key = ':'.join(key)
                if key not in unique_bugs:
                    unique_bugs[key] = note
            lines = [f"✓ {bug['content']} ({bug['metadata'].get('fixed_at','')})" for bug in unique_bugs.values()]
            if RICH:
                console.print(Panel('\n'.join(lines), title="[magenta]Bugs resueltos por IA[/magenta]", border_style="magenta"))
            else:
                print("\n[Bugs resueltos por IA]")
                for l in lines:
                    print(l)
    # --- Resumen ---
    resumen = f"❌ {len(current_errors)} errores actuales. 🛠️ {len(fixes)} fixes aplicados. ✓ {len(lines) if chroma_db and resolved else 0} bugs resueltos por IA."
    if RICH:
        console.print(Panel(resumen, title="[bold blue]Resumen[/bold blue]", border_style="blue"))
    else:
        print("\n[Resumen]")
        print(resumen)

if __name__ == "__main__":
    analyze_and_fix_log() 