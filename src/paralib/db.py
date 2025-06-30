#!/usr/bin/env python3
"""
paralib/db.py

Módulo SUPER ROBUSTO para la interacción con ChromaDB.
Maneja todos los errores de manera elegante y nunca falla.
"""
import os
import hashlib
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import tempfile
import shutil

# Imports con manejo robusto de errores
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

from .logger import logger, log_function_calls, log_exceptions
from .log_center import log_center

class RobustChromaPARADatabase:
    """
    Wrapper SUPER ROBUSTO para ChromaDB.
    - Maneja todos los errores gracefully
    - Nunca falla completamente
    - Siempre devuelve resultados válidos
    - Auto-recovery en caso de problemas
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa ChromaDB de manera super robusta.
        Si algo falla, continúa con modo fallback.
        """
        self.db_path = db_path or self._get_default_db_path()
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.is_healthy = False
        self.fallback_mode = False
        self.fallback_data = {}  # Cache en memoria para modo fallback
        self.logger = log_center  # Usar log_center como logger
        self.current_model = "none"
        self.embedding_dimension = 384  # Valor por defecto
        
        # Intentar inicialización robusta
        self._robust_initialization()
    
    def _get_default_db_path(self) -> str:
        """Obtiene ruta por defecto para ChromaDB."""
        try:
            from .vault import find_vault
            vault = find_vault()
            if vault:
                return str(vault / ".para_db" / "chroma")
        except Exception:
            pass
        
        # Fallback a directorio temporal
        temp_dir = Path(tempfile.gettempdir()) / "para_chroma_robust"
        temp_dir.mkdir(exist_ok=True)
        return str(temp_dir)
    
    @log_exceptions
    def _robust_initialization(self):
        """Inicialización super robusta con múltiples fallbacks."""
        try:
            # Forzar modo local para evitar HuggingFace
            self._force_local_models()
            
            # Inicializar componentes en orden
            self._initialize_chromadb_client()
            self._initialize_embedding_model()
            self._initialize_collection()
            self._health_check()
            
            log_center.log_info("[SUCCESS] Inicialización robusta completada", "ChromaDB-Robust")
            
        except Exception as e:
            log_center.log_error(f"[ERROR] Error en inicialización robusta: {e}", "ChromaDB-Robust")
            self._activate_fallback_mode(f"Error de inicialización: {str(e)}")
    
    def _initialize_chromadb_client(self):
        """Inicializa cliente ChromaDB con múltiples intentos."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.client = chromadb.PersistentClient(
                    path=self.db_path,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                log_center.log_debug(f"Cliente ChromaDB creado (intento {attempt + 1})", "ChromaDB-Robust")
                return
            except Exception as e:
                log_center.log_warning(f"Intento {attempt + 1} falló: {e}", "ChromaDB-Robust")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(1)  # Esperar antes del siguiente intento
    
    def _initialize_embedding_model(self):
        """Inicializa modelo de embeddings con manejo robusto de errores."""
        try:
            # Evitar múltiples intentos de carga
            if hasattr(self, 'embedding_model') and self.embedding_model:
                log_center.log_info("Modelo ya cargado, saltando inicialización", "ChromaDB-Robust")
                return
            
            # DESHABILITAR COMPLETAMENTE HUGGING FACE PARA EVITAR ERRORES 429
            log_center.log_info("Hugging Face deshabilitado para evitar errores de rate limiting", "ChromaDB-Robust")
            
            # Suprimir todos los mensajes de Hugging Face y sentence-transformers
            import os
            import warnings
            import logging
            
            # Deshabilitar warnings y logs de Hugging Face
            os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
            os.environ['HF_HUB_VERBOSITY'] = 'error'
            os.environ['TOKENIZERS_PARALLELISM'] = 'false'
            
            # Suprimir warnings específicos
            warnings.filterwarnings("ignore", category=UserWarning, module="sentence_transformers")
            warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
            warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
            
            # Deshabilitar logs de Hugging Face
            logging.getLogger("transformers").setLevel(logging.ERROR)
            logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
            logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
            
            # Usar solo modelos locales o fallback
            models_to_try = [
                # 🔧 SOLO MODELOS LOCALES (sin Hugging Face)
                "all-MiniLM-L6-v2",  # Modelo local simple
            ]
            
            # Intentar cargar modelo local
            for model_name in models_to_try:
                try:
                    # Intentar cargar desde cache local
                    cache_dir = Path.home() / ".cache" / "para_embeddings"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Redirigir stdout/stderr para suprimir mensajes
                    import sys
                    from io import StringIO
                    
                    # Capturar y suprimir output
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = StringIO()
                    sys.stderr = StringIO()
                    
                    try:
                        from sentence_transformers import SentenceTransformer
                        self.embedding_model = SentenceTransformer(
                            model_name, 
                            cache_folder=str(cache_dir),
                            device='cpu'  # Forzar CPU para evitar problemas de GPU
                        )
                        log_center.log_info(f"Modelo cargado exitosamente: {model_name}", "ChromaDB-Robust")
                        break
                    finally:
                        # Restaurar stdout/stderr
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr
                        
                except Exception as e:
                    log_center.log_warning(f"No se pudo cargar modelo {model_name}: {e}", "ChromaDB-Robust")
                    continue
            
            # Si no se pudo cargar ningún modelo, usar fallback
            if not hasattr(self, 'embedding_model') or not self.embedding_model:
                log_center.log_warning("Usando modo fallback sin embeddings", "ChromaDB-Robust")
                self.embedding_model = None
                
        except Exception as e:
            log_center.log_error(f"Error inicializando modelo de embeddings: {e}", "ChromaDB-Robust")
            self.embedding_model = None
    
    def _get_cache_dir(self):
        """Obtiene directorio de cache para modelos."""
        cache_dir = os.path.expanduser("~/.cache/para_embeddings")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    def _force_local_models(self):
        """Fuerza el uso de modelos locales para evitar problemas de HuggingFace."""
        try:
            # Configurar variables de entorno para evitar HuggingFace
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            os.environ["HF_DATASETS_OFFLINE"] = "1"
            
            log_center.log_info("[CONFIG] Modo offline activado para evitar HuggingFace", "ChromaDB-Robust")
        except Exception as e:
            log_center.log_warning(f"[WARNING] No se pudo configurar modo offline: {e}", "ChromaDB-Robust")
    
    def _initialize_collection(self):
        """Inicializa colección con manejo robusto."""
        try:
            self.collection = self.client.get_or_create_collection(
                name="para_notes_robust",
                metadata={"description": "PARA notes with robust handling"}
            )
            log_center.log_debug("Colección inicializada", "ChromaDB-Robust")
        except Exception as e:
            log_center.log_error(f"Error inicializando colección: {e}", "ChromaDB-Robust")
            raise
    
    def _health_check(self):
        """Verifica que todo funcione correctamente."""
        try:
            # Test básico
            count = self.collection.count()
            
            # Test de embedding
            if self.embedding_model:
                test_embedding = self.embedding_model.encode("test", convert_to_tensor=False)
                if len(test_embedding) > 0:
                    self.is_healthy = True
                    log_center.log_debug(f"Health check OK - {count} notas", "ChromaDB-Robust")
                else:
                    raise ValueError("Embedding vacío")
            else:
                raise ValueError("Modelo de embedding no disponible")
                
        except Exception as e:
            log_center.log_warning(f"Health check falló: {e}", "ChromaDB-Robust")
            self.is_healthy = False
    
    def _activate_fallback_mode(self, reason: str):
        """Activa modo fallback cuando ChromaDB no funciona."""
        self.fallback_mode = True
        self.is_healthy = False
        log_center.log_warning(f"🔄 Activando modo fallback: {reason}", "ChromaDB-Robust")
        
        # Cargar datos existentes si es posible
        self._load_fallback_data()
    
    def _load_fallback_data(self):
        """Carga datos en modo fallback desde archivo."""
        try:
            fallback_file = Path(self.db_path).parent / "fallback_data.json"
            if fallback_file.exists():
                import json
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    self.fallback_data = json.load(f)
                log_center.log_info(f"Datos fallback cargados: {len(self.fallback_data)} entradas", "ChromaDB-Robust")
        except Exception as e:
            log_center.log_warning(f"No se pudieron cargar datos fallback: {e}", "ChromaDB-Robust")
            self.fallback_data = {}
    
    def _save_fallback_data(self):
        """Guarda datos en modo fallback."""
        try:
            fallback_file = Path(self.db_path).parent / "fallback_data.json"
            fallback_file.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(fallback_file, 'w', encoding='utf-8') as f:
                json.dump(self.fallback_data, f, indent=2, default=str)
            log_center.log_debug("Datos fallback guardados", "ChromaDB-Robust")
        except Exception as e:
            log_center.log_warning(f"No se pudieron guardar datos fallback: {e}", "ChromaDB-Robust")
    
    @log_exceptions
    def add_or_update_note(self, note_path: Path, content: str, category: str, project_name: str = None) -> bool:
        """
        Agrega o actualiza nota de manera super robusta.
        Siempre devuelve True/False, nunca falla.
        """
        try:
            note_id = self._generate_id(note_path)
            
            if self.fallback_mode:
                return self._add_note_fallback(note_id, note_path, content, category, project_name)
            
            # Modo normal ChromaDB
            return self._add_note_chromadb(note_id, note_path, content, category, project_name)
            
        except Exception as e:
            log_center.log_error(f"Error agregando nota {note_path.name}: {e}", "ChromaDB-Robust")
            # Intentar modo fallback
            try:
                note_id = self._generate_id(note_path)
                return self._add_note_fallback(note_id, note_path, content, category, project_name)
            except Exception as e2:
                log_center.log_error(f"Error en fallback: {e2}", "ChromaDB-Robust")
                return False
    
    def _add_note_chromadb(self, note_id: str, note_path: Path, content: str, category: str, project_name: str) -> bool:
        """Agrega nota usando ChromaDB."""
        try:
            # Generar embedding
            embedding = self.embedding_model.encode(content[:1000], convert_to_tensor=False).tolist()
            
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
                documents=[content[:500]],
                metadatas=[metadata],
            )
            
            log_center.log_debug(f"Nota agregada a ChromaDB: {note_path.name}", "ChromaDB-Robust")
            return True
            
        except Exception as e:
            log_center.log_error(f"Error en ChromaDB para {note_path.name}: {e}", "ChromaDB-Robust")
            raise
    
    def _add_note_fallback(self, note_id: str, note_path: Path, content: str, category: str, project_name: str) -> bool:
        """Agrega nota en modo fallback."""
        try:
            self.fallback_data[note_id] = {
                "path": str(note_path),
                "category": category,
                "filename": note_path.name,
                "project_name": project_name or "",
                "content": content[:500],
                "last_updated_utc": datetime.utcnow().isoformat(),
            }
            
            self._save_fallback_data()
            log_center.log_debug(f"Nota agregada en modo fallback: {note_path.name}", "ChromaDB-Robust")
            return True
            
        except Exception as e:
            log_center.log_error(f"Error en modo fallback: {e}", "ChromaDB-Robust")
            return False
    
    @log_exceptions
    def search_similar_notes(self, content: str, n_results: int = 5, limit: int = None) -> List[Tuple[Dict, float]]:
        """
        Búsqueda super robusta que SIEMPRE devuelve resultados válidos.
        """
        try:
            results_count = limit if limit is not None else n_results
            
            if self.fallback_mode:
                return self._search_fallback(content, results_count)
            
            # Modo normal ChromaDB
            return self._search_chromadb(content, results_count)
            
        except Exception as e:
            log_center.log_error(f"Error en búsqueda: {e}", "ChromaDB-Robust")
            # Siempre devolver algo válido
            return []
    
    def _search_chromadb(self, content: str, n_results: int) -> List[Tuple[Dict, float]]:
        """Búsqueda usando ChromaDB."""
        try:
            if self.collection.count() == 0:
                log_center.log_warning("Búsqueda en colección vacía", "ChromaDB-Robust")
                return []
            
            query_embedding = self.embedding_model.encode(content[:1000], convert_to_tensor=False).tolist()
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                include=["metadatas", "distances"],
            )
            
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            result_pairs = list(zip(metadatas, distances))
            log_center.log_debug(f"Encontradas {len(result_pairs)} notas similares", "ChromaDB-Robust")
            
            return result_pairs
            
        except Exception as e:
            log_center.log_error(f"Error en búsqueda ChromaDB: {e}", "ChromaDB-Robust")
            raise
    
    def _search_fallback(self, content: str, n_results: int) -> List[Tuple[Dict, float]]:
        """Búsqueda en modo fallback usando similitud básica."""
        try:
            if not self.fallback_data:
                return []
            
            # Búsqueda básica por palabras clave
            content_words = set(content.lower().split())
            results = []
            
            for note_id, note_data in self.fallback_data.items():
                note_content = note_data.get('content', '')
                note_words = set(note_content.lower().split())
                
                # Similitud básica (intersección de palabras)
                similarity = len(content_words.intersection(note_words)) / max(len(content_words), 1)
                
                if similarity > 0:
                    metadata = {k: v for k, v in note_data.items() if k != 'content'}
                    results.append((metadata, 1.0 - similarity))  # Convertir a distancia
            
            # Ordenar por similitud y limitar resultados
            results.sort(key=lambda x: x[1])
            results = results[:n_results]
            
            log_center.log_debug(f"Búsqueda fallback: {len(results)} resultados", "ChromaDB-Robust")
            return results
            
        except Exception as e:
            log_center.log_error(f"Error en búsqueda fallback: {e}", "ChromaDB-Robust")
            return []
    
    def get_note_count(self) -> int:
        """Obtiene número de notas de manera robusta."""
        try:
            if self.fallback_mode:
                return len(self.fallback_data)
            elif self.collection:
                return self.collection.count()
            else:
                return 0
        except Exception:
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas robustas."""
        try:
            total_notes = self.get_note_count()
            
            stats = {
                "total_notes": total_notes,
                "mode": "fallback" if self.fallback_mode else "chromadb",
                "healthy": self.is_healthy,
                "db_path": self.db_path
            }
            
            if not self.fallback_mode and self.collection:
                # Estadísticas adicionales de ChromaDB
                try:
                    results = self.collection.get(include=["metadatas"], limit=100)
                    metadatas = results.get("metadatas", [])
                    
                    categories = [m.get('category', 'Unknown') for m in metadatas]
                    stats["categories"] = len(set(categories))
                    
                except Exception:
                    pass
            
            log_center.log_debug(f"Estadísticas generadas: {stats}", "ChromaDB-Robust")
            return stats
            
        except Exception as e:
            log_center.log_error(f"Error obteniendo estadísticas: {e}", "ChromaDB-Robust")
            return {
                "total_notes": 0,
                "mode": "error",
                "healthy": False,
                "error": str(e)
            }
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Obtiene distribución de categorías de manera robusta."""
        try:
            if self.fallback_mode:
                distribution = {}
                for note_data in self.fallback_data.values():
                    category = note_data.get('category', 'Unknown')
                    distribution[category] = distribution.get(category, 0) + 1
                return distribution
            
            elif self.collection and self.collection.count() > 0:
                results = self.collection.get(include=["metadatas"])
                metadatas = results.get("metadatas", [])
                
                distribution = {}
                for metadata in metadatas:
                    category = metadata.get('category', 'Unknown')
                    distribution[category] = distribution.get(category, 0) + 1
                
                return distribution
            
            else:
                return {}
                
        except Exception as e:
            log_center.log_error(f"Error obteniendo distribución: {e}", "ChromaDB-Robust")
            return {}
    
    def _generate_id(self, note_path: Path) -> str:
        """Genera ID único para una nota."""
        try:
            return hashlib.md5(str(note_path.resolve()).encode()).hexdigest()
        except Exception:
            # Fallback usando timestamp
            return hashlib.md5(f"{note_path.name}_{time.time()}".encode()).hexdigest()
    
    def update_note_category(self, note_path: Path, new_category: str, project_name: str = None) -> bool:
        """Actualiza categoría de manera robusta."""
        try:
            # Leer contenido
            try:
                content = note_path.read_text(encoding='utf-8')
            except Exception:
                content = ""
            
            # Usar add_or_update_note que ya es robusto
            return self.add_or_update_note(note_path, content, new_category, project_name)
            
        except Exception as e:
            log_center.log_error(f"Error actualizando categoría: {e}", "ChromaDB-Robust")
            return False
    
    def get_all_notes_metadata(self) -> List[Dict]:
        """Obtiene metadatos de todas las notas de manera robusta, incluyendo embeddings."""
        try:
            if self.fallback_mode:
                # Modo fallback: devolver metadatos desde cache
                metadata_list = []
                for note_data in self.fallback_data.values():
                    metadata = {k: v for k, v in note_data.items() if k != 'content'}
                    metadata_list.append(metadata)
                return metadata_list
            
            elif self.collection and self.collection.count() > 0:
                # Modo ChromaDB normal - INCLUIR EMBEDDINGS
                results = self.collection.get(include=["metadatas", "embeddings"])
                metadatas = results.get("metadatas", [])
                embeddings = results.get("embeddings", [])
                
                # Combinar metadatos con embeddings
                combined_metadata = []
                for i, metadata in enumerate(metadatas):
                    if i < len(embeddings):
                        metadata_with_embedding = metadata.copy()
                        metadata_with_embedding['embedding'] = embeddings[i]
                        combined_metadata.append(metadata_with_embedding)
                    else:
                        combined_metadata.append(metadata)
                
                log_center.log_debug(f"Obtenidos metadatos con embeddings de {len(combined_metadata)} notas", "ChromaDB-Robust")
                return combined_metadata
            
            else:
                # Colección vacía
                return []
                
        except Exception as e:
            log_center.log_error(f"Error obteniendo metadatos: {e}", "ChromaDB-Robust")
            return []
    
    def search_by_category(self, category: str, n_results: int = 10) -> List[Tuple[Dict, float]]:
        """Busca notas por categoría de manera robusta."""
        try:
            if self.fallback_mode:
                # Búsqueda en modo fallback
                results = []
                for note_data in self.fallback_data.values():
                    if note_data.get('category') == category:
                        metadata = {k: v for k, v in note_data.items() if k != 'content'}
                        results.append((metadata, 0.0))
                return results[:n_results]
            
            elif self.collection and self.collection.count() > 0:
                # Búsqueda en ChromaDB
                results = self.collection.get(
                    where={"category": category},
                    include=["metadatas"],
                    limit=n_results
                )
                
                metadatas = results.get("metadatas", [])
                result_pairs = [(metadata, 0.0) for metadata in metadatas]
                
                log_center.log_debug(f"Encontradas {len(result_pairs)} notas en categoría {category}", "ChromaDB-Robust")
                return result_pairs
            
            else:
                return []
                
        except Exception as e:
            log_center.log_error(f"Error buscando por categoría '{category}': {e}", "ChromaDB-Robust")
            return []
    
    def find_similar_in_category(self, content: str, category: str, n_results: int = 5) -> List[Tuple[Dict, float]]:
        """Busca notas similares dentro de una categoría específica."""
        try:
            if self.fallback_mode:
                # Búsqueda en modo fallback filtrada por categoría
                category_notes = {k: v for k, v in self.fallback_data.items() 
                                if v.get('category') == category}
                
                if not category_notes:
                    return []
                
                # Similitud básica dentro de la categoría
                content_words = set(content.lower().split())
                results = []
                
                for note_id, note_data in category_notes.items():
                    note_content = note_data.get('content', '')
                    note_words = set(note_content.lower().split())
                    
                    similarity = len(content_words.intersection(note_words)) / max(len(content_words), 1)
                    
                    if similarity > 0:
                        metadata = {k: v for k, v in note_data.items() if k != 'content'}
                        results.append((metadata, 1.0 - similarity))
                
                results.sort(key=lambda x: x[1])
                return results[:n_results]
            
            elif self.collection and self.collection.count() > 0:
                # Filtrar primero por categoría
                query_embedding = self.embedding_model.encode(content[:1000], convert_to_tensor=False).tolist()
                
                # Obtener todas las notas de la categoría
                all_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=self.collection.count(),
                    include=["metadatas", "distances"],
                    where={"category": category}
                )
                
                metadatas = all_results.get("metadatas", [[]])[0]
                distances = all_results.get("distances", [[]])[0]
                
                # Filtrar y limitar resultados
                result_pairs = list(zip(metadatas, distances))
                result_pairs.sort(key=lambda x: x[1])
                
                return result_pairs[:n_results]
            
            else:
                return []
                
        except Exception as e:
            log_center.log_error(f"Error buscando similares en categoría {category}: {e}", "ChromaDB-Robust")
            return []
    
    def get_semantic_neighbors_for_classification(self, content: str, n_results: int = 5) -> List[Dict]:
        """
        Obtiene vecinos semánticos para clasificación.
        Método requerido por analyze_manager.py
        
        Returns:
            List[Dict]: Lista de vecinos con información detallada
        """
        try:
            # Usar el método de búsqueda existente
            similar_notes = self.search_similar_notes(content, n_results)
            
            # Formatear resultados para el análisis de clasificación
            neighbors = []
            for metadata, distance in similar_notes:
                neighbor = {
                    "path": metadata.get("path", ""),
                    "category": metadata.get("category", ""),
                    "filename": metadata.get("filename", ""),
                    "project_name": metadata.get("project_name", ""),
                    "similarity_score": max(0, 1.0 - distance) if distance < 1.0 else 0.0,
                    "distance": distance
                }
                neighbors.append(neighbor)
            
            log_center.log_debug(f"Vecinos semánticos encontrados: {len(neighbors)}", "ChromaDB-Robust")
            return neighbors
            
        except Exception as e:
            log_center.log_error(f"Error obteniendo vecinos semánticos: {e}", "ChromaDB-Robust")
            return []

    def get_health_status(self) -> Dict[str, Any]:
        """Obtiene estado de salud completo."""
        return {
            "healthy": self.is_healthy,
            "fallback_mode": self.fallback_mode,
            "chromadb_available": CHROMADB_AVAILABLE,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
            "note_count": self.get_note_count(),
            "db_path": self.db_path
        }

# Alias para compatibilidad
ChromaPARADatabase = RobustChromaPARADatabase 