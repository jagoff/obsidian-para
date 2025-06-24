#!/usr/bin/env python3
"""
para_cli.py

CLI principal de PARA con sistema de plugins integrado y modo mixto automático.
"""
import sys
import argparse
from pathlib import Path
from typing import Dict, Any

from paralib.config import load_config
from paralib.logger import logger
from paralib.plugin_system import PARAPluginManager
from paralib.ai_engine import ai_engine, AICommand
from paralib.vault_selector import vault_selector
from paralib.vault import find_vault
from paralib.vault_cli import select_vault_interactive
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

console = Console()

class PARACLI:
    """CLI principal de PARA con sistema de plugins y modo mixto automático."""
    
    def __init__(self):
        self.config = load_config("para_config.default.json")
        self.plugin_manager = PARAPluginManager()
        
        # Cargar plugins al inicializar
        self.plugin_manager.load_all_plugins()
        
        # Comandos core del sistema
        self.core_commands = {
            'classify': self.cmd_classify,
            'analyze': self.cmd_analyze,
            'clean': self.cmd_clean,
            'learn': self.cmd_learn,
            'logs': self.cmd_logs,
            'dashboard': self.cmd_dashboard,
            'doctor': self.cmd_doctor,
            'plugins': self.cmd_plugins,
            'help': self.cmd_help,
            'version': self.cmd_version,
            'reclassify-all': self.cmd_reclassify_all
        }
    
    def get_all_available_commands(self) -> list:
        """Obtiene todos los comandos disponibles (core + plugins)."""
        commands = list(self.core_commands.keys())
        
        # Agregar comandos de plugins
        plugin_commands = self.plugin_manager.list_commands()
        for cmd_name in plugin_commands.keys():
            if cmd_name not in commands:
                commands.append(cmd_name)
        
        return commands
    
    def run(self, args=None):
        """Ejecuta la CLI con modo mixto automático."""
        if args is None:
            args = sys.argv[1:]
        
        if not args:
            self.cmd_help()
            return
        
        # Obtener el primer argumento (comando o prompt)
        first_arg = args[0]
        remaining_args = args[1:] if len(args) > 1 else []
        
        # Verificar si es un comando conocido
        if self._is_known_command(first_arg):
            # Modo comando tradicional
            self._execute_traditional_command(first_arg, remaining_args)
        else:
            # Modo prompt AI - verificar si hay más argumentos que formen un prompt completo
            if len(args) > 1:
                # Si hay múltiples argumentos, unirlos como un prompt completo
                full_prompt = " ".join(args)
                self._execute_ai_prompt(full_prompt, [])
            else:
                # Si solo hay un argumento, verificar si parece un prompt o comando incompleto
                if self._looks_like_prompt(first_arg):
                    self._execute_ai_prompt(first_arg, [])
                else:
                    # Comando desconocido, mostrar ayuda
                    logger.error(f"Comando desconocido: {first_arg}")
                    self.cmd_help()
    
    def _looks_like_prompt(self, text: str) -> bool:
        """Determina si el texto parece un prompt en lenguaje natural."""
        # Si contiene espacios o caracteres especiales, probablemente es un prompt
        if " " in text or len(text) > 10:
            return True
        
        # Si es muy corto y no es un comando conocido, probablemente es incompleto
        if len(text) <= 3:
            return True
        
        # Si contiene palabras en español comunes en prompts
        spanish_words = ["clasifica", "analiza", "muestra", "crea", "limpia", "aprende", "busca", "abre", "diagnostica"]
        text_lower = text.lower()
        if any(word in text_lower for word in spanish_words):
            return True
        
        return False
    
    def _is_known_command(self, command: str) -> bool:
        """Verifica si el comando es conocido."""
        available_commands = self.get_all_available_commands()
        
        # Los comandos core tienen prioridad sobre los de plugins
        if command in self.core_commands:
            return True
        
        # Verificar comandos de plugins
        plugin_commands = self.plugin_manager.list_commands()
        return command in plugin_commands
    
    def _execute_traditional_command(self, command: str, args: list):
        """Ejecuta un comando tradicional."""
        try:
            # Los comandos core tienen prioridad
            if command in self.core_commands:
                self.core_commands[command](*args)
                return
            
            # Verificar si es un comando de plugin
            plugin_command = self.plugin_manager.get_command(command)
            if plugin_command:
                plugin_command.function(*args)
                return
            
            logger.error(f"Comando desconocido: {command}")
            self.cmd_help()
        except Exception as e:
            logger.error(f"Error ejecutando comando {command}: {e}")
    
    def _execute_ai_prompt(self, prompt: str, additional_args: list):
        """Ejecuta un prompt interpretado por AI con manejo robusto de errores y deduplicación."""
        console.print(Panel(f"[bold blue]🤖 Interpretando prompt:[/bold blue]\n[dim]{prompt}[/dim]"))
        available_commands = self.get_all_available_commands()
        interpreted_command = None
        ai_error = None
        try:
            interpreted_command = ai_engine.interpret_prompt(prompt, available_commands)
        except Exception as e:
            ai_error = str(e)
        if not interpreted_command:
            if ai_error:
                console.print(f"[bold red]❌ Error interpretando prompt AI: {ai_error}[/bold red]")
            else:
                console.print("[bold red]❌ No se pudo interpretar el prompt. Mostrando ayuda y ejecutando doctor.[/bold red]")
            # Ejecutar doctor automáticamente
            try:
                from paralib.log_manager import PARALogManager
                log_manager = PARALogManager()
                log_manager.doctor()
                console.print(f"\n[bold green]✅ Doctor completado. Intenta ejecutar el comando nuevamente.[/bold green]")
            except Exception as doctor_error:
                console.print(f"[red]❌ Error ejecutando doctor: {doctor_error}[/red]")
            self.cmd_help()
            return
        # Mostrar interpretación
        console.print(f"\n[bold green]✅ Interpretación:[/bold green]")
        console.print(f"   Comando: [cyan]{interpreted_command.command}[/cyan]")
        if interpreted_command.args:
            console.print(f"   Argumentos: [yellow]{interpreted_command.args}[/yellow]")
        console.print(f"   Confianza: [{'green' if interpreted_command.confidence > 0.7 else 'yellow'}]{interpreted_command.confidence:.2f}[/]")
        console.print(f"   Razonamiento: [dim]{interpreted_command.reasoning}[/dim]")
        if interpreted_command.confidence < 0.7:
            console.print(f"\n[bold yellow]⚠️  Confianza baja ({interpreted_command.confidence:.2f}). ¿Continuar?[/bold yellow]")
        if not Confirm.ask(f"\n¿Ejecutar comando [cyan]{interpreted_command.command}[/cyan]?"):
            console.print("[yellow]Comando cancelado por el usuario.[/yellow]")
            return
        commands_requiring_vault = ["classify", "analyze", "clean", "learn", "logs", "reclassify-all", "obsidian-vault", "obsidian-sync", "obsidian-backup", "obsidian-plugins", "obsidian-notes", "obsidian-search", "obsidian-graph", "obsidian-watch"]
        if interpreted_command.command in commands_requiring_vault:
            vault = self._require_vault()
            if not vault:
                return
        try:
            success = self._execute_interpreted_command(interpreted_command, additional_args)
            ai_engine.record_prompt_execution(prompt, interpreted_command, success)
            if success:
                console.print(f"\n[bold green]✅ Comando ejecutado exitosamente![/bold green]")
            else:
                console.print(f"\n[bold red]❌ Error ejecutando el comando.[/bold red]")
        except Exception as e:
            logger.error(f"Error ejecutando comando interpretado: {e}")
            ai_engine.record_prompt_execution(prompt, interpreted_command, False)
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
    
    def _execute_interpreted_command(self, ai_command: AICommand, additional_args: list) -> bool:
        """Ejecuta un comando interpretado por AI."""
        from rich.prompt import Confirm
        
        # Confirmar ejecución (la interpretación ya se mostró en _execute_ai_prompt)
        if not Confirm.ask(f"¿Ejecutar comando {ai_command.command}?"):
            return False
        
        try:
            # Convertir guiones en guiones bajos para el nombre del método
            method_name = f"cmd_{ai_command.command.replace('-', '_')}"
            
            # Ejecutar comando
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                all_args = ai_command.args + additional_args
                method(*all_args)
                return True
            else:
                console.print(f"[red]❌ Comando '{ai_command.command}' no encontrado (método: {method_name}).[/red]")
                return False
                
        except Exception as e:
            logger.error(f"Error ejecutando comando interpretado: {e}")
            console.print(f"[red]❌ Error ejecutando el comando.[/red]")
            
            # Auto-ejecutar doctor si hay error
            console.print(f"\n[bold yellow]🔧 Error detectado. Ejecutando doctor automático...[/bold yellow]")
            try:
                from paralib.log_manager import PARALogManager
                log_manager = PARALogManager()
                log_manager.doctor()
                console.print(f"\n[bold green]✅ Doctor completado. Intenta ejecutar el comando nuevamente.[/bold green]")
            except Exception as doctor_error:
                console.print(f"[red]❌ Error ejecutando doctor: {doctor_error}[/red]")
            
            return False
    
    def _require_vault(self, vault_path=None, interactive=True, silent=False):
        """Obtiene el vault usando el Vault Selector. Si no hay, activa flujo interactivo o muestra mensaje."""
        vault = vault_selector.get_vault(vault_path, force_interactive=interactive, silent=silent)
        if not vault:
            if not silent:
                console.print("[red]❌ No se encontró ningún vault de Obsidian. Usa el comando 'vault' para configurarlo.[/red]")
            logger.error("No vault found. User must configure a vault.")
            return None
        return vault

    def cmd_classify(self, *args):
        """Comando de clasificación."""
        from paralib.organizer import PARAOrganizer
        parser = argparse.ArgumentParser(description="Clasificar notas usando PARA")
        parser.add_argument("path", nargs="?", help="Ruta al archivo o directorio (opcional, usa vault por defecto si no se indica)")
        parser.add_argument("--plan", action="store_true", help="Generar plan de clasificación")
        parser.add_argument("--confirm", action="store_true", help="Confirmar plan automáticamente")
        parser.add_argument("--backup", action="store_true", help="Crear backup antes de clasificar")
        parsed_args = parser.parse_args(args)
        vault = self._require_vault()
        if not vault:
            return
        organizer = PARAOrganizer()
        path = parsed_args.path or str(vault)
        if parsed_args.plan:
            organizer.plan_classification(path)
        else:
            organizer.classify_note(path, auto_confirm=parsed_args.confirm, create_backup=parsed_args.backup)
    
    def cmd_analyze(self, *args):
        """Comando de análisis."""
        from paralib.analyze_manager import AnalyzeManager
        parser = argparse.ArgumentParser(description="Analizar notas")
        parser.add_argument("path", nargs="?", help="Ruta al archivo o directorio (opcional, usa vault por defecto si no se indica)")
        parser.add_argument("--detailed", action="store_true", help="Análisis detallado")
        parser.add_argument("--export", help="Exportar resultados a archivo")
        parsed_args = parser.parse_args(args)
        vault = self._require_vault()
        if not vault:
            return
        analyzer = AnalyzeManager()
        path = parsed_args.path or str(vault)
        results = analyzer.analyze_note(path, detailed=parsed_args.detailed)
        if parsed_args.export:
            import json
            with open(parsed_args.export, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Resultados exportados a {parsed_args.export}")
    
    def cmd_clean(self, *args):
        """Comando de limpieza."""
        from paralib.clean_manager import CleanManager
        parser = argparse.ArgumentParser(description="Limpiar vault")
        parser.add_argument("--dry-run", action="store_true", help="Simular limpieza sin ejecutar")
        parser.add_argument("--backup", action="store_true", help="Crear backup antes de limpiar")
        parsed_args = parser.parse_args(args)
        vault = self._require_vault()
        if not vault:
            return
        cleaner = CleanManager()
        cleaner.clean_vault(vault_path=str(vault), dry_run=parsed_args.dry_run, create_backup=parsed_args.backup)
    
    def cmd_learn(self, *args):
        """Comando de aprendizaje."""
        from paralib.learning_system import PARA_Learning_System
        from paralib.db import ChromaPARADatabase
        parser = argparse.ArgumentParser(description="Sistema de aprendizaje")
        parser.add_argument("action", choices=["review", "analyze", "improve", "report"], help="Acción a realizar")
        parser.add_argument("--days", type=int, default=30, help="Días a analizar")
        parsed_args = parser.parse_args(args)
        vault = self._require_vault()
        if not vault:
            return
        db = ChromaPARADatabase(vault_path=str(vault))
        learning_system = PARA_Learning_System(db=db, vault_path=str(vault))
        if parsed_args.action == "review":
            learning_system.review_classifications(vault_path=str(vault), days=parsed_args.days)
        elif parsed_args.action == "analyze":
            learning_system.analyze_performance(vault_path=str(vault), days=parsed_args.days)
        elif parsed_args.action == "improve":
            learning_system.improve_models(vault_path=str(vault))
        elif parsed_args.action == "report":
            learning_system.generate_report(vault_path=str(vault), days=parsed_args.days)
    
    def cmd_logs(self, *args):
        """Comando de gestión de logs."""
        from paralib.log_manager import PARALogManager
        
        parser = argparse.ArgumentParser(description="Gestión de logs")
        parser.add_argument("--analyze", action="store_true", help="Analizar logs")
        parser.add_argument("--metrics", action="store_true", help="Mostrar métricas")
        parser.add_argument("--pending", action="store_true", help="Mostrar problemas pendientes")
        
        parsed_args = parser.parse_args(args)
        
        log_manager = PARALogManager()
        
        if parsed_args.analyze:
            analysis = log_manager.analyze_log_file()
            console.print(f"[green]Análisis completado: {analysis['processed']} entradas procesadas[/green]")
        elif parsed_args.metrics:
            metrics = log_manager.get_metrics()
            console.print(f"[blue]Métricas: {metrics}[/blue]")
        elif parsed_args.pending:
            pending = log_manager.get_pending_logs()
            if pending:
                console.print(f"[yellow]Problemas pendientes: {len(pending)}[/yellow]")
            else:
                console.print("[green]No hay problemas pendientes[/green]")
        else:
            log_manager.doctor_system()
    
    def cmd_dashboard(self, *args):
        """Comando del dashboard."""
        import subprocess
        import sys
        try:
            console.print("[bold blue]Lanzando dashboard en el navegador...[/bold blue]")
            subprocess.run([sys.executable.replace('python', 'streamlit'), 'run', 'para_backend_dashboard.py'], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando dashboard: {e}")
            console.print("[red]Error ejecutando el dashboard con Streamlit.[/red]")
        except FileNotFoundError:
            logger.error("Dashboard no encontrado. Ejecute: streamlit run para_backend_dashboard.py")
            console.print("[red]Dashboard no encontrado. Ejecute: streamlit run para_backend_dashboard.py[/red]")
    
    def cmd_doctor(self, *args):
        """Comando del doctor."""
        from paralib.log_manager import PARALogManager
        
        log_manager = PARALogManager()
        log_manager.doctor()
    
    def cmd_reclassify_all(self, *args):
        """Comando para reclasificar todas las notas."""
        from paralib.organizer import PARAOrganizer
        parser = argparse.ArgumentParser(description="Reclasificar todas las notas")
        parser.add_argument("--backup", action="store_true", help="Crear backup antes de reclasificar")
        parser.add_argument("--confirm", action="store_true", help="Confirmar automáticamente")
        parsed_args = parser.parse_args(args)
        vault = self._require_vault()
        if not vault:
            return
        organizer = PARAOrganizer()
        organizer.reclassify_all_notes(vault_path=str(vault), create_backup=parsed_args.backup, auto_confirm=parsed_args.confirm)
    
    def cmd_plugins(self, *args):
        """Comando de gestión de plugins (sin duplicados en la salida)."""
        from rich.table import Table
        from collections import OrderedDict
        if not args:
            # Listar plugins
            plugins = self.plugin_manager.list_plugins()
            stats = self.plugin_manager.get_plugin_stats()
            console.print(f"[bold blue]Sistema de Plugins - {stats['total_plugins']} plugins cargados[/bold blue]")
            if plugins:
                table = Table(title="Plugins Disponibles")
                table.add_column("Plugin", style="cyan")
                table.add_column("Versión", style="green")
                seen = set()
                for p in plugins:
                    if p not in seen:
                        table.add_row(p, stats['versions'].get(p, "-"))
                        seen.add(p)
                console.print(table)
            else:
                console.print("[yellow]No hay plugins instalados.[/yellow]")
            return
        if args[0] == "commands":
            # Listar comandos de plugins (sin duplicados)
            plugin_table = Table(title="Comandos de Plugins")
            plugin_table.add_column("Comando", style="magenta")
            plugin_table.add_column("Alias", style="cyan")
            plugin_table.add_column("Descripción", style="white")
            plugin_seen = set()
            for plugin in self.plugin_manager.list_plugins():
                for cmd in self.plugin_manager.get_plugin_commands(plugin):
                    key = (cmd['name'], tuple(cmd.get('aliases', [])))
                    if key not in plugin_seen:
                        plugin_table.add_row(cmd['name'], ", ".join(cmd.get('aliases', [])), cmd.get('description', ""))
                        plugin_seen.add(key)
            console.print(plugin_table)
            return
        elif args[0] == "enable" and len(args) > 1:
            plugin_name = args[1]
            if self.plugin_manager.enable_plugin(plugin_name):
                console.print(f"[green]Plugin {plugin_name} habilitado[/green]")
            else:
                console.print(f"[red]No se pudo habilitar el plugin {plugin_name}[/red]")
        elif args[0] == "disable" and len(args) > 1:
            plugin_name = args[1]
            if self.plugin_manager.disable_plugin(plugin_name):
                console.print(f"[green]Plugin {plugin_name} deshabilitado[/green]")
            else:
                console.print(f"[red]No se pudo deshabilitar el plugin {plugin_name}[/red]")
        elif args[0] == "reload":
            self.plugin_manager.load_all_plugins()
            console.print("[green]Plugins recargados[/green]")
        elif args[0] == "ai-stats":
            # Mostrar estadísticas de prompts AI
            stats = ai_engine.get_prompt_statistics()
            table = Table(title="Estadísticas de Prompts AI")
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="green")
            table.add_row("Total Prompts", str(stats['total']))
            table.add_row("Exitosos", str(stats['successful']))
            table.add_row("Fallidos", str(stats['failed']))
            table.add_row("Tasa de Éxito", f"{stats['success_rate']:.1%}")
            table.add_row("Confianza Promedio", f"{stats['avg_confidence']:.2f}")
            console.print(table)
    
    def cmd_help(self):
        """Muestra la ayuda sin duplicados (comandos y aliases)."""
        from rich.table import Table
        from collections import OrderedDict
        console.print(Panel("[bold blue]PARA CLI - Sistema de Gestión de Notas con AI[/bold blue]"))
        # Comandos core (sin duplicados)
        core_table = Table(title="Comandos Core")
        core_table.add_column("Comando", style="cyan")
        core_table.add_column("Descripción", style="white")
        core_seen = set()
        for name, func in self.core_commands.items():
            if name not in core_seen:
                core_table.add_row(name, func.__doc__ or "")
                core_seen.add(name)
        console.print(core_table)
        # Comandos de plugins (sin duplicados)
        plugin_table = Table(title="Comandos de Plugins")
        plugin_table.add_column("Comando", style="magenta")
        plugin_table.add_column("Alias", style="cyan")
        plugin_table.add_column("Descripción", style="white")
        plugin_seen = set()
        for plugin in self.plugin_manager.list_plugins():
            for cmd in self.plugin_manager.get_plugin_commands(plugin):
                key = (cmd['name'], tuple(cmd.get('aliases', [])))
                if key not in plugin_seen:
                    plugin_table.add_row(cmd['name'], ", ".join(cmd.get('aliases', [])), cmd.get('description', ""))
                    plugin_seen.add(key)
        console.print(plugin_table)
        # Ejemplos de prompts AI (sin cambios)
        ai_table = Table(title="Ejemplos de Prompts AI")
        ai_table.add_column("Prompt", style="cyan")
        ai_table.add_column("Comando Ejecutado", style="green")
        ai_table.add_row("re clasifica todas mis notas", "reclassify-all")
        ai_table.add_row("muéstrame las notas recientes", "obsidian-notes stats")
        ai_table.add_row("crea un backup", "obsidian-backup")
        ai_table.add_row("limpiar vault", "clean")
        ai_table.add_row("aprende de mis clasificaciones", "learn review")
        console.print(ai_table)
        console.print("\n[bold]Uso:[/bold] para <comando> [opciones] O para <prompt en lenguaje natural>")
        console.print("[bold]Ejemplos:[/bold]")
        console.print("  para classify nota.md --plan")
        console.print("  para analyze vault/ --detailed")
        console.print("  para learn review --days 7")
        console.print("  para plugins")
        console.print("  para obsidian-vault info")
        console.print("  para re clasifica todas mis notas")
        console.print("  para muéstrame los plugins de obsidian")
    
    def cmd_version(self):
        """Muestra la versión."""
        from paralib import __version__
        
        console.print(f"[bold blue]PARA CLI v{__version__}[/bold blue]")
        
        # Mostrar información de plugins
        stats = self.plugin_manager.get_plugin_stats()
        console.print(f"Plugins cargados: {stats['enabled_plugins']}/{stats['total_plugins']}")
        console.print(f"Comandos disponibles: {stats['total_commands']}")
        
        # Mostrar información de AI
        ai_stats = ai_engine.get_prompt_statistics()
        console.print(f"Prompts AI procesados: {ai_stats['total']}")
        if ai_stats['total'] > 0:
            console.print(f"Tasa de éxito AI: {ai_stats['success_rate']:.1%}")

def main():
    """Función principal."""
    cli = PARACLI()
    cli.run()

if __name__ == "__main__":
    main() 