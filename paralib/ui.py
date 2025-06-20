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
import sys
import time
import select
import tty
import termios
from pathlib import Path
from collections import Counter
import subprocess

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from .db import ChromaPARADatabase

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.layout import Layout as PtLayout
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl

console = Console()

class TreeNode:
    """Nodo en la estructura de árbol para el selector."""
    def __init__(self, path: Path, parent=None):
        self.path = path
        self.parent = parent
        self.children = []
        self.is_expanded = False
        self.is_selected = False

    def toggle_expanded(self):
        self.is_expanded = not self.is_expanded

    def toggle_selected(self):
        self.is_selected = not self.is_selected
        # Propagar selección a los hijos
        for child in self.children:
            child.set_selected_recursive(self.is_selected)

    def set_selected_recursive(self, selected: bool):
        self.is_selected = selected
        for child in self.children:
            child.set_selected_recursive(selected)
            
    @property
    def name(self):
        return self.path.name


def build_file_tree(root_path: Path, protected_folders: set[str]) -> TreeNode:
    """Construye el árbol de directorios a partir de una ruta raíz."""
    root_node = TreeNode(root_path)

    def _build_recursively(current_path: Path, parent_node: TreeNode):
        try:
            for item_path in sorted(current_path.iterdir()):
                if item_path.is_dir() and not item_path.name.startswith('.') and item_path.name not in protected_folders:
                    child_node = TreeNode(item_path, parent=parent_node)
                    parent_node.children.append(child_node)
                    _build_recursively(item_path, child_node)
        except (IOError, PermissionError):
            pass # Ignorar directorios no legibles
            
    _build_recursively(root_path, root_node)
    return root_node


def select_folders_to_exclude(vault_path: Path) -> list[str]:
    """
    Muestra un selector de carpetas interactivo para que el usuario elija
    cuáles excluir del proceso de indexado.
    """
    protected_folders = {"01-Projects", "02-Areas", "03-Resources", "04-Archive", "00-Inbox", ".obsidian", ".para_db", "backups", "Templates", ".git"}

    try:
        root_node = build_file_tree(vault_path, protected_folders)
        if not root_node.children:
            console.print("[yellow]No se encontraron carpetas que se puedan excluir.[/yellow]")
            return []
        
        flat_nodes = []
        
        def flatten_tree(node: TreeNode, level: int = 0):
            if node != root_node:
                flat_nodes.append((node, level))
            if node.is_expanded:
                for child in node.children:
                    flatten_tree(child, level + 1)

        def update_flat_nodes():
            nonlocal flat_nodes
            flat_nodes = []
            for child in root_node.children:
                flatten_tree(child, 0)

        update_flat_nodes()
        
        current_line = 0

        # Key Bindings
        bindings = KeyBindings()

        @bindings.add('c-c')
        @bindings.add('q')
        def _(event):
            """ Salir. """
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
            if not node.is_expanded:
                node.toggle_expanded()
                update_flat_nodes()

        @bindings.add('left')
        def _(event):
            nonlocal current_line
            node, _ = flat_nodes[current_line]
            if node.is_expanded:
                node.toggle_expanded()
                update_flat_nodes()
            # Si no está expandido, subimos al padre
            elif node.parent and node.parent != root_node:
                try:
                    # Encontrar el índice del padre en la lista plana
                    parent_index = [n for n, l in flat_nodes].index(node.parent)
                    current_line = parent_index
                except ValueError:
                    pass

        @bindings.add(' ')
        def _(event):
            node, _ = flat_nodes[current_line]
            node.toggle_selected()
        
        @bindings.add('enter')
        def _(event):
            selected = [node.path for node, _ in flat_nodes if node.is_selected]
            event.app.exit(result=[str(p.resolve()) for p in selected])

        def get_formatted_text():
            result = []
            for i, (node, level) in enumerate(flat_nodes):
                prefix = '  ' * level
                if node.children:
                    icon = '▼' if node.is_expanded else '▶'
                else:
                    icon = ' '
                
                checkbox = '[X]' if node.is_selected else '[ ]'
                
                line_style = 'class:reverse' if i == current_line else ''
                
                result.append((line_style, f"{prefix}{icon} {checkbox} {node.name}\n"))
            
            if not result:
                result.append(('', 'No hay directorios para mostrar.'))

            return result

        # Layout y Application
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
            # Salir de la pantalla completa y mostrar el error
            console.print(f"[bold red]Ocurrió un error en el selector: {e}[/bold red]")
            return []
    except Exception as e:
        console.print(f"[bold red]Ocurrió un error al construir el árbol: {e}[/bold red]")
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

def select_ollama_model(suggested: str = "llama3.2:3b") -> str:
    """
    Muestra una tabla de modelos locales y permite elegir uno, sugiriendo el mejor.
    """
    models = list_ollama_models()
    if not models:
        console.print("[bold red]No se encontraron modelos locales de Ollama.[/bold red]")
        return None
    table = Table(title="Modelos Ollama locales disponibles:")
    table.add_column("Nombre", style="cyan")
    table.add_column("Tamaño", style="magenta")
    table.add_column("Recomendación", style="green")
    for m in models:
        rec = "[RECOMENDADO]" if m["name"] == suggested else ""
        table.add_row(m["name"], m["size"], rec)
    console.print(table)
    # Sugerencia automática
    if any(m["name"] == suggested for m in models):
        default = suggested
        console.print(f"[bold green]Sugerido:[/bold green] {suggested}")
    else:
        default = models[0]["name"]
        console.print(f"[yellow]No se encontró el modelo sugerido. Usando el primero disponible: {default}[/yellow]")
    choice = Prompt.ask(f"¿Qué modelo quieres usar? (Enter para '{default}')", choices=[m["name"] for m in models], default=default)
    return choice 