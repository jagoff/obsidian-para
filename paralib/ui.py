"""
paralib/ui.py

Módulo para todos los componentes de la interfaz de usuario en la terminal.
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
from pathlib import Path
from collections import Counter
import termios
import sys
import tty
import time
import select

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from .db import ChromaPARADatabase
from paralib.logger import logger

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.layout import Layout as PtLayout
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

console = Console()

class TreeNode:
    """Nodo en la estructura de árbol para el selector."""
    def __init__(self, path: Path, parent=None):
        self.path = path
        self.name = path.name
        self.parent = parent
        self.children = []
        self.is_expanded = False
        self.is_selected = False
        self.is_dir = path.is_dir()

    def add_child(self, node):
        self.children.append(node)

    def toggle_expanded(self):
        if self.is_dir:
            self.is_expanded = not self.is_expanded

    def toggle_selected(self, recursive=True):
        self.is_selected = not self.is_selected
        # Selección recursiva hacia abajo
        if recursive and self.children:
            for child in self.children:
                child.set_selected(self.is_selected, recursive=True)
        # Selección hacia arriba
        if self.parent and not self.is_selected:
            self.parent.set_selected(False, recursive=False)
        if self.parent and self.is_selected:
            if all(child.is_selected for child in self.parent.children):
                self.parent.set_selected(True, recursive=False)

    def set_selected(self, value, recursive=True):
        self.is_selected = value
        if recursive and self.children:
            for child in self.children:
                child.set_selected(value, recursive=True)


def build_tree(path, parent=None, is_root=True):
    node = TreeNode(path, parent)
    node.is_expanded = is_root  # Solo la raíz expandida al inicio
    if path.is_dir():
        try:
            for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                if child.name.startswith('.'):
                    continue
                if child.is_dir():
                    node.add_child(build_tree(child, node, is_root=False))
        except Exception:
            pass
    return node


def normalize_folder_name(name: str) -> str:
    """Normaliza el nombre de carpeta PARA para comparación insensible a mayúsculas/minúsculas y espacios."""
    return name.lower().replace('-', '').replace(' ', '')

PROTECTED_FOLDERS = {normalize_folder_name(n) for n in [
    "01-Projects", "02-Areas", "03-Resources", "04-Archive", "00-Inbox", "Inbox", "00-inbox", "01-projects", "02-areas", "03-resources", "04-archive"
]}

def select_folders_to_exclude(vault_path: Path) -> list[str]:
    """
    Selector de carpetas en árbol, solo la raíz expandida al inicio.
    """
    root_node = build_tree(vault_path, is_root=True)
    flat_nodes = []

    def flatten(node, level=0):
        flat_nodes.append((node, level))
        if node.is_expanded:
            for child in node.children:
                flatten(child, level+1)

    def update_flat_nodes():
        flat_nodes.clear()
        flatten(root_node, 0)

    update_flat_nodes()
    current_line = 0

    bindings = KeyBindings()

    @bindings.add('c-c')
    @bindings.add('q')
    def _(event):
        event.app.exit(result=[])

    @bindings.add('down')
    def _(event):
        nonlocal current_line
        current_line = min(current_line + 1, len(flat_nodes) - 1)

    @bindings.add('up')
    def _(event):
        nonlocal current_line
        current_line = max(current_line - 1, 0)

    @bindings.add('right')
    def _(event):
        node, _ = flat_nodes[current_line]
        # No expandir el nodo raíz
        if node.parent is not None:
            node.toggle_expanded()
            update_flat_nodes()

    @bindings.add('left')
    def _(event):
        nonlocal current_line
        node, _ = flat_nodes[current_line]
        # No colapsar el nodo raíz ni navegar hacia su padre
        if node.parent is not None:
            if node.is_expanded:
                node.toggle_expanded()
                update_flat_nodes()
            elif node.parent:
                # Solo navegar hacia el padre si no es el nodo raíz
                parent_idx = None
                for idx, (n, lvl) in enumerate(flat_nodes):
                    if n == node.parent:
                        parent_idx = idx
                        break
                if parent_idx is not None:
                    current_line = parent_idx

    @bindings.add(' ')  # Espacio para seleccionar
    def _(event):
        node, _ = flat_nodes[current_line]
        # No seleccionar el nodo raíz
        if node.parent is not None:
            node.toggle_selected()
            update_flat_nodes()

    @bindings.add('enter')
    def _(event):
        selected = [str(node.path.resolve()) for node, _ in flat_nodes if node.is_selected and node.is_dir]
        event.app.exit(result=selected)

    def get_formatted_text():
        result = []
        for i, (node, level) in enumerate(flat_nodes):
            prefix = '  ' * level
            icon = '▼' if node.is_expanded and node.children else ('▶' if node.children else ' ')
            checkbox = '[X]' if node.is_selected else '[ ]'
            style = 'class:reverse' if i == current_line else ''
            result.append((style, f"{prefix}{icon} {checkbox} {node.name}\n"))
        if not result:
            result.append(('', 'No hay directorios para mostrar.'))
        return result

    header = "Seleccioná carpetas a excluir. [Espacio] marca, [Enter] confirma, [q] sale.\n" + \
             "---------------------------------------------------------------------\n"
    control = FormattedTextControl(get_formatted_text)
    layout = PtLayout(
        container=HSplit([
            Window(content=FormattedTextControl(header), height=2),
            Window(content=control)
        ])
    )
    app = Application(layout=layout, key_bindings=bindings, full_screen=True)
    try:
        selected_paths = app.run()
        return selected_paths if selected_paths else []
    except Exception as e:
        console.print(f"[bold red]Ocurrió un error en el selector: {e}[/bold red]")
        return []


def display_search_results(results: list[tuple[dict, float]], vault_path: Path):
    """
    Muestra los resultados de la búsqueda semántica en una tabla de Rich.
    """
    if not results:
        console.print("\n[yellow]No se encontraron resultados para tu búsqueda.[/yellow]")
        return

    table = Table(title="Resultados de la Búsqueda Semántica", show_header=True, header_style="bold magenta")
    table.add_column("Relevancia", style="cyan", justify="center")
    table.add_column("Nota", style="green")
    table.add_column("Categoría", justify="center")
    table.add_column("Ruta Relativa", style="dim")
    
    # La distancia de ChromaDB es menor cuanto más similar es. La invertimos para mostrar una "relevancia".
    max_dist = max(d for _, d in results) if results else 1
    
    for metadata, distance in results:
        relevance_score = max(0, 1 - (distance / (max_dist + 0.1))) # Evitar división por cero
        relevance_bar = "█" * int(relevance_score * 10)
        
        category = metadata.get('category', 'N/A')
        project = metadata.get('project_name')
        if project:
            category = f"{category}/{project}"
            
        try:
            relative_path = Path(metadata['path']).relative_to(vault_path)
        except (KeyError, ValueError):
            relative_path = metadata.get('path', 'N/A')

        table.add_row(
            f"{relevance_score:.0%}\n{relevance_bar}",
            metadata.get('filename', 'N/A'),
            category,
            str(relative_path)
        )
        
    console.print(table)


def run_monitor_dashboard(db: ChromaPARADatabase):
    """
    Ejecuta el dashboard interactivo que se actualiza en tiempo real.
    """
    def generate_dashboard() -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(ratio=1, name="main"),
            Layout(size=3, name="footer")
        )

        metadatas = db.get_all_notes_metadata()
        total_notes = len(metadatas)
        category_counts = Counter(meta.get('category', 'Sin categoría') for meta in metadatas)

        header_text = f"🗂️  [bold blue]Monitor del Vault PARA[/bold blue] ([dim]Press 'q' to quit[/dim])"
        layout["header"].update(Panel(header_text, style="bold", border_style="blue"))

        stats_table = Table(title="Estadísticas Generales", show_header=False, box=None)
        stats_table.add_column()
        stats_table.add_column(style="magenta", justify="right")
        stats_table.add_row("Total de notas en la BD:", str(total_notes))

        category_table = Table(title="Distribución por Categoría", box=None, show_header=True, header_style="bold green")
        category_table.add_column("Categoría")
        category_table.add_column("Cantidad", justify="right")
        category_table.add_column("Porcentaje", justify="right")

        for category, count in category_counts.most_common():
            percentage = (count / total_notes * 100) if total_notes > 0 else 0
            category_table.add_row(category.capitalize(), str(count), f"{percentage:.1f}%")
        
        main_layout = Layout()
        main_layout.split_row(Panel(stats_table), Panel(category_table))
        layout["main"].update(main_layout)
        
        footer_text = f"[dim]Última actualización: {time.strftime('%H:%M:%S')}[/dim]"
        layout["footer"].update(Panel(footer_text, border_style="blue"))
        return layout

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        with Live(generate_dashboard(), screen=True, redirect_stderr=False, transient=True) as live:
            while True:
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)
                    if char.lower() == 'q':
                        break
                time.sleep(2)
                live.update(generate_dashboard())
    except Exception as e:
        logger.error(f"Error in monitor dashboard: {e}", exc_info=True)
        raise
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings) 

def list_ollama_models() -> list[dict]:
    """Devuelve una lista de modelos locales de Ollama con nombre y tamaño."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = [p.strip() for p in line.split() if p.strip()]
            if len(parts) >= 3:
                name, _, size = parts[:3]
                models.append({"name": name, "size": size})
        return models
    except Exception as e:
        console.print(f"[bold red]Error al listar modelos de Ollama: {e}[/bold red]")
        return []

