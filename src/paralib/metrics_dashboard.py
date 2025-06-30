#!/usr/bin/env python3
"""
Dashboard de Métricas PARA
==========================

Dashboard completo con métricas del sistema PARA en tiempo real.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from paralib.logger import logger
from paralib.auto_balancer import AutoBalancer
from paralib.distribution_validator import DistributionValidator
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.progress import Progress, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.live import Live
import time

console = Console()

class PARAMetricsDashboard:
    """Dashboard completo de métricas PARA."""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.validator = DistributionValidator(str(vault_path))
        
        # Configurar auto-balancer
        class ConfigObject:
            def __init__(self, vault_path):
                self.vault_path = vault_path
        
        config = ConfigObject(str(vault_path))
        self.balancer = AutoBalancer(config)
    
    def get_comprehensive_metrics(self) -> Dict:
        """Obtiene métricas completas del sistema."""
        try:
            # Métricas de distribución
            distribution_metrics = self.balancer.analyze_distribution()
            deviations = self.balancer.identify_deviations(distribution_metrics)
            
            # Score de distribución
            distribution_score = self.validator.get_distribution_score()
            
            # Alertas activas
            alerts = self.validator.load_active_alerts()
            
            # Calcular scores de salud
            health_scores = self._calculate_health_scores(distribution_metrics, deviations, alerts)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'distribution_metrics': {
                    'projects_pct': distribution_metrics.projects_pct,
                    'areas_pct': distribution_metrics.areas_pct,
                    'resources_pct': distribution_metrics.resources_pct,
                    'archive_pct': distribution_metrics.archive_pct,
                    'total_files': distribution_metrics.total_count,
                    'projects_count': distribution_metrics.projects_count,
                    'areas_count': distribution_metrics.areas_count,
                    'resources_count': distribution_metrics.resources_count,
                    'archive_count': distribution_metrics.archive_count
                },
                'distribution_score': distribution_score,
                'deviations': deviations,
                'alerts': alerts,
                'health_scores': health_scores,
                'corrections_available': len(self.balancer.suggest_corrections(distribution_metrics, deviations)) if deviations else 0,
                'system_status': 'optimal' if distribution_score >= 85 else 'warning' if distribution_score >= 70 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'system_status': 'error'
            }
    
    def _calculate_health_scores(self, metrics, deviations: Dict, alerts: List) -> Dict:
        """Calcula scores de salud específicos."""
        scores = {}
        
        # Score de balance (0-100)
        total_deviation = sum(abs(dev['deviation']) for dev in deviations.values())
        balance_score = max(0, 100 - (total_deviation * 2))
        scores['balance'] = round(balance_score, 1)
        
        # Score de fragmentación (basado en ratio archivos/carpetas)
        try:
            # Calcular carpetas por categoría
            folder_counts = {}
            for category in ['Projects', 'Areas', 'Resources', 'Archive']:
                folder_path = self.vault_path / f"0{['Projects', 'Areas', 'Resources', 'Archive'].index(category) + 1}-{category}"
                if folder_path.exists():
                    folder_counts[category] = len([d for d in folder_path.iterdir() if d.is_dir()])
                else:
                    folder_counts[category] = 0
            
            total_folders = sum(folder_counts.values())
            total_files = metrics.total_count
            
            if total_files > 0:
                fragmentation_ratio = total_folders / total_files
                fragmentation_score = max(0, 100 - (fragmentation_ratio * 150))
            else:
                fragmentation_score = 100
            
            scores['fragmentation'] = round(fragmentation_score, 1)
        except Exception:
            scores['fragmentation'] = 85.0
        
        # Score de alertas (penalizar alertas críticas)
        critical_alerts = len([a for a in alerts if hasattr(a, 'severity') and a.severity in ['critical', 'emergency']])
        total_alerts = len(alerts)
        
        if total_alerts == 0:
            alerts_score = 100
        else:
            alerts_score = max(0, 100 - (critical_alerts * 20) - (total_alerts * 5))
        
        scores['alerts'] = round(alerts_score, 1)
        
        # Score general
        scores['overall'] = round((scores['balance'] + scores['fragmentation'] + scores['alerts']) / 3, 1)
        
        return scores
    
    def display_dashboard(self):
        """Muestra el dashboard completo."""
        try:
            metrics = self.get_comprehensive_metrics()
            
            if 'error' in metrics:
                console.print(f"[red]❌ Error obteniendo métricas: {metrics['error']}[/red]")
                return
            
            # Header
            status_color = {
                'optimal': 'green',
                'warning': 'yellow', 
                'critical': 'red',
                'error': 'red'
            }.get(metrics['system_status'], 'blue')
            
            console.print(Panel(
                f"🎯 [bold]DASHBOARD PARA - ESTADO: [{status_color}]{metrics['system_status'].upper()}[/{status_color}][/bold]\n"
                f"🕐 Actualizado: {datetime.now().strftime('%H:%M:%S')} | "
                f"📊 Score: {metrics['distribution_score']}/100 | "
                f"📁 Archivos: {metrics['distribution_metrics']['total_files']}",
                style="blue"
            ))
            
            # Distribución
            console.print(self._create_distribution_panel(metrics))
            
            # Salud del sistema
            console.print(self._create_health_panel(metrics))
            
            # Alertas
            console.print(self._create_alerts_panel(metrics))
            
            # Acciones disponibles
            console.print(self._create_actions_panel(metrics))
            
            # Footer
            console.print(Panel(
                "💡 Comandos: [cyan]balance --suggest[/cyan] | [cyan]balance --execute[/cyan] | [cyan]metrics --live[/cyan] para tiempo real",
                style="dim"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ Error mostrando dashboard: {e}[/red]")
            logger.error(f"Error en dashboard: {e}")
    
    def _create_distribution_panel(self, metrics: Dict) -> Panel:
        """Crea panel de distribución."""
        dist = metrics['distribution_metrics']
        deviations = metrics['deviations']
        
        table = Table(title="📊 Distribución PARA", show_header=True, header_style="bold cyan")
        table.add_column("Categoría", style="yellow")
        table.add_column("Archivos", justify="right")
        table.add_column("%", justify="right")
        table.add_column("Objetivo", justify="center")
        table.add_column("Estado", justify="center")
        
        categories = [
            ('Projects', dist['projects_count'], dist['projects_pct'], (15, 30)),
            ('Areas', dist['areas_count'], dist['areas_pct'], (20, 35)),
            ('Resources', dist['resources_count'], dist['resources_pct'], (25, 40)),
            ('Archive', dist['archive_count'], dist['archive_pct'], (10, 25))
        ]
        
        for category, count, pct, (min_range, max_range) in categories:
            # Determinar estado
            if min_range <= pct <= max_range:
                status = "✅ ÓPTIMO"
                status_style = "green"
            elif category in deviations:
                deviation = deviations[category]['deviation']
                if deviation >= 10:
                    status = "🔴 CRÍTICO"
                    status_style = "red"
                elif deviation >= 5:
                    status = "🟡 ALERTA"
                    status_style = "yellow"
                else:
                    status = "🟠 MENOR"
                    status_style = "orange1"
            else:
                status = "✅ ÓPTIMO"
                status_style = "green"
            
            table.add_row(
                category,
                str(count),
                f"{pct:.1f}%",
                f"{min_range}-{max_range}%",
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        return Panel(table, border_style="cyan")
    
    def _create_health_panel(self, metrics: Dict) -> Panel:
        """Crea panel de salud del sistema."""
        health = metrics['health_scores']
        
        def get_health_color(score: float) -> str:
            if score >= 85:
                return "green"
            elif score >= 70:
                return "yellow"
            else:
                return "red"
        
        health_items = [
            f"🎯 Balance: [{get_health_color(health['balance'])}]{health['balance']}/100[/{get_health_color(health['balance'])}]",
            f"📂 Fragmentación: [{get_health_color(health['fragmentation'])}]{health['fragmentation']}/100[/{get_health_color(health['fragmentation'])}]",
            f"🚨 Alertas: [{get_health_color(health['alerts'])}]{health['alerts']}/100[/{get_health_color(health['alerts'])}]",
            f"📈 General: [{get_health_color(health['overall'])}]{health['overall']}/100[/{get_health_color(health['overall'])}]"
        ]
        
        return Panel(
            "\n".join(health_items),
            title="💚 Salud del Sistema",
            border_style="green" if health['overall'] >= 85 else "yellow" if health['overall'] >= 70 else "red"
        )
    
    def _create_alerts_panel(self, metrics: Dict) -> Panel:
        """Crea panel de alertas."""
        alerts = metrics['alerts']
        
        if not alerts:
            content = "✅ [green]No hay alertas activas[/green]\n🎉 Sistema funcionando óptimamente"
        else:
            alert_lines = [f"🚨 [red]{len(alerts)} alertas activas[/red]"]
            
            # Mostrar solo las primeras 3 alertas más críticas
            for i, alert in enumerate(alerts[:3]):
                severity_icon = {
                    'emergency': '🔥',
                    'critical': '🚨', 
                    'warning': '⚠️',
                    'low': 'ℹ️'
                }.get(getattr(alert, 'severity', 'low'), 'ℹ️')
                
                alert_lines.append(f"{severity_icon} {getattr(alert, 'category', 'Unknown')}: "
                                 f"{getattr(alert, 'deviation', 0):.1f}% desviación")
            
            if len(alerts) > 3:
                alert_lines.append(f"... y {len(alerts) - 3} alertas más")
            
            content = "\n".join(alert_lines)
        
        return Panel(content, title="🚨 Alertas", border_style="red" if alerts else "green")
    
    def _create_actions_panel(self, metrics: Dict) -> Panel:
        """Crea panel de acciones disponibles."""
        corrections = metrics['corrections_available']
        system_status = metrics['system_status']
        
        actions = []
        
        if system_status == 'optimal':
            actions = [
                "✅ Sistema óptimo",
                "🔄 Monitoreo continuo activo",
                "📊 Métricas en rango objetivo"
            ]
        else:
            if corrections > 0:
                actions.append(f"🤖 {corrections} correcciones automáticas disponibles")
                actions.append("💡 Ejecutar: balance --execute")
            
            actions.append("🔍 Ver detalles: balance --suggest")
            actions.append("📋 Revisar alertas disponibles")
        
        return Panel(
            "\n".join(actions),
            title="🚀 Acciones Disponibles",
            border_style="cyan"
        )
    
    def run_live_dashboard(self, refresh_seconds: int = 30):
        """Ejecuta dashboard en tiempo real."""
        console.print("🔄 [bold]Iniciando Dashboard en Tiempo Real[/bold]")
        console.print(f"⏱️ Actualización cada {refresh_seconds} segundos")
        console.print("🛑 Presiona Ctrl+C para detener\n")
        
        try:
            while True:
                self.display_dashboard()
                console.print(f"\n⏳ Próxima actualización en {refresh_seconds}s...")
                time.sleep(refresh_seconds)
                console.clear()
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Dashboard detenido por el usuario[/yellow]")
        except Exception as e:
            console.print(f"\n[red]❌ Error en dashboard: {e}[/red]")

def main():
    """Función principal del dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dashboard de Métricas PARA")
    parser.add_argument("--vault", "-v", help="Ruta del vault")
    parser.add_argument("--live", "-l", action="store_true", help="Modo tiempo real")
    parser.add_argument("--refresh", "-r", type=int, default=30, help="Segundos entre actualizaciones")
    
    args = parser.parse_args()
    
    # Determinar vault
    vault_path = args.vault or "test_vault_demo"
    
    if not os.path.exists(vault_path):
        console.print(f"[red]❌ Vault no encontrado: {vault_path}[/red]")
        return 1
    
    dashboard = PARAMetricsDashboard(vault_path)
    
    try:
        if args.live:
            dashboard.run_live_dashboard(args.refresh)
        else:
            dashboard.display_dashboard()
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Error ejecutando dashboard: {e}[/red]")
        logger.error(f"Error en dashboard: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 