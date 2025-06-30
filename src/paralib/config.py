import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from paralib.logger import logger

class PARAConfig:
    """Gestor de configuración global de PARA con soporte para exclusiones de carpetas."""
    
    def __init__(self, config_file: str = "para_config.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self._ensure_default_structure()
    
    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde el archivo."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Configuración cargada desde {self.config_file}")
                    return config
            else:
                logger.info(f"Archivo de configuración no encontrado, creando nuevo: {self.config_file}")
                return {}
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def _save_config(self):
        """Guarda la configuración al archivo."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuración guardada en {self.config_file}")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
    
    def _ensure_default_structure(self):
        """Asegura que la configuración tenga la estructura por defecto."""
        defaults = {
            "ollama_model": "llama3.2:3b",
            "ai_backend": "auto",  # "ollama", "huggingface", "auto"
            "huggingface_model": "microsoft/DialoGPT-medium",
            "excluded_folders": [],
            "excluded_folders_global": [],
            "auto_backup": True,
            "learning_enabled": True,
            "chromadb_persist": True,
            "log_level": "INFO",
            "qa_system_enabled": True,
            "fallback_to_huggingface": True
        }
        
        changed = False
        for key, default_value in defaults.items():
            if key not in self.config:
                self.config[key] = default_value
                changed = True
        
        if changed:
            self._save_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Establece un valor de configuración."""
        self.config[key] = value
        self._save_config()
    
    def get_excluded_folders(self) -> List[str]:
        """Obtiene la lista de carpetas excluidas globalmente."""
        return self.config.get("excluded_folders_global", [])
    
    def add_excluded_folder(self, folder_path: str) -> bool:
        """Agrega una carpeta a la lista de exclusiones globales."""
        excluded = self.get_excluded_folders()
        if folder_path not in excluded:
            excluded.append(folder_path)
            self.config["excluded_folders_global"] = excluded
            self._save_config()
            logger.info(f"Carpeta agregada a exclusiones globales: {folder_path}")
            return True
        return False
    
    def remove_excluded_folder(self, folder_path: str) -> bool:
        """Remueve una carpeta de la lista de exclusiones globales."""
        excluded = self.get_excluded_folders()
        if folder_path in excluded:
            excluded.remove(folder_path)
            self.config["excluded_folders_global"] = excluded
            self._save_config()
            logger.info(f"Carpeta removida de exclusiones globales: {folder_path}")
            return True
        return False
    
    def clear_excluded_folders(self) -> int:
        """Limpia todas las exclusiones globales de carpetas."""
        count = len(self.get_excluded_folders())
        self.config["excluded_folders_global"] = []
        self._save_config()
        logger.info(f"Todas las exclusiones globales removidas ({count} carpetas)")
        return count
    
    def list_excluded_folders(self) -> List[str]:
        """Lista todas las carpetas excluidas globalmente."""
        return self.get_excluded_folders()
    
    def is_folder_excluded(self, folder_path: str) -> bool:
        """Verifica si una carpeta está en la lista de exclusiones globales."""
        excluded = self.get_excluded_folders()
        return folder_path in excluded
    
    def get_merged_exclusions(self, additional_exclusions: Optional[List[str]] = None) -> List[str]:
        """Combina las exclusiones globales con exclusiones adicionales específicas."""
        global_exclusions = self.get_excluded_folders()
        if additional_exclusions:
            # Combinar y eliminar duplicados
            all_exclusions = global_exclusions + additional_exclusions
            return list(dict.fromkeys(all_exclusions))  # Mantener orden y eliminar duplicados
        return global_exclusions

# Instancia global de configuración
_global_config = None

def get_global_config() -> PARAConfig:
    """Obtiene la instancia global de configuración."""
    global _global_config
    if _global_config is None:
        _global_config = PARAConfig()
    return _global_config

def load_config(config_file: str = "para_config.json") -> Dict[str, Any]:
    """Función de compatibilidad para cargar configuración."""
    config = get_global_config()
    return config.config

def get_excluded_folders() -> List[str]:
    """Obtiene las carpetas excluidas globalmente."""
    config = get_global_config()
    return config.get_excluded_folders()

def add_excluded_folder(folder_path: str) -> bool:
    """Agrega una carpeta a las exclusiones globales."""
    config = get_global_config()
    return config.add_excluded_folder(folder_path)

def remove_excluded_folder(folder_path: str) -> bool:
    """Remueve una carpeta de las exclusiones globales."""
    config = get_global_config()
    return config.remove_excluded_folder(folder_path)

def clear_excluded_folders() -> int:
    """Limpia todas las exclusiones globales."""
    config = get_global_config()
    return config.clear_excluded_folders()

def get_merged_exclusions(additional_exclusions: Optional[List[str]] = None) -> List[str]:
    """Combina exclusiones globales con adicionales."""
    config = get_global_config()
    return config.get_merged_exclusions(additional_exclusions)

def load_cache(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache: dict, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

# Funciones de compatibilidad para el sistema legacy
def load_para_config(config_file: str = "para_config.json") -> Dict[str, Any]:
    """Función de compatibilidad para cargar configuración PARA."""
    config = get_global_config()
    return config.config

def save_para_config(config_data: Dict[str, Any], config_file: str = "para_config.json"):
    """Función de compatibilidad para guardar configuración PARA."""
    config = get_global_config()
    config.config.update(config_data)
    config._save_config() 