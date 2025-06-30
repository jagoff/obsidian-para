#!/usr/bin/env python3
"""
SISTEMA DE NAMING INTELIGENTE PARA SUBCARPETAS PARA
Genera nombres de carpetas optimizados usando IA y análisis semántico.

CARACTERÍSTICAS:
- Análisis semántico profundo del contenido
- Detección de entidades (clientes, proyectos, tecnologías)
- Análisis temporal (fechas, fases, sprints)
- Consistencia con naming conventions
- Personalización por tipo de proyecto/área
- Jerarquía inteligente
"""

import re
import json
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from .ai_engine import AIEngine
from .rg_utils import search_files_containing, count_files_with_pattern

console = Console()

@dataclass
class ContentAnalysis:
    """Resultado del análisis de contenido para naming."""
    main_entities: List[str]  # Entidades principales (clientes, proyectos)
    technologies: List[str]   # Tecnologías mencionadas
    temporal_markers: List[str]  # Fechas, fases, sprints
    action_themes: List[str]  # Temas de acción (desarrollo, análisis, etc.)
    document_types: List[str]  # Tipos de documento (meeting, spec, etc.)
    priority_keywords: List[str]  # Palabras clave prioritarias
    context_category: str     # Categoría contextual (project, area, resource)

@dataclass
class NamingRule:
    """Regla de naming para diferentes contextos."""
    category: str
    pattern: str
    max_length: int
    case_style: str  # "title", "upper", "lower", "camel"
    separators: List[str]
    priority_order: List[str]  # Orden de prioridad de elementos

