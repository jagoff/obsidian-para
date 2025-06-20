"""
paralib/vault.py

Lógica para encontrar, cachear y gestionar la ruta del vault de Obsidian.
"""
#
# MIT License
#
# Copyright (c) 2024 Fernando Ferrari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import os
import json
from pathlib import Path
import glob
from rich.console import Console
from InquirerPy import inquirer

console = Console()
CACHE_FILE = Path(".para_cache.json")
COMMON_VAULT_LOCATIONS = [
    "~/Documents/Obsidian",
    "~/Library/Mobile Documents/iCloud~md~obsidian/Documents",
    "~/Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian",
    "~/Desktop/Obsidian",
]

def shorten_path(path: Path, max_len: int = 70) -> str:
    """Acorta una ruta para mostrarla de forma legible."""
    path_str = str(path.resolve())
    home = str(Path.home())
    if path_str.startswith(home):
        path_str = "~" + path_str[len(home):]
    if len(path_str) <= max_len:
        return path_str
    parts = path_str.split(os.sep)
    if len(parts) > 4:
        return os.path.join(parts[0], parts[1], "...", *parts[-2:])
    return path_str

def _load_vault_path_from_cache() -> Path | None:
    """Carga la ruta del vault desde un archivo de caché."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                path = Path(data.get("vault_path"))
                if path.is_dir():
                    return path
        except (json.JSONDecodeError, KeyError):
            pass
    return None

def _save_vault_path_to_cache(vault_path: Path):
    """Guarda la ruta del vault en el archivo de caché."""
    with open(CACHE_FILE, "w") as f:
        json.dump({"vault_path": str(vault_path.resolve())}, f)

def _detect_vault_automatically() -> Path | None:
    """Busca un vault de Obsidian en ubicaciones comunes."""
    console.print("🕵️  [dim]Detectando vaults de Obsidian...[/dim]")
    checked_paths = {Path(p).expanduser() for p in COMMON_VAULT_LOCATIONS}
    
    found_vaults = []
    for path in checked_paths:
        # Usamos glob para buscar carpetas .obsidian hasta 2 niveles de profundidad
        # Esto es más rápido que os.walk
        potential_obsidian_dirs = glob.glob(str(path / "**/.obsidian"), recursive=True)
        for obsidian_dir in potential_obsidian_dirs:
            vault_path = Path(obsidian_dir).parent
            if vault_path not in [v['path'] for v in found_vaults]:
                 found_vaults.append({'path': vault_path, 'type': 'definitive'})

    if not found_vaults:
        return None
    
    if len(found_vaults) == 1:
        vault = found_vaults[0]['path']
        console.print(f"🗄️  [bold]Vault detectado automáticamente:[/bold] [cyan]{shorten_path(vault)}[/cyan]")
        return vault

    # Si hay múltiples vaults, le pedimos al usuario que elija
    choices = [
        {"name": shorten_path(v['path']), "value": v['path']}
        for v in found_vaults
    ]
    selected_path_str = inquirer.select(
        message="Se encontraron varios vaults. Por favor, seleccioná uno:",
        choices=choices,
    ).execute()
    return Path(selected_path_str)


def find_vault(vault_path_str: str | None, force_cache: bool) -> Path | None:
    """
    Orquesta la búsqueda del vault: caché, parámetro o detección automática.

    Args:
        vault_path_str: La ruta del vault pasada como argumento (si existe).
        force_cache: Flag para usar la caché sin preguntar.

    Returns:
        La ruta del vault como objeto Path, o None si no se encuentra.
    """
    # 1. Chequeamos la caché
    cached_path = _load_vault_path_from_cache()
    if cached_path:
        use_cached = force_cache
        if not use_cached:
            use_cached = inquirer.confirm(
                message=f"Se encontró un vault en caché: {shorten_path(cached_path)}. ¿Querés usarlo?",
                default=True
            ).execute()
        
        if use_cached:
            if cached_path.is_dir():
                console.print(f"🗄️  [bold]Usando vault desde caché:[/bold] [cyan]{shorten_path(cached_path)}[/cyan]")
                return cached_path
            else:
                console.print("[yellow]La ruta en caché ya no es válida. Buscando de nuevo...[/yellow]")

    # 2. Usamos la ruta pasada como parámetro si existe
    if vault_path_str:
        path = Path(vault_path_str).expanduser().resolve()
        if path.is_dir():
            _save_vault_path_to_cache(path)
            console.print(f"🗄️  [bold]Usando vault especificado:[/bold] [cyan]{shorten_path(path)}[/cyan]")
            return path
        else:
            console.print(f"[red]La ruta especificada '{path}' no es un directorio válido.[/red]")
            return None
    
    # 3. Detección automática como último recurso
    path = _detect_vault_automatically()
    if path:
        _save_vault_path_to_cache(path)
        return path

    console.print("[bold red]No se pudo encontrar ningún vault de Obsidian.[/bold red]")
    return None 