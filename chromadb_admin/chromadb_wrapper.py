import hashlib
from pathlib import Path
from datetime import datetime
import chromadb
from sentence_transformers import SentenceTransformer

class ChromaDBWrapper:
    """
    Wrapper independiente para la base de datos ChromaDB, para exploración y análisis general.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(
            path=db_path, settings=chromadb.Settings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.collection = self.client.get_or_create_collection(
            name="para_notes",
            metadata={"description": "PARA note organization database"},
        )

    def _generate_id(self, note_path: str) -> str:
        return hashlib.md5(str(Path(note_path).resolve()).encode()).hexdigest()

    def get_all_notes_metadata(self) -> list:
        if self.collection.count() == 0:
            return []
        results = self.collection.get(include=["metadatas", "documents"])
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])
        # Emparejar metadatos y documentos
        for i, meta in enumerate(metadatas):
            meta["content"] = documents[i] if i < len(documents) else ""
        return metadatas

    def get_feedback_notes(self) -> list:
        results = self.collection.get(where={"feedback": True}, include=["metadatas"])
        return results.get("metadatas", [])

    def get_classification_history(self, note_path: str) -> list:
        note_id = self._generate_id(note_path)
        results = self.collection.get(ids=[note_id], include=["metadatas"])
        return results.get("metadatas", [])

    def search_similar_notes(self, content: str, n_results: int = 5) -> list:
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
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return list(zip(metadatas, distances)) 