def select_ollama_model(models: list[str], recommended: str) -> str:
    """Muestra una lista numerada de modelos y permite elegir por número o Enter para recomendado."""
    console.print("\n[bold blue]Modelos Ollama locales disponibles:[/bold blue]")
    for idx, model in enumerate(models, 1):
        rec = " [RECOMENDADO]" if model == recommended else ""
        console.print(f"  [cyan]{idx}.[/cyan] {model}{rec}")
    console.print(f"\n[dim]Selecciona el modelo a usar (1-{len(models)}), o presiona Enter para '{recommended}':[/dim]")
    while True:
        choice = input(f"Modelo [1-{len(models)}] (Enter para '{recommended}'): ").strip()
        if not choice:
            return recommended
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice)-1]
        console.print(f"[red]Opción inválida. Ingresa un número entre 1 y {len(models)}, o Enter para el recomendado.[/red]")

def interactive_note_review_loop(notes, show_detail_fn, input_fn=input):
    """
    Ciclo interactivo estándar para revisión de notas.
    - Muestra el detalle de cada nota con show_detail_fn(note).
    - Permite feedback/corrección.
    - Si el usuario presiona 'q', termina inmediatamente y retorna el resto para modo automático.
    Retorna: (notas_procesadas, notas_restantes)
    """
    processed = []
    for note in notes:
        show_detail_fn(note)
        opcion = input_fn("Opción [1-3/q]: ").strip().lower()
        if opcion == "q":
            print("Edición interactiva desactivada. Clasificación automática en curso...")
            break
        # Aquí puedes manejar feedback/corrección según la lógica del flujo
        processed.append(note)
    restantes = notes[len(processed):]
    return processed, restantes 