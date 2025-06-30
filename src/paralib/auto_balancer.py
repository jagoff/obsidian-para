#!/usr/bin/env python3
"""
Auto-Balanceador de Distribución PARA
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from paralib.logger import logger
from paralib.config import PARAConfig
# from paralib.utils import get_files_recursively
from rich.console import Console
from rich.table import Table

console = Console()

def get_files_recursively(directory, extensions):
    """Función simple para obtener archivos recursivamente."""
    directory = Path(directory)
    files = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    return files

@dataclass
class DistributionMetrics:
    """Métricas de distribución PARA."""
    projects_count: int = 0
    areas_count: int = 0
    resources_count: int = 0
    archive_count: int = 0
    total_count: int = 0
    
    @property
    def projects_pct(self) -> float:
        return (self.projects_count / self.total_count * 100) if self.total_count > 0 else 0
    
    @property
    def areas_pct(self) -> float:
        return (self.areas_count / self.total_count * 100) if self.total_count > 0 else 0
    
    @property
    def resources_pct(self) -> float:
        return (self.resources_count / self.total_count * 100) if self.total_count > 0 else 0
    
    @property
    def archive_pct(self) -> float:
        return (self.archive_count / self.total_count * 100) if self.total_count > 0 else 0

class AutoBalancer:
    """Sistema de auto-balanceador de distribución PARA."""
    
    # Rangos objetivo para cada categoría
    TARGET_RANGES = {
        'Projects': (15, 30),
        'Areas': (20, 35), 
        'Resources': (25, 40),
        'Archive': (10, 25)
    }
    
    def __init__(self, config):
        self.config = config
        self.vault_path = Path(config.vault_path)
    
    def analyze_distribution(self) -> DistributionMetrics:
        """Analiza la distribución actual del vault."""
        metrics = DistributionMetrics()
        
        try:
            para_folders = {
                '01-Projects': 'Projects',
                '02-Areas': 'Areas', 
                '03-Resources': 'Resources',
                '04-Archive': 'Archive'
            }
            
            for folder_name, category in para_folders.items():
                folder_path = self.vault_path / folder_name
                if folder_path.exists():
                    files = get_files_recursively(str(folder_path), ['.md'])
                    count = len(files)
                    
                    if category == 'Projects':
                        metrics.projects_count = count
                    elif category == 'Areas':
                        metrics.areas_count = count
                    elif category == 'Resources':
                        metrics.resources_count = count
                    elif category == 'Archive':
                        metrics.archive_count = count
            
            metrics.total_count = (metrics.projects_count + metrics.areas_count + 
                                 metrics.resources_count + metrics.archive_count)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analizando distribución: {e}")
            return metrics
    
    def identify_deviations(self, metrics: DistributionMetrics) -> Dict[str, Dict]:
        """Identifica desviaciones de los rangos objetivo."""
        deviations = {}
        
        categories = {
            'Projects': metrics.projects_pct,
            'Areas': metrics.areas_pct,
            'Resources': metrics.resources_pct,
            'Archive': metrics.archive_pct
        }
        
        for category, current_pct in categories.items():
            min_target, max_target = self.TARGET_RANGES[category]
            
            if current_pct < min_target:
                deviations[category] = {
                    'type': 'under',
                    'current': current_pct,
                    'target_range': (min_target, max_target),
                    'deviation': min_target - current_pct,
                    'severity': 'critical' if current_pct < min_target * 0.7 else 'warning'
                }
            elif current_pct > max_target:
                deviations[category] = {
                    'type': 'over',
                    'current': current_pct,
                    'target_range': (min_target, max_target),
                    'deviation': current_pct - max_target,
                    'severity': 'critical' if current_pct > max_target * 1.3 else 'warning'
                }
        
        return deviations

    def display_status(self) -> Dict:
        """Muestra el estado actual y retorna métricas."""
        console.print("\n🎯 [bold cyan]AUTO-BALANCEADOR PARA[/bold cyan]")
        console.print("=" * 50)
        
        # Analizar distribución
        metrics = self.analyze_distribution()
        deviations = self.identify_deviations(metrics)
        
        # Crear tabla
        table = Table(title="Distribución Actual PARA")
        table.add_column("Categoría", style="cyan", no_wrap=True)
        table.add_column("Archivos", justify="right")
        table.add_column("Porcentaje", justify="right")
        table.add_column("Rango Objetivo", justify="center")
        table.add_column("Estado", justify="center")
        
        categories = [
            ("Projects", metrics.projects_count, metrics.projects_pct),
            ("Areas", metrics.areas_count, metrics.areas_pct),
            ("Resources", metrics.resources_count, metrics.resources_pct),
            ("Archive", metrics.archive_count, metrics.archive_pct)
        ]
        
        for category, count, pct in categories:
            min_target, max_target = self.TARGET_RANGES[category]
            target_range = f"{min_target}%-{max_target}%"
            
            # Determinar estado
            if category in deviations:
                dev = deviations[category]
                if dev['severity'] == 'critical':
                    status = "🔴 CRÍTICO" if dev['type'] == 'over' else "🔴 BAJO"
                    style = "bold red"
                else:
                    status = "🟡 ALERTA" if dev['type'] == 'over' else "🟡 BAJO"
                    style = "yellow"
            else:
                status = "✅ ÓPTIMO"
                style = "green"
            
            table.add_row(
                category,
                str(count),
                f"{pct:.1f}%",
                target_range,
                status,
                style=style if category in deviations else None
            )
        
        console.print(table)
        console.print(f"\n📁 [bold]Total de archivos: {metrics.total_count}[/bold]")
        
        # Mostrar recomendaciones
        if deviations:
            console.print("\n💡 [bold yellow]Recomendaciones:[/bold yellow]")
            for category, dev in deviations.items():
                if dev['type'] == 'over':
                    console.print(f"  • {category}: Reducir contenido ({dev['deviation']:.1f}% por encima)")
                else:
                    console.print(f"  • {category}: Incrementar contenido ({dev['deviation']:.1f}% por debajo)")
            
            # Generar correcciones automáticas
            console.print("\n🔄 [bold cyan]Generando correcciones automáticas...[/bold cyan]")
            corrections = self.suggest_corrections(metrics, deviations)
            
            if corrections:
                console.print(f"✅ [green]{len(corrections)} correcciones automáticas disponibles[/green]")
                console.print("💡 [yellow]Para ver las correcciones: python para_cli.py balance --suggest[/yellow]")
                console.print("🚀 [yellow]Para aplicar correcciones: python para_cli.py balance --execute[/yellow]")
            else:
                console.print("⚠️ [yellow]No se encontraron correcciones automáticas viables[/yellow]")
        else:
            console.print("\n✅ [green]Distribución está en rangos óptimos[/green]")
        
        return {
            'metrics': metrics,
            'deviations': deviations,
            'is_optimal': len(deviations) == 0,
            'corrections_available': len(self.suggest_corrections(metrics, deviations)) if deviations else 0
        }
    
    def suggest_corrections(self, metrics: DistributionMetrics, deviations: Dict) -> List[Dict]:
        """Sugiere correcciones específicas basadas en contenido."""
        corrections = []
        
        try:
            if not deviations:
                return corrections
            
            # Patrones de corrección inteligente
            correction_patterns = {
                'Projects': {
                    'to_reduce': ['reunion', 'meeting', 'rutina', 'proceso', 'gestion', 'mantenimiento', 'revision'],
                    'move_to': 'Areas',
                    'reason': 'Procesos continuos deberían estar en Areas'
                },
                'Resources': {
                    'to_reduce': ['proyecto', 'implementar', 'lanzar', 'completar', 'deadline'],
                    'move_to': 'Projects',
                    'reason': 'Contenido con deadlines debería estar en Projects'
                },
                'Areas': {
                    'to_increase_from': 'Projects',
                    'patterns': ['gestion', 'administracion', 'proceso', 'rutina', 'planificacion'],
                    'reason': 'Procesos de gestión deberían estar en Areas'
                }
            }
            
            for category, deviation in deviations.items():
                if deviation['type'] == 'over' and category in correction_patterns:
                    # Categoría con exceso - buscar contenido para mover
                    pattern = correction_patterns[category]
                    suggestions = self._find_content_to_move(
                        category, 
                        pattern['to_reduce'],
                        pattern['move_to'],
                        max_items=min(5, int(deviation['deviation'] * metrics.total_count / 100))
                    )
                    
                    for suggestion in suggestions:
                        corrections.append({
                            'type': 'move_content',
                            'file_path': suggestion['file'],
                            'from_category': category,
                            'to_category': pattern['move_to'],
                            'reason': pattern['reason'],
                            'confidence': suggestion['confidence'],
                            'keywords_found': suggestion['keywords']
                        })
                
                elif deviation['type'] == 'under':
                    # Categoría con déficit - buscar contenido de otras categorías
                    source_corrections = self._find_content_for_deficit(category, deviation, metrics)
                    corrections.extend(source_corrections)
            
            # Ordenar por confianza
            corrections.sort(key=lambda x: x['confidence'], reverse=True)
            
            return corrections[:10]  # Máximo 10 sugerencias
            
        except Exception as e:
            logger.error(f"Error generando sugerencias de corrección: {e}")
            return []
    
    def _find_content_to_move(self, from_category: str, patterns: List[str], to_category: str, max_items: int = 5) -> List[Dict]:
        """Encuentra contenido específico para mover basado en patrones."""
        suggestions = []
        
        try:
            category_to_folder = {
                'Projects': '01-Projects',
                'Areas': '02-Areas',
                'Resources': '03-Resources',
                'Archive': '04-Archive'
            }
            
            folder_path = self.vault_path / category_to_folder[from_category]
            if not folder_path.exists():
                return suggestions
            
            files = get_files_recursively(str(folder_path), ['.md'])
            
            for file_path in files[:50]:  # Limitar búsqueda
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    # Contar coincidencias de patrones
                    matches = [pattern for pattern in patterns if pattern in content]
                    if matches:
                        confidence = len(matches) / len(patterns)
                        suggestions.append({
                            'file': str(file_path),
                            'confidence': confidence,
                            'keywords': matches
                        })
                        
                        if len(suggestions) >= max_items:
                            break
                
                except Exception:
                    continue
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error buscando contenido para mover: {e}")
            return []
    
    def _find_content_for_deficit(self, target_category: str, deviation: Dict, metrics: DistributionMetrics) -> List[Dict]:
        """Encuentra contenido de otras categorías para cubrir déficit."""
        corrections = []
        
        # Patrones para aumentar cada categoría
        increase_patterns = {
            'Areas': {
                'from_categories': ['Projects'],
                'keywords': ['gestion', 'administracion', 'proceso', 'rutina', 'planificacion', 'reunion'],
                'reason': 'Procesos de gestión continua pertenecen a Areas'
            },
            'Projects': {
                'from_categories': ['Resources'],
                'keywords': ['implementar', 'lanzar', 'completar', 'deadline', 'urgente', 'proyecto'],
                'reason': 'Contenido con deadlines específicos pertenece a Projects'
            },
            'Resources': {
                'from_categories': ['Projects', 'Areas'],
                'keywords': ['tutorial', 'documentacion', 'referencia', 'guia', 'manual'],
                'reason': 'Documentación y referencias pertenecen a Resources'
            }
        }
        
        if target_category in increase_patterns:
            pattern = increase_patterns[target_category]
            needed_items = min(5, int(deviation['deviation'] * metrics.total_count / 100))
            
            for source_category in pattern['from_categories']:
                suggestions = self._find_content_to_move(
                    source_category,
                    pattern['keywords'],
                    target_category,
                    max_items=needed_items
                )
                
                for suggestion in suggestions:
                    corrections.append({
                        'type': 'move_content',
                        'file_path': suggestion['file'],
                        'from_category': source_category,
                        'to_category': target_category,
                        'reason': pattern['reason'],
                        'confidence': suggestion['confidence'],
                        'keywords_found': suggestion['keywords']
                    })
        
        return corrections
    
    def execute_corrections(self, corrections: List[Dict], dry_run: bool = True) -> Dict:
        """Ejecuta las correcciones sugeridas."""
        results = {
            'total_corrections': len(corrections),
            'successful_moves': 0,
            'failed_moves': 0,
            'corrections_applied': [],
            'errors': []
        }
        
        if not corrections:
            return results
        
        category_to_folder = {
            'Projects': '01-Projects',
            'Areas': '02-Areas',
            'Resources': '03-Resources',
            'Archive': '04-Archive'
        }
        
        console.print(f"\n🔄 [bold]{'SIMULANDO' if dry_run else 'EJECUTANDO'} CORRECCIONES AUTOMÁTICAS[/bold]")
        console.print(f"Total de correcciones propuestas: {len(corrections)}")
        
        for i, correction in enumerate(corrections, 1):
            try:
                file_path = Path(correction['file_path'])
                from_folder = category_to_folder[correction['from_category']]
                to_folder = category_to_folder[correction['to_category']]
                
                # Calcular rutas
                try:
                    relative_path = file_path.relative_to(self.vault_path / from_folder)
                    target_path = self.vault_path / to_folder / relative_path
                except ValueError:
                    # El archivo puede estar en una subcarpeta
                    relative_path = file_path.name
                    target_path = self.vault_path / to_folder / relative_path
                
                if dry_run:
                    console.print(f"  {i}. [dim]SIMULAR: '{file_path.name}' {correction['from_category']} → {correction['to_category']} (confianza: {correction['confidence']:.2f})[/dim]")
                    console.print(f"     [dim]Razón: {correction['reason']}[/dim]")
                    console.print(f"     [dim]Palabras clave: {', '.join(correction['keywords_found'])}[/dim]")
                else:
                    # Crear directorio de destino
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Verificar que el archivo existe y el destino no
                    if file_path.exists() and not target_path.exists():
                        file_path.rename(target_path)
                        console.print(f"  {i}. ✅ Movido '{file_path.name}' {correction['from_category']} → {correction['to_category']}")
                        results['successful_moves'] += 1
                    else:
                        console.print(f"  {i}. ❌ Error: archivo no existe o destino ocupado")
                        results['failed_moves'] += 1
                
                results['corrections_applied'].append({
                    'file': file_path.name,
                    'from': correction['from_category'],
                    'to': correction['to_category'],
                    'confidence': correction['confidence'],
                    'dry_run': dry_run
                })
                
            except Exception as e:
                error_msg = f"Error procesando corrección {i}: {e}"
                results['errors'].append(error_msg)
                results['failed_moves'] += 1
                console.print(f"  {i}. ❌ {error_msg}")
        
        # Mostrar resumen
        if dry_run:
            console.print(f"\n📋 [bold]RESUMEN DE SIMULACIÓN:[/bold]")
            console.print(f"  📝 Correcciones propuestas: {results['total_corrections']}")
            console.print(f"  💡 Para ejecutar realmente, usa: python para_cli.py balance --execute")
        else:
            console.print(f"\n📋 [bold]RESUMEN DE EJECUCIÓN:[/bold]")
            console.print(f"  ✅ Movimientos exitosos: {results['successful_moves']}")
            console.print(f"  ❌ Movimientos fallidos: {results['failed_moves']}")
        
        return results

def main():
    """Función principal."""
    try:
        class ConfigObject:
            def __init__(self):
                self.vault_path = "test_vault_demo"
        
        config = ConfigObject()
        balancer = AutoBalancer(config)
        results = balancer.display_status()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
