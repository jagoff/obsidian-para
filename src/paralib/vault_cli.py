"""
paralib/vault_cli.py

Módulo CLI para búsqueda y selección de vaults de Obsidian.
Centraliza toda la lógica de detección, búsqueda y selección de vaults.

Uso:
    from paralib.vault_cli import select_vault_interactive
    vault_path = select_vault_interactive()
"""
import os
import json
from pathlib import Path
import signal
from contextlib import contextmanager
import sys
import time
import threading
from rich.console import Console
from paralib.logger import logger
from paralib.utils import format_vault_found_message, shorten_path

console = Console()
CACHE_FILE = Path(".para_cache.json")

def _get_common_vault_locations() -> list[Path]:
    """Genera dinámicamente una lista de posibles ubicaciones de vaults."""
    home = Path.home()
    locations = [
        home / "Documents",
        home / "Desktop",
    ]
    # Ubicaciones comunes de servicios en la nube en macOS
    if os.name == 'posix':
        cloud_storage_path = home / "Library/CloudStorage"
        if cloud_storage_path.is_dir():
            # Itera sobre todos los directorios de servicios de nube (e.g., iCloudDrive, GoogleDrive-xxx, Dropbox)
            for service_dir in cloud_storage_path.iterdir():
                if service_dir.is_dir():
                    locations.append(service_dir)
        
        mobile_docs_path = home / "Library/Mobile Documents"
        if mobile_docs_path.is_dir():
            # Busca específicamente la carpeta de iCloud de Obsidian
            icloud_obsidian_path = mobile_docs_path / "iCloud~md~obsidian/Documents"
            if icloud_obsidian_path.is_dir():
                locations.append(icloud_obsidian_path)
    return locations

