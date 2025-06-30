#!/usr/bin/env python3
"""
SISTEMA DE CLUSTERING SEMÁNTICO INTELIGENTE
Agrupa notas relacionadas y genera nombres de carpetas basados en factores comunes.

FUNCIONALIDADES:
- Análisis de similaridad semántica entre notas
- Detección de palabras clave compartidas
- Clustering automático por temática/proyecto
- Naming basado en características comunes del cluster
- Detección de proyectos fragmentados
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass
import math

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()

@dataclass
class NoteAnalysis:
    """Análisis completo de una nota para clustering."""
    path: Path
    content: str
    title: str
    keywords: Set[str]
    tags: Set[str]
    entities: Set[str]  # Clientes, tecnologías, personas
    concepts: Set[str]  # Conceptos principales
    word_count: int
    similarity_vector: Dict[str, float]  # Vector de características para similaridad

@dataclass
class NoteCluster:
    """Cluster de notas relacionadas."""
    notes: List[NoteAnalysis]
    shared_keywords: Set[str]
    shared_entities: Set[str]
    shared_concepts: Set[str]
    cluster_strength: float  # 0-1, qué tan cohesivo es el cluster
    suggested_name: str
    category_suggestion: str  # project, area, resource

class IntelligentClusteringSystem:
    """Sistema de clustering semántico para agrupación inteligente de notas."""
    
    def __init__(self):
        self.console = Console()
        
        # Patrones para detectar entidades importantes
        self.entity_patterns = {
            'clients': r'\b(cliente|client|company|empresa):?\s*([A-Z][a-zA-Z\s]+)',
            'projects': r'\b(proyecto|project):?\s*([A-Z][a-zA-Z\s]+)',
            'technologies': r'\b(tech|tecnología|using|con|framework):?\s*([a-zA-Z\.]+)',
            'people': r'\b(contacto|contact|pm|manager|dev|developer):?\s*([A-Z][a-zA-Z\s]+)',
            'sprints': r'\b(sprint|fase|phase):?\s*(\d+)',
            'dates': r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        }
        
        # Palabras clave que indican conceptos importantes
        self.concept_indicators = {
            'development': ['desarrollo', 'development', 'coding', 'programming', 'implementar'],
            'meeting': ['reunión', 'meeting', 'call', 'standup', 'review'],
            'planning': ['planning', 'planificación', 'roadmap', 'strategy', 'objectives'],
            'analysis': ['análisis', 'analysis', 'research', 'study', 'investigation'],
            'documentation': ['documentación', 'documentation', 'guide', 'manual', 'tutorial'],
            'testing': ['testing', 'qa', 'quality', 'pruebas', 'test'],
            'deployment': ['deploy', 'deployment', 'producción', 'production', 'release']
        }
        
        # Stop words para filtrar ruido
        self.stop_words = {
            'para', 'nota', 'archivo', 'documento', 'información', 'datos',
            'sistema', 'proceso', 'ejemplo', 'esto', 'esta', 'este', 'más',
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'con', 'del', 'las', 'los', 'una', 'uno', 'por', 'como', 'que'
        }

    def analyze_note(self, note_path: Path) -> Optional[NoteAnalysis]:
        """Analiza una nota individual para extraer características relevantes."""
        try:
            content = note_path.read_text(encoding='utf-8')
            
            # Extraer título
            title = self._extract_title(content)
            
            # Extraer keywords importantes
            keywords = self._extract_keywords(content)
            
            # Extraer tags de Obsidian
            tags = self._extract_obsidian_tags(content)
            
            # Extraer entidades (clientes, tecnologías, etc.)
            entities = self._extract_entities(content)
            
            # Extraer conceptos principales
            concepts = self._extract_concepts(content)
            
            # Crear vector de similaridad
            similarity_vector = self._create_similarity_vector(keywords, entities, concepts, tags)
            
            return NoteAnalysis(
                path=note_path,
                content=content,
                title=title,
                keywords=keywords,
                tags=tags,
                entities=entities,
                concepts=concepts,
                word_count=len(content.split()),
                similarity_vector=similarity_vector
            )
            
        except Exception as e:
            self.console.print(f"⚠️ Error analizando {note_path.name}: {e}")
            return None

    def _extract_title(self, content: str) -> str:
        """Extrae el título de la nota."""
        lines = content.strip().split('\n')
        
        # Buscar header markdown
        for line in lines[:10]:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        
        # Fallback: primera línea no vacía
        for line in lines[:5]:
            line = line.strip()
            if line and not line.startswith('---'):
                return line[:50]
        
        return "Sin Título"

    def _extract_keywords(self, content: str) -> Set[str]:
        """Extrae palabras clave importantes del contenido."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Filtrar stop words
        filtered_words = [w for w in words if w not in self.stop_words and len(w) >= 3]
        
        # Contar frecuencias
        word_freq = Counter(filtered_words)
        
        # Dar prioridad a palabras en títulos
        title_words = set()
        title_patterns = [r'^#+\s*([^\n]+)', r'\*\*([^*]+)\*\*']
        for pattern in title_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                title_text = match.group(1).lower()
                title_words.update(re.findall(r'\b[a-zA-Z]{3,}\b', title_text))
        
        # Boost palabras en títulos
        for word in title_words:
            if word in word_freq:
                word_freq[word] *= 3
        
        # Retornar top keywords
        top_keywords = [word for word, _ in word_freq.most_common(15)]
        return set(top_keywords)

    def _extract_obsidian_tags(self, content: str) -> Set[str]:
        """Extrae tags de Obsidian (#tag)."""
        tags = re.findall(r'#(\w+)', content)
        return set(tags)

    def _extract_entities(self, content: str) -> Set[str]:
        """Extrae entidades importantes usando patrones."""
        entities = set()
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    entity = match.group(2).strip()
                    if len(entity) >= 2 and len(entity) <= 20:
                        entities.add(entity.lower())
        
        return entities

    def _extract_concepts(self, content: str) -> Set[str]:
        """Extrae conceptos principales del contenido."""
        content_lower = content.lower()
        concepts = set()
        
        for concept, indicators in self.concept_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    concepts.add(concept)
                    break
        
        return concepts

    def _create_similarity_vector(self, keywords: Set[str], entities: Set[str], 
                                concepts: Set[str], tags: Set[str]) -> Dict[str, float]:
        """Crea vector de características para cálculo de similaridad."""
        vector = {}
        
        # Pesos por tipo de característica
        for keyword in keywords:
            vector[f"kw_{keyword}"] = 1.0
        
        for entity in entities:
            vector[f"ent_{entity}"] = 2.0  # Entidades tienen más peso
        
        for concept in concepts:
            vector[f"con_{concept}"] = 1.5
        
        for tag in tags:
            vector[f"tag_{tag}"] = 1.5
        
        return vector

    def calculate_similarity(self, note1: NoteAnalysis, note2: NoteAnalysis) -> float:
        """Calcula similaridad coseno entre dos notas."""
        v1 = note1.similarity_vector
        v2 = note2.similarity_vector
        
        # Obtener todas las características
        all_features = set(v1.keys()) | set(v2.keys())
        
        if not all_features:
            return 0.0
        
        # Calcular producto punto y magnitudes
        dot_product = sum(v1.get(feature, 0) * v2.get(feature, 0) for feature in all_features)
        magnitude1 = math.sqrt(sum(v1[f]**2 for f in v1))
        magnitude2 = math.sqrt(sum(v2[f]**2 for f in v2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def cluster_notes(self, notes: List[NoteAnalysis], 
                     similarity_threshold: float = 0.3) -> List[NoteCluster]:
        """Agrupa notas similares en clusters."""
        self.console.print(f"🔍 Calculando similaridades entre {len(notes)} notas...")
        
        clusters = []
        used_notes = set()
        
        with Progress() as progress:
            task = progress.add_task("Clustering notas...", total=len(notes))
            
            for i, note in enumerate(notes):
                if note.path in used_notes:
                    progress.advance(task)
                    continue
                
                # Crear nuevo cluster con esta nota
                cluster_notes = [note]
                used_notes.add(note.path)
                
                # Buscar notas similares
                for j, other_note in enumerate(notes[i+1:], i+1):
                    if other_note.path in used_notes:
                        continue
                    
                    similarity = self.calculate_similarity(note, other_note)
                    
                    if similarity >= similarity_threshold:
                        cluster_notes.append(other_note)
                        used_notes.add(other_note.path)
                
                # Crear cluster si tiene más de una nota o es muy relevante
                if len(cluster_notes) > 1 or self._is_significant_note(note):
                    cluster = self._create_cluster(cluster_notes)
                    clusters.append(cluster)
                
                progress.advance(task)
        
        # Ordenar clusters por fuerza (más cohesivos primero)
        clusters.sort(key=lambda c: c.cluster_strength, reverse=True)
        
        return clusters

    def _is_significant_note(self, note: NoteAnalysis) -> bool:
        """Determina si una nota es lo suficientemente significativa para formar su propio cluster."""
        return (len(note.entities) > 0 or 
                len(note.tags) > 0 or 
                len(note.keywords) >= 5 or
                note.word_count > 100)

    def _create_cluster(self, notes: List[NoteAnalysis]) -> NoteCluster:
        """Crea un cluster a partir de una lista de notas."""
        # Encontrar elementos compartidos
        shared_keywords = set.intersection(*[note.keywords for note in notes]) if notes else set()
        shared_entities = set.intersection(*[note.entities for note in notes]) if notes else set()
        shared_concepts = set.intersection(*[note.concepts for note in notes]) if notes else set()
        
        # Calcular fuerza del cluster
        cluster_strength = self._calculate_cluster_strength(notes, shared_keywords, shared_entities, shared_concepts)
        
        # Generar nombre sugerido
        suggested_name = self._generate_cluster_name(shared_keywords, shared_entities, shared_concepts, notes)
        
        # Sugerir categoría
        category_suggestion = self._suggest_category(shared_entities, shared_concepts, notes)
        
        return NoteCluster(
            notes=notes,
            shared_keywords=shared_keywords,
            shared_entities=shared_entities,
            shared_concepts=shared_concepts,
            cluster_strength=cluster_strength,
            suggested_name=suggested_name,
            category_suggestion=category_suggestion
        )

    def _calculate_cluster_strength(self, notes: List[NoteAnalysis], 
                                  shared_keywords: Set[str], shared_entities: Set[str], 
                                  shared_concepts: Set[str]) -> float:
        """Calcula qué tan cohesivo es un cluster (0-1)."""
        if len(notes) == 1:
            return 0.5  # Nota individual
        
        # Factores de cohesión
        shared_factor = len(shared_keywords) + len(shared_entities) * 2 + len(shared_concepts) * 1.5
        
        # Normalizar por tamaño del cluster
        avg_features = sum(len(note.keywords) + len(note.entities) + len(note.concepts) 
                          for note in notes) / len(notes)
        
        if avg_features == 0:
            return 0.1
        
        strength = min(shared_factor / avg_features, 1.0)
        
        # Bonus por múltiples notas relacionadas
        if len(notes) > 2:
            strength *= 1.2
        
        return min(strength, 1.0)

    def _generate_cluster_name(self, shared_keywords: Set[str], shared_entities: Set[str], 
                             shared_concepts: Set[str], notes: List[NoteAnalysis]) -> str:
        """Genera nombre para el cluster basado en factores comunes."""
        name_parts = []
        
        # Prioridad 1: Entidades compartidas (clientes, proyectos)
        if shared_entities:
            primary_entity = max(shared_entities, key=len) if shared_entities else None
            if primary_entity:
                name_parts.append(primary_entity.title())
        
        # Prioridad 2: Conceptos compartidos
        if shared_concepts:
            primary_concept = max(shared_concepts, key=lambda c: len([n for n in notes if c in n.concepts]))
            name_parts.append(primary_concept.title())
        
        # Prioridad 3: Keywords más frecuentes
        if shared_keywords and len(name_parts) < 2:
            # Contar frecuencia de keywords en todas las notas del cluster
            keyword_freq = Counter()
            for note in notes:
                for keyword in shared_keywords:
                    if keyword in note.keywords:
                        keyword_freq[keyword] += 1
            
            if keyword_freq:
                top_keyword = keyword_freq.most_common(1)[0][0]
                name_parts.append(top_keyword.title())
        
        # Fallback: usar título de la nota más representativa
        if not name_parts:
            most_representative = max(notes, key=lambda n: len(n.keywords) + len(n.entities))
            title_words = most_representative.title.split()[:2]
            name_parts.extend([w.title() for w in title_words if len(w) > 2])
        
        # Construir nombre final
        if not name_parts:
            name_parts = ['General']
        
        return ' '.join(name_parts[:3])  # Máximo 3 componentes, usar espacios

    def _suggest_category(self, shared_entities: Set[str], shared_concepts: Set[str], 
                         notes: List[NoteAnalysis]) -> str:
        """Sugiere categoría PARA basada en las características del cluster."""
        
        # Si hay entidades (clientes), probablemente es proyecto
        if shared_entities:
            return 'project'
        
        # Si hay conceptos de desarrollo/implementación, es proyecto
        project_concepts = {'development', 'meeting', 'planning', 'testing', 'deployment'}
        if shared_concepts & project_concepts:
            return 'project'
        
        # Si hay conceptos de análisis/documentación, es recurso
        resource_concepts = {'analysis', 'documentation'}
        if shared_concepts & resource_concepts:
            return 'resource'
        
        # Por defecto, área
        return 'area'

    def analyze_vault_clustering(self, vault_path: Path, 
                                target_categories: List[str] = None) -> Dict[str, List[NoteCluster]]:
        """Analiza todo el vault para detectar clusters de notas relacionadas."""
        if not target_categories:
            target_categories = ['01-Projects', '02-Areas', '03-Resources']
        
        all_clusters = {}
        
        for category in target_categories:
            category_path = vault_path / category
            if not category_path.exists():
                continue
            
            self.console.print(f"\n🔍 [bold]Analizando {category}...[/bold]")
            
            # Recopilar todas las notas de la categoría
            all_notes = []
            for note_file in category_path.rglob("*.md"):
                analysis = self.analyze_note(note_file)
                if analysis:
                    all_notes.append(analysis)
            
            if not all_notes:
                continue
            
            self.console.print(f"📄 Encontradas {len(all_notes)} notas para análisis")
            
            # Hacer clustering
            clusters = self.cluster_notes(all_notes)
            
            # Filtrar clusters significativos
            significant_clusters = [c for c in clusters if c.cluster_strength > 0.2]
            
            all_clusters[category] = significant_clusters
            
            self.console.print(f"🎯 Generados {len(significant_clusters)} clusters significativos")
        
        return all_clusters

    def generate_clustering_report(self, clusters_by_category: Dict[str, List[NoteCluster]]) -> None:
        """Genera reporte de clustering con sugerencias de agrupación."""
        self.console.print("\n📊 [bold]REPORTE DE CLUSTERING SEMÁNTICO[/bold]")
        
        for category, clusters in clusters_by_category.items():
            if not clusters:
                continue
            
            self.console.print(f"\n📂 [yellow]{category}[/yellow]:")
            
            table = Table(title=f"Clusters Detectados en {category}")
            table.add_column("Cluster", style="cyan")
            table.add_column("Notas", style="green")
            table.add_column("Nombre Sugerido", style="yellow")
            table.add_column("Fuerza", style="blue")
            table.add_column("Factores Comunes", style="magenta")
            
            for i, cluster in enumerate(clusters[:10], 1):  # Top 10
                factors = []
                if cluster.shared_entities:
                    factors.extend(list(cluster.shared_entities)[:2])
                if cluster.shared_concepts:
                    factors.extend(list(cluster.shared_concepts)[:2])
                if cluster.shared_keywords:
                    factors.extend(list(cluster.shared_keywords)[:3])
                
                factors_text = ', '.join(factors[:5]) if factors else "N/A"
                
                table.add_row(
                    f"Cluster {i}",
                    str(len(cluster.notes)),
                    cluster.suggested_name,
                    f"{cluster.cluster_strength:.3f}",
                    factors_text
                )
            
            self.console.print(table)

def analyze_note_relationships(vault_path: Path, min_cluster_size: int = 2) -> Dict[str, List[NoteCluster]]:
    """Función principal para analizar relaciones entre notas y generar clusters."""
    clustering_system = IntelligentClusteringSystem()
    return clustering_system.analyze_vault_clustering(vault_path) 