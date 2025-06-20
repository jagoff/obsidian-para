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