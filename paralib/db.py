"""
paralib/db.py

Módulo para la interacción con la base de datos vectorial ChromaDB.
"""
#
# MIT License
#
# Copyright (c) 2024 Fernando Ferrari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import hashlib
from pathlib import Path
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer


class ChromaPARADatabase:
    """
    Wrapper para la base de datos ChromaDB, adaptada para la gestión de notas PARA.
    """

    def __init__(self, db_path: str):
        """
        Inicializa la conexión con la base de datos.

        Args:
            db_path (str): Ruta al directorio de la base de datos.
        """
        self.db_path = db_path
        self.client = chromadb.PersistentClient(
            path=db_path, settings=chromadb.Settings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection(
            name="para_notes",
            metadata={"description": "PARA note organization database"},
        )

    def _generate_id(self, note_path: Path) -> str:
        """
        Genera un ID único y consistente para una nota a partir de su ruta.

        Args:
            note_path (Path): La ruta a la nota.

        Returns:
            str: Un hash MD5 como ID.
        """
        return hashlib.md5(str(note_path.resolve()).encode()).hexdigest()

    def add_or_update_note(
        self, note_path: Path, content: str, category: str, project_name: str = None
    ):
        """
        Agrega o actualiza una nota en la base de datos vectorial.

        Args:
            note_path (Path): Ruta al archivo de la nota.
            content (str): Contenido de la nota.
            category (str): Categoría PARA asignada.
            project_name (str, optional): Nombre del proyecto si aplica.
        """
        note_id = self._generate_id(note_path)
        # Usamos solo los primeros 1000 caracteres para el embedding por eficiencia.
        embedding = self.embedding_model.encode(
            content[:1000], convert_to_tensor=False
        ).tolist()

        metadata = {
            "path": str(note_path),
            "category": category,
            "filename": note_path.name,
            "project_name": project_name or "",
            "last_updated_utc": datetime.utcnow().isoformat(),
        }

        self.collection.upsert(
            ids=[note_id],
            embeddings=[embedding],
            documents=[content[:500]],  # Guardamos un snippet del documento.
            metadatas=[metadata],
        )

    def search_similar_notes(self, content: str, n_results: int = 5) -> list[tuple[dict, float]]:
        """
        Busca notas similares a un contenido dado.

        Args:
            content (str): El contenido a comparar.
            n_results (int, optional): Número de resultados a devolver.

        Returns:
            list[tuple[dict, float]]: Una lista de tuplas, donde cada tupla contiene
                                     los metadatos de una nota y su distancia/score.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.embedding_model.encode(
            content[:1000], convert_to_tensor=False
        ).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            include=["metadatas", "distances"],
        )
        
        # Emparejar metadatos con sus distancias
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return list(zip(metadatas, distances))

    def get_all_notes_metadata(self) -> list:
        """
        Obtiene los metadatos de todas las notas en la base de datos.

        Returns:
            list: Lista de diccionarios con los metadatos.
        """
        if self.collection.count() == 0:
            return []
        
        # Obtenemos todos los resultados de la colección
        results = self.collection.get(include=["metadatas"])
        return results.get("metadatas", [])

    def search_by_category(self, category: str, n_results: int = 10) -> list[tuple[dict, float]]:
        """
        Busca notas por categoría específica (Projects, Areas, Resources, Archive).

        Args:
            category (str): Categoría PARA a buscar
            n_results (int): Número de resultados a devolver

        Returns:
            list[tuple[dict, float]]: Notas de la categoría con sus metadatos
        """
        if self.collection.count() == 0:
            return []
        
        # Filtrar por categoría usando where
        results = self.collection.get(
            where={"category": category},
            include=["metadatas"],
            limit=n_results
        )
        
        metadatas = results.get("metadatas", [])
        # Para búsquedas por categoría, no tenemos distancias, así que usamos 0.0
        return [(metadata, 0.0) for metadata in metadatas]

    def get_category_distribution(self) -> dict:
        """
        Obtiene la distribución de categorías en la base de datos.

        Returns:
            dict: Diccionario con el conteo de cada categoría
        """
        if self.collection.count() == 0:
            return {}
        
        all_metadata = self.get_all_notes_metadata()
        distribution = {}
        
        for metadata in all_metadata:
            category = metadata.get('category', 'Unknown')
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution

    def find_similar_in_category(self, content: str, category: str, n_results: int = 5) -> list[tuple[dict, float]]:
        """
        Busca notas similares dentro de una categoría específica.
        Útil para mejorar la precisión de clasificación.

        Args:
            content (str): Contenido a comparar
            category (str): Categoría donde buscar
            n_results (int): Número de resultados

        Returns:
            list[tuple[dict, float]]: Notas similares en la categoría
        """
        if self.collection.count() == 0:
            return []
        
        query_embedding = self.embedding_model.encode(
            content[:1000], convert_to_tensor=False
        ).tolist()

        # Buscar solo en la categoría específica
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where={"category": category},
            n_results=n_results,
            include=["metadatas", "distances"],
        )
        
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        return list(zip(metadatas, distances))

    def get_semantic_neighbors_for_classification(self, content: str, n_results: int = 10) -> dict:
        """
        Obtiene vecinos semánticos para mejorar la clasificación PARA.
        Analiza patrones en categorías similares.

        Args:
            content (str): Contenido de la nota a clasificar
            n_results (int): Número de vecinos por categoría

        Returns:
            dict: Análisis de vecinos por categoría
        """
        categories = ["Projects", "Areas", "Resources", "Archive"]
        neighbors_analysis = {}
        
        for category in categories:
            similar_notes = self.find_similar_in_category(content, category, n_results)
            if similar_notes:
                neighbors_analysis[category] = {
                    'notes': similar_notes,
                    'avg_distance': sum(distance for _, distance in similar_notes) / len(similar_notes),
                    'count': len(similar_notes)
                }
            else:
                neighbors_analysis[category] = {
                    'notes': [],
                    'avg_distance': float('inf'),
                    'count': 0
                }
        
        return neighbors_analysis

    def get_project_patterns(self) -> dict:
        """
        Analiza patrones en proyectos para mejorar clasificación.
        Identifica características comunes de proyectos.

        Returns:
            dict: Patrones y características de proyectos
        """
        project_notes = self.search_by_category("Projects", n_results=100)
        
        patterns = {
            'total_projects': len(project_notes),
            'common_keywords': [],
            'project_names': [],
            'recent_projects': []
        }
        
        if project_notes:
            # Extraer nombres de proyectos
            project_names = [metadata.get('project_name', '') for metadata, _ in project_notes if metadata.get('project_name')]
            patterns['project_names'] = list(set(project_names))
            
            # Proyectos recientes (últimos 30 días)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_projects = []
            for metadata, _ in project_notes:
                last_updated = metadata.get('last_updated_utc')
                if last_updated:
                    try:
                        update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        if update_date > thirty_days_ago:
                            recent_projects.append(metadata)
                    except:
                        pass
            
            patterns['recent_projects'] = recent_projects[:10]  # Top 10 más recientes
        
        return patterns

    def update_note_category(self, note_path: Path, new_category: str, project_name: str = None):
        """
        Actualiza la categoría de una nota existente en la base de datos.

        Args:
            note_path (Path): Ruta de la nota
            new_category (str): Nueva categoría PARA
            project_name (str, optional): Nombre del proyecto
        """
        note_id = self._generate_id(note_path)
        
        # Obtener el contenido actual
        try:
            content = note_path.read_text(encoding='utf-8')
        except:
            content = ""
        
        # Actualizar con nueva categoría
        self.add_or_update_note(note_path, content, new_category, project_name)

    def get_notes_by_project(self, project_name: str) -> list[dict]:
        """
        Obtiene todas las notas de un proyecto específico.

        Args:
            project_name (str): Nombre del proyecto

        Returns:
            list[dict]: Metadatos de las notas del proyecto
        """
        if self.collection.count() == 0:
            return []
        
        results = self.collection.get(
            where={"project_name": project_name},
            include=["metadatas"]
        )
        
        return results.get("metadatas", [])

    def get_recent_notes(self, days: int = 7) -> list[dict]:
        """
        Obtiene notas actualizadas recientemente.

        Args:
            days (int): Número de días hacia atrás

        Returns:
            list[dict]: Metadatos de notas recientes
        """
        if self.collection.count() == 0:
            return []
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        all_metadata = self.get_all_notes_metadata()
        recent_notes = []
        
        for metadata in all_metadata:
            last_updated = metadata.get('last_updated_utc')
            if last_updated:
                try:
                    update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    if update_date > cutoff_date:
                        recent_notes.append(metadata)
                except:
                    pass
        
        return recent_notes 