#!/usr/bin/env python3
"""
Progress Utils
==============

Utilidades para mostrar barras de progreso fijas mientras el contenido hace scroll.
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from contextlib import contextmanager
import sys

class FixedProgressBar:
    """Barra de progreso que se mantiene fija mientras el contenido hace scroll."""
    
    def __init__(self, title: str = "Procesando...", total: int = 100):
        self.title = title
        self.total = total
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,  # No borrar al terminar
            refresh_per_second=4  # Actualizar 4 veces por segundo
        )
        self.task_id = None
        self.live = None
        
    def __enter__(self):
        # Limpiar la pantalla y mover cursor al inicio
        print("\033[2J\033[H", end="")
        
        # Crear layout con la barra fija arriba
        self.layout = Layout()
        self.layout.split_column(
            Layout(Panel(self.progress, title="📊 Progreso", border_style="cyan"), size=3),
            Layout(name="content")
        )
        
        # Iniciar Live display
        self.live = Live(self.layout, console=self.console, refresh_per_second=4)
        self.live.__enter__()
        
        # Agregar tarea
        self.task_id = self.progress.add_task(self.title, total=self.total)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.live:
            self.live.__exit__(exc_type, exc_val, exc_tb)
            
    def update(self, advance: int = 1, description: str = None):
        """Actualiza el progreso."""
        if self.task_id is not None:
            self.progress.advance(self.task_id, advance)
            if description:
                self.progress.update(self.task_id, description=description)
                
    def print_content(self, content: str, style: str = None):
        """Imprime contenido en el área de scroll."""
        # Para Rich Live, necesitamos acumular el contenido
        if hasattr(self, '_content_buffer'):
            self._content_buffer.append((content, style))
        else:
            self._content_buffer = [(content, style)]
            
        # Actualizar el layout con el contenido
        content_text = "\n".join([
            f"[{s}]{c}[/{s}]" if s else c 
            for c, s in self._content_buffer[-50:]  # Mostrar últimas 50 líneas
        ])
        
        self.layout["content"].update(
            Panel(content_text, title="📝 Logs", border_style="dim", padding=(1, 2))
        )

@contextmanager
def fixed_progress(title: str = "Procesando...", total: int = 100):
    """Context manager para barra de progreso fija."""
    progress_bar = FixedProgressBar(title, total)
    try:
        with progress_bar:
            yield progress_bar
    finally:
        pass

# Versión alternativa más simple usando solo posicionamiento de cursor
class SimpleFixedProgress:
    """Versión simple de barra fija usando códigos ANSI."""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = None
        self.task = None
        
    @contextmanager
    def track(self, sequence, description: str = "Procesando...", total: int = None):
        """Track progress con barra fija en la parte superior."""
        
        # Guardar posición actual
        self.console.print("\033[s", end="")
        
        # Crear Progress
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        )
        
        with self.progress:
            if total is None:
                total = len(sequence) if hasattr(sequence, '__len__') else 100
                
            task = self.progress.add_task(description, total=total)
            
            # Reservar espacio para la barra (3 líneas)
            self.console.print("\n\n\n")
            
            for item in sequence:
                # Mover cursor a la línea 1
                self.console.print("\033[1;1H", end="")
                
                # Actualizar progreso
                self.progress.refresh()
                
                # Restaurar posición para contenido
                self.console.print("\033[u", end="")
                
                yield item
                
                # Avanzar progreso
                self.progress.advance(task)
                
                # Guardar nueva posición
                self.console.print("\033[s", end="")

def create_fixed_progress_context(title: str, total: int, console: Console = None):
    """
    Crea un contexto de progreso fijo que mantiene la barra en la parte superior.
    
    Returns:
        Tupla de (progress, task_id, print_func)
    """
    if not console:
        console = Console()
    
    # Limpiar pantalla y posicionar cursor
    console.clear()
    
    # Crear progress con diseño mejorado
    progress = Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
        expand=True
    )
    
    # Función para imprimir manteniendo la barra arriba
    def print_with_fixed_bar(message: str, style: str = None):
        # Guardar posición actual
        console.print("\033[s", end="")
        
        # Mover al final del documento
        console.print("\033[9999;1H", end="")
        
        # Imprimir mensaje
        if style:
            console.print(f"[{style}]{message}[/{style}]")
        else:
            console.print(message)
            
        # Restaurar posición de la barra
        console.print("\033[u", end="")
        
    return progress, print_with_fixed_bar 