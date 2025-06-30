"""
Analyze command module for PARA CLI.

This module handles the analysis of classification logs and learning statistics.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add the parent directory to the path to import paralib modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from paralib.logger import logger, log_center, log_exceptions
from paralib.db import get_shared_chromadb
from paralib.debug_config import should_show


class AnalyzeCommands:
    """Commands for analyzing PARA system performance and logs."""
    
    def __init__(self, cli_instance):
        """Initialize the analyze commands with CLI instance."""
        self.cli = cli_instance
    
    @log_exceptions
    def cmd_analyze(self, *args):
        """Analiza logs de clasificación y estadísticas de aprendizaje."""
        try:
            from paralib.learning_system import PARA_Learning_System
            from paralib.precision_measurement import PrecisionMeasurementSystem
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from pathlib import Path
            import json
            
            console = Console()
            
            # Obtener vault path
            vault_path = self.cli._get_vault_path()
            if not vault_path:
                console.print("[red]❌ No se pudo determinar el vault path[/red]")
                return
            
            vault_path = Path(vault_path)
            if not vault_path.exists():
                console.print(f"[red]❌ Vault no existe: {vault_path}[/red]")
                return
            
            # Inicializar sistemas
            db = get_shared_chromadb(vault_path)
            learning_system = PARA_Learning_System(db, vault_path)
            precision_system = PrecisionMeasurementSystem(vault_path, db)
            
            console.print(f"\n[bold blue]🔍 ANALIZANDO SISTEMA DE CLASIFICACIÓN PARA[/bold blue]")
            console.print(f"📁 Vault: {vault_path}")
            
            # === ANÁLISIS DE MÉTRICAS DE APRENDIZAJE ===
            console.print(f"\n[bold]📊 Métricas de Aprendizaje:[/bold]")
            try:
                metrics = learning_system.get_metrics()
                if metrics:
                    metrics_table = Table(title="Métricas del Sistema de Aprendizaje")
                    metrics_table.add_column("Métrica", style="cyan")
                    metrics_table.add_column("Valor", style="green")
                    metrics_table.add_column("Estado", style="yellow")
                    
                    for key, value in metrics.items():
                        if key == 'error':
                            continue
                        
                        # Determinar estado
                        if key == 'accuracy_rate':
                            status = "✅ Excelente" if value > 90 else "⚠️ Bueno" if value > 70 else "❌ Necesita mejora"
                        elif key == 'confidence_correlation':
                            status = "✅ Alto" if value > 0.8 else "⚠️ Medio" if value > 0.5 else "❌ Bajo"
                        elif key == 'learning_velocity':
                            status = "✅ Aprendiendo rápido" if value > 0.7 else "⚠️ Aprendiendo lento" if value > 0.3 else "❌ Sin mejora"
                        else:
                            status = "📊 Normal"
                        
                        metrics_table.add_row(key.replace('_', ' ').title(), f"{value:.2f}", status)
                    
                    console.print(metrics_table)
                else:
                    console.print("[yellow]⚠️ No hay métricas de aprendizaje disponibles[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error obteniendo métricas: {e}[/red]")
            
            # === ANÁLISIS DE LOGS DETALLADOS ===
            console.print(f"\n[bold]📝 Análisis de Logs de Clasificación:[/bold]")
            try:
                log_dir = vault_path / ".para_db" / "classification_logs"
                if log_dir.exists():
                    log_files = list(log_dir.glob("*.json"))
                    if log_files:
                        console.print(f"📄 Encontrados {len(log_files)} logs de clasificación")
                        
                        # Analizar logs recientes
                        recent_logs = []
                        for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                            try:
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    log_data = json.load(f)
                                recent_logs.append(log_data)
                            except Exception as e:
                                console.print(f"[dim]Error leyendo {log_file.name}: {e}[/dim]")
                        
                        if recent_logs:
                            # Estadísticas de logs recientes
                            total_classifications = len(recent_logs)
                            fallbacks_used = sum(1 for log in recent_logs if log.get('final_decision', {}).get('fallback_used', False))
                            requires_review = sum(1 for log in recent_logs if log.get('learning_data', {}).get('requires_review', False))
                            avg_confidence = sum(log.get('final_decision', {}).get('confidence', 0) for log in recent_logs) / total_classifications
                            
                            stats_table = Table(title="Estadísticas de Clasificaciones Recientes")
                            stats_table.add_column("Métrica", style="cyan")
                            stats_table.add_column("Valor", style="green")
                            
                            stats_table.add_row("Total clasificaciones", str(total_classifications))
                            stats_table.add_row("Fallbacks usados", f"{fallbacks_used} ({fallbacks_used/total_classifications*100:.1f}%)")
                            stats_table.add_row("Requieren revisión", f"{requires_review} ({requires_review/total_classifications*100:.1f}%)")
                            stats_table.add_row("Confianza promedio", f"{avg_confidence:.3f}")
                            
                            console.print(stats_table)
                            
                            # Mostrar clasificaciones problemáticas
                            problematic_logs = [log for log in recent_logs if log.get('learning_data', {}).get('requires_review', False)]
                            if problematic_logs:
                                console.print(f"\n[bold yellow]⚠️ Clasificaciones que Requieren Revisión:[/bold yellow]")
                                for log in problematic_logs[:5]:  # Mostrar solo las primeras 5
                                    note_name = log.get('note_name', 'Unknown')
                                    category = log.get('final_decision', {}).get('category', 'Unknown')
                                    confidence = log.get('final_decision', {}).get('confidence', 0)
                                    reason = log.get('final_decision', {}).get('fallback_reason', 'Baja confianza')
                                    console.print(f"  • {note_name} → {category} (conf: {confidence:.3f}) - {reason}")
                    else:
                        console.print("[yellow]⚠️ No se encontraron logs de clasificación[/yellow]")
                else:
                    console.print("[yellow]⚠️ Directorio de logs no existe[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error analizando logs: {e}[/red]")
            
            # === ANÁLISIS DE PRECISIÓN ===
            console.print(f"\n[bold]🎯 Análisis de Precisión:[/bold]")
            try:
                precision_stats = precision_system.get_precision_stats()
                if precision_stats:
                    precision_table = Table(title="Estadísticas de Precisión")
                    precision_table.add_column("Métrica", style="cyan")
                    precision_table.add_column("Valor", style="green")
                    
                    for key, value in precision_stats.items():
                        if isinstance(value, float):
                            precision_table.add_row(key.replace('_', ' ').title(), f"{value:.2f}")
                        else:
                            precision_table.add_row(key.replace('_', ' ').title(), str(value))
                    
                    console.print(precision_table)
                else:
                    console.print("[yellow]⚠️ No hay datos de precisión disponibles[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error obteniendo precisión: {e}[/red]")
            
            # === RECOMENDACIONES ===
            console.print(f"\n[bold]💡 Recomendaciones:[/bold]")
            try:
                # Analizar tendencias
                trends = learning_system.analyze_trends()
                if trends and trends.get('status') != 'no_data':
                    if trends.get('accuracy_improving', False):
                        console.print("✅ La precisión está mejorando")
                    else:
                        console.print("⚠️ La precisión no está mejorando - considerar ajustes")
                    
                    if trends.get('confidence_stable', False):
                        console.print("✅ La confianza es estable")
                    else:
                        console.print("⚠️ La confianza es inestable - revisar modelo")
                    
                    console.print(f"📈 Velocidad de aprendizaje: {trends.get('learning_velocity', 0):.2f}")
                else:
                    console.print("📊 No hay suficientes datos para analizar tendencias")
            except Exception as e:
                console.print(f"[red]❌ Error analizando tendencias: {e}[/red]")
            
            console.print(f"\n[bold green]✅ Análisis completado[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error en análisis: {e}[/red]")
            if should_show('show_debug'):
                import traceback
                console.print(traceback.format_exc()) 