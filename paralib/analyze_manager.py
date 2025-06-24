#!/usr/bin/env python3
"""
paralib/analyze_manager.py

Motor de análisis estadístico y semántico para notas Obsidian.
Expone features y métricas para mejorar clasificación, reclasificación y limpieza.
POTENCIADO CON CHROMADB para máxima precisión de clasificación PARA.
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
from paralib.db import ChromaPARADatabase
from paralib.logger import logger
import json
import datetime

class AnalyzeManager:
    def __init__(self, vault_path: Path, db_path: Path = None):
        self.vault_path = Path(vault_path)
        self.db_path = db_path or (self.vault_path / ".para_db" / "chroma")
        self.db = ChromaPARADatabase(db_path=str(self.db_path))
        self.snapshots = []  # Lista de snapshots históricos
        self.clusters = None
        self.cluster_labels = None
        self.cluster_keywords = None
        self.note_to_cluster = {}
        self.stats = {}
        self.category_patterns = {}  # Patrones semánticos por categoría
        self._analyze()

    def _analyze(self):
        """Calcula embeddings, clusters, comunidades y métricas globales."""
        notes = self.db.get_all_notes_metadata()
        embeddings = np.array([n['embedding'] for n in notes if 'embedding' in n])
        paths = [n['filename'] for n in notes]
        # Clustering simple (puede mejorarse con HDBSCAN, etc.)
        from sklearn.cluster import KMeans
        n_clusters = min(8, len(embeddings)//10+1) if len(embeddings) > 10 else 1
        if len(embeddings) < 2:
            self.clusters = np.zeros(len(embeddings), dtype=int)
        else:
            self.clusters = KMeans(n_clusters=n_clusters, n_init=5, random_state=42).fit_predict(embeddings)
        self.cluster_labels = {i: [] for i in range(n_clusters)}
        for idx, label in enumerate(self.clusters):
            self.cluster_labels[label].append(paths[idx])
            self.note_to_cluster[paths[idx]] = label
        # Palabras clave por cluster
        from collections import Counter
        self.cluster_keywords = {}
        for label, files in self.cluster_labels.items():
            keywords = []
            for f in files:
                note = next((n for n in notes if n['filename'] == f), None)
                if note and 'content' in note:
                    keywords += [w for w in note['content'].split() if len(w) > 4]
            most_common = [w for w, _ in Counter(keywords).most_common(5)]
            self.cluster_keywords[label] = most_common
        # Métricas globales
        self.stats = {
            'total_notes': len(notes),
            'n_clusters': n_clusters,
            'cluster_sizes': {k: len(v) for k, v in self.cluster_labels.items()},
            'keywords_per_cluster': self.cluster_keywords,
        }
        # Análisis de patrones por categoría usando ChromaDB
        self._analyze_category_patterns()
        # Guardar snapshot
        self.save_snapshot()

    def _analyze_category_patterns(self):
        """
        Analiza patrones semánticos por categoría usando ChromaDB.
        Mejora significativamente la precisión de clasificación.
        """
        categories = ["Projects", "Areas", "Resources", "Archive"]
        
        for category in categories:
            category_notes = self.db.search_by_category(category, n_results=50)
            
            if category_notes:
                # Extraer patrones de contenido
                contents = []
                project_names = []
                
                for metadata, _ in category_notes:
                    if 'content' in metadata:
                        contents.append(metadata['content'])
                    if 'project_name' in metadata and metadata['project_name']:
                        project_names.append(metadata['project_name'])
                
                # Análisis de patrones
                self.category_patterns[category] = {
                    'sample_size': len(category_notes),
                    'common_project_names': list(set(project_names))[:10],
                    'content_patterns': self._extract_content_patterns(contents),
                    'semantic_centroid': self._calculate_semantic_centroid(contents)
                }
            else:
                self.category_patterns[category] = {
                    'sample_size': 0,
                    'common_project_names': [],
                    'content_patterns': {},
                    'semantic_centroid': None
                }

    def _extract_content_patterns(self, contents: List[str]) -> Dict[str, Any]:
        """
        Extrae patrones de contenido para identificar características de categoría.
        """
        if not contents:
            return {}
        
        # Análisis de palabras clave
        from collections import Counter
        import re
        
        all_words = []
        for content in contents:
            # Limpiar y tokenizar
            words = re.findall(r'\b\w+\b', content.lower())
            all_words.extend([w for w in words if len(w) > 3])
        
        word_freq = Counter(all_words)
        top_keywords = [word for word, freq in word_freq.most_common(20)]
        
        # Análisis de estructura (títulos, fechas, etc.)
        has_dates = any(re.search(r'\d{4}-\d{2}-\d{2}', content) for content in contents)
        has_todos = any('todo' in content.lower() or 'task' in content.lower() for content in contents)
        has_links = any('[[' in content and ']]' in content for content in contents)
        
        return {
            'top_keywords': top_keywords,
            'has_dates': has_dates,
            'has_todos': has_todos,
            'has_links': has_links,
            'avg_content_length': sum(len(c) for c in contents) / len(contents)
        }

    def _calculate_semantic_centroid(self, contents: List[str]) -> List[float]:
        """
        Calcula el centroide semántico de una lista de contenidos.
        """
        if not contents:
            return None
        
        # Usar el modelo de embeddings para calcular centroide
        embeddings = []
        for content in contents[:10]:  # Limitar para eficiencia
            try:
                embedding = self.db.embedding_model.encode(
                    content[:1000], convert_to_tensor=False
                ).tolist()
                embeddings.append(embedding)
            except:
                continue
        
        if embeddings:
            return np.mean(embeddings, axis=0).tolist()
        return None

    def get_enhanced_classification_suggestion(self, note_path: Path, content: str) -> Dict[str, Any]:
        """
        Obtiene sugerencia de clasificación potenciada con ChromaDB.
        Combina análisis semántico, patrones de categoría y vecinos cercanos.
        """
        # Análisis de vecinos semánticos por categoría
        neighbors_analysis = self.db.get_semantic_neighbors_for_classification(content, n_results=5)
        
        # Calcular scores por categoría
        category_scores = {}
        for category, analysis in neighbors_analysis.items():
            if analysis['count'] > 0:
                # Score basado en distancia promedio (menor = mejor)
                avg_distance = analysis['avg_distance']
                score = max(0, 1 - avg_distance)  # Normalizar a 0-1
                category_scores[category] = score
            else:
                category_scores[category] = 0.0
        
        # Análisis de patrones de contenido
        content_patterns = self._extract_content_patterns([content])
        
        # Ajustar scores basado en patrones
        pattern_adjustments = self._calculate_pattern_adjustments(content_patterns)
        
        for category, adjustment in pattern_adjustments.items():
            if category in category_scores:
                category_scores[category] += adjustment
                category_scores[category] = max(0, min(1, category_scores[category]))  # Clamp 0-1
        
        # Obtener la mejor categoría
        best_category = max(category_scores.items(), key=lambda x: x[1])
        
        # Análisis de confianza
        confidence = self._calculate_classification_confidence(category_scores, neighbors_analysis)
        
        return {
            'suggested_category': best_category[0],
            'confidence_score': confidence,
            'category_scores': category_scores,
            'neighbors_analysis': neighbors_analysis,
            'content_patterns': content_patterns,
            'reasoning': self._generate_classification_reasoning(best_category[0], neighbors_analysis, content_patterns)
        }

    def _calculate_pattern_adjustments(self, content_patterns: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula ajustes de score basado en patrones de contenido.
        """
        adjustments = {
            'Projects': 0.0,
            'Areas': 0.0,
            'Resources': 0.0,
            'Archive': 0.0
        }
        
        # Patrones específicos por categoría
        if content_patterns.get('has_todos', False):
            adjustments['Projects'] += 0.2
            adjustments['Areas'] += 0.1
        
        if content_patterns.get('has_dates', False):
            adjustments['Projects'] += 0.15
        
        if content_patterns.get('has_links', False):
            adjustments['Resources'] += 0.2
        
        # Análisis de palabras clave
        keywords = set(content_patterns.get('top_keywords', []))
        
        # Patrones para Projects
        project_keywords = {'project', 'proyecto', 'deadline', 'milestone', 'goal', 'objetivo'}
        if keywords & project_keywords:
            adjustments['Projects'] += 0.3
        
        # Patrones para Areas
        area_keywords = {'area', 'responsabilidad', 'review', 'quarterly', 'monthly'}
        if keywords & area_keywords:
            adjustments['Areas'] += 0.3
        
        # Patrones para Resources
        resource_keywords = {'resource', 'recurso', 'reference', 'referencia', 'template', 'prompt'}
        if keywords & resource_keywords:
            adjustments['Resources'] += 0.3
        
        # Patrones para Archive
        archive_keywords = {'archive', 'archivado', 'old', 'completado', 'finished'}
        if keywords & archive_keywords:
            adjustments['Archive'] += 0.3
        
        return adjustments

    def _calculate_classification_confidence(self, category_scores: Dict[str, float], neighbors_analysis: Dict) -> float:
        """
        Calcula el nivel de confianza en la clasificación sugerida.
        """
        if not category_scores:
            return 0.0
        
        # Score más alto
        max_score = max(category_scores.values())
        
        # Diferencia con el segundo mejor
        sorted_scores = sorted(category_scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            score_diff = sorted_scores[0] - sorted_scores[1]
        else:
            score_diff = 0.0
        
        # Número de vecinos encontrados
        total_neighbors = sum(analysis['count'] for analysis in neighbors_analysis.values())
        
        # Calcular confianza
        confidence = max_score * 0.6 + min(score_diff * 2, 0.3) + min(total_neighbors / 20, 0.1)
        
        return min(confidence, 1.0)

    def _generate_classification_reasoning(self, category: str, neighbors_analysis: Dict, content_patterns: Dict[str, Any]) -> str:
        """
        Genera explicación del razonamiento de clasificación.
        """
        reasoning_parts = []
        
        # Análisis de vecinos
        if neighbors_analysis[category]['count'] > 0:
            avg_distance = neighbors_analysis[category]['avg_distance']
            reasoning_parts.append(f"Encontrados {neighbors_analysis[category]['count']} documentos similares en {category} (distancia promedio: {avg_distance:.3f})")
        
        # Análisis de patrones
        if content_patterns.get('has_todos'):
            reasoning_parts.append("Contiene elementos de tareas/TO-DOs")
        
        if content_patterns.get('has_dates'):
            reasoning_parts.append("Contiene fechas/deadlines")
        
        if content_patterns.get('has_links'):
            reasoning_parts.append("Contiene enlaces a otros documentos")
        
        # Palabras clave relevantes
        relevant_keywords = content_patterns.get('top_keywords', [])[:5]
        if relevant_keywords:
            reasoning_parts.append(f"Palabras clave relevantes: {', '.join(relevant_keywords)}")
        
        return "; ".join(reasoning_parts) if reasoning_parts else "Clasificación basada en análisis semántico general"

    def get_semantic_duplicates(self, note_path: Path, content: str, threshold: float = 0.85) -> List[Tuple[Dict, float]]:
        """
        Encuentra duplicados semánticos usando ChromaDB.
        """
        similar_notes = self.db.search_similar_notes(content, n_results=10)
        duplicates = []
        
        for metadata, distance in similar_notes:
            if distance < threshold and metadata.get('path') != str(note_path):
                duplicates.append((metadata, distance))
        
        return duplicates

    def get_category_insights(self) -> Dict[str, Any]:
        """
        Obtiene insights detallados sobre cada categoría usando ChromaDB.
        """
        insights = {}
        
        for category in ["Projects", "Areas", "Resources", "Archive"]:
            category_notes = self.db.search_by_category(category, n_results=100)
            
            if category_notes:
                # Análisis de proyectos activos
                if category == "Projects":
                    project_patterns = self.db.get_project_patterns()
                    insights[category] = {
                        'total_notes': len(category_notes),
                        'active_projects': len(project_patterns.get('recent_projects', [])),
                        'project_names': project_patterns.get('project_names', [])[:10],
                        'patterns': self.category_patterns.get(category, {})
                    }
                else:
                    insights[category] = {
                        'total_notes': len(category_notes),
                        'patterns': self.category_patterns.get(category, {})
                    }
            else:
                insights[category] = {
                    'total_notes': 0,
                    'patterns': {}
                }
        
        return insights

    def save_snapshot(self):
        snap = {
            'timestamp': datetime.datetime.now().isoformat(),
            'stats': self.stats,
            'cluster_labels': self.cluster_labels,
            'cluster_keywords': self.cluster_keywords,
        }
        self.snapshots.append(snap)
        logger.info(f"[ANALYZE-MANAGER] Snapshot guardado: {snap['timestamp']}")

    def get_features_for_note(self, note_path: Path) -> Dict[str, Any]:
        """Devuelve features estadísticos y de cluster para una nota."""
        note_path_str = str(note_path)
        cluster = self.note_to_cluster.get(note_path_str, None)
        features = {}
        if cluster is not None:
            size = len(self.cluster_labels[cluster])
            features['cluster_cohesion_score'] = size / max(1, self.stats['total_notes'])
            features['community_size'] = size
            features['suggested_category_by_cluster'] = self._suggest_category(cluster)
            features['cluster_keywords'] = self.cluster_keywords[cluster]
        else:
            features['cluster_cohesion_score'] = 0
            features['community_size'] = 1
            features['suggested_category_by_cluster'] = None
            features['cluster_keywords'] = []
        # Redundancia semántica (similitud > 0.95 con otra nota)
        similar = self.db.search_similar_notes(note_path_str, n_results=2)
        features['is_semantic_duplicate'] = False
        if similar and len(similar) > 1:
            _, sim_score = similar[1]
            features['is_semantic_duplicate'] = sim_score > 0.95
        return features

    def _suggest_category(self, cluster):
        # Sugerencia simple: si keywords dominantes coinciden con PARA
        keywords = set([k.lower() for k in self.cluster_keywords.get(cluster, [])])
        if any(k in keywords for k in ['project', 'proyecto', 'okr', 'deadline']):
            return 'Projects'
        if any(k in keywords for k in ['area', 'responsabilidad', 'review']):
            return 'Areas'
        if any(k in keywords for k in ['resource', 'recurso', 'referencia', 'prompt']):
            return 'Resources'
        if any(k in keywords for k in ['archive', 'archivado', 'old']):
            return 'Archive'
        return None

    def get_cluster_for_note(self, note_path: Path):
        return self.note_to_cluster.get(str(note_path), None)

    def get_statistical_summary(self):
        return self.stats

    def export_snapshot(self, path: Path, fmt: str = 'json'):
        snap = self.snapshots[-1] if self.snapshots else {}
        if fmt == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(snap, f, indent=2, ensure_ascii=False)
        elif fmt == 'csv':
            import csv
            with open(path, 'w', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Cluster', 'Size', 'Keywords'])
                for k, v in self.stats['cluster_sizes'].items():
                    writer.writerow([k, v, ', '.join(self.cluster_keywords[k])])
        logger.info(f"[ANALYZE-MANAGER] Snapshot exportado a {path}") 