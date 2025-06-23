#!/usr/bin/env python3
"""
paralib/analyze_manager.py

Motor de análisis estadístico y semántico para notas Obsidian.
Expone features y métricas para mejorar clasificación, reclasificación y limpieza.
"""
from pathlib import Path
from typing import Dict, Any
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
        self._analyze()

    def _analyze(self):
        """Calcula embeddings, clusters, comunidades y métricas globales."""
        notes = self.db.get_all_notes()
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
        # Guardar snapshot
        self.save_snapshot()

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