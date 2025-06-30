"""
paralib/exclusion_manager.py

Módulo centralizado para gestionar exclusiones de carpetas en el sistema PARA.
Proporciona una interfaz unificada para todos los scripts y módulos que necesiten excluir carpetas.
"""

from pathlib import Path
from typing import List, Optional, Set
from paralib.config import get_global_config, get_excluded_folders, add_excluded_folder, remove_excluded_folder, clear_excluded_folders, get_merged_exclusions as config_get_merged_exclusions
from paralib.ui import select_folders_to_exclude
from paralib.logger import logger

class ExclusionManager:
    """Gestor centralizado de exclusiones de carpetas para el sistema PARA."""
    
    def __init__(self):
        self.config = get_global_config()
        self._is_initialized = False
        self._exclusions_configured = False
    
    def ensure_exclusions_configured(self, vault_path: Path, force_interactive: bool = False) -> bool:
        """
        Asegura que las exclusiones estén configuradas ANTES de cualquier operación.
        SIEMPRE usa la GUI VISUAL con CHECKBOXES.
        
        Args:
            vault_path: Ruta del vault
            force_interactive: Forzar selector interactivo aunque ya estén configuradas
            
        Returns:
            bool: True si las exclusiones están configuradas (puede ser lista vacía)
        """
        try:
            logger.info(f"[EXCLUSION-GLOBAL] Verificando exclusiones para vault: {vault_path}")
            
            # Si ya están configuradas y no se fuerza, usar las existentes
            if self._exclusions_configured and not force_interactive:
                current_exclusions = self.get_global_exclusions()
                logger.info(f"[EXCLUSION-GLOBAL] Exclusiones ya configuradas: {len(current_exclusions)} carpetas")
                return True
            
            # Verificar si ya hay exclusiones globales guardadas
            existing_exclusions = self.get_global_exclusions()
            
            if existing_exclusions and not force_interactive:
                logger.info(f"[EXCLUSION-GLOBAL] Usando exclusiones persistentes: {len(existing_exclusions)} carpetas")
                self._exclusions_configured = True
                return True
            
            # SIEMPRE USAR GUI VISUAL CON CHECKBOXES
            logger.info("[EXCLUSION-GLOBAL] Configurando exclusiones con GUI visual")
            print("\n🌳 SELECTOR VISUAL DE EXCLUSIONES CON CHECKBOXES")
            print("="*55)
            print("🔒 Por razones de PRIVACIDAD, debes configurar qué carpetas excluir")
            print("📁 Las carpetas excluidas NO serán tocadas por la IA")
            print("✅ Se copiarán tal como están, sin clasificar")
            print("🌐 Esta configuración se aplicará a TODA la CLI")
            print("\n🎮 CONTROLES:")
            print("   ⬆️⬇️  Navegar  |  ➡️⬅️  Expandir/Colapsar")
            print("   🔘 ESPACIO: Marcar/Desmarcar  |  ✅ ENTER: Confirmar")
            print("   🚪 Q: Salir sin cambios")
            print("─" * 55)
            
            # Lanzar GUI visual DIRECTAMENTE
            logger.info("[EXCLUSION-GLOBAL] Lanzando GUI visual con checkboxes")
            selected_paths = self.select_exclusions_interactive(vault_path)
            
            # Guardar exclusiones globales
            if selected_paths:
                self.clear_global_exclusions()  # Limpiar anteriores
                for path in selected_paths:
                    self.add_global_exclusion(path)
                
                print(f"\n✅ Exclusiones configuradas: {len(selected_paths)} carpetas")
                for path in selected_paths:
                    print(f"   🚫 {Path(path).name}")
                logger.info(f"[EXCLUSION-GLOBAL] Exclusiones guardadas: {len(selected_paths)} carpetas")
            else:
                print("\n✅ Sin exclusiones configuradas")
                logger.info("[EXCLUSION-GLOBAL] Sin exclusiones configuradas")
            
            self._exclusions_configured = True
            
            print("\n🌐 EXCLUSIONES APLICADAS GLOBALMENTE A TODA LA CLI")
            print("💡 Para cambiar, ejecuta: python para_cli.py exclude reconfig")
            
            return True
            
        except Exception as e:
            logger.error(f"[EXCLUSION-GLOBAL] Error configurando exclusiones: {e}")
            print(f"❌ Error configurando exclusiones: {e}")
            return False
    
    def _detect_personal_folders(self, vault_path: Path) -> List[str]:
        """
        Detecta automáticamente carpetas que probablemente contengan información personal
        para ser excluidas por defecto. GENÉRICO para cualquier usuario de la comunidad.
        """
        personal_folders = []
        
        try:
            # Patrones de carpetas que suelen contener información personal
            personal_patterns = [
                # Carpetas del sistema original de Obsidian
                "**/*obsidian-system*",
                "**/*99*",
                "**/Templates",
                "**/templates", 
                "**/Attachments",
                "**/attachments",
                "**/Daily*",
                "**/daily*",
                "**/Personal*",
                "**/personal*",
                "**/Private*",
                "**/private*",
                "**/Diary*",
                "**/diary*",
                "**/Journal*",
                "**/journal*",
                
                # Carpetas técnicas que no deben clasificarse
                "**/.obsidian*",
                "**/.para_db*",
                "**/node_modules*",
                "**/.git*",
                "**/.vscode*",
                
                # Carpetas de configuración
                "**/Config*",
                "**/config*",
                "**/Settings*",
                "**/settings*",
                
                # Carpetas de trabajo personal
                "**/Inbox*",  # Solo si no es parte de PARA
                "**/Draft*",
                "**/drafts*",
                "**/Temp*",
                "**/temp*",
                "**/Trash*",
                "**/trash*"
            ]
            
            # Buscar carpetas que coincidan con los patrones
            for pattern in personal_patterns:
                matches = list(vault_path.glob(pattern))
                for match in matches:
                    if match.is_dir():
                        # Verificar que no sea una carpeta PARA principal
                        if not self._is_para_main_folder(match):
                            personal_folders.append(str(match.resolve()))
            
            # Remover duplicados y ordenar
            personal_folders = list(dict.fromkeys(personal_folders))
            personal_folders.sort()
            
            logger.info(f"[EXCLUSION-GLOBAL] Detectadas {len(personal_folders)} carpetas personales potenciales")
            
        except Exception as e:
            logger.error(f"[EXCLUSION-GLOBAL] Error detectando carpetas personales: {e}")
        
        return personal_folders
    
    def _is_para_main_folder(self, folder_path: Path) -> bool:
        """
        Verifica si una carpeta es una carpeta principal del sistema PARA
        que NO debe ser excluida automáticamente.
        """
        para_main_folders = {
            "00-Inbox", "01-Projects", "02-Areas", "03-Resources", "04-Archive",
            "00-inbox", "01-projects", "02-areas", "03-resources", "04-archive",
            "Inbox", "Projects", "Areas", "Resources", "Archive"
        }
        
        return folder_path.name in para_main_folders
    
    def get_global_exclusions(self) -> List[str]:
        """Obtiene las exclusiones globales configuradas."""
        return get_excluded_folders()
    
    def add_global_exclusion(self, folder_path: str) -> bool:
        """Agrega una carpeta a las exclusiones globales."""
        return add_excluded_folder(folder_path)
    
    def remove_global_exclusion(self, folder_path: str) -> bool:
        """Remueve una carpeta de las exclusiones globales."""
        return remove_excluded_folder(folder_path)
    
    def clear_global_exclusions(self) -> int:
        """Limpia todas las exclusiones globales."""
        return clear_excluded_folders()
    
    def list_global_exclusions(self) -> List[str]:
        """Lista todas las exclusiones globales."""
        return get_excluded_folders()
    
    def is_folder_excluded(self, folder_path: str) -> bool:
        """Verifica si una carpeta está excluida globalmente."""
        excluded = get_excluded_folders()
        return folder_path in excluded
    
    def get_merged_exclusions(self, additional_exclusions: Optional[List[str]] = None) -> List[str]:
        """Combina exclusiones globales con exclusiones adicionales específicas."""
        return config_get_merged_exclusions(additional_exclusions)
    
    def select_exclusions_interactive(self, vault_path: Path) -> List[str]:
        """Lanza la GUI interactiva para seleccionar carpetas a excluir."""
        try:
            logger.info(f"[EXCLUSION-MANAGER] Lanzando GUI interactiva para vault: {vault_path}")
            selected_paths = select_folders_to_exclude(vault_path)
            logger.info(f"[EXCLUSION-MANAGER] GUI devolvió {len(selected_paths)} carpetas seleccionadas")
            return selected_paths
        except Exception as e:
            logger.error(f"[EXCLUSION-MANAGER] Error en GUI interactiva: {e}")
            return []
    
    def filter_notes_by_exclusions(self, notes: List[Path], excluded_paths: Optional[List[str]] = None) -> List[Path]:
        """Filtra una lista de notas aplicando las exclusiones configuradas."""
        if not excluded_paths:
            excluded_paths = self.get_merged_exclusions()
        
        if not excluded_paths:
            return notes
        
        filtered_notes = []
        for note in notes:
            note_resolved = str(note.resolve())
            is_excluded = False
            
            for excluded_path in excluded_paths:
                excluded_resolved = str(Path(excluded_path).resolve())
                if note_resolved.startswith(excluded_resolved):
                    is_excluded = True
                    break
            
            if not is_excluded:
                filtered_notes.append(note)
        
        logger.info(f"[EXCLUSION-MANAGER] Filtradas {len(notes)} notas, {len(filtered_notes)} después de exclusiones")
        return filtered_notes
    
    def get_exclusion_stats(self, vault_path: Path) -> dict:
        """Obtiene estadísticas sobre las exclusiones en un vault."""
        excluded_paths = self.get_global_exclusions()
        total_notes = len(list(vault_path.rglob("*.md")))
        
        if excluded_paths:
            excluded_notes = 0
            for excluded_path in excluded_paths:
                excluded_folder = Path(excluded_path)
                if excluded_folder.exists():
                    excluded_notes += len(list(excluded_folder.rglob("*.md")))
        else:
            excluded_notes = 0
        
        return {
            "total_notes": total_notes,
            "excluded_notes": excluded_notes,
            "available_notes": total_notes - excluded_notes,
            "excluded_folders": len(excluded_paths),
            "exclusion_percentage": (excluded_notes / total_notes * 100) if total_notes > 0 else 0
        }