class IntelligentNamingSystem:
    """Sistema avanzado de naming inteligente."""
    
    def __init__(self):
        self.console = Console()
        self.ai_engine = AIEngine()
        
        # Configuración de reglas de naming por categoría
        self.naming_rules = {
            'project': NamingRule(
                category='project',
                pattern='{client}_{theme}_{type}',
                max_length=40,
                case_style='title',
                separators=['_', '-'],
                priority_order=['client', 'theme', 'type', 'phase']
            ),
            'area': NamingRule(
                category='area',
                pattern='{theme}_{type}',
                max_length=35,
                case_style='title', 
                separators=['_', '-'],
                priority_order=['theme', 'type', 'skill']
            ),
            'resource': NamingRule(
                category='resource',
                pattern='{technology}_{theme}',
                max_length=30,
                case_style='title',
                separators=['_', '-'],
                priority_order=['technology', 'theme', 'type']
            )
        }
        
        # Diccionarios de entidades conocidas
        self.known_entities = {
            'clients': {
                'moka', 'bbi', 'prestafe', 'crombie', 'avature', 'compass'
            },
            'technologies': {
                'docker', 'nginx', 'wordpress', 'git', 'jenkins', 'aws', 
                'react', 'node', 'python', 'javascript', 'css', 'html',
                'mysql', 'postgresql', 'mongodb', 'redis', 'kubernetes'
            },
            'document_types': {
                'meeting', 'spec', 'analysis', 'planning', 'review',
                'retrospective', 'standup', 'demo', 'training', 'onboarding'
            },
            'action_themes': {
                'development', 'design', 'testing', 'deployment', 'analysis',
                'planning', 'research', 'documentation', 'training', 'coaching'
            },
            'temporal_markers': {
                'sprint', 'phase', 'milestone', 'quarter', 'month', 'week',
                'daily', 'weekly', 'monthly', 'quarterly', 'annual'
            }
        }
        
        # Patrones para análisis de contenido
        self.content_patterns = {
            'client_indicators': [
                r'\b(cliente|client|company|empresa|corp|inc)\s*[:\-]?\s*([A-Z][a-zA-Z\s]+)',
                r'\b(proyecto|project)\s+([A-Z][a-zA-Z]+)',
                r'\b([A-Z]{2,})\s*[-:]?\s*(proyecto|project|client)'
            ],
            'date_patterns': [
                r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}',
                r'\b(sprint|phase|fase)\s*(\d+)',
                r'\bQ[1-4]\s*\d{4}',
                r'\b(deadline|due|entrega):\s*([^\n]+)'
            ],
            'technology_patterns': [
                r'\b(tech|technology|tecnología|using|con|framework|library|tool)[\s:\-]*([a-zA-Z\.]+)',
                r'\b(docker|nginx|wordpress|git|jenkins|aws|react|vue|angular|node|python|java)\b',
                r'\b([a-zA-Z]+\.(js|py|php|java|cpp|go|rs|rb))\b'
            ],
            'action_patterns': [
                r'\b(desarrollar|develop|crear|create|implementar|implement|analizar|analyze)',
                r'\b(diseñar|design|planificar|plan|documentar|document|entrenar|train)',
                r'\b(reunión|meeting|junta|call|session|workshop|training)'
            ]
        }

    def analyze_content_for_naming(self, content_list: List[str]) -> ContentAnalysis:
        """Analiza contenido para extraer información relevante para naming."""
        console.print("🧠 [bold]Analizando contenido para naming inteligente...[/bold]")
        
        full_content = '\n'.join(content_list)
        
        # Extraer diferentes tipos de entidades
        main_entities = self._extract_entities(full_content, 'clients')
        technologies = self._extract_entities(full_content, 'technologies')
        action_themes = self._extract_entities(full_content, 'action_themes')
        document_types = self._extract_entities(full_content, 'document_types')
        
        # Extraer marcadores temporales
        temporal_markers = self._extract_temporal_markers(full_content)
        
        # Extraer palabras clave por frecuencia
        priority_keywords = self._extract_priority_keywords(full_content)
        
        # Determinar categoría contextual
        context_category = self._determine_context_category(main_entities, technologies, action_themes)
        
        return ContentAnalysis(
            main_entities=main_entities,
            technologies=technologies,
            temporal_markers=temporal_markers,
            action_themes=action_themes,
            document_types=document_types,
            priority_keywords=priority_keywords,
            context_category=context_category
        )

    def _extract_entities(self, content: str, entity_type: str) -> List[str]:
        """Extrae entidades específicas del contenido."""
        entities = set()
        known_set = self.known_entities.get(entity_type, set())
        
        for entity in known_set:
            if re.search(rf'\b{entity}\b', content, re.IGNORECASE):
                entities.add(entity.title())
        
        return list(entities)[:3]

    def _extract_temporal_markers(self, content: str) -> List[str]:
        """Extrae marcadores temporales del contenido."""
        patterns = [
            r'\b(sprint|phase|fase)\s*(\d+)',
            r'\bQ[1-4]\s*\d{4}',
            r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        ]
        
        temporal_info = []
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                temporal_info.append(match.group(0))
        
        return temporal_info[:2]

    def _extract_priority_keywords(self, content: str, max_keywords: int = 5) -> List[str]:
        """Extrae palabras clave prioritarias por frecuencia, IGNORANDO URLs y elementos técnicos."""
        
        # PRIMERO: Limpiar URLs y elementos técnicos del contenido
        cleaned_content = content
        
        # Remover URLs completos
        cleaned_content = re.sub(r'https?://[^\s]+', '', cleaned_content)
        
        # Remover parámetros de URL (#gid=, ?param=, etc.)
        cleaned_content = re.sub(r'#[a-zA-Z0-9_]+=[a-zA-Z0-9_]+', '', cleaned_content)
        cleaned_content = re.sub(r'\?[a-zA-Z0-9_]+=[a-zA-Z0-9_]+', '', cleaned_content)
        
        # Remover IDs técnicos (gid, id, etc.)
        cleaned_content = re.sub(r'\b[a-zA-Z]*id\s*=\s*[a-zA-Z0-9_]+\b', '', cleaned_content, flags=re.IGNORECASE)
        
        # Remover códigos de Google Drive, IDs de documentos, etc.
        cleaned_content = re.sub(r'\b[a-zA-Z0-9]{20,}\b', '', cleaned_content)  # IDs largos
        
        # Remover elementos de markdown que no son contenido real
        cleaned_content = re.sub(r'!\[([^\]]*)\]\([^)]*\)', '', cleaned_content)  # Imágenes
        cleaned_content = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cleaned_content)  # Links -> solo texto
        
        # Ahora extraer palabras limpias
        words = re.findall(r'\b[a-zA-Z]{3,}\b', cleaned_content.lower())
        
        # Expandir stop words para incluir términos técnicos comunes y conectores
        stop_words = {
            'para', 'nota', 'archivo', 'documento', 'información', 'datos',
            'sistema', 'proceso', 'ejemplo', 'esto', 'esta', 'este', 'más',
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'con', 'del', 'las', 'los', 'una', 'uno', 'por', 'como', 'que',
            'web', 'app', 'file', 'code', 'line', 'text', 'user', 'data',
            'new', 'old', 'get', 'set', 'run', 'add', 'use', 'make', 'work',
            'project', 'projects', 'note', 'notes', 'content', 'folder',
            'docker', 'nginx', 'git', 'wordpress', 'jenkins', 'aws',  # Evitar tecnologías duplicadas
            'gid', 'id', 'url', 'http', 'https', 'www', 'com', 'org', 'net',  # Elementos técnicos
            'drive', 'google', 'docs', 'sheets', 'mural', 'app', 'co', 'io'  # Servicios web
        }
        
        # Priorizar palabras que aparecen en títulos (headers markdown)
        title_words = set()
        title_patterns = [r'^#+\s*([^\n]+)', r'\*\*([^*]+)\*\*']
        for pattern in title_patterns:
            matches = re.finditer(pattern, cleaned_content, re.MULTILINE)
            for match in matches:
                title_text = match.group(1).lower()
                title_words.update(re.findall(r'\b[a-zA-Z]{3,}\b', title_text))
        
        # Contar frecuencias y dar boost a palabras en títulos
        word_freq = Counter()
        for word in words:
            if word not in stop_words and len(word) >= 3:
                weight = 2 if word in title_words else 1
                word_freq[word] += weight
        
        # Filtrar palabras muy largas (probablemente no útiles para nombres)
        filtered_words = [(word, freq) for word, freq in word_freq.most_common() 
                         if len(word) <= 12]
        
        return [word.title() for word, _ in filtered_words[:max_keywords]]

    def _determine_context_category(self, entities: List[str], technologies: List[str], themes: List[str]) -> str:
        """Determina la categoría contextual para aplicar reglas de naming."""
        if entities:
            return 'project'
        elif technologies:
            return 'resource'
        else:
            return 'area'

    def generate_intelligent_folder_name(self, analysis: ContentAnalysis) -> str:
        """Genera nombre de carpeta inteligente basado en análisis."""
        console.print(f"🎯 [bold]Generando nombre para categoría: {analysis.context_category}[/bold]")
        
        components = []
        used_words = set()  # Para evitar duplicados
        
        # Estrategia por categoría
        if analysis.context_category == 'project':
            # Para proyectos: Cliente_Tema_Tipo
            if analysis.main_entities:
                comp = analysis.main_entities[0]
                if comp.lower() not in used_words:
                    components.append(comp)
                    used_words.add(comp.lower())
            
            # Buscar tema principal (no cliente)
            theme_found = False
            if analysis.action_themes:
                comp = analysis.action_themes[0]
                if comp.lower() not in used_words:
                    components.append(comp)
                    used_words.add(comp.lower())
                    theme_found = True
            
            if not theme_found and analysis.priority_keywords:
                for keyword in analysis.priority_keywords:
                    if keyword.lower() not in used_words:
                        components.append(keyword)
                        used_words.add(keyword.lower())
                        break
                        
            # Tipo de documento si es útil
            if len(components) < 3 and analysis.document_types:
                comp = analysis.document_types[0]
                if comp.lower() not in used_words:
                    components.append(comp)
                    used_words.add(comp.lower())
                
        elif analysis.context_category == 'resource':
            # Para recursos: Tecnología_Propósito
            if analysis.technologies:
                comp = analysis.technologies[0]
                components.append(comp)
                used_words.add(comp.lower())
            
            # Buscar propósito/tema principal que no sea la tecnología
            if analysis.priority_keywords:
                for keyword in analysis.priority_keywords:
                    if (keyword.lower() not in used_words and 
                        keyword.lower() not in ['docker', 'nginx', 'git', 'wordpress', 'jenkins']):
                        components.append(keyword)
                        used_words.add(keyword.lower())
                        break
            
            # Si no encontramos tema, usar action theme
            if len(components) < 2 and analysis.action_themes:
                comp = analysis.action_themes[0]
                if comp.lower() not in used_words:
                    components.append(comp)
                    used_words.add(comp.lower())
                
        else:  # area
            # Para áreas: Tema_Subtema
            if analysis.action_themes:
                comp = analysis.action_themes[0]
                components.append(comp)
                used_words.add(comp.lower())
            
            if analysis.priority_keywords:
                for keyword in analysis.priority_keywords:
                    if keyword.lower() not in used_words:
                        components.append(keyword)
                        used_words.add(keyword.lower())
                        break
        
        # Agregar marcador temporal si existe y es útil
        if len(components) < 3 and analysis.temporal_markers:
            temporal = self._clean_temporal_marker(analysis.temporal_markers[0])
            if temporal and temporal.lower() not in used_words:
                components.append(temporal)
                used_words.add(temporal.lower())
        
        # Si no hay suficientes componentes, usar keywords adicionales
        if len(components) < 2 and analysis.priority_keywords:
            for keyword in analysis.priority_keywords:
                if keyword.lower() not in used_words:
                    components.append(keyword)
                    used_words.add(keyword.lower())
                    if len(components) >= 2:
                        break
        
        # Fallback
        if not components:
            components = ['General']
        
        # Limpiar y unir componentes - máximo 3
        clean_components = []
        for comp in components[:3]:
            cleaned = self._clean_component(comp)
            if cleaned and cleaned.lower() not in [c.lower() for c in clean_components]:
                clean_components.append(cleaned)
        
        final_name = ' '.join(clean_components)  # Usar espacios en lugar de guiones bajos
        
        # Limitar longitud
        if len(final_name) > 40:
            final_name = final_name[:37] + "..."
        
        return final_name.title()

    def _clean_component(self, component: str) -> str:
        """Limpia componente de nombre."""
        if not component:
            return ""
        
        cleaned = re.sub(r'[^\w\s\-]', '', str(component))
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Usar espacios normales
        cleaned = cleaned.strip()
        
        return cleaned[:15]  # Máximo 15 caracteres por componente

    def _clean_temporal_marker(self, marker: str) -> str:
        """Limpia marcador temporal."""
        marker = marker.lower().strip()
        
        if 'sprint' in marker:
            sprint_match = re.search(r'sprint\s*(\d+)', marker)
            if sprint_match:
                return f"S{sprint_match.group(1)}"
        
        if 'phase' in marker or 'fase' in marker:
            phase_match = re.search(r'(phase|fase)\s*(\d+)', marker)
            if phase_match:
                return f"P{phase_match.group(2)}"
        
        return ""

    def analyze_and_suggest_renames(self, vault_path: Path, 
                                  target_category: str = "01-Projects") -> Dict[str, str]:
        """
        Analiza carpetas existentes y sugiere mejores nombres.
        SOLO PROCESA CARPETAS CON CONTENIDO REAL.
        
        Args:
            vault_path: Ruta del vault
            target_category: Categoría a analizar (01-Projects, 02-Areas, etc.)
            
        Returns:
            Dict[str, str]: Mapeo de nombre_actual -> nombre_sugerido
        """
        console.print(f"🔍 [bold]Analizando nombres en {target_category}...[/bold]")
        
        category_path = vault_path / target_category
        if not category_path.exists():
            return {}
        
        suggestions = {}
        empty_folders = []
        processed_folders = 0
        
        for folder in category_path.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                # VERIFICAR QUE LA CARPETA TENGA CONTENIDO REAL
                content_files = list(folder.rglob("*.md"))
                
                if not content_files:
                    empty_folders.append(folder.name)
                    continue  # IGNORAR CARPETAS VACÍAS
                
                processed_folders += 1
                contents = []
                for file_path in content_files[:5]:  # Máximo 5 archivos para análisis
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        contents.append(content)
                    except:
                        continue
                
                if contents:
                    # Analizar contenido
                    analysis = self.analyze_content_for_naming(contents)
                    
                    # Generar sugerencia
                    suggested_name = self.generate_intelligent_folder_name(analysis)
                    
                    # Solo sugerir si es diferente y mejor
                    if suggested_name != folder.name and len(suggested_name) < len(folder.name):
                        suggestions[folder.name] = suggested_name
        
        # Mostrar estadísticas de carpetas vacías
        if empty_folders:
            console.print(f"⚠️ [yellow]Se encontraron {len(empty_folders)} carpetas vacías (ignoradas)[/yellow]")
            console.print(f"📊 [dim]Carpetas procesadas: {processed_folders} | Vacías: {len(empty_folders)}[/dim]")
        
        return suggestions

    def generate_naming_report(self, suggestions: Dict[str, str]) -> None:
        """Genera reporte de sugerencias de naming."""
        console.print("\n📊 [bold]REPORTE DE SUGERENCIAS DE NAMING[/bold]")
        
        if not suggestions:
            console.print("✅ [green]No se encontraron mejoras necesarias en los nombres.[/green]")
            return
        
        table = Table(title="Sugerencias de Nombres Mejorados")
        table.add_column("Nombre Actual", style="red")
        table.add_column("Nombre Sugerido", style="green")
        table.add_column("Mejora", style="cyan")
        
        for current, suggested in suggestions.items():
            improvement = "Más conciso" if len(suggested) < len(current) else "Más descriptivo"
            if len(current) > 40:
                improvement += " + Menos caracteres"
            
            table.add_row(current, suggested, improvement)
        
        console.print(table)

    def _detect_and_handle_duplicates(self, suggested_name: str, existing_folders: set, vault_path: Path, category: str) -> str:
        """
        Detecta duplicados inteligentemente y maneja la situación apropiadamente.
        
        Estrategias:
        1. Si es un duplicado exacto -> consolidar
        2. Si es similar pero diferente -> usar nombre único descriptivo
        3. Si es realmente único -> usar el nombre sugerido
        """
        if not existing_folders:
            return suggested_name
        
        # Normalizar nombres para comparación
        suggested_normalized = self._normalize_for_comparison(suggested_name)
        existing_normalized = {self._normalize_for_comparison(name) for name in existing_folders}
        
        # 1. DUPLICADO EXACTO - Consolidar
        if suggested_normalized in existing_normalized:
            console.print(f"🔄 [yellow]Duplicado detectado: '{suggested_name}' ya existe. Consolidando...[/yellow]")
            return self._get_consolidation_target(suggested_name, existing_folders, vault_path, category)
        
        # 2. SIMILARIDAD ALTA - Usar nombre más específico
        similar_folders = self._find_similar_folders(suggested_normalized, existing_normalized, existing_folders)
        if similar_folders:
            console.print(f"🔍 [blue]Carpetas similares encontradas: {similar_folders}. Generando nombre más específico...[/blue]")
            return self._generate_specific_name(suggested_name, similar_folders)
        
        # 3. NOMBRE ÚNICO - Usar el sugerido
        return suggested_name

    def _normalize_for_comparison(self, name: str) -> str:
        """Normaliza nombre para comparación eliminando números y caracteres especiales."""
        import re
        
        # Remover números de sufijo (_1, _2, etc.)
        normalized = re.sub(r'_\d+$', '', name)
        normalized = re.sub(r'\s+\d+$', '', normalized)
        
        # Remover caracteres especiales y convertir a minúsculas
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = normalized.lower().strip()
        
        return normalized

    def _find_similar_folders(self, suggested_normalized: str, existing_normalized: set, existing_folders: set) -> list:
        """Encuentra carpetas existentes similares al nombre sugerido."""
        similar = []
        
        for existing in existing_folders:
            existing_norm = self._normalize_for_comparison(existing)
            
            # Calcular similitud usando diferentes métricas
            similarity_score = self._calculate_similarity(suggested_normalized, existing_norm)
            
            if similarity_score > 0.7:  # Umbral de similitud
                similar.append(existing)
        
        return similar

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calcula similitud entre dos nombres."""
        from difflib import SequenceMatcher
        
        # Similitud de secuencia
        sequence_similarity = SequenceMatcher(None, name1, name2).ratio()
        
        # Similitud de palabras
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if not words1 or not words2:
            return sequence_similarity
        
        word_overlap = len(words1.intersection(words2))
        word_similarity = word_overlap / max(len(words1), len(words2))
        
        # Combinar métricas
        return (sequence_similarity + word_similarity) / 2

    def _get_consolidation_target(self, suggested_name: str, existing_folders: set, vault_path: Path, category: str) -> str:
        """Determina la carpeta objetivo para consolidación."""
        # Buscar la carpeta existente más apropiada
        category_path = vault_path / category
        
        for existing in existing_folders:
            existing_path = category_path / existing
            if existing_path.exists():
                # Verificar si la carpeta existente tiene contenido
                if any(existing_path.rglob("*.md")):
                    console.print(f"✅ [green]Consolidando en carpeta existente: '{existing}'[/green]")
                    return existing
        
        # Si no hay carpetas con contenido, usar la primera
        return list(existing_folders)[0]

    def _generate_specific_name(self, base_name: str, similar_folders: list) -> str:
        """Genera un nombre más específico para evitar confusión."""
        # Extraer palabras clave únicas
        base_words = set(base_name.lower().split())
        
        for similar in similar_folders:
            similar_words = set(similar.lower().split())
            base_words = base_words - similar_words  # Remover palabras comunes
        
        # Construir nombre más específico
        if base_words:
            specific_name = " ".join(list(base_words)[:3])  # Máximo 3 palabras
            specific_name = specific_name.title()
            
            # Agregar contexto si es necesario
            if len(specific_name) < 10:
                specific_name = f"{specific_name} Project"
            
            return specific_name
        
        # Fallback: agregar descriptor temporal
        return f"{base_name} New"

    def _update_learning_metrics(self, classification_result, confidence_score):
        """Actualiza métricas de aprendizaje basadas en el resultado de clasificación."""
        try:
            # Actualizar contadores de clasificación
            category = classification_result.get('category', 'unknown')
            if category in self.classification_counts:
                self.classification_counts[category] += 1
            
            # Actualizar métricas de confianza
            self.confidence_scores.append(confidence_score)
            if len(self.confidence_scores) > 100:  # Mantener solo los últimos 100
                self.confidence_scores.pop(0)
            
            # Calcular promedio de confianza
            if self.confidence_scores:
                self.avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
            
            # Guardar métricas
            self._save_learning_metrics()
            
        except Exception as e:
            logger.warning(f"Error actualizando métricas de aprendizaje: {e}")
            # No fallar si hay error en métricas

def create_intelligent_name(note_contents: List[str], context_category: str = "project", existing_folders: set = None, vault_path: Path = None, category: str = None) -> str:
    """Función principal para generar nombres inteligentes con detección de duplicados."""
    naming_system = IntelligentNamingSystem()
    analysis = naming_system.analyze_content_for_naming(note_contents)
    analysis.context_category = context_category
    
    # Agregar prompt específico para forzar inglés
    english_prompt = """
    IMPORTANT: Generate folder names ONLY in English. 
    - Use English terms for all concepts
    - Translate any Spanish/other language terms to English
    - Use standard English naming conventions
    - Keep names concise and professional
    - Avoid mixed languages
    """
    
    # Aplicar el prompt de inglés al análisis
    if hasattr(analysis, 'english_prompt'):
        analysis.english_prompt = english_prompt
    
    # Generar nombre base
    base_name = naming_system.generate_intelligent_folder_name(analysis)
    
    # Aplicar detección de duplicados si se proporcionan los parámetros necesarios
    if existing_folders is not None and vault_path is not None and category is not None:
        final_name = naming_system._detect_and_handle_duplicates(base_name, existing_folders, vault_path, category)
        return final_name
    
    return base_name

def clean_empty_folders(vault_path: Path, target_category: str = None, execute: bool = False) -> Dict[str, int]:
    """
    Identifica y opcionalmente elimina carpetas vacías.
    
    Args:
        vault_path: Ruta del vault
        target_category: Categoría específica o None para todas
        execute: Si True, elimina las carpetas vacías
        
    Returns:
        Dict con estadísticas de limpieza
    """
    from rich.console import Console
    console = Console()
    
    categories_to_check = ['01-Projects', '02-Areas', '03-Resources', '04-Archive'] if not target_category else [target_category]
    
    stats = {
        'empty_folders_found': 0,
        'empty_folders_removed': 0,
        'categories_processed': 0,
        'total_folders_checked': 0
    }
    
    empty_folders_by_category = {}
    
    for category in categories_to_check:
        category_path = vault_path / category
        if not category_path.exists():
            continue
            
        stats['categories_processed'] += 1
        category_empty = []
        
        for folder in category_path.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                stats['total_folders_checked'] += 1
                
                # Verificar si tiene archivos .md
                md_files = list(folder.rglob("*.md"))
                if not md_files:
                    category_empty.append(folder)
                    stats['empty_folders_found'] += 1
        
        if category_empty:
            empty_folders_by_category[category] = category_empty
    
    # Mostrar resultados
    console.print(f"\n🔍 [bold]ANÁLISIS DE CARPETAS VACÍAS:[/bold]")
    console.print(f"📊 Carpetas analizadas: {stats['total_folders_checked']}")
    console.print(f"🗑️ Carpetas vacías encontradas: {stats['empty_folders_found']}")
    
    if stats['empty_folders_found'] > 0:
        for category, empty_folders in empty_folders_by_category.items():
            console.print(f"\n📁 [yellow]{category}[/yellow]: {len(empty_folders)} carpetas vacías")
            for folder in empty_folders[:5]:  # Mostrar primeras 5
                console.print(f"   🗑️ {folder.name}")
            if len(empty_folders) > 5:
                console.print(f"   ... y {len(empty_folders) - 5} más")
        
        # Ejecutar limpieza si se solicita
        if execute:
            console.print(f"\n🔧 [bold]ELIMINANDO CARPETAS VACÍAS...[/bold]")
            
            for category, empty_folders in empty_folders_by_category.items():
                for folder in empty_folders:
                    try:
                        folder.rmdir()  # Solo elimina si está vacía
                        console.print(f"✅ Eliminada: {category}/{folder.name}")
                        stats['empty_folders_removed'] += 1
                    except OSError as e:
                        console.print(f"❌ Error eliminando {folder.name}: {e}")
            
            console.print(f"\n🎯 [green]Limpieza completada: {stats['empty_folders_removed']} carpetas eliminadas[/green]")
        else:
            console.print(f"\n💡 [dim]Usa --execute para eliminar las carpetas vacías[/dim]")
    else:
        console.print("✅ [green]No se encontraron carpetas vacías[/green]")
    
    return stats

def consolidate_duplicate_folders(vault_path: Path, category: str = None, execute: bool = False) -> Dict[str, int]:
    """
    Consolida carpetas duplicadas en el vault.
    
    Args:
        vault_path: Ruta del vault
        category: Categoría específica o None para todas
        execute: Si True, ejecuta la consolidación
        
    Returns:
        Dict con estadísticas de consolidación
    """
    console = Console()
    
    categories_to_check = ['01-Projects', '02-Areas', '03-Resources', '04-Archive'] if not category else [category]
    
    stats = {
        'duplicates_found': 0,
        'folders_consolidated': 0,
        'files_moved': 0,
        'errors': 0
    }
    
    for cat in categories_to_check:
        category_path = vault_path / cat
        if not category_path.exists():
            continue
            
        console.print(f"\n🔍 [bold]Analizando duplicados en {cat}...[/bold]")
        
        # Obtener todas las carpetas
        folders = [f for f in category_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
        
        if not folders:
            continue
        
        # Agrupar carpetas por nombre normalizado
        folder_groups = {}
        naming_system = IntelligentNamingSystem()
        
        for folder in folders:
            normalized_name = naming_system._normalize_for_comparison(folder.name)
            if normalized_name not in folder_groups:
                folder_groups[normalized_name] = []
            folder_groups[normalized_name].append(folder)
        
        # Procesar grupos con duplicados
        for normalized_name, folder_list in folder_groups.items():
            if len(folder_list) > 1:
                stats['duplicates_found'] += 1
                console.print(f"\n🔄 [yellow]Duplicados encontrados para '{normalized_name}':[/yellow]")
                
                for folder in folder_list:
                    console.print(f"   📁 {folder.name}")
                
                if execute:
                    # Consolidar en la primera carpeta (la más antigua)
                    target_folder = folder_list[0]
                    source_folders = folder_list[1:]
                    
                    console.print(f"   ✅ Consolidando en: {target_folder.name}")
                    
                    for source_folder in source_folders:
                        try:
                            # Mover archivos
                            for file_path in source_folder.rglob("*.md"):
                                relative_path = file_path.relative_to(source_folder)
                                target_file = target_folder / relative_path.name
                                
                                # Manejar conflictos de nombres
                                counter = 1
                                while target_file.exists():
                                    stem = target_file.stem
                                    suffix = target_file.suffix
                                    target_file = target_folder / f"{stem}_{counter}{suffix}"
                                    counter += 1
                                
                                file_path.rename(target_file)
                                stats['files_moved'] += 1
                            
                            # Eliminar carpeta fuente si está vacía
                            if not any(source_folder.iterdir()):
                                source_folder.rmdir()
                                stats['folders_consolidated'] += 1
                                console.print(f"   🗑️ Eliminada carpeta vacía: {source_folder.name}")
                            
                        except Exception as e:
                            console.print(f"   ❌ Error consolidando {source_folder.name}: {e}")
                            stats['errors'] += 1
                else:
                    console.print(f"   💡 Usa --execute para consolidar automáticamente")
    
    # Resumen final
    console.print(f"\n📊 [bold]RESUMEN DE CONSOLIDACIÓN:[/bold]")
    console.print(f"   🔍 Duplicados encontrados: {stats['duplicates_found']}")
    console.print(f"   🔄 Carpetas consolidadas: {stats['folders_consolidated']}")
    console.print(f"   📄 Archivos movidos: {stats['files_moved']}")
    console.print(f"   ❌ Errores: {stats['errors']}")
    
    if stats['duplicates_found'] > 0 and not execute:
        console.print(f"\n💡 [dim]Ejecuta con --execute para aplicar la consolidación[/dim]")
    
    return stats 