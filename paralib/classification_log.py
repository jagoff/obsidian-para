"""
paralib/classification_log.py

Registro exhaustivo y consulta de clasificaciones, factores, vecinos y feedback para aprendizaje activo y trazabilidad perfecta.
"""
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from paralib.db import ChromaPARADatabase
import json

def log_classification(
    db: ChromaPARADatabase,
    note_path: Path,
    content: str,
    predicted_category: str,
    predicted_folder: str,
    explanation: str,
    confidence: float,
    neighbors: List[Dict],
    prompt: str,
    model: str,
    keywords: List[str] = None,
    rules: List[str] = None,
    alias_used: Optional[str] = None,
    previous_category: Optional[str] = None,
    previous_folder: Optional[str] = None,
    tags: List[str] = None,
    created: Optional[str] = None,
    modified: Optional[str] = None,
    feedback: bool = False,
    feedback_category: Optional[str] = None,
    feedback_folder: Optional[str] = None,
    correction_reason: Optional[str] = None,
    extra_metadata: Dict = None
):
    """
    Registra todos los factores y la predicción de una clasificación en ChromaDB.
    """
    note_id = db._generate_id(note_path)
    embedding = db.embedding_model.encode(content[:1000], convert_to_tensor=False).tolist()
    metadata = {
        "path": str(note_path),
        "filename": note_path.name,
        "predicted_category": predicted_category,
        "predicted_folder": predicted_folder,
        "explanation": explanation,
        "confidence": confidence,
        "neighbors": json.dumps(neighbors),
        "prompt": prompt,
        "model": model,
        "keywords": json.dumps(keywords) if keywords is not None else "[]",
        "rules": json.dumps(rules) if rules is not None else "[]",
        "tags": json.dumps(tags) if tags is not None else "[]",
        "alias_used": alias_used,
        "previous_category": previous_category,
        "previous_folder": previous_folder,
        "created": created,
        "modified": modified,
        "feedback": feedback,
        "feedback_category": feedback_category,
        "feedback_folder": feedback_folder,
        "correction_reason": correction_reason,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    # --- Limpieza y serialización: ---
    for k, v in list(metadata.items()):
        if v is None:
            del metadata[k]
        elif isinstance(v, (list, dict)):
            metadata[k] = json.dumps(v)
    db.collection.upsert(
        ids=[note_id],
        embeddings=[embedding],
        documents=[content[:500]],
        metadatas=[metadata],
    )

def log_feedback(
    db: ChromaPARADatabase,
    note_path: Path,
    feedback_category: str,
    feedback_folder: str,
    correction_reason: Optional[str] = None
):
    """
    Marca una nota como corregida por feedback y actualiza la metadata.
    """
    note_id = db._generate_id(note_path)
    db.collection.update(
        ids=[note_id],
        metadatas=[{
            "feedback": True,
            "feedback_category": feedback_category,
            "feedback_folder": feedback_folder,
            "correction_reason": correction_reason,
            "feedback_timestamp": datetime.utcnow().isoformat(),
        }]
    )

def get_feedback_notes(db: ChromaPARADatabase) -> List[Dict]:
    """
    Devuelve todas las notas con feedback/corrección manual registrada.
    """
    results = db.collection.get(where={"feedback": True}, include=["metadatas"])
    return results.get("metadatas", [])

def get_classification_history(db: ChromaPARADatabase, note_path: Path) -> List[Dict]:
    """
    Devuelve el historial de clasificaciones para una nota específica.
    """
    note_id = db._generate_id(note_path)
    results = db.collection.get(ids=[note_id], include=["metadatas"])
    return results.get("metadatas", [])

def export_finetune_dataset(db: ChromaPARADatabase, output_path: str = "finetune_dataset.jsonl"):
    """
    Exporta todos los ejemplos de clasificación y feedback a un archivo JSONL para fine-tuning.
    """
    # Obtener todos los metadatos de la colección
    results = db.collection.get(include=["metadatas", "documents"])
    metadatas = results.get("metadatas", [])
    documents = results.get("documents", [])
    with open(output_path, "w", encoding="utf-8") as f:
        for meta, doc in zip(metadatas, documents):
            example = {
                "input": {
                    "note_content": doc,
                    "neighbors": meta.get("neighbors"),
                    "predicted_category": meta.get("predicted_category"),
                    "predicted_folder": meta.get("predicted_folder"),
                    "explanation": meta.get("explanation"),
                    "confidence": meta.get("confidence"),
                    "context": {
                        "keywords": meta.get("keywords"),
                        "rules": meta.get("rules"),
                        "alias_used": meta.get("alias_used"),
                        "prompt": meta.get("prompt"),
                        "model": meta.get("model"),
                        "tags": meta.get("tags"),
                        "created": meta.get("created"),
                        "modified": meta.get("modified"),
                        "previous_category": meta.get("previous_category"),
                        "previous_folder": meta.get("previous_folder"),
                    }
                },
                "user_feedback": {
                    "feedback": meta.get("feedback"),
                    "feedback_category": meta.get("feedback_category"),
                    "feedback_folder": meta.get("feedback_folder"),
                    "correction_reason": meta.get("correction_reason"),
                    "timestamp": meta.get("timestamp"),
                }
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n") 