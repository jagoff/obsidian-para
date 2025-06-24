"""
paralib/feedback_manager.py

Sistema avanzado de gestión de feedback para mejora continua del sistema de clasificación PARA.
Incluye análisis de calidad, ajuste automático de parámetros, y revisión interactiva.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json
import statistics
from collections import defaultdict, Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
import pandas as pd

from paralib.db import ChromaPARADatabase
from paralib.classification_log import get_feedback_notes, get_classification_history, log_feedback
from paralib.vault import load_para_config, save_para_config
from paralib.logger import logger

console = Console()

class FeedbackAnalyzer:
    """Analizador avanzado de feedback para mejorar la clasificación."""
    
    def __init__(self, db: ChromaPARADatabase, vault_path: Path):
        self.db = db
        self.vault_path = vault_path
        self.config = load_para_config()
    
    def get_all_classifications(self) -> List[Dict]:
        """Obtiene todas las clasificaciones de la base de datos."""
        results = self.db.collection.get(include=["metadatas", "documents"])
        return [
            {**meta, "content": doc} 
            for meta, doc in zip(results.get("metadatas", []), results.get("documents", []))
        ]
    
    def analyze_feedback_quality(self, detailed: bool = False) -> Dict:
        """Analiza la calidad del sistema basado en feedback."""
        classifications = self.get_all_classifications()
        feedback_notes = get_feedback_notes(self.db)
        
        # Métricas básicas
        total_notes = len(classifications)
        feedback_count = len(feedback_notes)
        feedback_rate = (feedback_count / total_notes * 100) if total_notes > 0 else 0
        
        # Análisis de categorías
        category_stats = self._analyze_category_distribution(classifications, feedback_notes)
        
        # Análisis de confianza
        confidence_stats = self._analyze_confidence_distribution(classifications, feedback_notes)
        
        # Análisis de patrones de corrección
        correction_patterns = self._analyze_correction_patterns(feedback_notes)
        
        # Análisis temporal
        temporal_stats = self._analyze_temporal_patterns(classifications, feedback_notes)
        
        quality_score = self._calculate_quality_score(
            feedback_rate, category_stats, confidence_stats, correction_patterns
        )
        
        result = {
            "total_notes": total_notes,
            "feedback_count": feedback_count,
            "feedback_rate": feedback_rate,
            "quality_score": quality_score,
            "category_stats": category_stats,
            "confidence_stats": confidence_stats,
            "correction_patterns": correction_patterns,
            "temporal_stats": temporal_stats,
        }
        
        if detailed:
            result.update({
                "detailed_analysis": self._detailed_analysis(classifications, feedback_notes),
                "improvement_suggestions": self._generate_improvement_suggestions(result)
            })
        
        return result
    
    def _analyze_category_distribution(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza la distribución de categorías y correcciones."""
        category_counts = Counter()
        feedback_by_category = defaultdict(list)
        
        for note in classifications:
            category = note.get("predicted_category", "Unknown")
            category_counts[category] += 1
            
            if note.get("feedback"):
                feedback_by_category[category].append(note)
        
        # Calcular tasa de corrección por categoría
        correction_rates = {}
        for category in category_counts:
            total = category_counts[category]
            corrections = len(feedback_by_category[category])
            correction_rates[category] = (corrections / total * 100) if total > 0 else 0
        
        return {
            "total_by_category": dict(category_counts),
            "feedback_by_category": {k: len(v) for k, v in feedback_by_category.items()},
            "correction_rates": correction_rates
        }
    
    def _analyze_confidence_distribution(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza la distribución de confianza y su relación con correcciones."""
        confidences = [float(note.get("confidence", 0)) for note in classifications if note.get("confidence")]
        feedback_confidences = [float(note.get("confidence", 0)) for note in feedback_notes if note.get("confidence")]
        
        if not confidences:
            return {"error": "No hay datos de confianza disponibles"}
        
        return {
            "overall_stats": {
                "mean": statistics.mean(confidences),
                "median": statistics.median(confidences),
                "std": statistics.stdev(confidences) if len(confidences) > 1 else 0,
                "min": min(confidences),
                "max": max(confidences)
            },
            "feedback_stats": {
                "mean": statistics.mean(feedback_confidences) if feedback_confidences else 0,
                "median": statistics.median(feedback_confidences) if feedback_confidences else 0,
                "std": statistics.stdev(feedback_confidences) if len(feedback_confidences) > 1 else 0
            },
            "confidence_threshold_analysis": self._analyze_confidence_thresholds(confidences, feedback_confidences)
        }
    
    def _analyze_confidence_thresholds(self, all_confidences: List[float], feedback_confidences: List[float]) -> Dict:
        """Analiza diferentes umbrales de confianza para optimizar el sistema."""
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
        results = {}
        
        for threshold in thresholds:
            high_conf = [c for c in all_confidences if c >= threshold]
            high_conf_feedback = [c for c in feedback_confidences if c >= threshold]
            
            if high_conf:
                error_rate = len(high_conf_feedback) / len(high_conf) * 100
                results[f"threshold_{threshold}"] = {
                    "total_notes": len(high_conf),
                    "feedback_count": len(high_conf_feedback),
                    "error_rate": error_rate
                }
        
        return results
    
    def _analyze_correction_patterns(self, feedback_notes: List[Dict]) -> Dict:
        """Analiza patrones en las correcciones realizadas."""
        corrections = []
        for note in feedback_notes:
            original = note.get("predicted_category", "Unknown")
            corrected = note.get("feedback_category", "Unknown")
            if original != corrected:
                corrections.append({
                    "from": original,
                    "to": corrected,
                    "reason": note.get("correction_reason", "No especificado")
                })
        
        # Análisis de transiciones más comunes
        transitions = Counter((c["from"], c["to"]) for c in corrections)
        
        # Análisis de razones de corrección
        reasons = Counter(c["reason"] for c in corrections)
        
        return {
            "total_corrections": len(corrections),
            "most_common_transitions": transitions.most_common(5),
            "correction_reasons": dict(reasons.most_common(5))
        }
    
    def _analyze_temporal_patterns(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza patrones temporales en clasificaciones y feedback."""
        # Agrupar por fecha (simplificado)
        daily_classifications = defaultdict(int)
        daily_feedback = defaultdict(int)
        
        for note in classifications:
            timestamp = note.get("timestamp", "")
            if timestamp:
                date = timestamp[:10]  # YYYY-MM-DD
                daily_classifications[date] += 1
        
        for note in feedback_notes:
            timestamp = note.get("feedback_timestamp", "")
            if timestamp:
                date = timestamp[:10]
                daily_feedback[date] += 1
        
        return {
            "daily_classifications": dict(daily_classifications),
            "daily_feedback": dict(daily_feedback),
            "feedback_lag_analysis": self._analyze_feedback_lag(classifications, feedback_notes)
        }
    
    def _analyze_feedback_lag(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza el tiempo entre clasificación y feedback."""
        lags = []
        for note in feedback_notes:
            class_time = note.get("timestamp", "")
            feedback_time = note.get("feedback_timestamp", "")
            
            if class_time and feedback_time:
                try:
                    class_dt = datetime.fromisoformat(class_time.replace('Z', '+00:00'))
                    feedback_dt = datetime.fromisoformat(feedback_time.replace('Z', '+00:00'))
                    lag = (feedback_dt - class_dt).total_seconds() / 3600  # horas
                    lags.append(lag)
                except:
                    continue
        
        if lags:
            return {
                "mean_lag_hours": statistics.mean(lags),
                "median_lag_hours": statistics.median(lags),
                "min_lag_hours": min(lags),
                "max_lag_hours": max(lags)
            }
        return {"error": "No hay datos de lag disponibles"}
    
    def _calculate_quality_score(self, feedback_rate: float, category_stats: Dict, 
                                confidence_stats: Dict, correction_patterns: Dict) -> float:
        """Calcula un score de calidad del sistema (0-100)."""
        score = 0
        
        # Factor 1: Tasa de feedback (ideal: 5-15%)
        if 5 <= feedback_rate <= 15:
            score += 30
        elif feedback_rate < 5:
            score += feedback_rate * 6  # Máximo 30 puntos
        else:
            score += max(0, 30 - (feedback_rate - 15) * 2)  # Penalizar exceso
        
        # Factor 2: Distribución de correcciones por categoría
        correction_rates = category_stats.get("correction_rates", {})
        if correction_rates:
            avg_correction_rate = statistics.mean(correction_rates.values())
            if avg_correction_rate < 20:  # Menos del 20% de correcciones
                score += 25
            else:
                score += max(0, 25 - (avg_correction_rate - 20))
        
        # Factor 3: Análisis de confianza
        if "overall_stats" in confidence_stats:
            mean_confidence = confidence_stats["overall_stats"]["mean"]
            if mean_confidence > 0.7:
                score += 25
            else:
                score += mean_confidence * 35.7  # Máximo 25 puntos
        
        # Factor 4: Consistencia en correcciones
        transitions = correction_patterns.get("most_common_transitions", [])
        if len(transitions) <= 3:  # Pocos patrones de corrección = más consistencia
            score += 20
        else:
            score += max(0, 20 - (len(transitions) - 3) * 2)
        
        return min(100, max(0, score))
    
    def _detailed_analysis(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Análisis detallado adicional."""
        return {
            "model_performance": self._analyze_model_performance(classifications, feedback_notes),
            "content_patterns": self._analyze_content_patterns(classifications, feedback_notes),
            "user_behavior": self._analyze_user_behavior_patterns(classifications, feedback_notes)
        }
    
    def _analyze_model_performance(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza el rendimiento del modelo de IA."""
        models_used = Counter(note.get("model", "Unknown") for note in classifications)
        model_accuracy = {}
        
        for model in models_used:
            model_notes = [n for n in classifications if n.get("model") == model]
            model_feedback = [n for n in feedback_notes if n.get("model") == model]
            accuracy = (1 - len(model_feedback) / len(model_notes)) * 100 if model_notes else 0
            model_accuracy[model] = accuracy
        
        return {
            "models_used": dict(models_used),
            "model_accuracy": model_accuracy
        }
    
    def _analyze_content_patterns(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza patrones en el contenido de las notas."""
        # Análisis de longitud
        lengths = [len(note.get("content", "")) for note in classifications]
        feedback_lengths = [len(note.get("content", "")) for note in feedback_notes]
        
        return {
            "content_length_stats": {
                "overall": {
                    "mean": statistics.mean(lengths) if lengths else 0,
                    "median": statistics.median(lengths) if lengths else 0
                },
                "feedback": {
                    "mean": statistics.mean(feedback_lengths) if feedback_lengths else 0,
                    "median": statistics.median(feedback_lengths) if feedback_lengths else 0
                }
            }
        }
    
    def _analyze_user_behavior_patterns(self, classifications: List[Dict], feedback_notes: List[Dict]) -> Dict:
        """Analiza patrones de comportamiento del usuario."""
        # Análisis de sesiones de feedback
        feedback_sessions = self._identify_feedback_sessions(feedback_notes)
        
        return {
            "feedback_sessions": feedback_sessions,
            "user_engagement": {
                "total_feedback_sessions": len(feedback_sessions),
                "avg_feedback_per_session": len(feedback_notes) / len(feedback_sessions) if feedback_sessions else 0
            }
        }
    
    def _identify_feedback_sessions(self, feedback_notes: List[Dict]) -> List[Dict]:
        """Identifica sesiones de feedback (grupos de feedback cercanos en tiempo)."""
        if not feedback_notes:
            return []
        
        # Ordenar por timestamp
        sorted_notes = sorted(
            [n for n in feedback_notes if n.get("feedback_timestamp")],
            key=lambda x: x["feedback_timestamp"]
        )
        
        sessions = []
        current_session = []
        
        for note in sorted_notes:
            if not current_session:
                current_session = [note]
            else:
                # Si hay más de 2 horas entre feedback, nueva sesión
                last_time = datetime.fromisoformat(current_session[-1]["feedback_timestamp"].replace('Z', '+00:00'))
                current_time = datetime.fromisoformat(note["feedback_timestamp"].replace('Z', '+00:00'))
                
                if (current_time - last_time).total_seconds() > 7200:  # 2 horas
                    sessions.append(current_session)
                    current_session = [note]
                else:
                    current_session.append(note)
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _generate_improvement_suggestions(self, analysis: Dict) -> List[Dict]:
        """Genera sugerencias de mejora basadas en el análisis."""
        suggestions = []
        
        # Sugerencia 1: Tasa de feedback
        feedback_rate = analysis["feedback_rate"]
        if feedback_rate < 5:
            suggestions.append({
                "type": "feedback_rate",
                "priority": "high",
                "title": "Baja tasa de feedback",
                "description": f"La tasa de feedback es {feedback_rate:.1f}%. Considera revisar más clasificaciones.",
                "action": "Revisar clasificaciones recientes y proporcionar feedback"
            })
        elif feedback_rate > 20:
            suggestions.append({
                "type": "feedback_rate",
                "priority": "medium",
                "title": "Alta tasa de feedback",
                "description": f"La tasa de feedback es {feedback_rate:.1f}%. El sistema puede necesitar ajustes.",
                "action": "Revisar parámetros de clasificación y reglas"
            })
        
        # Sugerencia 2: Categorías problemáticas
        correction_rates = analysis["category_stats"]["correction_rates"]
        problematic_categories = [cat for cat, rate in correction_rates.items() if rate > 30]
        if problematic_categories:
            suggestions.append({
                "type": "category_issues",
                "priority": "high",
                "title": "Categorías con alta tasa de corrección",
                "description": f"Categorías problemáticas: {', '.join(problematic_categories)}",
                "action": "Revisar reglas y ejemplos para estas categorías"
            })
        
        # Sugerencia 3: Umbral de confianza
        confidence_analysis = analysis["confidence_stats"].get("confidence_threshold_analysis", {})
        if confidence_analysis:
            # Encontrar el mejor umbral
            best_threshold = min(confidence_analysis.items(), 
                               key=lambda x: x[1].get("error_rate", 100))
            suggestions.append({
                "type": "confidence_threshold",
                "priority": "medium",
                "title": "Optimizar umbral de confianza",
                "description": f"Considerar umbral de {best_threshold[0].split('_')[1]} para mejor precisión",
                "action": "Ajustar parámetros de clasificación"
            })
        
        return suggestions

def run_feedback_review_interactive(db: ChromaPARADatabase, vault_path: Path):
    """Ejecuta la revisión interactiva de feedback."""
    console.print("[bold blue]📝 Revisión Interactiva de Feedback[/bold blue]")
    
    # Obtener notas con feedback
    feedback_notes = get_feedback_notes(db)
    
    if not feedback_notes:
        console.print("[yellow]No hay notas con feedback para revisar.[/yellow]")
        return
    
    console.print(f"[green]Encontradas {len(feedback_notes)} notas con feedback.[/green]")
    
    # Mostrar resumen
    table = Table(title="Resumen de Feedback")
    table.add_column("Categoría Original", style="cyan")
    table.add_column("Categoría Corregida", style="green")
    table.add_column("Cantidad", style="yellow")
    
    corrections = Counter()
    for note in feedback_notes:
        original = note.get("predicted_category", "Unknown")
        corrected = note.get("feedback_category", "Unknown")
        corrections[(original, corrected)] += 1
    
    for (original, corrected), count in corrections.most_common():
        table.add_row(original, corrected, str(count))
    
    console.print(table)
    
    # Opciones de revisión
    console.print("\n[bold]Opciones de revisión:[/bold]")
    console.print("1. Revisar todas las correcciones")
    console.print("2. Revisar solo correcciones específicas")
    console.print("3. Exportar dataset para fine-tuning")
    console.print("4. Analizar patrones de corrección")
    
    choice = input("\nSelecciona una opción (1-4): ").strip()
    
    if choice == "1":
        review_all_corrections(db, feedback_notes)
    elif choice == "2":
        review_specific_corrections(db, feedback_notes)
    elif choice == "3":
        from paralib.classification_log import export_finetune_dataset
        export_finetune_dataset(db, str(vault_path / "feedback_dataset.jsonl"))
        console.print("[green]✅ Dataset exportado.[/green]")
    elif choice == "4":
        analyze_correction_patterns(feedback_notes)

def review_all_corrections(db: ChromaPARADatabase, feedback_notes: List[Dict]):
    """Revisa todas las correcciones de feedback."""
    console.print(f"\n[bold]Revisando {len(feedback_notes)} correcciones...[/bold]")
    
    for i, note in enumerate(feedback_notes, 1):
        console.print(f"\n[bold cyan]Nota {i}/{len(feedback_notes)}[/bold cyan]")
        console.print(f"Archivo: {note.get('filename', 'N/A')}")
        console.print(f"Original: {note.get('predicted_category', 'N/A')} → {note.get('predicted_folder', 'N/A')}")
        console.print(f"Corregido: {note.get('feedback_category', 'N/A')} → {note.get('feedback_folder', 'N/A')}")
        console.print(f"Razón: {note.get('correction_reason', 'No especificada')}")
        
        if input("\n¿Continuar? (Enter/n): ").lower() == 'n':
            break

def review_specific_corrections(db: ChromaPARADatabase, feedback_notes: List[Dict]):
    """Revisa correcciones específicas filtradas."""
    console.print("\n[bold]Filtros disponibles:[/bold]")
    console.print("1. Por categoría original")
    console.print("2. Por categoría corregida")
    console.print("3. Por razón de corrección")
    
    filter_choice = input("Selecciona filtro (1-3): ").strip()
    
    if filter_choice == "1":
        categories = set(note.get("predicted_category") for note in feedback_notes)
        console.print(f"Categorías disponibles: {', '.join(categories)}")
        category = input("Ingresa categoría: ").strip()
        filtered = [n for n in feedback_notes if n.get("predicted_category") == category]
    elif filter_choice == "2":
        categories = set(note.get("feedback_category") for note in feedback_notes)
        console.print(f"Categorías disponibles: {', '.join(categories)}")
        category = input("Ingresa categoría: ").strip()
        filtered = [n for n in feedback_notes if n.get("feedback_category") == category]
    elif filter_choice == "3":
        reasons = set(note.get("correction_reason") for note in feedback_notes)
        console.print(f"Razones disponibles: {', '.join(reasons)}")
        reason = input("Ingresa razón: ").strip()
        filtered = [n for n in feedback_notes if n.get("correction_reason") == reason]
    else:
        console.print("[red]Opción inválida.[/red]")
        return
    
    if filtered:
        review_all_corrections(db, filtered)
    else:
        console.print("[yellow]No se encontraron notas con ese filtro.[/yellow]")

def analyze_correction_patterns(feedback_notes: List[Dict]):
    """Analiza patrones en las correcciones."""
    console.print("\n[bold blue]📊 Análisis de Patrones de Corrección[/bold blue]")
    
    # Transiciones más comunes
    transitions = Counter()
    for note in feedback_notes:
        original = note.get("predicted_category", "Unknown")
        corrected = note.get("feedback_category", "Unknown")
        if original != corrected:
            transitions[(original, corrected)] += 1
    
    if transitions:
        console.print("\n[bold]Transiciones más comunes:[/bold]")
        table = Table()
        table.add_column("Desde", style="red")
        table.add_column("Hacia", style="green")
        table.add_column("Cantidad", style="yellow")
        
        for (original, corrected), count in transitions.most_common(10):
            table.add_row(original, corrected, str(count))
        
        console.print(table)
    
    # Razones de corrección
    reasons = Counter(note.get("correction_reason", "No especificada") for note in feedback_notes)
    if reasons:
        console.print("\n[bold]Razones de corrección más comunes:[/bold]")
        for reason, count in reasons.most_common(5):
            console.print(f"• {reason}: {count} veces")

def analyze_feedback_quality(db: ChromaPARADatabase, vault_path: Path, detailed: bool = False):
    """Analiza la calidad del feedback y muestra reportes."""
    analyzer = FeedbackAnalyzer(db, vault_path)
    analysis = analyzer.analyze_feedback_quality(detailed)
    
    # Mostrar métricas principales
    console.print(f"\n[bold blue]📊 Reporte de Calidad del Sistema[/bold blue]")
    console.print(f"Score de Calidad: [bold green]{analysis['quality_score']:.1f}/100[/bold green]")
    console.print(f"Total de notas: {analysis['total_notes']}")
    console.print(f"Notas con feedback: {analysis['feedback_count']}")
    console.print(f"Tasa de feedback: {analysis['feedback_rate']:.1f}%")
    
    # Distribución por categorías
    console.print(f"\n[bold]Distribución por Categorías:[/bold]")
    table = Table()
    table.add_column("Categoría", style="cyan")
    table.add_column("Total", style="yellow")
    table.add_column("Feedback", style="red")
    table.add_column("Tasa Corrección", style="green")
    
    for category, total in analysis['category_stats']['total_by_category'].items():
        feedback_count = analysis['category_stats']['feedback_by_category'].get(category, 0)
        correction_rate = analysis['category_stats']['correction_rates'].get(category, 0)
        table.add_row(category, str(total), str(feedback_count), f"{correction_rate:.1f}%")
    
    console.print(table)
    
    # Análisis de confianza
    if 'overall_stats' in analysis['confidence_stats']:
        console.print(f"\n[bold]Estadísticas de Confianza:[/bold]")
        stats = analysis['confidence_stats']['overall_stats']
        console.print(f"Promedio: {stats['mean']:.3f}")
        console.print(f"Mediana: {stats['median']:.3f}")
        console.print(f"Desv. Estándar: {stats['std']:.3f}")
    
    # Sugerencias de mejora
    if detailed and 'improvement_suggestions' in analysis:
        console.print(f"\n[bold]💡 Sugerencias de Mejora:[/bold]")
        for suggestion in analysis['improvement_suggestions']:
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}[suggestion['priority']]
            console.print(f"[{priority_color}]{suggestion['title']}[/{priority_color}]")
            console.print(f"  {suggestion['description']}")
            console.print(f"  Acción: {suggestion['action']}\n")

def compare_classification_quality(db: ChromaPARADatabase, vault_path: Path):
    """Compara la calidad antes y después de mejoras."""
    console.print("[bold blue]🔄 Comparación de Calidad[/bold blue]")
    console.print("[yellow]Esta funcionalidad requiere datos históricos de calidad.[/yellow]")
    console.print("Para implementar comparaciones, necesitarías:")
    console.print("1. Guardar snapshots de calidad periódicamente")
    console.print("2. Comparar métricas entre períodos")
    console.print("3. Identificar tendencias de mejora")

def auto_adjust_classification_parameters(db: ChromaPARADatabase, vault_path: Path):
    """Ajusta automáticamente parámetros basado en feedback."""
    console.print("[bold blue]⚙️ Ajuste Automático de Parámetros[/bold blue]")
    
    analyzer = FeedbackAnalyzer(db, vault_path)
    analysis = analyzer.analyze_feedback_quality(True)
    
    # Obtener configuración actual
    config = load_para_config()
    
    # Ajustes basados en análisis
    adjustments = []
    
    # Ajuste 1: Umbral de confianza
    confidence_analysis = analysis['confidence_stats'].get('confidence_threshold_analysis', {})
    if confidence_analysis:
        best_threshold = min(confidence_analysis.items(), 
                           key=lambda x: x[1].get('error_rate', 100))
        threshold_value = float(best_threshold[0].split('_')[1])
        current_threshold = config.get('confidence_threshold', 0.7)
        
        if abs(threshold_value - current_threshold) > 0.05:
            adjustments.append({
                'parameter': 'confidence_threshold',
                'old_value': current_threshold,
                'new_value': threshold_value,
                'reason': f'Optimización basada en análisis de feedback (error rate: {best_threshold[1]["error_rate"]:.1f}%)'
            })
    
    # Ajuste 2: Peso de clasificación híbrida
    feedback_rate = analysis['feedback_rate']
    if feedback_rate > 15:
        # Alta tasa de feedback, aumentar peso de ChromaDB
        current_semantic_weight = config.get('semantic_weight', 0.5)
        new_weight = min(0.8, current_semantic_weight + 0.1)
        adjustments.append({
            'parameter': 'semantic_weight',
            'old_value': current_semantic_weight,
            'new_value': new_weight,
            'reason': f'Alta tasa de feedback ({feedback_rate:.1f}%), aumentando peso semántico'
        })
    
    # Aplicar ajustes
    if adjustments:
        console.print(f"\n[bold]Ajustes propuestos:[/bold]")
        for adj in adjustments:
            console.print(f"• {adj['parameter']}: {adj['old_value']} → {adj['new_value']}")
            console.print(f"  Razón: {adj['reason']}")
        
        if input("\n¿Aplicar estos ajustes? (y/N): ").lower() == 'y':
            for adj in adjustments:
                config[adj['parameter']] = adj['new_value']
            
            save_para_config(config)
            console.print("[green]✅ Ajustes aplicados y guardados.[/green]")
    else:
        console.print("[yellow]No se encontraron ajustes necesarios.[/yellow]")

def test_classification_improvements(db: ChromaPARADatabase, vault_path: Path):
    """Prueba mejoras en un subconjunto de notas."""
    console.print("[bold blue]🧪 Prueba de Mejoras[/bold blue]")
    console.print("[yellow]Esta funcionalidad permitiría probar cambios en un subconjunto antes de aplicarlos globalmente.[/yellow]")

def suggest_improvements(db: ChromaPARADatabase, vault_path: Path):
    """Sugiere mejoras basadas en análisis de feedback."""
    analyzer = FeedbackAnalyzer(db, vault_path)
    analysis = analyzer.analyze_feedback_quality(True)
    
    console.print("[bold blue]💡 Sugerencias de Mejora[/bold blue]")
    
    if 'improvement_suggestions' in analysis:
        for suggestion in analysis['improvement_suggestions']:
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}[suggestion['priority']]
            console.print(f"\n[{priority_color}]{suggestion['title']}[/{priority_color}]")
            console.print(f"  {suggestion['description']}")
            console.print(f"  Acción: {suggestion['action']}")
    else:
        console.print("[green]¡Excelente! No se detectaron problemas críticos en el sistema.[/green]")

def create_sample_feedback(db: ChromaPARADatabase, vault_path: Path):
    """Crea feedback de muestra para demostrar el sistema."""
    console.print("[bold blue]🧪 Creando Feedback de Muestra[/bold blue]")
    
    # Obtener algunas clasificaciones recientes
    classifications = db.collection.get(include=["metadatas", "documents"])
    metadatas = classifications.get("metadatas", [])
    documents = classifications.get("documents", [])
    
    if not metadatas:
        console.print("[yellow]No hay clasificaciones para crear feedback de muestra.[/yellow]")
        return
    
    # Crear feedback de muestra para las primeras 5 notas
    sample_feedback = [
        {
            "original_category": "Projects",
            "corrected_category": "Areas", 
            "reason": "Es un área de responsabilidad continua, no un proyecto específico"
        },
        {
            "original_category": "Resources",
            "corrected_category": "Projects",
            "reason": "Es un proyecto activo con fecha límite"
        },
        {
            "original_category": "Archive",
            "corrected_category": "Resources",
            "reason": "Contiene información de referencia útil"
        },
        {
            "original_category": "Areas",
            "corrected_category": "Projects",
            "reason": "Tiene objetivos específicos y fechas definidas"
        },
        {
            "original_category": "Projects",
            "corrected_category": "Archive",
            "reason": "Proyecto completado hace tiempo"
        }
    ]
    
    feedback_created = 0
    for i, (meta, doc) in enumerate(zip(metadatas[:5], documents[:5])):
        if i < len(sample_feedback):
            feedback = sample_feedback[i]
            
            # Crear el feedback
            note_path = Path(meta.get("path", ""))
            if note_path.exists():
                log_feedback(
                    db=db,
                    note_path=note_path,
                    feedback_category=feedback["corrected_category"],
                    feedback_folder=f"0{i+1}-{feedback['corrected_category']}",
                    correction_reason=feedback["reason"]
                )
                feedback_created += 1
                console.print(f"✅ Feedback creado para: {note_path.name}")
    
    console.print(f"\n[green]Se crearon {feedback_created} feedbacks de muestra.[/green]")
    console.print("[yellow]Ahora puedes probar los comandos de análisis de feedback.[/yellow]")

def export_quality_report(db: ChromaPARADatabase, vault_path: Path, output_path: str = None):
    """Exporta un reporte completo de calidad a JSON."""
    if not output_path:
        output_path = str(vault_path / "quality_report.json")
    
    analyzer = FeedbackAnalyzer(db, vault_path)
    analysis = analyzer.analyze_feedback_quality(True)
    
    # Agregar timestamp al reporte
    analysis["report_timestamp"] = datetime.utcnow().isoformat()
    analysis["vault_path"] = str(vault_path)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    console.print(f"[green]✅ Reporte de calidad exportado a: {output_path}[/green]")
    return output_path 