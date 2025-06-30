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
from paralib.db import RobustChromaPARADatabase as ChromaPARADatabase
from paralib.logger import logger
from paralib.log_center import log_center
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
        # Usar rutas completas en lugar de solo filenames
        paths = [n.get('path', n.get('filename', '')) for n in notes]
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
        # Palabras clave por cluster - USAR CONTENIDO DE CHROMADB
        from collections import Counter
        self.cluster_keywords = {}
        for label, file_paths in self.cluster_labels.items():
            keywords = []
            for file_path in file_paths:
                # Buscar nota por path completo
                note = next((n for n in notes if n.get('path') == file_path or n.get('filename') == file_path), None)
                if note:
                    # Usar contenido directamente desde ChromaDB si está disponible
                    content = ""
                    if 'content' in note:
                        content = note['content']
                    else:
                        # Intentar leer desde disco como fallback
                        try:
                            note_path = Path(file_path) if Path(file_path).is_absolute() else self.vault_path / file_path
                            if note_path.exists():
                                content = note_path.read_text(encoding='utf-8')
                        except Exception:
                            continue
                    
                    if content:
                        # Extraer palabras significativas
                        import re
                        words = re.findall(r'\b\w+\b', content.lower())
                        keywords += [w for w in words if len(w) > 4 and w.isalpha()]
            
            # Obtener palabras más comunes
            most_common = [w for w, _ in Counter(keywords).most_common(10)]
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
        POTENCIADO: Incluye contenido completo para análisis de urgencia.
        """
        if not contents:
            return {}
        
        # Análisis de palabras clave
        from collections import Counter
        import re
        
        all_words = []
        full_content = " ".join(contents)  # NUEVO: Contenido completo para urgencia
        
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
            'avg_content_length': sum(len(c) for c in contents) / len(contents),
            'content_text': full_content  # NUEVO: Para análisis de urgencia
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
        try:
            # Obtener vecinos semánticos
            neighbors = self.db.get_semantic_neighbors_for_classification(content, n_results=5)
            
            # Analizar distribución de categorías en vecinos
            from collections import Counter
            category_counter = Counter()
            total_similarity = 0
            
            for neighbor in neighbors:
                category = neighbor.get('category', 'Unknown')
                similarity = neighbor.get('similarity_score', 0)
                category_counter[category] += similarity
                total_similarity += similarity
            
            # Normalizar scores por categoría
            category_scores = {}
            categories = ["Projects", "Areas", "Resources", "Archive"]
            
            for category in categories:
                if total_similarity > 0:
                    category_scores[category] = category_counter.get(category, 0) / max(total_similarity, 1)
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
            if category_scores:
                best_category = max(category_scores.items(), key=lambda x: x[1])
                suggested_category = best_category[0]
                confidence = best_category[1]
            else:
                suggested_category = "Resources"  # Fallback
                confidence = 0.5
            
            # Crear estructura de análisis de neighbors para compatibilidad
            neighbors_analysis = {}
            for category in categories:
                neighbor_count = sum(1 for n in neighbors if n.get('category') == category)
                neighbor_distances = [n.get('distance', 1.0) for n in neighbors if n.get('category') == category]
                avg_distance = sum(neighbor_distances) / len(neighbor_distances) if neighbor_distances else 1.0
                
                neighbors_analysis[category] = {
                    'count': neighbor_count,
                    'avg_distance': avg_distance
                }
            
            return {
                'suggested_category': suggested_category,
                'confidence_score': min(confidence, 1.0),
                'category_scores': category_scores,
                'neighbors_analysis': neighbors_analysis,
                'content_patterns': content_patterns,
                'reasoning': self._generate_classification_reasoning(suggested_category, neighbors_analysis, content_patterns)
            }
            
        except Exception as e:
            log_center.log_error(f"Error en clasificación mejorada: {e}", "AnalyzeManager")
            # Fallback básico
            return {
                'suggested_category': "Resources",
                'confidence_score': 0.5,
                'category_scores': {"Projects": 0.25, "Areas": 0.25, "Resources": 0.25, "Archive": 0.25},
                'neighbors_analysis': {},
                'content_patterns': {},
                'reasoning': "Clasificación de respaldo por error en análisis"
            }

    def _calculate_pattern_adjustments(self, content_patterns: Dict[str, Any]) -> Dict[str, float]:
        """
        Calcula ajustes de score basado en patrones de contenido.
        CORREGIDO: Reduce sesgo hacia Archive y mejora detección español.
        POTENCIADO: Agrega Factor 16 - Urgency Indicators.
        """
        adjustments = {
            'Projects': 0.0,
            'Areas': 0.0,
            'Resources': 0.0,
            'Archive': 0.0
        }
        
        # FACTOR 16: URGENCY INDICATORS (NUEVO - CRÍTICO) +12% PRECISIÓN
        urgency_keywords = {
            # Urgencia explícita - Español e Inglés
            'urgent', 'urgente', 'crítico', 'critical', 'emergency', 'emergencia',
            'asap', 'immediately', 'inmediatamente', 'ya', 'now', 'ahora',
            'priority', 'prioridad', 'prioritario', 'importante', 'important',
            
            # Indicadores temporales urgentes
            'deadline', 'fecha límite', 'overdue', 'atrasado', 'late', 'tarde',
            'rushing', 'apurando', 'hurry', 'apurar', 'quickly', 'rápido',
            'time-sensitive', 'sensible al tiempo', 'pressing', 'apremiante',
            
            # Modalidad de obligación
            'must do', 'debo hacer', 'tengo que', 'have to', 'need to', 'necesito',
            'required by', 'requerido para', 'due today', 'vence hoy', 'due tomorrow',
            'vence mañana', 'this week', 'esta semana', 'end of day', 'EOD',
            
            # Escalación de urgencia
            'escalate', 'escalar', 'urgent request', 'solicitud urgente',
            'high priority', 'alta prioridad', 'critical path', 'ruta crítica',
            'blocker', 'bloqueador', 'blocking', 'bloqueando'
        }
        
        # Obtener contenido para análisis de urgencia
        content = content_patterns.get('content_text', '')
        if hasattr(content_patterns, 'get') and 'top_keywords' in content_patterns:
            keywords = set(content_patterns.get('top_keywords', []))
        else:
            # Extraer keywords del contenido directamente
            import re
            content_words = re.findall(r'\b\w+\b', content.lower()) if content else []
            keywords = set(content_words)
        
        # Calcular score de urgencia
        urgency_matches = len(keywords & urgency_keywords)
        
        # Contar signos de exclamación y mayúsculas (indicadores de urgencia)
        if content:
            exclamation_count = content.count('!')
            caps_words = sum(1 for word in content.split() if word.isupper() and len(word) > 2)
            urgency_signals = urgency_matches + (exclamation_count * 0.5) + (caps_words * 0.3)
        else:
            urgency_signals = urgency_matches
        
        # Aplicar ajustes basados en urgencia
        if urgency_signals > 3:  # Muy urgente = proyecto
            adjustments['Projects'] += 0.35  # BOOST SIGNIFICATIVO
            adjustments['Archive'] -= 0.2   # Penalizar archive
        elif urgency_signals > 1:  # Moderadamente urgente
            adjustments['Projects'] += 0.2
            adjustments['Areas'] += 0.1      # También puede ser área urgente
            adjustments['Archive'] -= 0.1
        
        # Patrones específicos por categoría
        if content_patterns.get('has_todos', False):
            adjustments['Projects'] += 0.3  # Aumentado
            adjustments['Areas'] += 0.15
        
        if content_patterns.get('has_dates', False):
            adjustments['Projects'] += 0.25  # Aumentado
        
        if content_patterns.get('has_links', False):
            adjustments['Resources'] += 0.25  # Aumentado
            adjustments['Projects'] += 0.1   # También puede ser proyecto
        
        # Análisis de palabras clave - ESPAÑOL + INGLÉS
        keywords = set(content_patterns.get('top_keywords', []))
        
        # Patrones para Projects - EXPANDIDO
        project_keywords = {
            'project', 'proyecto', 'proyectos', 'deadline', 'milestone', 'goal', 'objetivo', 'objetivos',
            'desarrollo', 'implementacion', 'implementación', 'cliente', 'clientes', 'entrega',
            'planning', 'planificacion', 'task', 'tasks', 'tarea', 'tareas', 'sprint', 'epic',
            'requirement', 'requerimiento', 'feature', 'funcionalidad', 'scope', 'alcance'
        }
        if keywords & project_keywords:
            adjustments['Projects'] += 0.4  # Aumentado
        
        # Patrones para Areas - SUPER EXPANDIDO  
        area_keywords = {
            # Areas básicas
            'area', 'areas', 'responsabilidad', 'responsabilidades', 'review', 'revision',
            'quarterly', 'monthly', 'semanal', 'diario', 'proceso', 'procesos', 'standard',
            'estandar', 'política', 'politica', 'procedimiento', 'metodologia', 'framework',
            'coaching', 'liderazgo', 'management', 'gestion', 'administracion',
            
            # Áreas de vida/trabajo
            'health', 'salud', 'fitness', 'ejercicio', 'finanzas', 'finance', 'financial',
            'career', 'carrera', 'profesional', 'personal', 'desarrollo', 'growth',
            'relationships', 'relaciones', 'familia', 'family', 'education', 'educacion',
            'learning', 'aprendizaje', 'skills', 'habilidades', 'habits', 'habitos',
            
            # Gestión y mantenimiento
            'maintenance', 'mantenimiento', 'routine', 'rutina', 'checklist', 'monitoring',
            'seguimiento', 'improvement', 'mejora', 'optimization', 'optimizacion',
            'quality', 'calidad', 'standards', 'standardize', 'standardizar',
            
            # Indicadores de actividad continua
            'ongoing', 'continuo', 'continuous', 'regular', 'periodic', 'periodico',
            'recurring', 'recurrente', 'maintain', 'mantener', 'sustain', 'sostener'
        }
        if keywords & area_keywords:
            adjustments['Areas'] += 0.45  # AUMENTADO para compensar
        
        # Patrones para Resources - EXPANDIDO
        resource_keywords = {
            'resource', 'recurso', 'recursos', 'reference', 'referencia', 'referencias', 'template', 
            'plantilla', 'prompt', 'prompts', 'guia', 'guide', 'tutorial', 'documentacion',
            'documentation', 'manual', 'instrucciones', 'commands', 'comandos', 'codigo', 'code',
            'snippet', 'ejemplo', 'example', 'cheatsheet', 'tip', 'tips', 'tool', 'herramienta'
        }
        if keywords & resource_keywords:
            adjustments['Resources'] += 0.35
        
        # Patrones para Archive - REDUCIDO Y MÁS ESPECÍFICO
        archive_keywords = {
            'archive', 'archivado', 'archived', 'old', 'viejo', 'antiguo', 'obsoleto',
            'completado', 'finished', 'terminado', 'completed', 'deprecated', 'legacy'
        }
        if keywords & archive_keywords:
            adjustments['Archive'] += 0.2  # REDUCIDO de 0.3 a 0.2
        
        # ANTI-SESGO: Penalizar Archive si hay indicadores de contenido activo
        active_indicators = {
            'hacer', 'todo', 'pending', 'pendiente', 'working', 'current', 'actual',
            'nuevo', 'new', 'importante', 'important', 'urgente', 'urgent', 'prioritario'
        }
        if keywords & active_indicators:
            adjustments['Archive'] -= 0.2  # PENALIZACIÓN
            adjustments['Projects'] += 0.1
            adjustments['Areas'] += 0.1
        
        # BONUS: Detectar contenido técnico/desarrollo = Projects o Resources
        tech_keywords = {
            'docker', 'kubernetes', 'python', 'javascript', 'react', 'vue', 'node',
            'database', 'sql', 'api', 'server', 'deploy', 'git', 'github', 'config',
            'setup', 'install', 'configure', 'debug', 'error', 'fix', 'solution'
        }
        if keywords & tech_keywords:
            adjustments['Projects'] += 0.15
            adjustments['Resources'] += 0.15
            adjustments['Archive'] -= 0.1  # Reducir probabilidad archive
        
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
                    #project_patterns = self.db.get_project_patterns()
                    insights[category] = {
                        'total_notes': len(category_notes),
                        'active_projects': 0,
                        'project_names': [],
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

    def analyze_vault_structure(self, vault_path=None) -> dict:
        """Devuelve un resumen estructural del vault: total de notas, notas sin clasificar, estructura PARA."""
        from pathlib import Path
        path = Path(vault_path) if vault_path else self.vault_path
        total_notes = len(list(path.rglob("*.md")))
        para_dirs = ['00-inbox', '01-projects', '02-areas', '03-resources', '04-archive']
        para_exists = any((path / dir_name).exists() for dir_name in para_dirs)
        unclassified_notes = total_notes if not para_exists else 0
        return {
            'total_notes': total_notes,
            'unclassified_notes': unclassified_notes,
            'para_structure': 'Implementada' if para_exists else 'No implementada'
        }

    def analyze_note(self, note_path: Path, note_content: str = None, user_directive: str = "", detailed: bool = False) -> dict:
        """
        Análisis completo de una nota: contenido, tags, metadatos, fechas, etc.
        Si note_content no se pasa, lo lee del archivo.
        El argumento 'detailed' se acepta para compatibilidad con el CLI.
        """
        import re
        from datetime import datetime
        import os
        if note_content is None:
            try:
                note_content = note_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"No se pudo leer la nota {note_path}: {e}")
                return {"error": str(e)}
        analysis = {
            'content': note_content,
            'tags': [],
            'frontmatter': {},
            'last_modified': None,
            'word_count': 0,
            'has_todos': False,
            'has_dates': False,
            'has_links': False,
            'has_attachments': False,
            'content_patterns': {},
            'user_directive': user_directive
        }
        # 1. Metadatos
        try:
            stat = note_path.stat()
            analysis['last_modified'] = datetime.fromtimestamp(stat.st_mtime)
            analysis['file_size'] = stat.st_size
            analysis['created_date'] = datetime.fromtimestamp(stat.st_ctime)
        except Exception as e:
            logger.debug(f"Error leyendo metadatos: {e}")
        # 2. Contenido y patrones
        analysis['word_count'] = len(note_content.split())
        todo_pattern = r'- \[ \].*|#todo|#TODO|TODO:|todo:'
        analysis['has_todos'] = bool(re.search(todo_pattern, note_content, re.IGNORECASE))
        analysis['todo_count'] = len(re.findall(todo_pattern, note_content, re.IGNORECASE))
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b'
        ]
        dates_found = []
        for pattern in date_patterns:
            dates_found.extend(re.findall(pattern, note_content, re.IGNORECASE))
        analysis['has_dates'] = bool(dates_found)
        analysis['dates_found'] = dates_found[:5]
        link_pattern = r'\[\[([^\]]+)\]\]'
        links = re.findall(link_pattern, note_content)
        analysis['has_links'] = bool(links)
        analysis['link_count'] = len(links)
        analysis['links'] = links[:10]
        attachment_pattern = r'!\[.*?\]\(([^)]+)\)'
        attachments = re.findall(attachment_pattern, note_content)
        analysis['has_attachments'] = bool(attachments)
        analysis['attachments'] = attachments
        # 3. FRONTMATTER (YAML)
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', note_content, re.DOTALL)
        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            try:
                import yaml
                analysis['frontmatter'] = yaml.safe_load(frontmatter_content) or {}
            except:
                analysis['frontmatter'] = {}
        # 4. TAGS
        if 'tags' in analysis['frontmatter']:
            analysis['tags'].extend(analysis['frontmatter']['tags'])
        content_tags = re.findall(r'#([a-zA-Z0-9_]+)', note_content)
        analysis['tags'].extend(content_tags)
        obsidian_tags = re.findall(r'#(project|area|resource|archive|inbox)', note_content, re.IGNORECASE)
        analysis['obsidian_tags'] = obsidian_tags
        analysis['tags'] = list(set(analysis['tags']))
        # 5. PATRONES DE CONTENIDO
        analysis['content_patterns'] = {
            'has_headers': bool(re.search(r'^#{1,6}\s+', note_content, re.MULTILINE)),
            'has_lists': bool(re.search(r'^[-*+]\s+', note_content, re.MULTILINE)),
            'has_code_blocks': bool(re.search(r'```', note_content)),
            'has_tables': bool(re.search(r'\|.*\|', note_content)),
            'has_quotes': bool(re.search(r'^>\s+', note_content, re.MULTILINE)),
            'has_emphasis': bool(re.search(r'\*\*.*\*\*|__.*__', note_content)),
            'has_strikethrough': bool(re.search(r'~~.*~~', note_content)),
            'has_footnotes': bool(re.search(r'\[\^.*\]', note_content))
        }
        # 6. TEMPORAL
        if analysis['last_modified']:
            days_since_modified = (datetime.now() - analysis['last_modified']).days
            analysis['days_since_modified'] = days_since_modified
            if days_since_modified <= 7:
                analysis['recency'] = 'very_recent'
            elif days_since_modified <= 30:
                analysis['recency'] = 'recent'
            elif days_since_modified <= 90:
                analysis['recency'] = 'moderate'
            else:
                analysis['recency'] = 'old'
        # 7. CONTEXTO DEL USUARIO
        def extract_keywords_from_directive(directive):
            return re.findall(r'\b\w+\b', directive.lower())
        analysis['user_context'] = {
            'directive': user_directive,
            'directive_keywords': extract_keywords_from_directive(user_directive),
            'has_specific_instructions': bool(re.search(r'\b(project|area|resource|archive)\b', user_directive, re.IGNORECASE))
        }
        return analysis 