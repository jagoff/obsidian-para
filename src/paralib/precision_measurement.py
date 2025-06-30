"""
Sistema de Medición de Precisión PARA - DEBUG Y TRACKING
Objetivo: Alcanzar 95% de precisión medible y real
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any
import sqlite3
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import statistics

from paralib.db import ChromaPARADatabase
from paralib.learning_system import PARA_Learning_System
from paralib.classification_log import get_feedback_notes
from paralib.organizer import classify_note_with_enhanced_analysis
from paralib.logger import logger

console = Console()

class PrecisionMeasurementSystem:
    """Sistema completo de medición de precisión para clasificación PARA."""
    
    def __init__(self, vault_path: Path, db: ChromaPARADatabase):
        self.vault_path = vault_path
        self.db = db
        self.learning_system = PARA_Learning_System(str(vault_path))
        self.measurement_db_path = vault_path / ".para_db" / "precision_measurements.db"
        self._init_measurement_database()
    
    def _init_measurement_database(self):
        """Inicializa la base de datos de mediciones de precisión."""
        self.measurement_db_path.parent.mkdir(exist_ok=True, parents=True)
        conn = sqlite3.connect(str(self.measurement_db_path))
        cursor = conn.cursor()
        
        # Tabla principal de mediciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS precision_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                measurement_type TEXT NOT NULL,
                before_accuracy REAL,
                after_accuracy REAL,
                improvement_percentage REAL,
                notes_tested INTEGER,
                factors_applied TEXT,
                detailed_results TEXT,
                target_achieved INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla de factores individuales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS factor_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                factor_value REAL,
                impact_score REAL,
                category_correlation TEXT,
                note_path TEXT
            )
        ''')
        
        # Tabla de comparaciones A/B
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                note_path TEXT NOT NULL,
                original_prediction TEXT,
                original_confidence REAL,
                supreme_prediction TEXT,
                supreme_confidence REAL,
                actual_category TEXT,
                original_correct INTEGER,
                supreme_correct INTEGER,
                improvement_gained INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def measure_baseline_accuracy(self) -> Dict[str, Any]:
        """Mide la precisión actual del sistema como baseline."""
        console.print("📊 [blue]Midiendo precisión baseline del sistema...[/blue]")
        
        # Obtener métricas actuales del learning system
        current_metrics = self.learning_system.get_metrics()
        
        # Obtener feedback notes para cálculo manual
        feedback_notes = get_feedback_notes(self.db)
        classifications = self.learning_system._get_all_classifications()
        
        # Calcular precisión manual
        if feedback_notes:
            correct_count = sum(1 for note in feedback_notes 
                              if note.get('predicted_category') == note.get('feedback_category'))
            manual_accuracy = (correct_count / len(feedback_notes)) * 100
        else:
            manual_accuracy = 0.0
        
        baseline = {
            'timestamp': datetime.utcnow().isoformat(),
            'learning_system_accuracy': current_metrics.get('accuracy_rate', 0.0),
            'manual_calculated_accuracy': manual_accuracy,
            'total_classifications': len(classifications),
            'total_feedback': len(feedback_notes),
            'confidence_correlation': current_metrics.get('confidence_correlation', 0.0),
            'category_balance': current_metrics.get('category_balance', 0.0),
            'semantic_coherence': current_metrics.get('semantic_coherence', 0.0)
        }
        
        console.print(f"✅ Baseline capturado:")
        console.print(f"   • Precisión actual: {baseline['learning_system_accuracy']:.2f}%")
        console.print(f"   • Total clasificaciones: {baseline['total_classifications']}")
        console.print(f"   • Total feedback: {baseline['total_feedback']}")
        
        return baseline
    
    def test_supreme_factors_on_sample(self, sample_size: int = 20) -> Dict[str, Any]:
        """Prueba los factores supremos en una muestra de notas."""
        console.print(f"🧪 [yellow]Probando factores supremos en muestra de {sample_size} notas...[/yellow]")
        
        # Obtener notas para testing
        test_notes = self._get_test_sample(sample_size)
        
        if not test_notes:
            console.print("❌ No hay notas disponibles para testing")
            return {'error': 'No test notes available'}
        
        results = []
        improvements = 0
        total_tested = 0
        
        with Progress() as progress:
            task = progress.add_task("Probando factores supremos...", total=len(test_notes))
            
            for note_path, expected_category in test_notes:
                try:
                    # Leer contenido de la nota
                    content = note_path.read_text(encoding='utf-8')
                    
                    # Clasificar con factores supremos
                    result = classify_note_with_enhanced_analysis(
                        content, note_path, "clasificar con máxima precisión", 
                        "llama3.2:3b", "", self.db, self.vault_path
                    )
                    
                    if result:
                        predicted_category = result.get('category', 'Unknown')
                        confidence = result.get('confidence', 0.0)
                        factors_applied = result.get('factors_applied', {})
                        
                        # Verificar si es correcto
                        is_correct = predicted_category == expected_category
                        
                        test_result = {
                            'note_path': str(note_path),
                            'expected_category': expected_category,
                            'predicted_category': predicted_category,
                            'confidence': confidence,
                            'is_correct': is_correct,
                            'factors_applied': factors_applied,
                            'method': result.get('method', 'unknown')
                        }
                        
                        results.append(test_result)
                        
                        if is_correct:
                            improvements += 1
                        
                        total_tested += 1
                        
                        # Guardar factor performance
                        self._save_factor_performance(factors_applied, note_path, predicted_category)
                    
                except Exception as e:
                    logger.error(f"Error testing note {note_path}: {e}")
                
                progress.advance(task)
        
        # Calcular métricas
        accuracy = (improvements / total_tested * 100) if total_tested > 0 else 0.0
        avg_confidence = statistics.mean([r['confidence'] for r in results]) if results else 0.0
        
        test_summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_tested': total_tested,
            'correct_predictions': improvements,
            'accuracy_percentage': accuracy,
            'average_confidence': avg_confidence,
            'detailed_results': results,
            'target_95_achieved': accuracy >= 95.0
        }
        
        console.print(f"🎯 Resultados del test:")
        console.print(f"   • Precisión con factores supremos: {accuracy:.2f}%")
        console.print(f"   • Confianza promedio: {avg_confidence:.3f}")
        console.print(f"   • Objetivo 95% {'✅ ALCANZADO' if accuracy >= 95.0 else '❌ NO ALCANZADO'}")
        
        return test_summary
    
    def _get_test_sample(self, sample_size: int) -> List[Tuple[Path, str]]:
        """Obtiene una muestra de notas para testing con sus categorías esperadas."""
        test_notes = []
        
        # Buscar notas en categorías PARA
        para_folders = ['01-Projects', '02-Areas', '03-Resources', '04-Archive']
        
        for folder_name in para_folders:
            folder_path = self.vault_path / folder_name
            if folder_path.exists():
                # Obtener notas de esta categoría
                for note_path in folder_path.rglob("*.md"):
                    if len(test_notes) >= sample_size:
                        break
                    
                    # La categoría esperada es el folder principal
                    expected_category = folder_name.split('-')[1]  # "Projects", "Areas", etc.
                    test_notes.append((note_path, expected_category))
                
                if len(test_notes) >= sample_size:
                    break
        
        return test_notes[:sample_size]
    
    def _save_factor_performance(self, factors: Dict[str, Any], note_path: Path, category: str):
        """Guarda el rendimiento de factores individuales."""
        conn = sqlite3.connect(str(self.measurement_db_path))
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        
        for factor_name, factor_value in factors.items():
            # Calcular impact score básico
            impact_score = self._calculate_factor_impact(factor_name, factor_value)
            
            cursor.execute('''
                INSERT INTO factor_performance 
                (timestamp, factor_name, factor_value, impact_score, category_correlation, note_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, factor_name, str(factor_value), impact_score, category, str(note_path)))
        
        conn.commit()
        conn.close()
    
    def _calculate_factor_impact(self, factor_name: str, factor_value: Any) -> float:
        """Calcula el impacto de un factor específico."""
        # Pesos de impacto por factor (basado en importancia para precisión)
        impact_weights = {
            'network_centrality': 0.20,
            'action_density': 0.25,
            'outcome_specificity': 0.30,
            'urgency': 0.20,
            'temporal_context': 0.15,
            'semantic_coherence': 0.25,
            'completion_status': 0.18,
            'knowledge_depth': 0.15,
            'emotional_context': 0.12,
            'stakeholder_density': 0.10,
            'cross_reference_density': 0.08,
            'update_frequency': 0.12
        }
        
        weight = impact_weights.get(factor_name, 0.1)
        
        # Normalizar valor del factor
        if isinstance(factor_value, (int, float)):
            normalized_value = min(1.0, max(0.0, float(factor_value)))
        else:
            # Para valores categóricos, asignar scores
            category_scores = {
                'deadline_driven': 0.9, 'scheduled': 0.7, 'evergreen': 0.5,
                'high_stress': 0.8, 'excitement': 0.7, 'neutral_analytical': 0.6,
                'deep_technical': 0.9, 'reference_material': 0.8, 'procedural': 0.7,
                'in_progress': 0.9, 'completed': 0.6, 'planning': 0.8,
                'very_frequent': 0.9, 'frequent': 0.7, 'moderate': 0.5
            }
            normalized_value = category_scores.get(str(factor_value), 0.5)
        
        return weight * normalized_value
    
    def compare_with_baseline(self, baseline: Dict[str, Any], test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compara los resultados del test con el baseline."""
        console.print("🔍 [green]Comparando resultados con baseline...[/green]")
        
        baseline_accuracy = baseline['learning_system_accuracy']
        test_accuracy = test_results['accuracy_percentage']
        improvement = test_accuracy - baseline_accuracy
        improvement_percentage = (improvement / baseline_accuracy * 100) if baseline_accuracy > 0 else 0.0
        
        comparison = {
            'timestamp': datetime.utcnow().isoformat(),
            'baseline_accuracy': baseline_accuracy,
            'test_accuracy': test_accuracy,
            'improvement_points': improvement,
            'improvement_percentage': improvement_percentage,
            'target_95_achieved': test_accuracy >= 95.0,
            'significant_improvement': improvement >= 5.0,  # Mejora significativa si aumenta 5+ puntos
            'factors_impact_analysis': self._analyze_factor_impacts()
        }
        
        # Guardar en base de datos
        self._save_measurement_result(comparison, test_results)
        
        # Mostrar resultados
        console.print(f"📈 Comparación de resultados:")
        console.print(f"   • Baseline: {baseline_accuracy:.2f}%")
        console.print(f"   • Con factores supremos: {test_accuracy:.2f}%")
        console.print(f"   • Mejora: {improvement:+.2f} puntos ({improvement_percentage:+.1f}%)")
        console.print(f"   • Objetivo 95%: {'✅ ALCANZADO' if test_accuracy >= 95.0 else '❌ NO ALCANZADO'}")
        
        return comparison
    
    def _analyze_factor_impacts(self) -> Dict[str, float]:
        """Analiza el impacto de cada factor en la precisión."""
        conn = sqlite3.connect(str(self.measurement_db_path))
        cursor = conn.cursor()
        
        # Obtener rendimiento promedio por factor
        cursor.execute('''
            SELECT factor_name, AVG(impact_score) as avg_impact
            FROM factor_performance
            GROUP BY factor_name
            ORDER BY avg_impact DESC
        ''')
        
        factor_impacts = {}
        for row in cursor.fetchall():
            factor_impacts[row[0]] = row[1]
        
        conn.close()
        return factor_impacts
    
    def _save_measurement_result(self, comparison: Dict[str, Any], test_results: Dict[str, Any]):
        """Guarda el resultado de la medición en la base de datos."""
        conn = sqlite3.connect(str(self.measurement_db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO precision_measurements 
            (timestamp, measurement_type, before_accuracy, after_accuracy, 
             improvement_percentage, notes_tested, factors_applied, detailed_results, target_achieved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comparison['timestamp'],
            'supreme_factors_test',
            comparison['baseline_accuracy'],
            comparison['test_accuracy'],
            comparison['improvement_percentage'],
            test_results['total_tested'],
            json.dumps(comparison['factors_impact_analysis']),
            json.dumps(test_results['detailed_results']),
            1 if comparison['target_95_achieved'] else 0
        ))
        
        conn.commit()
        conn.close()
    
    def generate_precision_report(self) -> Dict[str, Any]:
        """Genera un reporte completo de precisión."""
        console.print("📋 [bold]Generando reporte de precisión...[/bold]")
        
        # 1. Medir baseline
        baseline = self.measure_baseline_accuracy()
        
        # 2. Probar factores supremos
        test_results = self.test_supreme_factors_on_sample(sample_size=30)
        
        # 3. Comparar resultados
        comparison = self.compare_with_baseline(baseline, test_results)
        
        # 4. Generar reporte final
        report = {
            'report_timestamp': datetime.utcnow().isoformat(),
            'baseline_metrics': baseline,
            'test_results': test_results,
            'comparison': comparison,
            'recommendations': self._generate_recommendations(comparison),
            'next_steps': self._suggest_next_steps(comparison)
        }
        
        self._display_precision_report(report)
        
        return report
    
    def _generate_recommendations(self, comparison: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en los resultados."""
        recommendations = []
        
        if comparison['target_95_achieved']:
            recommendations.append("🎯 ¡OBJETIVO ALCANZADO! Precisión ≥ 95%")
            recommendations.append("✅ Implementar factores supremos en producción")
            recommendations.append("📊 Mantener monitoreo continuo de precisión")
        else:
            recommendations.append("📈 Aumentar tamaño de muestra de testing")
            recommendations.append("🔧 Ajustar pesos de factores de mayor impacto")
            recommendations.append("🎯 Optimizar factores con menor rendimiento")
        
        if comparison['significant_improvement']:
            recommendations.append("✨ Mejora significativa detectada - proceder con implementación")
        
        # Analizar factores específicos
        factor_impacts = comparison.get('factors_impact_analysis', {})
        if factor_impacts:
            top_factor = max(factor_impacts.items(), key=lambda x: x[1])
            recommendations.append(f"🔥 Factor más efectivo: {top_factor[0]} (impacto: {top_factor[1]:.3f})")
        
        return recommendations
    
    def _suggest_next_steps(self, comparison: Dict[str, Any]) -> List[str]:
        """Sugiere próximos pasos basados en los resultados."""
        next_steps = []
        
        if comparison['target_95_achieved']:
            next_steps.extend([
                "1. Activar factores supremos en clasificación de producción",
                "2. Implementar monitoreo continuo de precisión en tiempo real",
                "3. Crear alertas para detectar degradación de precisión",
                "4. Expandir testing a muestras más grandes (100+ notas)"
            ])
        else:
            next_steps.extend([
                "1. Analizar factores individuales con mayor detalle",
                "2. Ajustar pesos de factores basado en datos de impacto",
                "3. Probar con muestras más grandes y diversas",
                "4. Considerar factores adicionales específicos del dominio"
            ])
        
        return next_steps
    
    def _display_precision_report(self, report: Dict[str, Any]):
        """Muestra el reporte de precisión en formato visual."""
        console.print("\n" + "="*80)
        console.print("🎯 [bold]REPORTE DE PRECISIÓN PARA SISTEMA DE CLASIFICACIÓN[/bold]")
        console.print("="*80)
        
        # Métricas principales
        table = Table(title="📊 Métricas de Precisión")
        table.add_column("Métrica", style="cyan")
        table.add_column("Baseline", style="yellow")
        table.add_column("Con Factores Supremos", style="green")
        table.add_column("Mejora", style="bold magenta")
        
        baseline = report['baseline_metrics']
        test = report['test_results']
        comparison = report['comparison']
        
        table.add_row(
            "Precisión (%)",
            f"{baseline['learning_system_accuracy']:.2f}%",
            f"{test['accuracy_percentage']:.2f}%",
            f"{comparison['improvement_points']:+.2f} pts"
        )
        
        table.add_row(
            "Confianza Promedio",
            "N/A",
            f"{test['average_confidence']:.3f}",
            "Nueva métrica"
        )
        
        table.add_row(
            "Notas Probadas",
            f"{baseline['total_classifications']}",
            f"{test['total_tested']}",
            "Muestra focalizada"
        )
        
        console.print(table)
        
        # Recomendaciones
        console.print("\n💡 [bold]Recomendaciones:[/bold]")
        for i, rec in enumerate(report['recommendations'], 1):
            console.print(f"   {i}. {rec}")
        
        # Próximos pasos
        console.print("\n🚀 [bold]Próximos pasos:[/bold]")
        for i, step in enumerate(report['next_steps'], 1):
            console.print(f"   {i}. {step}")
        
        console.print("\n" + "="*80)

def debug_classification_factors(vault_path: Path, db: ChromaPARADatabase, note_content: str, note_path: Path) -> Dict[str, Any]:
    """Función de debug para analizar factores de clasificación en detalle."""
    console.print("🔧 [bold]DEBUG: Analizando factores de clasificación...[/bold]")
    
    # Clasificar con factores supremos activados
    result = classify_note_with_enhanced_analysis(
        note_content, note_path, "debug classification", 
        "llama3.2:3b", "", db, vault_path
    )
    
    if not result:
        return {'error': 'Classification failed'}
    
    # Extraer información detallada
    debug_info = {
        'note_path': str(note_path),
        'predicted_category': result.get('category', 'Unknown'),
        'confidence': result.get('confidence', 0.0),
        'method': result.get('method', 'unknown'),
        'semantic_score': result.get('semantic_score', 0.0),
        'llm_score': result.get('llm_score', 0.0),
        'factors_applied': result.get('factors_applied', {}),
        'reasoning': result.get('reasoning', ''),
        'analysis': result.get('analysis', {})
    }
    
    # Mostrar debug información
    console.print(f"📄 Nota: {note_path.name}")
    console.print(f"🎯 Categoría predicha: {debug_info['predicted_category']}")
    console.print(f"📊 Confianza: {debug_info['confidence']:.3f}")
    console.print(f"⚙️ Método: {debug_info['method']}")
    
    # Mostrar factores aplicados
    if debug_info['factors_applied']:
        factor_table = Table(title="🔍 Factores Supremos Aplicados")
        factor_table.add_column("Factor", style="cyan")
        factor_table.add_column("Valor", style="yellow")
        factor_table.add_column("Impacto", style="green")
        
        for factor, value in debug_info['factors_applied'].items():
            impact = "Alto" if isinstance(value, (int, float)) and value > 0.5 else "Medio"
            factor_table.add_row(factor, str(value), impact)
        
        console.print(factor_table)
    
    return debug_info

# Función principal para ejecutar medición completa
def run_precision_measurement(vault_path: Path, db: ChromaPARADatabase) -> Dict[str, Any]:
    """Ejecuta medición completa de precisión del sistema."""
    measurement_system = PrecisionMeasurementSystem(vault_path, db)
    return measurement_system.generate_precision_report() 