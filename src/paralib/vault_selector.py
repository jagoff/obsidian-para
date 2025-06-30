"""
paralib/vault_selector.py

Vault Selector Module - Centraliza la selección de vaults de Obsidian
con caché inteligente, logging centralizado y experiencia de usuario mejorada.

Uso:
    from paralib.vault_selector import vault_selector
    vault_path = vault_selector.get_vault()
"""
import os
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from .logger import logger
from .vault import find_vault
from .vault_cli import select_vault_interactive

console = Console()
CACHE_FILE = Path(".para_vault_cache.json")

class VaultSelector:
    """Selector centralizado de vaults con caché y logging."""
    
    def __init__(self):
        self.cached_vault = None
        self._load_cache()
    
    def _load_cache(self):
        """Carga el vault desde caché."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    cached_path = Path(data.get("vault_path", ""))
                    if cached_path.is_dir() and (cached_path / '.obsidian').is_dir():
                        self.cached_vault = cached_path
                        logger.info(f"Vault en caché cargado: {cached_path}")
            except Exception as e:
                logger.warning(f"Error al leer caché de vault: {e}")
    
    def _save_cache(self, vault_path: Path):
        """Guarda el vault en caché."""
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"vault_path": str(vault_path.resolve())}, f)
            logger.info(f"Vault guardado en caché: {vault_path}")
        except Exception as e:
            logger.error(f"Error al guardar caché de vault: {e}")
    
    def get_vault(self, vault_path: str = None, force_interactive: bool = False, silent: bool = False) -> Path | None:
        """
        Obtiene el vault usando el sistema de caché y detección automática.
        
        Args:
            vault_path: Ruta específica del vault (opcional)
            force_interactive: Forzar selección interactiva
            silent: No mostrar mensajes de información
            
        Returns:
            Path del vault o None si no se encuentra
        """
        # 1. Priorizar ruta explícita del usuario
        if vault_path:
            path = Path(vault_path).expanduser().resolve()
            if path.is_dir() and (path / '.obsidian').is_dir():
                if not silent:
                    console.print(f"[green]📁 Vault: [cyan]{path}[/cyan]")
                self._save_cache(path)
                return path
            else:
                if not silent:
                    console.print(f"[red]❌ Ruta inválida: [yellow]{vault_path}[/yellow]")
                return None
        
        # 2. Usar caché si está disponible y no se fuerza interactivo
        if self.cached_vault and not force_interactive:
            if self.cached_vault.is_dir() and (self.cached_vault / '.obsidian').is_dir():
                if not silent:
                    console.print(f"[green]📁 Vault: [cyan]{self.cached_vault}[/cyan]")
                return self.cached_vault
            else:
                logger.warning("Vault en caché ya no existe")
                self.cached_vault = None
        
        # 3. Detección automática
        logger.info("Iniciando detección automática de vault")
        auto_vault = find_vault()
        if auto_vault:
            if not silent:
                console.print(f"[green]📁 Vault: [cyan]{auto_vault}[/cyan]")
            self._save_cache(auto_vault)
            return auto_vault
        
        # 4. Selección interactiva como último recurso
        if not force_interactive:
            if not silent:
                console.print("[yellow]⚠️ No se detectó vault automáticamente.[/yellow]")
            if Confirm.ask("¿Deseas seleccionar un vault manualmente?"):
                force_interactive = True
        
        if force_interactive:
            logger.info("Iniciando selección interactiva de vault")
            interactive_vault = select_vault_interactive()
            if interactive_vault:
                if not silent:
                    console.print(f"[green]📁 Vault: [cyan]{interactive_vault}[/cyan]")
                self._save_cache(interactive_vault)
                return interactive_vault
        
        # 5. No se encontró ningún vault
        if not silent:
            console.print("[red]❌ No se encontró ningún vault de Obsidian.[/red]")
        logger.error("No se pudo encontrar ningún vault de Obsidian")
        return None
    
    def clear_cache(self):
        """Limpia el caché de vault."""
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            self.cached_vault = None
            console.print("[green]✅ Caché de vault limpiado[/green]")
            logger.info("Caché de vault limpiado")
        else:
            console.print("[yellow]ℹ️ No hay caché para limpiar[/yellow]")
    
    def list_available_vaults(self) -> list[Path]:
        """Lista todos los vaults disponibles."""
        logger.info("Buscando vaults disponibles")
        vaults = []
        
        # Usar la función de detección automática para encontrar todos los vaults
        from .vault import _detect_vault_automatically
        detected_vault = _detect_vault_automatically()
        if detected_vault:
            vaults.append(detected_vault)
        
        return vaults

# Instancia global del selector
vault_selector = VaultSelector() 