def _load_vault_path_from_cache() -> Path | None:
    """Carga la ruta del vault desde un archivo de caché."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                path = Path(data.get("vault_path"))
                if path.is_dir():
                    return path
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error al leer caché de vault: {e}")
            pass
    return None

def _save_vault_path_to_cache(vault_path: Path):
    """Guarda la ruta del vault en el archivo de caché."""
    with open(CACHE_FILE, "w") as f:
        json.dump({"vault_path": str(vault_path.resolve())}, f)

def _detect_vault_automatically() -> Path | None:
    """
    Detecta automáticamente vaults de Obsidian en ubicaciones comunes.
    Evita timeouts en rutas en la nube y maneja errores de red graciosamente.
    """
    @contextmanager
    def timeout_handler(seconds):
        """Maneja timeouts para operaciones de red"""
        def timeout_signal_handler(signum, frame):
            raise TimeoutError(f"Operación cancelada después de {seconds} segundos")
        
        # Solo usar signal en Unix
        if hasattr(signal, 'SIGALRM'):
            old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(seconds)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            # En sistemas sin SIGALRM, usar timeout más simple
            yield
    
    def is_cloud_path(path: Path) -> bool:
        """Detecta si una ruta está en la nube (Google Drive, iCloud, etc.)"""
        path_str = str(path).lower()
        cloud_indicators = [
            'cloudstorage',
            'googledrive',
            'icloud',
            'dropbox',
            'onedrive',
            'box',
            'mega'
        ]
        return any(indicator in path_str for indicator in cloud_indicators)
    
    def safe_rglob(path: Path, pattern: str, max_depth: int = 3) -> list[Path]:
        """Búsqueda recursiva segura con timeout y límite de profundidad"""
        results = []
        is_cloud = is_cloud_path(path)
        is_google_drive = 'googledrive' in str(path).lower()
        exclude_dirs = {'.Encrypted', '.Trash', '.file-revisions-by-id', '.shortcut-targets-by-id', '.DS_Store', '.TemporaryItems', '.Spotlight-V100', '.fseventsd', '.DocumentRevisions-V100', '.apdisk'}
        if is_google_drive:
            timeout_seconds = 20
            search_depth = 5
        elif is_cloud:
            timeout_seconds = 15
            search_depth = 2
        else:
            timeout_seconds = 5
            search_depth = max_depth
        def recursive_find_obsidian(base, depth):
            if depth < 0:
                return
            try:
                for entry in base.iterdir():
                    if entry.is_dir() and entry.name not in exclude_dirs and not entry.name.startswith('.'):
                        if (entry / '.obsidian').is_dir():
                            results.append(entry / '.obsidian')
                        recursive_find_obsidian(entry, depth-1)
            except Exception as e:
                logger.warning(f"Error al iterar en {base}: {e}")
                pass
        try:
            with timeout_handler(timeout_seconds):
                recursive_find_obsidian(path, search_depth)
        except TimeoutError:
            print(' ' * 80, end='\r', flush=True)
            logger.warning(f"Timeout al buscar en {shorten_path(path, 40)}")
            console.print(f"[yellow]⏱️ Timeout al buscar en {shorten_path(path, 40)}[/yellow]")
        except Exception as e:
            print(' ' * 80, end='\r', flush=True)
            logger.error(f"Error al buscar en {shorten_path(path, 40)}: {e}", exc_info=True)
            console.print(f"[red]Error al buscar en {shorten_path(path, 40)}: {e}[/red]")
        return results

    potential_vaults = []
    
    # Usar la función dinámica para obtener las ubicaciones base
    search_locations = _get_common_vault_locations()
    
    spinner_frames = ['|', '/', '-', '\\']
    spinner_idx = [0]
    searching = [True]
    current_path = [""]
    def spinner_thread():
        while searching[0]:
            short_path = shorten_path(current_path[0], 40)
            spinner = spinner_frames[spinner_idx[0] % len(spinner_frames)]
            # Línea de progreso solo con print plano
            print(f"Buscando vault: {short_path} {spinner}   ", end='\r', flush=True)
            spinner_idx[0] += 1
            time.sleep(0.12)
    t = threading.Thread(target=spinner_thread)
    t.start()
    try:
        for location in search_locations:
            if not location.is_dir():
                continue
            current_path[0] = location
            is_cloud = is_cloud_path(location)
            location_type = "nube" if is_cloud else "local"
            # Línea de progreso animada y coloreada
            short_path = shorten_path(location, max_len=40)
            obsidian_dirs = safe_rglob(location, ".obsidian")
            # Limpiar la línea de progreso después de cada búsqueda
            print(' ' * 80, end='\r', flush=True)
            for obsidian_dir in obsidian_dirs:
                vault_path = obsidian_dir.parent
                if vault_path not in potential_vaults:
                    potential_vaults.append(vault_path)
                    console.print(format_vault_found_message(vault_path))
            # Pequeña pausa para animación si hay muchas rutas
            time.sleep(0.08)
    finally:
        searching[0] = False
        t.join()
        print(' ' * 80, end='\r', flush=True)

    # Validar y deduplicar solo vaults reales
    valid_vaults = []
    seen = set()
    for v in potential_vaults:
        v_path = Path(v).resolve()
        if (v_path / '.obsidian').is_dir() and str(v_path) not in seen:
            valid_vaults.append(v_path)
            seen.add(str(v_path))
    potential_vaults = valid_vaults

    if not potential_vaults:
        console.print("[yellow]⚠️ No se encontró ningún vault de Obsidian en las ubicaciones conocidas.[/yellow]")
        return None

    # Línea vacía para separar visualmente
    console.print("")

    # Selección automática si solo hay un vault
    if len(potential_vaults) == 1:
        vault = potential_vaults[0]
        console.print(f"[green]📁 Vault: [cyan]{shorten_path(vault)}[/cyan]")
        console.print("[dim]─────────────────────────────────────────────── 📂[/dim]")
        console.print(f"[dim]Ruta completa: {vault}[/dim]")
        return vault

    # Si hay múltiples vaults, mostrar selección
    try:
        from InquirerPy import inquirer
        from InquirerPy.base.control import Choice
        # Instrucciones claras
        console.print("[bold blue]Usa las flechas ↑ ↓ para moverte, Enter para seleccionar, 'q' para salir.[/bold blue]")
        console.print("")
        # Opciones con path acortado y path completo como subtexto
        def unique_label(v):
            short = shorten_path(v)
            parent = v.parent.name if hasattr(v, 'parent') else ''
            full = str(v)
            # Detecta Google Drive por la ruta
            if 'GoogleDrive' in full or 'googledrive' in full:
                return f"{short} (GoogleDrive)\n{full}"
            if parent and short == shorten_path(v):
                return f"{short} ({parent})\n{full}"
            return f"{short}\n{full}"
        choices = [Choice(value=str(v), name=f"📁 {unique_label(v)}") for v in potential_vaults]
        selected_path_str = inquirer.select(
            message="Se encontraron varios vaults. Selecciona el que deseas usar:",
            choices=choices,
            default=choices[0]
        ).execute()
        if selected_path_str.strip().lower() == 'q':
            print(' ' * 80, end='\r', flush=True)
            console.print("[cyan]👋 Saliste del flujo de selección de vault. ¡Hasta la próxima![/cyan]")
            import sys; sys.exit(0)
        selected_vault = Path(selected_path_str)
        console.print(f"[green]✅ Vault seleccionado: [cyan]{shorten_path(selected_vault)}[/cyan][/green]")
        console.print("[dim]─────────────────────────────────────────────── 📂[/dim]")
        console.print(f"[dim]Ruta completa: {selected_vault}[/dim]")
        return selected_vault
    except ImportError:
        console.print("[bold blue]Usa las flechas ↑ ↓ para moverte, Enter para seleccionar, 'q' para salir.[/bold blue]")
        console.print("[blue]Se encontraron varios vaults. Selecciona el que deseas usar (o 'q' para salir):[/blue]")
        for i, v in enumerate(potential_vaults, 1):
            console.print(f"  {i}. 📁 {shorten_path(v, 60)} [dim]({v})[/dim]")
        try:
            idx = input(f"Selecciona vault (1-{len(potential_vaults)}) o 'q' para salir: ").strip()
            if idx.lower() == 'q':
                print(' ' * 80, end='\r', flush=True)
                console.print("[cyan]👋 Saliste del flujo de selección de vault. ¡Hasta la próxima![/cyan]")
                import sys; sys.exit(0)
            idx = int(idx)
            selected_vault = potential_vaults[idx-1]
            console.print(f"[green]✅ Vault seleccionado: [cyan]{shorten_path(selected_vault)}[/cyan][/green]")
            console.print("[dim]─────────────────────────────────────────────── 📂[/dim]")
            console.print(f"[dim]Ruta completa: {selected_vault}[/dim]")
            return selected_vault
        except (ValueError, IndexError):
            console.print("[yellow]Selección inválida. Usando el primer vault encontrado.[/yellow]")
            selected_vault = potential_vaults[0]
            console.print(f"[green]✅ Vault seleccionado: [cyan]{shorten_path(selected_vault)}[/cyan][/green]")
            console.print("[dim]─────────────────────────────────────────────── 📂[/dim]")
            console.print(f"[dim]Ruta completa: {selected_vault}[/dim]")
            return selected_vault
    except Exception as e:
        logger.error(f"Error durante la selección de vault: {e}", exc_info=True)
        console.print(f"[red]Error durante la selección de vault: {e}. Usando el primero.[/red]")
        return potential_vaults[0]

def select_vault_interactive(vault_path: str = None, force_cache: bool = False) -> Path | None:
    """
    Función principal para selección interactiva de vault.
    Detecta y retorna la ruta del vault de Obsidian a usar, con mensajes de marca y auto-selección.
    
    Args:
        vault_path: Ruta explícita del vault (opcional)
        force_cache: Si True, ignora el caché y busca de nuevo
        
    Returns:
        Path del vault seleccionado o None si no se encontró
    """
    # 1. Priorizar ruta explícita del usuario
    if vault_path:
        path = Path(vault_path).expanduser().resolve()
        if path.is_dir() and (path / '.obsidian').is_dir():
            console.print(f"[green]📁 Vault: [cyan]{shorten_path(path)}[/cyan]")
            return path
        else:
            console.print(f"[red]❌ La ruta especificada no es un directorio válido de vault: [yellow]{vault_path}[/yellow]")
            return None
    
    # 2. Intentar usar caché
    if CACHE_FILE.exists() and not force_cache:
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            cached_path = Path(data.get('vault_path', '')).expanduser().resolve()
            if cached_path.is_dir() and (cached_path / '.obsidian').is_dir():
                console.print(f"[green]📁 Vault: [cyan]{shorten_path(cached_path)}[/cyan]")
                return cached_path
        except Exception as e:
            logger.warning(f"Error al leer caché de vault: {e}")
            pass
    
    # 3. Búsqueda automática robusta
    auto_vault = _detect_vault_automatically()
    if auto_vault:
        # Guardar en caché
        _save_vault_path_to_cache(auto_vault)
        return auto_vault
    
    console.print("[red]❌ No se pudo detectar ningún vault de Obsidian. Por favor, especifícalo con --vault.[/red]")
    return None

def get_vault_path(vault_path: str = None, force_cache: bool = False) -> Path | None:
    """
    Función simplificada para obtener la ruta del vault sin interacción.
    Usa caché si está disponible, busca automáticamente si no.
    
    Args:
        vault_path: Ruta explícita del vault (opcional)
        force_cache: Si True, ignora el caché
        
    Returns:
        Path del vault o None si no se encontró
    """
    # 1. Priorizar ruta explícita del usuario
    if vault_path:
        path = Path(vault_path).expanduser().resolve()
        if path.is_dir() and (path / '.obsidian').is_dir():
            return path
        return None
    
    # 2. Intentar usar caché
    cached_path = _load_vault_path_from_cache()
    if cached_path and not force_cache:
        return cached_path
    
    # 3. Búsqueda automática sin interacción
    auto_vault = _detect_vault_automatically()
    if auto_vault:
        _save_vault_path_to_cache(auto_vault)
        return auto_vault
    
    return None 