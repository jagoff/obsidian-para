"""
paralib/similarity.py

Funciones para evitar duplicados, detectar carpetas/proyectos similares, gestionar alias y enriquecer la clasificación usando embeddings y el historial.
"""
import unicodedata
import re
from typing import List, Optional
from difflib import SequenceMatcher
from pathlib import Path
from paralib.db import ChromaPARADatabase

# 1. Normalización de nombres

def normalize_name(name: str) -> str:
    """Normaliza un nombre para comparación: minúsculas, sin tildes, sin espacios, sin guiones, sin números, solo letras."""
    name = name.lower()
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r'[^a-z]', '', name)
    return name

# 2. Similitud de string (Levenshtein/Jaccard/SequenceMatcher)
def string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# 3. Similitud de embeddings
def embedding_similarity(a: str, b: str, db: ChromaPARADatabase) -> float:
    emb_a = db.embedding_model.encode(a, convert_to_tensor=False)
    emb_b = db.embedding_model.encode(b, convert_to_tensor=False)
    # Cosine similarity
    dot = sum(x*y for x, y in zip(emb_a, emb_b))
    norm_a = sum(x*x for x in emb_a) ** 0.5
    norm_b = sum(x*x for x in emb_b) ** 0.5
    return dot / (norm_a * norm_b + 1e-8)

# 4. Buscar carpeta/proyecto similar
def find_similar_folder(target_name: str, folders: List[str], db: ChromaPARADatabase, threshold: float = 0.85) -> Optional[str]:
    norm_target = normalize_name(target_name)
    best_score = 0
    best_folder = None
    for folder in folders:
        norm_folder = normalize_name(folder)
        score = string_similarity(norm_target, norm_folder)
        if score < threshold:
            # Probar similitud semántica si la de string no es suficiente
            score = embedding_similarity(target_name, folder, db)
        if score > best_score:
            best_score = score
            best_folder = folder
    if best_score >= threshold:
        return best_folder
    return None

# 5. Alias de proyectos (simple: guardar en ChromaDB como metadato especial)
def register_project_alias(project: str, alias: str, db: ChromaPARADatabase):
    # Guardar como nota especial con metadato 'alias_of'
    db.collection.upsert(
        ids=[f"alias_{normalize_name(alias)}"],
        embeddings=[[0.0]*384],  # Embedding dummy
        documents=[alias],
        metadatas=[{"alias_of": project, "type": "alias"}]
    )

def get_project_aliases(project: str, db: ChromaPARADatabase) -> List[str]:
    results = db.collection.get(where={"alias_of": project, "type": "alias"}, include=["documents"])
    return [doc for doc in results.get("documents", [])]

# 6. Historial de clasificación
def record_classification(note_path: Path, content: str, tags: List[str], category: str, folder: str, db: ChromaPARADatabase):
    db.add_or_update_note(note_path, content, category, folder)
    # Se puede enriquecer con tags y feedback en el futuro

def find_similar_classification(content: str, db: ChromaPARADatabase, n: int = 3) -> Optional[dict]:
    results = db.search_similar_notes(content, n_results=n)
    if not results:
        return None
    # Retornar la clasificación más frecuente entre los vecinos
    categories = [meta.get('category') for meta, _ in results if meta.get('category')]
    if not categories:
        return None
    from collections import Counter
    most_common = Counter(categories).most_common(1)[0][0]
    return {"category": most_common, "neighbors": results} 