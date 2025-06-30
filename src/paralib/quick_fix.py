#!/usr/bin/env python3
"""
Quick Fix PARA
==============

Script de corrección rápida para movimientos manuales específicos
en el sistema PARA.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from paralib.logger import logger
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

console = Console()

class QuickFixPARA:
    """Sistema de corrección rápida para clasificaciones PARA."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.categories = {
            'projects': '01-Projects',
            'areas': '02-Areas',
            'resources': '03-Resources',
            'archive': '04-Archive'
        }
    
    def quick_move_file(self, file_path: str, target_category: str, target_folder: str = None) -> bool:
        """Mueve un archivo rápidamente a una categoría específica."""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                console.print(f"[red]❌ Archivo no encontrado: {file_path}[/red]")
                return False
            
            # Validar categoría
            if target_category not in self.categories:
                console.print(f"[red]❌ Categoría inválida: {target_category}[/red]")
                console.print(f"Categorías válidas: {', '.join(self.categories.keys())}")
                return False
            
            target_base = self.vault_path / self.categories[target_category]
            
            # Determinar carpeta de destino
            if target_folder:
                target_dir = target_base / target_folder
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                target_dir = target_base
            
            target_path = target_dir / source_path.name
            
            # Verificar que el destino no exista
            if target_path.exists():
                console.print(f"[yellow]⚠️ El archivo ya existe en destino: {target_path}[/yellow]")
                if not Confirm.ask("¿Sobrescribir?", default=False):
                    return False
            
            # Mover archivo
            source_path.rename(target_path)
            console.print(f"[green]✅ Movido: {source_path.name} → {target_category}/{target_folder or ''}[/green]")
            
            logger.info(f"Quick fix: {source_path} → {target_path}")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error moviendo archivo: {e}[/red]")
            logger.error(f"Error en quick fix: {e}")
            return False
    
    def batch_move_by_pattern(self, pattern: str, target_category: str, dry_run: bool = True) -> Dict:
        """Mueve archivos por patrones en el nombre."""
        try:
            files_found = []
            
            # Buscar archivos que coincidan con el patrón
            for category_folder in self.categories.values():
                category_path = self.vault_path / category_folder
                if category_path.exists():
                    for file_path in category_path.rglob("*.md"):
                        if pattern.lower() in file_path.name.lower():
                            files_found.append(file_path)
            
            results = {
                'files_found': len(files_found),
                'moved_successfully': 0,
                'errors': []
            }
            
            if not files_found:
                console.print(f"[yellow]No se encontraron archivos con patrón '{pattern}'[/yellow]")
                return results
            
            console.print(f"[cyan]📁 Archivos encontrados con patrón '{pattern}': {len(files_found)}[/cyan]")
            
            if dry_run:
                console.print("[yellow]MODO SIMULACIÓN - Los archivos NO se moverán[/yellow]")
            
            target_base = self.vault_path / self.categories[target_category]
            target_base.mkdir(exist_ok=True)
            
            for file_path in files_found:
                try:
                    target_path = target_base / file_path.name
                    
                    if dry_run:
                        console.print(f"  [dim]SIMULAR: {file_path.name} → {target_category}[/dim]")
                    else:
                        if target_path.exists():
                            console.print(f"  [yellow]⚠️ Ya existe: {file_path.name}[/yellow]")
                            continue
                        
                        file_path.rename(target_path)
                        console.print(f"  [green]✅ Movido: {file_path.name}[/green]")
                        results['moved_successfully'] += 1
                
                except Exception as e:
                    error_msg = f"Error moviendo {file_path.name}: {e}"
                    results['errors'].append(error_msg)
                    console.print(f"  [red]❌ {error_msg}[/red]")
            
            return results
            
        except Exception as e:
            console.print(f"[red]❌ Error en batch move: {e}[/red]")
            return {'files_found': 0, 'moved_successfully': 0, 'errors': [str(e)]}
    
    def show_misclassified_suggestions(self) -> List[Dict]:
        """Muestra sugerencias de archivos mal clasificados."""
        try:
            suggestions = []
            
            # Patrones de clasificación incorrecta
            misclassification_patterns = {
                'projects_to_areas': {
                    'keywords': ['rutina', 'proceso', 'gestion', 'administracion', 'mantenimiento'],
                    'target': 'areas',
                    'reason': 'Procesos continuos deberían estar en Areas'
                },
                'resources_to_projects': {
                    'keywords': ['proyecto', 'implementar', 'lanzar', 'deadline', 'urgente'],
                    'target': 'projects',
                    'reason': 'Contenido con deadlines debería estar en Projects'
                },
                'any_to_archive': {
                    'keywords': ['completado', 'finalizado', 'cerrado', 'terminado', 'obsoleto'],
                    'target': 'archive',
                    'reason': 'Contenido completado debería estar en Archive'
                }
            }
            
            for category_key, category_folder in self.categories.items():
                category_path = self.vault_path / category_folder
                if not category_path.exists():
                    continue
                
                for file_path in category_path.rglob("*.md"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                        
                        for pattern_name, pattern_data in misclassification_patterns.items():
                            keywords_found = [kw for kw in pattern_data['keywords'] if kw in content]
                            
                            if keywords_found and pattern_data['target'] != category_key:
                                suggestions.append({
                                    'file_path': str(file_path),
                                    'current_category': category_key,
                                    'suggested_category': pattern_data['target'],
                                    'reason': pattern_data['reason'],
                                    'keywords_found': keywords_found,
                                    'confidence': len(keywords_found) / len(pattern_data['keywords'])
                                })
                    
                    except Exception:
                        continue
            
            # Ordenar por confianza
            suggestions.sort(key=lambda x: x['confidence'], reverse=True)
            
            return suggestions[:20]  # Top 20 sugerencias
            
        except Exception as e:
            console.print(f"[red]❌ Error generando sugerencias: {e}[/red]")
            return []
    
    def interactive_fix_session(self):
        """Sesión interactiva de corrección rápida."""
        try:
            console.print(Panel.fit(
                "🔧 [bold]QUICK FIX PARA - SESIÓN INTERACTIVA[/bold]\n"
                "Correcciones rápidas para clasificaciones PARA",
                border_style="cyan"
            ))
            
            while True:
                console.print("\n🔧 [bold]OPCIONES DISPONIBLES:[/bold]")
                console.print("1. Mover archivo específico")
                console.print("2. Mover archivos por patrón")
                console.print("3. Ver sugerencias de mal clasificados")
                console.print("4. Salir")
                
                choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4"])
                
                if choice == "1":
                    self._interactive_single_move()
                elif choice == "2":
                    self._interactive_batch_move()
                elif choice == "3":
                    self._show_misclassified_interactive()
                elif choice == "4":
                    console.print("👋 ¡Hasta luego!")
                    break
        
        except KeyboardInterrupt:
            console.print("\n👋 Sesión interrumpida por el usuario")
        except Exception as e:
            console.print(f"[red]❌ Error en sesión interactiva: {e}[/red]")
    
    def _interactive_single_move(self):
        """Interfaz interactiva para mover un archivo."""
        file_path = Prompt.ask("Ruta del archivo a mover")
        
        if not Path(file_path).exists():
            console.print(f"[red]❌ Archivo no encontrado: {file_path}[/red]")
            return
        
        console.print("Categorías disponibles:")
        for i, (key, folder) in enumerate(self.categories.items(), 1):
            console.print(f"  {i}. {key} ({folder})")
        
        category_choice = Prompt.ask("Selecciona categoría", choices=["1", "2", "3", "4"])
        category_key = list(self.categories.keys())[int(category_choice) - 1]
        
        target_folder = Prompt.ask("Carpeta específica (opcional, Enter para raíz)", default="")
        
        if self.quick_move_file(file_path, category_key, target_folder if target_folder else None):
            console.print("[green]✅ Archivo movido exitosamente[/green]")
        else:
            console.print("[red]❌ Error moviendo archivo[/red]")
    
    def _interactive_batch_move(self):
        """Interfaz interactiva para mover archivos por patrón."""
        pattern = Prompt.ask("Patrón de búsqueda (parte del nombre del archivo)")
        
        console.print("Categorías disponibles:")
        for i, (key, folder) in enumerate(self.categories.items(), 1):
            console.print(f"  {i}. {key} ({folder})")
        
        category_choice = Prompt.ask("Selecciona categoría destino", choices=["1", "2", "3", "4"])
        category_key = list(self.categories.keys())[int(category_choice) - 1]
        
        # Simulación primero
        console.print("\n🔍 [bold]SIMULACIÓN:[/bold]")
        results = self.batch_move_by_pattern(pattern, category_key, dry_run=True)
        
        if results['files_found'] > 0:
            if Confirm.ask(f"\n¿Mover {results['files_found']} archivos a {category_key}?", default=False):
                console.print("\n🔄 [bold]EJECUTANDO MOVIMIENTO:[/bold]")
                final_results = self.batch_move_by_pattern(pattern, category_key, dry_run=False)
                console.print(f"[green]✅ {final_results['moved_successfully']} archivos movidos exitosamente[/green]")
                if final_results['errors']:
                    console.print(f"[red]❌ {len(final_results['errors'])} errores encontrados[/red]")
        else:
            console.print("[yellow]No hay archivos para mover[/yellow]")
    
    def _show_misclassified_interactive(self):
        """Muestra sugerencias de archivos mal clasificados de forma interactiva."""
        console.print("\n🔍 [bold]ANALIZANDO CLASIFICACIONES...[/bold]")
        suggestions = self.show_misclassified_suggestions()
        
        if not suggestions:
            console.print("[green]✅ No se detectaron problemas de clasificación obvios[/green]")
            return
        
        console.print(f"\n📋 [bold]SUGERENCIAS DE CORRECCIÓN ({len(suggestions)}):[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Archivo", style="cyan")
        table.add_column("De", style="red")
        table.add_column("A", style="green")
        table.add_column("Confianza", justify="right")
        table.add_column("Razón", style="dim")
        
        for i, suggestion in enumerate(suggestions[:10], 1):  # Mostrar solo 10
            table.add_row(
                Path(suggestion['file_path']).name[:30] + "...",
                suggestion['current_category'],
                suggestion['suggested_category'],
                f"{suggestion['confidence']:.2f}",
                suggestion['reason'][:40] + "..."
            )
        
        console.print(table)
        
        if Confirm.ask("\n¿Aplicar correcciones automáticamente?", default=False):
            applied = 0
            for suggestion in suggestions:
                try:
                    if self.quick_move_file(
                        suggestion['file_path'],
                        suggestion['suggested_category']
                    ):
                        applied += 1
                except Exception:
                    continue
            
            console.print(f"[green]✅ {applied} correcciones aplicadas[/green]")

def main():
    """Función principal del quick fix."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick Fix PARA")
    parser.add_argument("--vault", "-v", help="Ruta del vault")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interactivo")
    parser.add_argument("--file", "-f", help="Archivo específico a mover")
    parser.add_argument("--category", "-c", help="Categoría destino")
    parser.add_argument("--pattern", "-p", help="Patrón para batch move")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Solo simular")
    
    args = parser.parse_args()
    
    # Determinar vault
    vault_path = args.vault or "test_vault_demo"
    
    if not os.path.exists(vault_path):
        console.print(f"[red]❌ Vault no encontrado: {vault_path}[/red]")
        return 1
    
    quick_fix = QuickFixPARA(vault_path)
    
    try:
        if args.interactive:
            quick_fix.interactive_fix_session()
        elif args.file and args.category:
            success = quick_fix.quick_move_file(args.file, args.category)
            return 0 if success else 1
        elif args.pattern and args.category:
            results = quick_fix.batch_move_by_pattern(args.pattern, args.category, args.dry_run)
            console.print(f"Archivos encontrados: {results['files_found']}")
            console.print(f"Movidos exitosamente: {results['moved_successfully']}")
            if results['errors']:
                console.print(f"Errores: {len(results['errors'])}")
        else:
            # Mostrar ayuda
            console.print("🔧 [bold]Quick Fix PARA[/bold]")
            console.print("Comandos disponibles:")
            console.print("  python -m paralib.quick_fix --interactive")
            console.print("  python -m paralib.quick_fix --file archivo.md --category projects")
            console.print("  python -m paralib.quick_fix --pattern 'moka' --category projects")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Error ejecutando quick fix: {e}[/red]")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 