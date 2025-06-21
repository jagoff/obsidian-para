"""
paralib/finetune_manager.py

Herramientas para preparar, analizar y utilizar el dataset de feedback/corrección para fine-tuning de modelos locales.
"""
import json
from typing import List, Dict

# Cargar dataset JSONL
def load_finetune_dataset(jsonl_path: str) -> List[Dict]:
    with open(jsonl_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

# Analizar ejemplos (estadísticas básicas)
def analyze_finetune_dataset(dataset: List[Dict]) -> Dict:
    total = len(dataset)
    feedback_count = sum(1 for ex in dataset if ex["user_feedback"].get("feedback"))
    categories = {}
    for ex in dataset:
        cat = ex["input"].get("predicted_category")
        categories[cat] = categories.get(cat, 0) + 1
    return {
        "total_examples": total,
        "with_feedback": feedback_count,
        "category_distribution": categories
    }

# Preparar datos para fine-tuning (OpenAI, HuggingFace, etc.)
def prepare_for_openai(dataset: List[Dict]) -> List[Dict]:
    """
    Prepara el dataset en formato OpenAI: {"messages": [{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]}
    """
    out = []
    for ex in dataset:
        user_content = ex["input"]["note_content"]
        if ex["user_feedback"].get("feedback_category"):
            assistant_content = ex["user_feedback"]["feedback_category"]
        else:
            assistant_content = ex["input"].get("predicted_category")
        out.append({
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content}
            ]
        })
    return out

# (Opcional) Preparar para otros frameworks... 