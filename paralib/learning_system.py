"""
paralib/learning_system.py

Sistema de Aprendizaje Autónomo PARA - Aprende, mejora y se optimiza automáticamente
con métricas cuantificables y visualización de progreso en tiempo real.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json
import statistics
import numpy as np
from collections import defaultdict, Counter
import sqlite3
import re

from paralib.db import ChromaPARADatabase
from paralib.classification_log import get_feedback_notes, log_feedback
from paralib.vault import load_para_config, save_para_config
from paralib.logger import logger

class PARA_Learning_System:
    """Sistema de Aprendizaje Autónomo que mejora continuamente la clasificación PARA."""
    
    def __init__(self, db: ChromaPARADatabase, vault_path: Path):
        self.db = db
        self.vault_path = vault_path
        self.config = load_para_config()
        self.learning_db_path = vault_path / ".para_db" / "learning_system.db"
        self.learning_db_path.parent.mkdir(exist_ok=True)
        self._init_learning_database()
        
    def _init_learning_database(self):
        """Inicializa la base de datos de aprendizaje."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        # Tabla de métricas de aprendizaje
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_classifications INTEGER,
                accuracy_rate REAL,
                confidence_correlation REAL,
                learning_velocity REAL,
                improvement_score REAL,
                category_balance REAL,
                semantic_coherence REAL,
                user_satisfaction REAL,
                system_adaptability REAL
            )
        ''')
        
        # Tabla de patrones de aprendizaje
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence REAL,
                discovered_at TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla de feedback sobre carpetas creadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folder_creation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                folder_name TEXT NOT NULL,
                category TEXT NOT NULL,
                note_content TEXT,
                note_tags TEXT,
                note_patterns TEXT,
                user_feedback TEXT NOT NULL,
                feedback_reason TEXT,
                confidence REAL,
                method_used TEXT,
                semantic_score REAL,
                ai_score REAL,
                learning_insights TEXT
            )
        ''')
        
        # Tabla de patrones de nombres de carpetas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folder_name_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                category TEXT NOT NULL,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def learn_from_classification(self, classification_result: Dict) -> Dict[str, Any]:
        """Aprende de una clasificación individual."""
        learning_insights = []
        improvements = []
        
        # Análisis básico
        confidence = classification_result.get('confidence', 0)
        predicted_category = classification_result.get('predicted_category', 'Unknown')
        actual_category = classification_result.get('actual_category')
        
        # Evaluar precisión si hay feedback
        if actual_category:
            is_correct = predicted_category == actual_category
            if not is_correct:
                learning_insights.append("Error detectado - aprendiendo del patrón")
                improvements.append({
                    'type': 'error_correction',
                    'from': predicted_category,
                    'to': actual_category,
                    'confidence': confidence
                })
        
        # Análisis de confianza
        if confidence < 0.7:
            learning_insights.append("Baja confianza - necesita más ejemplos")
            improvements.append({
                'type': 'confidence_improvement',
                'current_confidence': confidence
            })
        
        # Actualizar métricas
        self._update_learning_metrics(classification_result)
        
        return {
            'learning_insights': learning_insights,
            'improvements': improvements,
            'confidence_analysis': self._analyze_confidence([confidence])
        }
    
    def _analyze_confidence(self, confidences: List[float]) -> Dict[str, Any]:
        """Analiza la distribución de confianza."""
        if not confidences:
            return {'mean': 0, 'std': 0}
        
        return {
            'mean': statistics.mean(confidences),
            'median': statistics.median(confidences),
            'std': statistics.stdev(confidences) if len(confidences) > 1 else 0
        }
    
    def _update_learning_metrics(self, classification_result: Dict):
        """Actualiza las métricas de aprendizaje."""
        metrics = self._calculate_current_metrics()
        self._save_learning_metrics(metrics)
    
    def _calculate_current_metrics(self) -> Dict[str, Any]:
        """Calcula las métricas actuales del sistema."""
        classifications = self._get_all_classifications()
        feedback_notes = get_feedback_notes(self.db)
        
        total_classifications = len(classifications)
        feedback_count = len(feedback_notes)
        
        # Calcular precisión
        correct_classifications = sum(1 for note in feedback_notes 
                                    if note.get('predicted_category') == note.get('feedback_category'))
        accuracy_rate = (correct_classifications / feedback_count * 100) if feedback_count > 0 else 0
        
        # Calcular correlación de confianza
        confidences = [float(note.get('confidence', 0)) for note in classifications if note.get('confidence')]
        feedback_confidences = [float(note.get('confidence', 0)) for note in feedback_notes if note.get('confidence')]
        
        if confidences and feedback_confidences:
            try:
                confidence_correlation = np.corrcoef(confidences[:len(feedback_confidences)], feedback_confidences)[0, 1]
                if np.isnan(confidence_correlation):
                    confidence_correlation = 0.0
            except:
                confidence_correlation = 0.0
        else:
            confidence_correlation = 0.0
        
        # Calcular velocidad de aprendizaje
        learning_velocity = self._calculate_learning_velocity()
        
        # Calcular balance de categorías
        category_balance = self._calculate_category_balance(classifications)
        
        # Calcular coherencia semántica
        semantic_coherence = self._calculate_semantic_coherence(classifications)
        
        # Calcular satisfacción del usuario
        user_satisfaction = self._calculate_user_satisfaction(feedback_count, total_classifications)
        
        # Calcular adaptabilidad del sistema
        system_adaptability = self._calculate_system_adaptability()
        
        # Calcular score de mejora
        improvement_score = self._calculate_improvement_score()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_classifications': total_classifications,
            'accuracy_rate': accuracy_rate,
            'confidence_correlation': confidence_correlation,
            'learning_velocity': learning_velocity,
            'improvement_score': improvement_score,
            'category_balance': category_balance,
            'semantic_coherence': semantic_coherence,
            'user_satisfaction': user_satisfaction,
            'system_adaptability': system_adaptability
        }
    
    def _get_all_classifications(self) -> List[Dict]:
        """Obtiene todas las clasificaciones."""
        results = self.db.collection.get(include=["metadatas", "documents"])
        return [
            {**meta, "content": doc} 
            for meta, doc in zip(results.get("metadatas", []), results.get("documents", []))
        ]
    
    def _calculate_learning_velocity(self) -> float:
        """Calcula la velocidad de aprendizaje."""
        recent_metrics = self._get_recent_metrics(10)
        
        if len(recent_metrics) < 2:
            return 0.0
        
        # Calcular tendencia de mejora
        accuracy_values = [m['accuracy_rate'] for m in recent_metrics]
        try:
            trend = np.polyfit(range(len(accuracy_values)), accuracy_values, 1)[0]
            return max(0, min(1, (trend + 0.1) / 0.2))
        except:
            return 0.5
    
    def _calculate_category_balance(self, classifications: List[Dict]) -> float:
        """Calcula el balance de categorías."""
        category_counts = Counter(note.get('predicted_category', 'Unknown') for note in classifications)
        
        if not category_counts:
            return 0.0
        
        total = sum(category_counts.values())
        probabilities = [count / total for count in category_counts.values()]
        
        # Calcular entropía
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)
        max_entropy = np.log2(4)  # 4 categorías PARA
        
        return entropy / max_entropy
    
    def _calculate_semantic_coherence(self, classifications: List[Dict]) -> float:
        """Calcula la coherencia semántica."""
        semantic_scores = []
        
        for note in classifications:
            neighbors = note.get('neighbors', [])
            if neighbors:
                predicted_category = note.get('predicted_category', 'Unknown')
                neighbor_categories = [n.get('category', 'Unknown') for n in neighbors]
                same_category_count = sum(1 for cat in neighbor_categories if cat == predicted_category)
                semantic_scores.append(same_category_count / len(neighbor_categories))
        
        return statistics.mean(semantic_scores) if semantic_scores else 0.5
    
    def _calculate_user_satisfaction(self, feedback_count: int, total_classifications: int) -> float:
        """Calcula la satisfacción del usuario."""
        if total_classifications == 0:
            return 0.5
        
        feedback_rate = feedback_count / total_classifications
        
        # Tasa ideal: 5-15%
        if 0.05 <= feedback_rate <= 0.15:
            return 1.0
        elif feedback_rate < 0.05:
            return feedback_rate * 20
        else:
            return max(0, 1 - (feedback_rate - 0.15) * 5)
    
    def _calculate_system_adaptability(self) -> float:
        """Calcula la adaptabilidad del sistema."""
        # Basado en mejoras recientes
        recent_improvements = self._get_recent_improvements(30)
        
        if not recent_improvements:
            return 0.5
        
        improvement_types = Counter(imp['improvement_type'] for imp in recent_improvements)
        total_improvements = len(recent_improvements)
        
        diversity_score = len(improvement_types) / 4
        frequency_score = min(1, total_improvements / 10)
        
        return (diversity_score + frequency_score) / 2
    
    def _calculate_improvement_score(self) -> float:
        """Calcula el score de mejora."""
        historical_metrics = self._get_recent_metrics(50)
        
        if len(historical_metrics) < 5:
            return 0.5
        
        recent_accuracy = statistics.mean([m['accuracy_rate'] for m in historical_metrics[-5:]])
        older_accuracy = statistics.mean([m['accuracy_rate'] for m in historical_metrics[:5]])
        accuracy_improvement = (recent_accuracy - older_accuracy) / 100
        
        recent_confidence = statistics.mean([m['confidence_correlation'] for m in historical_metrics[-5:]])
        older_confidence = statistics.mean([m['confidence_correlation'] for m in historical_metrics[:5]])
        confidence_improvement = (recent_confidence - older_confidence) / 2
        
        improvement_score = (accuracy_improvement + confidence_improvement) / 2
        return max(0, min(1, improvement_score + 0.5))
    
    def _get_recent_metrics(self, limit: int) -> List[Dict]:
        """Obtiene métricas recientes."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM learning_metrics 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append({
                'timestamp': row[1],
                'total_classifications': row[2],
                'accuracy_rate': row[3],
                'confidence_correlation': row[4],
                'learning_velocity': row[5],
                'improvement_score': row[6],
                'category_balance': row[7],
                'semantic_coherence': row[8],
                'user_satisfaction': row[9],
                'system_adaptability': row[10]
            })
        
        return list(reversed(metrics))
    
    def _get_recent_improvements(self, days: int) -> List[Dict]:
        """Obtiene mejoras recientes."""
        # Simulado por ahora
        return []
    
    def _save_learning_metrics(self, metrics: Dict[str, Any]):
        """Guarda métricas de aprendizaje."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO learning_metrics (
                timestamp, total_classifications, accuracy_rate, confidence_correlation,
                learning_velocity, improvement_score, category_balance, semantic_coherence,
                user_satisfaction, system_adaptability
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics['timestamp'], metrics['total_classifications'], metrics['accuracy_rate'],
            metrics['confidence_correlation'], metrics['learning_velocity'], metrics['improvement_score'],
            metrics['category_balance'], metrics['semantic_coherence'], metrics['user_satisfaction'],
            metrics['system_adaptability']
        ))
        
        conn.commit()
        conn.close()
    
    def get_learning_progress(self, days: int = 30) -> Dict[str, Any]:
        """Obtiene el progreso de aprendizaje."""
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM learning_metrics 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (start_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {'error': 'No hay datos de aprendizaje en el período especificado'}
        
        # Convertir a métricas
        metrics_list = []
        for row in rows:
            metrics_list.append({
                'timestamp': row[1],
                'accuracy_rate': row[3],
                'confidence_correlation': row[4],
                'learning_velocity': row[5],
                'improvement_score': row[6]
            })
        
        # Calcular progreso
        progress = {
            'period_days': days,
            'total_snapshots': len(metrics_list),
            'accuracy_trend': [m['accuracy_rate'] for m in metrics_list],
            'confidence_trend': [m['confidence_correlation'] for m in metrics_list],
            'learning_velocity_trend': [m['learning_velocity'] for m in metrics_list],
            'improvement_trend': [m['improvement_score'] for m in metrics_list],
            'timestamps': [m['timestamp'] for m in metrics_list],
            'overall_improvement': self._calculate_overall_improvement(metrics_list)
        }
        
        return progress
    
    def _calculate_overall_improvement(self, metrics_list: List[Dict]) -> Dict[str, float]:
        """Calcula la mejora general."""
        if len(metrics_list) < 2:
            return {'accuracy': 0, 'confidence': 0, 'overall': 0}
        
        initial_accuracy = metrics_list[0]['accuracy_rate']
        final_accuracy = metrics_list[-1]['accuracy_rate']
        accuracy_improvement = final_accuracy - initial_accuracy
        
        initial_confidence = metrics_list[0]['confidence_correlation']
        final_confidence = metrics_list[-1]['confidence_correlation']
        confidence_improvement = final_confidence - initial_confidence
        
        overall_improvement = (accuracy_improvement + confidence_improvement) / 2
        
        return {
            'accuracy': accuracy_improvement,
            'confidence': confidence_improvement,
            'overall': overall_improvement
        }
    
    def create_learning_snapshot(self) -> Dict[str, Any]:
        """Crea un snapshot del estado de aprendizaje."""
        metrics = self._calculate_current_metrics()
        
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'model_performance': self._get_model_performance(),
            'category_performance': self._get_category_performance(),
            'learning_insights': self._generate_learning_insights(metrics),
            'improvement_suggestions': self._generate_improvement_suggestions(metrics)
        }
        
        return snapshot
    
    def _get_model_performance(self) -> Dict[str, float]:
        """Obtiene rendimiento por modelo."""
        classifications = self._get_all_classifications()
        feedback_notes = get_feedback_notes(self.db)
        
        model_performance = {}
        models_used = set(note.get('model', 'Unknown') for note in classifications)
        
        for model in models_used:
            model_notes = [n for n in classifications if n.get('model') == model]
            model_feedback = [n for n in feedback_notes if n.get('model') == model]
            
            if model_notes:
                accuracy = (1 - len(model_feedback) / len(model_notes)) * 100
                model_performance[model] = accuracy
        
        return model_performance
    
    def _get_category_performance(self) -> Dict[str, Dict[str, float]]:
        """Obtiene rendimiento por categoría."""
        classifications = self._get_all_classifications()
        feedback_notes = get_feedback_notes(self.db)
        
        category_performance = {}
        categories = set(note.get('predicted_category', 'Unknown') for note in classifications)
        
        for category in categories:
            category_notes = [n for n in classifications if n.get('predicted_category') == category]
            category_feedback = [n for n in feedback_notes if n.get('predicted_category') == category]
            
            if category_notes:
                total = len(category_notes)
                corrections = len(category_feedback)
                accuracy = (1 - corrections / total) * 100 if total > 0 else 0
                
                category_performance[category] = {
                    'total_notes': total,
                    'corrections': corrections,
                    'accuracy': accuracy,
                    'correction_rate': (corrections / total * 100) if total > 0 else 0
                }
        
        return category_performance
    
    def _generate_learning_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Genera insights de aprendizaje."""
        insights = []
        
        if metrics['learning_velocity'] > 0.7:
            insights.append("El sistema está aprendiendo rápidamente")
        elif metrics['learning_velocity'] < 0.3:
            insights.append("El sistema necesita más datos para aprender")
        
        if metrics['accuracy_rate'] > 90:
            insights.append("Excelente precisión en clasificaciones")
        elif metrics['accuracy_rate'] < 70:
            insights.append("Necesita mejorar la precisión de clasificación")
        
        if metrics['confidence_correlation'] > 0.8:
            insights.append("Alta correlación entre confianza y precisión")
        elif metrics['confidence_correlation'] < 0.3:
            insights.append("Baja correlación entre confianza y precisión")
        
        return insights
    
    def _generate_improvement_suggestions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera sugerencias de mejora."""
        suggestions = []
        
        if metrics['accuracy_rate'] < 85:
            suggestions.append({
                'type': 'accuracy_improvement',
                'priority': 'high',
                'description': f'Precisión actual: {metrics["accuracy_rate"]:.1f}%. Objetivo: 85%',
                'action': 'Revisar reglas de clasificación y entrenar con más ejemplos'
            })
        
        if metrics['confidence_correlation'] < 0.6:
            suggestions.append({
                'type': 'confidence_optimization',
                'priority': 'medium',
                'description': 'Baja correlación entre confianza y precisión',
                'action': 'Ajustar umbrales de confianza y mejorar calibración'
            })
        
        return suggestions
    
    def learn_from_folder_creation(self, folder_info: Dict, user_feedback: str, feedback_reason: str = "") -> Dict[str, Any]:
        """Aprende específicamente de la creación de carpetas basado en feedback del usuario."""
        learning_insights = []
        improvements = []
        
        # Extraer información de la carpeta
        folder_name = folder_info.get('folder_name', '')
        category = folder_info.get('category', '')
        note_content = folder_info.get('note_content', '')
        note_tags = folder_info.get('note_tags', [])
        note_patterns = folder_info.get('note_patterns', {})
        confidence = folder_info.get('confidence', 0)
        method_used = folder_info.get('method_used', '')
        semantic_score = folder_info.get('semantic_score', 0)
        ai_score = folder_info.get('ai_score', 0)
        
        # Guardar feedback en la base de datos
        self._save_folder_feedback(folder_info, user_feedback, feedback_reason)
        
        # Analizar el feedback
        is_positive = user_feedback.lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
        
        if is_positive:
            learning_insights.append(f"Carpeta '{folder_name}' aprobada - patrón válido")
            improvements.append({
                'type': 'folder_pattern_validation',
                'folder_name': folder_name,
                'category': category,
                'confidence': confidence,
                'method': method_used
            })
        else:
            learning_insights.append(f"Carpeta '{folder_name}' rechazada - patrón a evitar")
            improvements.append({
                'type': 'folder_pattern_rejection',
                'folder_name': folder_name,
                'category': category,
                'confidence': confidence,
                'method': method_used,
                'reason': feedback_reason
            })
        
        # Actualizar patrones de nombres de carpetas
        self._update_folder_name_patterns(folder_name, category, is_positive)
        
        # Generar insights específicos para carpetas
        folder_insights = self._analyze_folder_creation_patterns(folder_name, category, note_content, note_tags, note_patterns)
        learning_insights.extend(folder_insights)
        
        return {
            'learning_insights': learning_insights,
            'improvements': improvements,
            'folder_analysis': {
                'name_quality': self._analyze_folder_name_quality(folder_name),
                'category_appropriateness': self._analyze_category_appropriateness(category, note_content),
                'pattern_detection': self._detect_folder_creation_patterns(note_content, note_tags, note_patterns)
            }
        }
    
    def _save_folder_feedback(self, folder_info: Dict, user_feedback: str, feedback_reason: str):
        """Guarda el feedback sobre la creación de carpetas."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO folder_creation_feedback 
            (timestamp, folder_name, category, note_content, note_tags, note_patterns, 
             user_feedback, feedback_reason, confidence, method_used, semantic_score, ai_score, learning_insights)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            folder_info.get('folder_name', ''),
            folder_info.get('category', ''),
            folder_info.get('note_content', ''),
            json.dumps(folder_info.get('note_tags', [])),
            json.dumps(folder_info.get('note_patterns', {})),
            user_feedback,
            feedback_reason,
            folder_info.get('confidence', 0),
            folder_info.get('method_used', ''),
            folder_info.get('semantic_score', 0),
            folder_info.get('ai_score', 0),
            json.dumps([])  # learning_insights se calculan después
        ))
        
        conn.commit()
        conn.close()
    
    def _update_folder_name_patterns(self, folder_name: str, category: str, is_positive: bool):
        """Actualiza los patrones de nombres de carpetas basado en feedback."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        # Buscar patrón existente
        cursor.execute('''
            SELECT id, success_rate, usage_count FROM folder_name_patterns 
            WHERE pattern = ? AND category = ?
        ''', (folder_name, category))
        
        result = cursor.fetchone()
        
        if result:
            pattern_id, current_success_rate, usage_count = result
            new_usage_count = usage_count + 1
            new_success_rate = ((current_success_rate * usage_count) + (1 if is_positive else 0)) / new_usage_count
            
            cursor.execute('''
                UPDATE folder_name_patterns 
                SET success_rate = ?, usage_count = ?, last_used = ?
                WHERE id = ?
            ''', (new_success_rate, new_usage_count, datetime.utcnow().isoformat(), pattern_id))
        else:
            cursor.execute('''
                INSERT INTO folder_name_patterns 
                (pattern, category, success_rate, usage_count, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                folder_name, 
                category, 
                1.0 if is_positive else 0.0, 
                1, 
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def _analyze_folder_creation_patterns(self, folder_name: str, category: str, note_content: str, note_tags: List, note_patterns: Dict) -> List[str]:
        """Analiza patrones en la creación de carpetas."""
        insights = []
        
        # Analizar longitud del nombre
        if len(folder_name) < 3:
            insights.append("Nombre de carpeta muy corto - considerar nombres más descriptivos")
        elif len(folder_name) > 50:
            insights.append("Nombre de carpeta muy largo - considerar nombres más concisos")
        
        # Analizar uso de guiones y guiones bajos
        if '-' in folder_name and '_' in folder_name:
            insights.append("Mezcla de guiones y guiones bajos - mantener consistencia")
        
        # Analizar contenido de la nota vs nombre de carpeta
        content_words = set(note_content.lower().split())
        folder_words = set(folder_name.lower().replace('-', ' ').replace('_', ' ').split())
        
        overlap = content_words.intersection(folder_words)
        if len(overlap) < 1:
            insights.append("Poca relación entre contenido de nota y nombre de carpeta")
        
        # Analizar tags relevantes
        if note_tags:
            tag_words = set()
            for tag in note_tags:
                tag_words.update(tag.lower().replace('#', '').split())
            
            tag_overlap = tag_words.intersection(folder_words)
            if len(tag_overlap) > 0:
                insights.append("Tags coinciden con nombre de carpeta - patrón positivo")
        
        return insights
    
    def _analyze_folder_name_quality(self, folder_name: str) -> Dict[str, Any]:
        """Analiza la calidad del nombre de la carpeta."""
        return {
            'length': len(folder_name),
            'word_count': len(folder_name.split()),
            'has_hyphens': '-' in folder_name,
            'has_underscores': '_' in folder_name,
            'has_spaces': ' ' in folder_name,
            'is_lowercase': folder_name.islower(),
            'is_uppercase': folder_name.isupper(),
            'has_numbers': any(c.isdigit() for c in folder_name),
            'quality_score': self._calculate_name_quality_score(folder_name)
        }
    
    def _calculate_name_quality_score(self, folder_name: str) -> float:
        """Calcula un score de calidad para el nombre de la carpeta."""
        score = 0.0
        
        # Longitud óptima (5-30 caracteres)
        length = len(folder_name)
        if 5 <= length <= 30:
            score += 0.3
        elif 3 <= length <= 50:
            score += 0.2
        
        # Uso de guiones (preferido)
        if '-' in folder_name and ' ' not in folder_name:
            score += 0.2
        
        # Consistencia de formato
        if folder_name.islower() or folder_name.isupper():
            score += 0.2
        
        # Palabras múltiples
        word_count = len(folder_name.split())
        if 1 <= word_count <= 4:
            score += 0.2
        
        # Sin caracteres especiales problemáticos
        if not any(c in folder_name for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            score += 0.1
        
        return min(1.0, score)
    
    def _analyze_category_appropriateness(self, category: str, note_content: str) -> Dict[str, Any]:
        """Analiza si la categoría es apropiada para el contenido."""
        content_lower = note_content.lower()
        
        # Patrones específicos por categoría
        patterns = {
            'Projects': ['proyecto', 'project', 'desarrollo', 'development', 'implementación', 'implementation'],
            'Areas': ['área', 'area', 'responsabilidad', 'responsibility', 'rol', 'role', 'función', 'function'],
            'Resources': ['recurso', 'resource', 'referencia', 'reference', 'documentación', 'documentation'],
            'Archive': ['archivo', 'archive', 'completado', 'completed', 'finalizado', 'finished']
        }
        
        category_patterns = patterns.get(category, [])
        matches = sum(1 for pattern in category_patterns if pattern in content_lower)
        
        return {
            'category': category,
            'pattern_matches': matches,
            'total_patterns': len(category_patterns),
            'appropriateness_score': matches / len(category_patterns) if category_patterns else 0.5
        }
    
    def _detect_folder_creation_patterns(self, note_content: str, note_tags: List, note_patterns: Dict) -> Dict[str, Any]:
        """Detecta patrones que sugieren la creación de carpetas."""
        patterns = {
            'has_todos': bool(note_patterns.get('todos', [])),
            'has_dates': bool(note_patterns.get('dates', [])),
            'has_links': bool(note_patterns.get('links', [])),
            'has_attachments': bool(note_patterns.get('attachments', [])),
            'has_headers': bool(note_patterns.get('headers', [])),
            'has_lists': bool(note_patterns.get('lists', [])),
            'has_code_blocks': bool(note_patterns.get('code_blocks', [])),
            'has_tables': bool(note_patterns.get('tables', [])),
            'has_quotes': bool(note_patterns.get('quotes', [])),
            'has_emphasis': bool(note_patterns.get('emphasis', [])),
            'has_strikethroughs': bool(note_patterns.get('strikethroughs', [])),
            'has_footnotes': bool(note_patterns.get('footnotes', [])),
            'project_indicators': self._detect_project_indicators(note_content, note_tags),
            'area_indicators': self._detect_area_indicators(note_content, note_tags),
            'resource_indicators': self._detect_resource_indicators(note_content, note_tags)
        }
        
        return patterns
    
    def _detect_project_indicators(self, note_content: str, note_tags: List) -> List[str]:
        """Detecta indicadores de que la nota es un proyecto."""
        indicators = []
        content_lower = note_content.lower()
        
        project_keywords = [
            'proyecto', 'project', 'desarrollo', 'development', 'implementación', 'implementation',
            'objetivo', 'objective', 'meta', 'goal', 'deadline', 'fecha límite', 'timeline',
            'equipo', 'team', 'colaboración', 'collaboration', 'plan', 'planning'
        ]
        
        for keyword in project_keywords:
            if keyword in content_lower:
                indicators.append(keyword)
        
        # Buscar tags de proyecto
        project_tags = [tag for tag in note_tags if any(keyword in tag.lower() for keyword in ['proyecto', 'project', 'dev', 'development'])]
        indicators.extend(project_tags)
        
        return indicators
    
    def _detect_area_indicators(self, note_content: str, note_tags: List) -> List[str]:
        """Detecta indicadores de que la nota es un área."""
        indicators = []
        content_lower = note_content.lower()
        
        area_keywords = [
            'área', 'area', 'responsabilidad', 'responsibility', 'rol', 'role', 'función', 'function',
            'mantenimiento', 'maintenance', 'gestión', 'management', 'supervisión', 'supervision',
            'política', 'policy', 'proceso', 'process', 'estándar', 'standard'
        ]
        
        for keyword in area_keywords:
            if keyword in content_lower:
                indicators.append(keyword)
        
        # Buscar tags de área
        area_tags = [tag for tag in note_tags if any(keyword in tag.lower() for keyword in ['área', 'area', 'responsabilidad', 'responsibility'])]
        indicators.extend(area_tags)
        
        return indicators
    
    def _detect_resource_indicators(self, note_content: str, note_tags: List) -> List[str]:
        """Detecta indicadores de que la nota es un recurso."""
        indicators = []
        content_lower = note_content.lower()
        
        resource_keywords = [
            'recurso', 'resource', 'referencia', 'reference', 'documentación', 'documentation',
            'manual', 'guide', 'tutorial', 'how-to', 'ejemplo', 'example', 'template',
            'biblioteca', 'library', 'herramienta', 'tool', 'framework', 'api'
        ]
        
        for keyword in resource_keywords:
            if keyword in content_lower:
                indicators.append(keyword)
        
        # Buscar tags de recurso
        resource_tags = [tag for tag in note_tags if any(keyword in tag.lower() for keyword in ['recurso', 'resource', 'referencia', 'reference'])]
        indicators.extend(resource_tags)
        
        return indicators
    
    def get_folder_creation_stats(self, days: int = 30) -> Dict[str, Any]:
        """Obtiene estadísticas sobre la creación de carpetas."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        # Obtener feedback reciente
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor.execute('''
            SELECT folder_name, category, user_feedback, confidence, method_used, semantic_score, ai_score
            FROM folder_creation_feedback 
            WHERE timestamp >= ?
        ''', (cutoff_date,))
        
        feedback_data = cursor.fetchall()
        
        if not feedback_data:
            return {
                'total_folders': 0,
                'approval_rate': 0.0,
                'category_distribution': {},
                'method_performance': {},
                'confidence_analysis': {},
                'top_patterns': [],
                'learning_insights': []
            }
        
        # Analizar datos
        total_folders = len(feedback_data)
        positive_feedback = sum(1 for row in feedback_data if row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena'])
        approval_rate = (positive_feedback / total_folders) * 100
        
        # Distribución por categoría
        category_counts = Counter(row[1] for row in feedback_data)
        category_approval = defaultdict(lambda: {'total': 0, 'approved': 0})
        
        for row in feedback_data:
            category = row[1]
            is_approved = row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
            category_approval[category]['total'] += 1
            if is_approved:
                category_approval[category]['approved'] += 1
        
        category_distribution = {
            cat: {
                'total': data['total'],
                'approved': data['approved'],
                'approval_rate': (data['approved'] / data['total']) * 100 if data['total'] > 0 else 0
            }
            for cat, data in category_approval.items()
        }
        
        # Rendimiento por método
        method_performance = defaultdict(lambda: {'total': 0, 'approved': 0, 'avg_confidence': []})
        
        for row in feedback_data:
            method = row[4] or 'unknown'
            is_approved = row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
            confidence = row[3] or 0
            
            method_performance[method]['total'] += 1
            method_performance[method]['avg_confidence'].append(confidence)
            if is_approved:
                method_performance[method]['approved'] += 1
        
        method_performance = {
            method: {
                'total': data['total'],
                'approved': data['approved'],
                'approval_rate': (data['approved'] / data['total']) * 100 if data['total'] > 0 else 0,
                'avg_confidence': statistics.mean(data['avg_confidence']) if data['avg_confidence'] else 0
            }
            for method, data in method_performance.items()
        }
        
        # Análisis de confianza
        confidences = [row[3] for row in feedback_data if row[3] is not None]
        confidence_analysis = {
            'mean': statistics.mean(confidences) if confidences else 0,
            'median': statistics.median(confidences) if confidences else 0,
            'std': statistics.stdev(confidences) if len(confidences) > 1 else 0,
            'high_confidence_approval': self._calculate_high_confidence_approval(feedback_data)
        }
        
        # Patrones más exitosos
        top_patterns = self._get_top_folder_patterns(days)
        
        # Insights de aprendizaje
        learning_insights = self._generate_folder_learning_insights(feedback_data)
        
        conn.close()
        
        return {
            'total_folders': total_folders,
            'approval_rate': approval_rate,
            'category_distribution': category_distribution,
            'method_performance': method_performance,
            'confidence_analysis': confidence_analysis,
            'top_patterns': top_patterns,
            'learning_insights': learning_insights
        }
    
    def _calculate_high_confidence_approval(self, feedback_data: List) -> Dict[str, float]:
        """Calcula la tasa de aprobación para diferentes niveles de confianza."""
        high_confidence = []  # > 0.8
        medium_confidence = []  # 0.5-0.8
        low_confidence = []  # < 0.5
        
        for row in feedback_data:
            confidence = row[3] or 0
            is_approved = row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
            
            if confidence > 0.8:
                high_confidence.append(is_approved)
            elif confidence >= 0.5:
                medium_confidence.append(is_approved)
            else:
                low_confidence.append(is_approved)
        
        return {
            'high_confidence': (sum(high_confidence) / len(high_confidence) * 100) if high_confidence else 0,
            'medium_confidence': (sum(medium_confidence) / len(medium_confidence) * 100) if medium_confidence else 0,
            'low_confidence': (sum(low_confidence) / len(low_confidence) * 100) if low_confidence else 0
        }
    
    def _get_top_folder_patterns(self, days: int) -> List[Dict[str, Any]]:
        """Obtiene los patrones de nombres de carpetas más exitosos."""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor.execute('''
            SELECT pattern, category, success_rate, usage_count, last_used
            FROM folder_name_patterns 
            WHERE last_used >= ? AND usage_count >= 2
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT 10
        ''', (cutoff_date,))
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'pattern': row[0],
                'category': row[1],
                'success_rate': row[2],
                'usage_count': row[3],
                'last_used': row[4]
            })
        
        conn.close()
        return patterns
    
    def _generate_folder_learning_insights(self, feedback_data: List) -> List[str]:
        """Genera insights de aprendizaje basado en el feedback de carpetas."""
        insights = []
        
        if not feedback_data:
            return ["No hay datos suficientes para generar insights"]
        
        # Análisis de confianza vs aprobación
        high_conf_approved = sum(1 for row in feedback_data 
                               if (row[3] or 0) > 0.8 and row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena'])
        high_conf_total = sum(1 for row in feedback_data if (row[3] or 0) > 0.8)
        
        if high_conf_total > 0:
            high_conf_rate = (high_conf_approved / high_conf_total) * 100
            if high_conf_rate < 80:
                insights.append(f"Alta confianza no garantiza aprobación ({high_conf_rate:.1f}% aprobación)")
            else:
                insights.append(f"Alta confianza correlaciona bien con aprobación ({high_conf_rate:.1f}% aprobación)")
        
        # Análisis por método
        method_approval = defaultdict(lambda: {'total': 0, 'approved': 0})
        for row in feedback_data:
            method = row[4] or 'unknown'
            is_approved = row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
            method_approval[method]['total'] += 1
            if is_approved:
                method_approval[method]['approved'] += 1
        
        best_method = max(method_approval.items(), 
                         key=lambda x: (x[1]['approved'] / x[1]['total']) if x[1]['total'] > 0 else 0)
        worst_method = min(method_approval.items(), 
                          key=lambda x: (x[1]['approved'] / x[1]['total']) if x[1]['total'] > 0 else 1)
        
        if best_method[1]['total'] > 0:
            best_rate = (best_method[1]['approved'] / best_method[1]['total']) * 100
            insights.append(f"Método más efectivo: {best_method[0]} ({best_rate:.1f}% aprobación)")
        
        if worst_method[1]['total'] > 0:
            worst_rate = (worst_method[1]['approved'] / worst_method[1]['total']) * 100
            insights.append(f"Método menos efectivo: {worst_method[0]} ({worst_rate:.1f}% aprobación)")
        
        # Análisis por categoría
        category_approval = defaultdict(lambda: {'total': 0, 'approved': 0})
        for row in feedback_data:
            category = row[1]
            is_approved = row[2].lower() in ['yes', 'y', 'si', 'sí', 'correcto', 'correcta', 'bueno', 'buena']
            category_approval[category]['total'] += 1
            if is_approved:
                category_approval[category]['approved'] += 1
        
        best_category = max(category_approval.items(), 
                           key=lambda x: (x[1]['approved'] / x[1]['total']) if x[1]['total'] > 0 else 0)
        
        if best_category[1]['total'] > 0:
            best_cat_rate = (best_category[1]['approved'] / best_category[1]['total']) * 100
            insights.append(f"Categoría más precisa: {best_category[0]} ({best_cat_rate:.1f}% aprobación)")
        
        return insights
    
    def suggest_folder_improvements(self) -> List[Dict[str, Any]]:
        """Sugiere mejoras basadas en el análisis de carpetas."""
        suggestions = []
        
        # Obtener estadísticas recientes
        stats = self.get_folder_creation_stats(30)
        
        if stats['total_folders'] == 0:
            return [{'type': 'no_data', 'message': 'No hay datos suficientes para sugerir mejoras', 'priority': 'low'}]
        
        # Sugerencias basadas en tasa de aprobación
        if stats['approval_rate'] < 70:
            suggestions.append({
                'type': 'low_approval_rate',
                'message': f"Tasa de aprobación baja ({stats['approval_rate']:.1f}%)",
                'suggestion': 'Revisar criterios de clasificación y patrones de nombres',
                'priority': 'high'
            })
        
        # Sugerencias basadas en rendimiento por método
        for method, performance in stats['method_performance'].items():
            if performance['total'] >= 5 and performance['approval_rate'] < 60:
                suggestions.append({
                    'type': 'method_underperforming',
                    'message': f"Método '{method}' con baja aprobación ({performance['approval_rate']:.1f}%)",
                    'suggestion': f'Optimizar o ajustar el método {method}',
                    'priority': 'medium'
                })
        
        # Sugerencias basadas en categorías
        for category, data in stats['category_distribution'].items():
            if data['total'] >= 3 and data['approval_rate'] < 60:
                suggestions.append({
                    'type': 'category_underperforming',
                    'message': f"Categoría '{category}' con baja aprobación ({data['approval_rate']:.1f}%)",
                    'suggestion': f'Revisar criterios para la categoría {category}',
                    'priority': 'medium'
                })
        
        # Sugerencias basadas en confianza
        confidence_analysis = stats['confidence_analysis']
        if confidence_analysis['high_confidence_approval']['high_confidence'] < 80:
            suggestions.append({
                'type': 'confidence_misalignment',
                'message': 'Alta confianza no correlaciona con alta aprobación',
                'suggestion': 'Revisar cálculo de confianza o criterios de aprobación',
                'priority': 'high'
            })
        
        return suggestions