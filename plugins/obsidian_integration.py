"""
plugins/obsidian_integration.py

Plugin de Integración con Obsidian para PARA CLI.
Conecta toda la CLI con Obsidian de forma nativa.
"""
import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sqlite3

from paralib.plugin_system import PARAPlugin, PARAPluginManager
from paralib.logger import logger
from paralib.vault import find_vault
from paralib.vault_cli import select_vault_interactive

class ObsidianIntegrationPlugin(PARAPlugin):
    """Plugin de integración nativa con Obsidian."""
    
    name = "Obsidian Integration"
    version = "1.0.0"
    description = "Integración nativa con Obsidian - Conecta toda la CLI con Obsidian"
    author = "PARA Team"
    dependencies = []
    
    def __init__(self):
        super().__init__()
        self.obsidian_config = {}
        self.vault_path = None
        self.obsidian_db_path = None
        self.plugins_dir = None
        self.themes_dir = None
        
    def register_commands(self, plugin_manager: PARAPluginManager):
        """Registra comandos específicos de Obsidian."""
        self.plugin_manager = plugin_manager
        
        # Comandos de gestión de vault
        plugin_manager.register_command(
            "obsidian-vault", 
            self.cmd_obsidian_vault,
            "Gestionar vault de Obsidian",
            aliases=["ov"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-sync", 
            self.cmd_obsidian_sync,
            "Sincronizar con Obsidian",
            aliases=["os"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-backup", 
            self.cmd_obsidian_backup,
            "Crear backup del vault de Obsidian",
            aliases=["ob"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-plugins", 
            self.cmd_obsidian_plugins,
            "Gestionar plugins de Obsidian",
            aliases=["op"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-notes", 
            self.cmd_obsidian_notes,
            "Gestionar notas de Obsidian",
            aliases=["on"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-search", 
            self.cmd_obsidian_search,
            "Búsqueda avanzada en Obsidian",
            aliases=["osearch"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-graph", 
            self.cmd_obsidian_graph,
            "Análisis del grafo de Obsidian",
            aliases=["ograph"],
            plugin_name="obsidian_integration"
        )
        
        plugin_manager.register_command(
            "obsidian-watch", 
            self.cmd_obsidian_watch,
            "Monitorear cambios en tiempo real",
            aliases=["owatch"],
            plugin_name="obsidian_integration"
        )
    
    def register_hooks(self, plugin_manager: PARAPluginManager):
        """Registra hooks específicos de Obsidian."""
        self.plugin_manager = plugin_manager
        
        # Hook para cuando se procesa una nota
        plugin_manager.register_hook(
            "note_processed",
            self.on_note_processed,
            priority=50,
            plugin_name="obsidian_integration"
        )
        
        # Hook para cuando se completa una clasificación
        plugin_manager.register_hook(
            "classification_completed",
            self.on_classification_completed,
            priority=50,
            plugin_name="obsidian_integration"
        )
        
        # Hook para cuando cambia el vault
        plugin_manager.register_hook(
            "vault_changed",
            self.on_vault_changed,
            priority=50,
            plugin_name="obsidian_integration"
        )
    
    def detect_obsidian_vault(self, path: Path) -> bool:
        """Detecta si un directorio es un vault de Obsidian."""
        return (path / ".obsidian").exists()
    
    def get_obsidian_config(self, vault_path: Path) -> Dict:
        """Obtiene la configuración de Obsidian."""
        config_file = vault_path / ".obsidian" / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error leyendo configuración de Obsidian: {e}")
        return {}
    
    def get_obsidian_plugins(self, vault_path: Path) -> List[Dict]:
        """Obtiene la lista de plugins instalados."""
        plugins_dir = vault_path / ".obsidian" / "plugins"
        plugins = []
        
        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    manifest_file = plugin_dir / "manifest.json"
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                                plugins.append(manifest)
                        except Exception as e:
                            logger.error(f"Error leyendo manifest de plugin {plugin_dir.name}: {e}")
        
        return plugins
    
    def get_obsidian_notes_stats(self, vault_path: Path) -> Dict:
        """Obtiene estadísticas de las notas del vault."""
        stats = {
            'total_notes': 0,
            'total_size': 0,
            'notes_by_extension': {},
            'notes_by_folder': {},
            'recent_notes': [],
            'largest_notes': []
        }
        
        for note_file in vault_path.rglob("*.md"):
            if note_file.is_file():
                stats['total_notes'] += 1
                stats['total_size'] += note_file.stat().st_size
                
                # Por extensión
                ext = note_file.suffix
                stats['notes_by_extension'][ext] = stats['notes_by_extension'].get(ext, 0) + 1
                
                # Por carpeta
                folder = note_file.parent.name
                stats['notes_by_folder'][folder] = stats['notes_by_folder'].get(folder, 0) + 1
                
                # Notas recientes
                mtime = note_file.stat().st_mtime
                stats['recent_notes'].append({
                    'path': str(note_file.relative_to(vault_path)),
                    'modified': datetime.fromtimestamp(mtime),
                    'size': note_file.stat().st_size
                })
        
        # Ordenar por fecha de modificación
        stats['recent_notes'].sort(key=lambda x: x['modified'], reverse=True)
        stats['recent_notes'] = stats['recent_notes'][:10]
        
        # Notas más grandes
        all_notes = []
        for note_file in vault_path.rglob("*.md"):
            if note_file.is_file():
                all_notes.append({
                    'path': str(note_file.relative_to(vault_path)),
                    'size': note_file.stat().st_size
                })
        
        all_notes.sort(key=lambda x: x['size'], reverse=True)
        stats['largest_notes'] = all_notes[:10]
        
        return stats
    
    def cmd_obsidian_vault(self, action: str = "info", vault_path: str = None):
        """Comando para gestionar el vault de Obsidian."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        if action == "info":
            if not vault_path:
                # Buscar vault automáticamente
                vault_path = self._find_obsidian_vault()
            
            if vault_path and self.detect_obsidian_vault(Path(vault_path)):
                vault_path = Path(vault_path)
                config = self.get_obsidian_config(vault_path)
                plugins = self.get_obsidian_plugins(vault_path)
                stats = self.get_obsidian_notes_stats(vault_path)
                
                console.print(Panel(f"[bold blue]Vault de Obsidian: {vault_path}[/bold blue]"))
                
                # Información básica
                table = Table(title="Información del Vault")
                table.add_column("Propiedad", style="cyan")
                table.add_column("Valor", style="green")
                
                table.add_row("Ruta", str(vault_path))
                table.add_row("Total Notas", str(stats['total_notes']))
                table.add_row("Tamaño Total", f"{stats['total_size'] / 1024 / 1024:.1f} MB")
                table.add_row("Plugins Instalados", str(len(plugins)))
                table.add_row("Configurado", "✅" if config else "❌")
                
                console.print(table)
                
                # Plugins instalados
                if plugins:
                    plugin_table = Table(title="Plugins Instalados")
                    plugin_table.add_column("Plugin", style="cyan")
                    plugin_table.add_column("Versión", style="green")
                    plugin_table.add_column("Autor", style="yellow")
                    
                    for plugin in plugins[:10]:  # Mostrar solo los primeros 10
                        plugin_table.add_row(
                            plugin.get('name', 'N/A'),
                            plugin.get('version', 'N/A'),
                            plugin.get('author', 'N/A')
                        )
                    
                    console.print(plugin_table)
                
            else:
                console.print("[red]No se encontró un vault de Obsidian válido[/red]")
        
        elif action == "set":
            if vault_path and self.detect_obsidian_vault(Path(vault_path)):
                self.vault_path = Path(vault_path)
                console.print(f"[green]Vault configurado: {vault_path}[/green]")
            else:
                console.print("[red]Ruta de vault inválida[/red]")
    
    def cmd_obsidian_sync(self, action: str = "status"):
        """Comando para sincronizar con Obsidian."""
        from rich.console import Console
        
        console = Console()
        
        if action == "status":
            if self.vault_path:
                console.print(f"[blue]Estado de sincronización: {self.vault_path}[/blue]")
                # Aquí implementarías la lógica de sincronización
            else:
                console.print("[red]No hay vault configurado[/red]")
    
    def cmd_obsidian_backup(self, backup_dir: str = None):
        """Comando para crear backup del vault."""
        from rich.console import Console
        from rich.progress import Progress
        
        console = Console()
        
        if not self.vault_path:
            console.print("[red]No hay vault configurado[/red]")
            return
        
        if not backup_dir:
            backup_dir = f"backup_obsidian_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = Path(backup_dir)
        backup_path.mkdir(exist_ok=True)
        
        with Progress() as progress:
            task = progress.add_task("Creando backup...", total=100)
            
            try:
                # Copiar archivos
                shutil.copytree(self.vault_path, backup_path / self.vault_path.name, dirs_exist_ok=True)
                progress.update(task, advance=100)
                
                console.print(f"[green]Backup creado en: {backup_path}[/green]")
            except Exception as e:
                console.print(f"[red]Error creando backup: {e}[/red]")
    
    def cmd_obsidian_plugins(self, action: str = "list"):
        """Comando para gestionar plugins de Obsidian."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if action == "list":
            if self.vault_path:
                plugins = self.get_obsidian_plugins(self.vault_path)
                
                table = Table(title="Plugins de Obsidian")
                table.add_column("Plugin", style="cyan")
                table.add_column("Versión", style="green")
                table.add_column("Autor", style="yellow")
                table.add_column("Descripción", style="white")
                
                for plugin in plugins:
                    table.add_row(
                        plugin.get('name', 'N/A'),
                        plugin.get('version', 'N/A'),
                        plugin.get('author', 'N/A'),
                        plugin.get('description', 'N/A')[:50] + "..." if len(plugin.get('description', '')) > 50 else plugin.get('description', 'N/A')
                    )
                
                console.print(table)
            else:
                console.print("[red]No hay vault configurado[/red]")
    
    def cmd_obsidian_notes(self, action: str = "stats"):
        """Comando para gestionar notas de Obsidian."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if action == "stats":
            if self.vault_path:
                stats = self.get_obsidian_notes_stats(self.vault_path)
                
                console.print(f"[blue]Estadísticas de Notas: {self.vault_path}[/blue]")
                
                # Estadísticas generales
                table = Table(title="Estadísticas Generales")
                table.add_column("Métrica", style="cyan")
                table.add_column("Valor", style="green")
                
                table.add_row("Total Notas", str(stats['total_notes']))
                table.add_row("Tamaño Total", f"{stats['total_size'] / 1024 / 1024:.1f} MB")
                table.add_row("Tamaño Promedio", f"{stats['total_size'] / max(stats['total_notes'], 1) / 1024:.1f} KB")
                
                console.print(table)
                
                # Notas recientes
                if stats['recent_notes']:
                    recent_table = Table(title="Notas Recientes")
                    recent_table.add_column("Nota", style="cyan")
                    recent_table.add_column("Modificada", style="green")
                    recent_table.add_column("Tamaño", style="yellow")
                    
                    for note in stats['recent_notes'][:5]:
                        recent_table.add_row(
                            note['path'],
                            note['modified'].strftime('%Y-%m-%d %H:%M'),
                            f"{note['size'] / 1024:.1f} KB"
                        )
                    
                    console.print(recent_table)
            else:
                console.print("[red]No hay vault configurado[/red]")
    
    def cmd_obsidian_search(self, query: str, folder: str = None):
        """Comando para búsqueda avanzada en Obsidian."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if not self.vault_path:
            console.print("[red]No hay vault configurado[/red]")
            return
        
        if not query:
            console.print("[red]Debe especificar una consulta de búsqueda[/red]")
            return
        
        # Implementar búsqueda
        results = self._search_notes(query, folder)
        
        if results:
            table = Table(title=f"Resultados de búsqueda: '{query}'")
            table.add_column("Nota", style="cyan")
            table.add_column("Carpeta", style="green")
            table.add_column("Tamaño", style="yellow")
            table.add_column("Modificada", style="white")
            
            for result in results[:20]:  # Limitar a 20 resultados
                table.add_row(
                    result['name'],
                    result['folder'],
                    f"{result['size'] / 1024:.1f} KB",
                    result['modified'].strftime('%Y-%m-%d')
                )
            
            console.print(table)
        else:
            console.print("[yellow]No se encontraron resultados[/yellow]")
    
    def cmd_obsidian_graph(self, action: str = "analyze"):
        """Comando para análisis del grafo de Obsidian."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if action == "analyze":
            if self.vault_path:
                graph_stats = self._analyze_graph()
                
                table = Table(title="Análisis del Grafo")
                table.add_column("Métrica", style="cyan")
                table.add_column("Valor", style="green")
                
                table.add_row("Total Nodos", str(graph_stats['total_nodes']))
                table.add_row("Total Enlaces", str(graph_stats['total_links']))
                table.add_row("Nodos Aislados", str(graph_stats['isolated_nodes']))
                table.add_row("Densidad", f"{graph_stats['density']:.3f}")
                table.add_row("Componentes", str(graph_stats['components']))
                
                console.print(table)
            else:
                console.print("[red]No hay vault configurado[/red]")
    
    def cmd_obsidian_watch(self, watch_time: int = 60):
        """Comando para monitorear cambios en tiempo real."""
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table
        import time
        
        console = Console()
        
        if not self.vault_path:
            console.print("[red]No hay vault configurado[/red]")
            return
        
        console.print(f"[blue]Monitoreando cambios en: {self.vault_path}[/blue]")
        console.print(f"[yellow]Presiona Ctrl+C para detener (monitoreando por {watch_time} segundos)[/yellow]")
        
        # Implementar monitoreo en tiempo real
        # Por ahora es un placeholder
        console.print("[green]Monitoreo iniciado...[/green]")
    
    def _find_obsidian_vault(self) -> Optional[Path]:
        """Busca automáticamente un vault de Obsidian."""
        # Buscar en directorios comunes
        common_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
            Path.home() / "Library" / "CloudStorage" / "GoogleDrive-fernandoferrari@gmail.com" / "Mi unidad" / "Obsidian"
        ]
        
        for path in common_paths:
            if path.exists() and self.detect_obsidian_vault(path):
                return path
        
        return None
    
    def _search_notes(self, query: str, folder: str = None) -> List[Dict]:
        """Busca notas que coincidan con la consulta."""
        results = []
        search_path = self.vault_path
        
        if folder:
            search_path = search_path / folder
        
        for note_file in search_path.rglob("*.md"):
            if note_file.is_file():
                try:
                    content = note_file.read_text(encoding='utf-8')
                    if query.lower() in content.lower() or query.lower() in note_file.name.lower():
                        results.append({
                            'name': note_file.name,
                            'path': str(note_file.relative_to(self.vault_path)),
                            'folder': note_file.parent.name,
                            'size': note_file.stat().st_size,
                            'modified': datetime.fromtimestamp(note_file.stat().st_mtime)
                        })
                except Exception as e:
                    logger.error(f"Error leyendo nota {note_file}: {e}")
        
        return results
    
    def _analyze_graph(self) -> Dict:
        """Analiza el grafo de enlaces de Obsidian."""
        # Implementación básica del análisis de grafo
        nodes = set()
        links = set()
        
        for note_file in self.vault_path.rglob("*.md"):
            if note_file.is_file():
                nodes.add(note_file.stem)
                try:
                    content = note_file.read_text(encoding='utf-8')
                    # Buscar enlaces [[nota]]
                    import re
                    link_matches = re.findall(r'\[\[([^\]]+)\]\]', content)
                    for link in link_matches:
                        links.add((note_file.stem, link))
                except Exception as e:
                    logger.error(f"Error analizando enlaces en {note_file}: {e}")
        
        # Calcular métricas básicas
        total_nodes = len(nodes)
        total_links = len(links)
        isolated_nodes = len([n for n in nodes if not any(n in link for link in links)])
        density = total_links / max(total_nodes * (total_nodes - 1), 1)
        
        return {
            'total_nodes': total_nodes,
            'total_links': total_links,
            'isolated_nodes': isolated_nodes,
            'density': density,
            'components': 1  # Simplificado
        }
    
    def on_note_processed(self, note_path: Path, result: Dict):
        """Hook llamado cuando se procesa una nota."""
        if self.vault_path and note_path.is_relative_to(self.vault_path):
            logger.info(f"[OBSIDIAN-PLUGIN] Nota procesada en vault: {note_path.name}")
            # Aquí podrías implementar lógica específica de Obsidian
    
    def on_classification_completed(self, note_path: Path, classification: Dict):
        """Hook llamado cuando se completa una clasificación."""
        if self.vault_path and note_path.is_relative_to(self.vault_path):
            logger.info(f"[OBSIDIAN-PLUGIN] Clasificación completada: {note_path.name} -> {classification.get('category', 'Unknown')}")
            # Aquí podrías actualizar metadatos de Obsidian
    
    def on_vault_changed(self, old_vault: Path, new_vault: Path):
        """Hook llamado cuando cambia el vault."""
        logger.info(f"[OBSIDIAN-PLUGIN] Vault cambiado: {old_vault} -> {new_vault}")
        self.vault_path = new_vault
        self.obsidian_config = self.get_obsidian_config(new_vault)

    def _require_vault(self, vault_path=None, interactive=True):
        vault = find_vault(vault_path)
        if not vault and interactive:
            vault = select_vault_interactive()
        if not vault:
            from rich.console import Console
            console = Console()
            console.print("[red]❌ No se encontró ningún vault de Obsidian. Usa el comando 'vault' para configurarlo.[/red]")
            logger.error("No vault found in Obsidian plugin. User must configure a vault.")
            return None
        return Path(vault)

# Instancia del plugin para registro
PARAPlugin = ObsidianIntegrationPlugin 