# Instancia global única
_exclusion_manager = None

def get_exclusion_manager() -> ExclusionManager:
    """Obtiene la instancia global del gestor de exclusiones."""
    global _exclusion_manager
    if _exclusion_manager is None:
        _exclusion_manager = ExclusionManager()
    return _exclusion_manager

def ensure_global_exclusions_configured(vault_path: Path, force_interactive: bool = False) -> bool:
    """
    FUNCIÓN GLOBAL OBLIGATORIA: Asegura que las exclusiones estén configuradas.
    DEBE llamarse ANTES de cualquier operación de clasificación.
    """
    return get_exclusion_manager().ensure_exclusions_configured(vault_path, force_interactive)

# Funciones de conveniencia para compatibilidad
def get_global_exclusions() -> List[str]:
    """Obtiene las exclusiones globales."""
    return get_exclusion_manager().get_global_exclusions()

def add_global_exclusion(folder_path: str) -> bool:
    """Agrega una exclusión global."""
    return get_exclusion_manager().add_global_exclusion(folder_path)

def remove_global_exclusion(folder_path: str) -> bool:
    """Remueve una exclusión global."""
    return get_exclusion_manager().remove_global_exclusion(folder_path)

def clear_global_exclusions() -> int:
    """Limpia todas las exclusiones globales."""
    return get_exclusion_manager().clear_global_exclusions()

def get_merged_exclusions(additional_exclusions: Optional[List[str]] = None) -> List[str]:
    """Combina exclusiones globales con adicionales."""
    return get_exclusion_manager().get_merged_exclusions(additional_exclusions)

def filter_notes_by_exclusions(notes: List[Path], excluded_paths: Optional[List[str]] = None) -> List[Path]:
    """Filtra notas aplicando exclusiones."""
    return get_exclusion_manager().filter_notes_by_exclusions(notes, excluded_paths)

def select_exclusions_interactive(vault_path: Path) -> List[str]:
    """Lanza la GUI interactiva de exclusión."""
    return get_exclusion_manager().select_exclusions_interactive(vault_path) 