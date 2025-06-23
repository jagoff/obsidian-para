"""
paralib/vault.py

Vault Manager para PARA System.
- Detección automática y robusta de vaults de Obsidian
- Gestión de caché y configuración
- Utilidades para manipulación de vaults

Uso:
    from paralib.vault import find_vault, load_para_config
    vault_path = find_vault()
    config = load_para_config()
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
import yaml
import re
import signal
from contextlib import contextmanager

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
        if is_google_drive:
            timeout_seconds = 20
            search_depth = 5  # Permitir profundidad suficiente para 'Mi unidad/Obsidian'
        elif is_cloud:
            timeout_seconds = 15
            search_depth = 2
        else:
            timeout_seconds = 5
            search_depth = max_depth
        if is_cloud:
            cloud_type = "Google Drive" if is_google_drive else "nube"
            console.print(f"[dim]Buscando en {cloud_type} (timeout: {timeout_seconds}s, profundidad: {search_depth}): {shorten_path(path)}[/dim]")
        try:
            with timeout_handler(timeout_seconds):
                if is_google_drive:
                    # Usar rglob manual con control de profundidad
                    def rglob_depth(base, pat, depth):
                        if depth < 0:
                            return
                        try:
                            for entry in base.iterdir():
                                if entry.is_dir():
                                    if entry.name == pat:
                                        results.append(entry)
                                        console.print(f"[green]✓ Vault encontrado en {shorten_path(path)}: {shorten_path(entry.parent)}[/green]")
                                    else:
                                        rglob_depth(entry, pat, depth-1)
                        except Exception as e:
                            console.print(f"[dim]No se pudo acceder a {base}: {e}[/dim]")
                    rglob_depth(path, ".obsidian", search_depth)
                else:
                    # Búsqueda limitada por profundidad para otras rutas
                    for depth in range(search_depth + 1):
                        if depth == 0:
                            search_path = path
                        else:
                            search_path = path / ("*/" * depth)
                        try:
                            for item in search_path.glob(pattern if depth == 0 else "*/" + pattern):
                                if item.is_dir() and item.name == ".obsidian":
                                    results.append(item)
                                    console.print(f"[green]✓ Vault encontrado en {shorten_path(path)}: {shorten_path(item.parent)}[/green]")
                                    break
                        except (PermissionError, OSError) as e:
                            console.print(f"[dim]No se pudo acceder a {search_path}: {e}[/dim]")
                            continue
        except TimeoutError:
            console.print(f"[dim]Timeout al buscar en {shorten_path(path)} (después de {timeout_seconds}s)[/dim]")
        except Exception as e:
            console.print(f"[dim]Error al buscar en {shorten_path(path)}: {e}[/dim]")
        return results

    potential_vaults = []
    
    # Usar la función dinámica para obtener las ubicaciones base
    search_locations = _get_common_vault_locations()
    
    # Buscar en todas las ubicaciones, priorizando locales pero incluyendo nube
    for location in search_locations:
        if not location.is_dir():
            continue
        
        is_cloud = is_cloud_path(location)
        location_type = "nube" if is_cloud else "local"
        console.print(f"[dim]Buscando vaults en {location_type}: {shorten_path(location)}[/dim]")
        
        obsidian_dirs = safe_rglob(location, ".obsidian")
        
        for obsidian_dir in obsidian_dirs:
            vault_path = obsidian_dir.parent
            if vault_path not in potential_vaults:
                potential_vaults.append(vault_path)
                console.print(f"[green]✓ Vault encontrado: {shorten_path(vault_path)}[/green]")

    if not potential_vaults:
        console.print("[bold yellow]⚠️ No se encontró ningún vault de Obsidian en las ubicaciones conocidas.[/bold yellow]")
        return None

    if len(potential_vaults) == 1:
        vault = potential_vaults[0]
        console.print(f"[bold green]🗄️ Vault detectado automáticamente:[/bold green] [cyan]{shorten_path(vault)}[/cyan] (seleccionado automáticamente)")
        return vault
        
    # Si hay múltiples vaults, mostrar selección
    try:
        from InquirerPy import inquirer
        from InquirerPy.base.control import Choice

        choices = [Choice(value=str(v), name=shorten_path(v)) for v in potential_vaults]
        
        selected_path_str = inquirer.select(
            message="Se encontraron varios vaults. Selecciona el que deseas usar:",
            choices=choices,
            default=choices[0]
        ).execute()
        
        return Path(selected_path_str)

    except ImportError:
        console.print("[bold blue]Se encontraron varios vaults. Selecciona el que deseas usar:[/bold blue]")
        for i, v in enumerate(potential_vaults, 1):
            console.print(f"  {i}. {shorten_path(v)}")
        try:
            idx = int(input(f"Selecciona vault (1-{len(potential_vaults)}): ").strip())
            return potential_vaults[idx-1]
        except (ValueError, IndexError):
            console.print("[yellow]Selección inválida. Usando el primer vault encontrado.[/yellow]")
            return potential_vaults[0]
    except Exception as e:
        console.print(f"[bold red]Error durante la selección de vault: {e}. Usando el primero.[/bold red]")
        return potential_vaults[0]

def find_vault(vault_path: str = None, force_cache: bool = False) -> Path | None:
    """Detecta y retorna la ruta del vault de Obsidian a usar, con mensajes de marca y auto-selección."""
    if vault_path:
        path = Path(vault_path).expanduser().resolve()
        if path.is_dir():
            console.print(f"[bold green]🗄️ Vault especificado por parámetro:[/bold green] [cyan]{shorten_path(path)}[/cyan]")
            return path
        else:
            console.print(f"[bold red]❌ La ruta especificada no es un directorio válido:[/bold red] [yellow]{vault_path}[/yellow]")
            return None
    # Intentar usar caché
    if CACHE_FILE.exists() and not force_cache:
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            cached_path = Path(data.get('vault_path', '')).expanduser().resolve()
            if cached_path.is_dir():
                console.print(f"[bold green]🗄️ Vault en caché detectado y seleccionado automáticamente:[/bold green] [cyan]{shorten_path(cached_path)}[/cyan]")
                return cached_path
        except Exception:
            pass
    # Si no hay caché válida, buscar automáticamente
    auto_vault = _detect_vault_automatically()
    if auto_vault:
        # Guardar en caché
        with open(CACHE_FILE, 'w') as f:
            json.dump({'vault_path': str(auto_vault)}, f)
        return auto_vault
    console.print("[bold red]❌ No se pudo detectar ningún vault de Obsidian. Por favor, especifícalo con --vault.[/bold red]")
    return None

def extract_frontmatter(note_text: str) -> tuple[dict, str]:
    """
    Extrae el frontmatter YAML de una nota de Obsidian y devuelve (frontmatter_dict, cuerpo_sin_frontmatter).
    Si no hay frontmatter, devuelve ({}, note_text).
    """
    if note_text.startswith('---'):
        parts = note_text.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception:
                frontmatter = {}
            body = parts[2].lstrip('\n')
            return frontmatter, body
    return {}, note_text

def save_para_config(config: dict, path: str = "para_config.json"):
    """Guarda el diccionario de configuración en para_config.json."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_para_config(path: str = "para_config.json") -> dict:
    """Carga el archivo de configuración para_config.json y lo retorna como dict."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def extract_links_and_backlinks(vault_path: Path) -> tuple[dict, dict, dict]:
    """
    Escanea todas las notas del vault y construye:
      - links_dict: nota -> [notas que enlaza]
      - backlinks_dict: nota -> [notas que la enlazan]
      - centrality: nota -> número de backlinks
    Devuelve (links_dict, backlinks_dict, centrality)
    """
    notes = list(vault_path.rglob("*.md"))
    name_to_path = {n.stem: n for n in notes}
    links_dict = {str(n): [] for n in notes}
    backlinks_dict = {str(n): [] for n in notes}
    # Extraer enlaces internos
    for note in notes:
        content = note.read_text(encoding='utf-8')
        # Buscar [[Nombre de nota]]
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        # Normalizar nombres y filtrar solo notas existentes
        links = [l.split('|')[0].strip() for l in links]  # Soporta alias Obsidian [[Nota|Alias]]
        links = [l for l in links if l in name_to_path]
        links_dict[str(note)] = [str(name_to_path[l]) for l in links]
    # Calcular backlinks
    for src, targets in links_dict.items():
        for tgt in targets:
            backlinks_dict[tgt].append(src)
    # Centralidad: número de backlinks
    centrality = {n: len(backlinks_dict[n]) for n in backlinks_dict}
    return links_dict, backlinks_dict, centrality

def get_notes_modification_times(vault_path: Path, top_n: int = 20) -> tuple[dict, list]:
    """
    Devuelve un dict nota->timestamp y una lista de las top_n notas más recientes.
    """
    notes = list(vault_path.rglob("*.md"))
    mod_times = {str(n): n.stat().st_mtime for n in notes}
    sorted_notes = sorted(mod_times.items(), key=lambda x: x[1], reverse=True)
    top_notes = [n for n, _ in sorted_notes[:top_n]]
    return mod_times, top_notes

def detect_tasks_in_notes(vault_path: Path) -> dict:
    """
    Devuelve un dict nota->(total_tareas, tareas_pendientes, tareas_completadas).
    """
    notes = list(vault_path.rglob("*.md"))
    task_info = {}
    for note in notes:
        content = note.read_text(encoding='utf-8')
        total = len(re.findall(r'- \[.\]', content))
        pendientes = len(re.findall(r'- \[ \]', content))
        completadas = len(re.findall(r'- \[x\]', content, re.IGNORECASE))
        task_info[str(note)] = (total, pendientes, completadas)
    return task_info

def extract_structured_features_from_note(note_text: str, note_path: str = None, db=None, backlinks_dict=None) -> dict:
    """
    Extrae features estructurados relevantes para clasificación PARA de una nota Obsidian.
    Devuelve un dict con flags y valores detectados y una breve explicación de cada uno.
    """
    import re, os
    features = {}
    explanations = {}
    # OKR, KPI, SMART
    features['has_okr'] = bool(re.search(r'OKR', note_text, re.IGNORECASE))
    explanations['has_okr'] = 'Contiene sección OKR (objetivos y resultados clave)'
    features['has_kpi'] = bool(re.search(r'KPI', note_text, re.IGNORECASE))
    explanations['has_kpi'] = 'Contiene sección KPI (indicadores clave de desempeño)'
    features['has_smart'] = bool(re.search(r'Meta[s]? SMART|SMART goals?', note_text, re.IGNORECASE))
    explanations['has_smart'] = 'Contiene metas SMART (específicas, medibles, alcanzables, relevantes, temporales)'
    # Dashboards y reportes
    features['has_dashboard'] = bool(re.search(r'Dashboard|Reporte|Tracker', note_text, re.IGNORECASE))
    explanations['has_dashboard'] = 'Contiene dashboard, reporte o tracker'
    # Roles y asignaciones
    features['has_roles'] = bool(re.search(r'Manager|Owner|Responsable|Engineer|Equipo|Asignad[oa]', note_text, re.IGNORECASE))
    explanations['has_roles'] = 'Menciona roles, responsables o equipos'
    # Deadlines y fechas
    features['has_deadline'] = bool(re.search(r'\bQ[1-4]\b|\b20\d{2}\b|deadline|entrega|final de|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}', note_text, re.IGNORECASE))
    explanations['has_deadline'] = 'Contiene deadlines, fechas de entrega o ciclos temporales'
    # Status YAML o en texto
    features['status'] = None
    m = re.search(r'status:\s*([\w ]+)', note_text, re.IGNORECASE)
    if m:
        features['status'] = m.group(1).strip()
    explanations['status'] = 'Status de la nota (ej: Backlog, En progreso, Completado)'
    # Palabras clave de dominio
    domain_keywords = ['FinOps', 'Automation', 'Compliance', 'Migration', 'Security', 'Optimization', 'Tagging', 'SLA', 'Pipeline', 'Cloud', 'AWS', 'Costos', 'Ahorro']
    found_keywords = [kw for kw in domain_keywords if re.search(kw, note_text, re.IGNORECASE)]
    features['domain_keywords'] = found_keywords
    explanations['domain_keywords'] = 'Palabras clave de dominio detectadas en la nota'
    # Tareas
    features['n_tasks'] = len(re.findall(r'- \[.\]', note_text))
    features['n_pending'] = len(re.findall(r'- \[ \]', note_text))
    features['n_completed'] = len(re.findall(r'- \[x\]', note_text, re.IGNORECASE))
    explanations['n_tasks'] = 'Cantidad total de tareas (checkboxes) en la nota'
    explanations['n_pending'] = 'Cantidad de tareas pendientes'
    explanations['n_completed'] = 'Cantidad de tareas completadas'
    # Tamaño de archivo y cantidad de palabras
    features['file_size'] = os.path.getsize(note_path) if note_path and os.path.exists(note_path) else None
    explanations['file_size'] = 'Tamaño del archivo en bytes'
    features['word_count'] = len(re.findall(r'\w+', note_text))
    explanations['word_count'] = 'Cantidad de palabras en la nota'
    # Presencia de imágenes/tablas
    features['has_images'] = bool(re.search(r'!\[.*?\]\(.*?\)', note_text))
    explanations['has_images'] = 'Contiene imágenes embebidas'
    features['has_tables'] = bool(re.search(r'\|.*\|', note_text))
    explanations['has_tables'] = 'Contiene tablas markdown'
    # Vecinos semánticos predominantes (requiere db)
    features['semantic_neighbors_majority'] = None
    if db and note_text:
        try:
            results = db.search_similar_notes(note_text, n_results=5)
            categories = [meta.get('category') for meta, _ in results if meta.get('category')]
            if categories:
                from collections import Counter
                most_common = Counter(categories).most_common(1)[0][0]
                features['semantic_neighbors_majority'] = most_common
        except Exception:
            pass
    explanations['semantic_neighbors_majority'] = 'Categoría predominante entre los vecinos semánticos (por embeddings)'
    # Historial de clasificación previa (requiere db)
    features['previous_classification'] = None
    if db and note_path:
        try:
            meta_list = db.get_all_notes_metadata()
            for meta in meta_list:
                if meta.get('path') == note_path:
                    features['previous_classification'] = meta.get('category')
                    break
        except Exception:
            pass
    explanations['previous_classification'] = 'Categoría previa registrada en la base de datos para esta nota'
    # Distribución de categorías en backlinks
    features['backlinks_category_distribution'] = None
    if backlinks_dict and note_path and note_path in backlinks_dict:
        from collections import Counter
        parent_folders = [os.path.dirname(src) for src in backlinks_dict[note_path]]
        cat_counter = Counter()
        for folder in parent_folders:
            if "01-Projects" in folder:
                cat_counter['Projects'] += 1
            elif "02-Areas" in folder:
                cat_counter['Areas'] += 1
            elif "03-Resources" in folder:
                cat_counter['Resources'] += 1
        features['backlinks_category_distribution'] = dict(cat_counter)
    explanations['backlinks_category_distribution'] = 'Distribución de categorías de las notas que enlazan a esta nota'
    # Retornar features y explicaciones
    return {k: {'value': features[k], 'explanation': explanations.get(k, '')} for k in features}

def score_para_classification(features: dict, category_weights: dict) -> tuple[str, int, dict]:
    """
    Calcula el puntaje de clasificación para cada categoría PARA y determina el ganador.
    Devuelve (categoría_ganadora, puntaje, desglose_puntaje).
    """
    scores = {}
    breakdowns = {}

    for category, weights in category_weights.items():
        total_score = 0
        score_breakdown = {}

        # El feature 'llm_prediction' ahora es solo el nombre de la categoría predicha por la IA
        llm_prediction_category = features.get('llm_prediction')
        if llm_prediction_category == category:
            weight = weights.get('llm_prediction', 0)
            total_score += weight
            if weight != 0:
                score_breakdown['llm_prediction'] = f"+{weight}"
        
        # Iterar sobre los otros features
        for feature, value in features.items():
            if feature == 'llm_prediction':
                continue

            weight = weights.get(feature, 0)
            if weight == 0:
                continue

            # Puntuación para valores booleanos y numéricos
            feature_score = 0
            if isinstance(value, bool) and value:
                feature_score = weight
            elif isinstance(value, (int, float)):
                # Ponderar el valor numérico (ej. 0.0 a 1.0) por el peso del factor
                # Asegura que el valor esté normalizado (ej. 0-1) si es necesario
                feature_score = value * weight
            
            if feature_score != 0:
                total_score += feature_score
                # Usar un formato consistente para el desglose
                sign = "+" if feature_score > 0 else ""
                score_breakdown[feature] = f"{sign}{int(feature_score)}"

        scores[category] = total_score
        breakdowns[category] = score_breakdown

    # Determinar la categoría ganadora
    if not scores:
        return "Inbox", 0, {}

    # Umbral mínimo de confianza. Si nadie lo supera, se queda en Inbox.
    MIN_SCORE_THRESHOLD = 5 

    # Filtrar categorías que no alcanzan el umbral
    eligible_scores = {cat: score for cat, score in scores.items() if score >= MIN_SCORE_THRESHOLD}
    
    if not eligible_scores:
        # Devolver el desglose del que más se acercó, para transparencia
        winner_if_no_threshold = max(scores, key=scores.get)
        return "Inbox", scores[winner_if_no_threshold], breakdowns[winner_if_no_threshold]

    winner = max(eligible_scores, key=eligible_scores.get)
    return winner, int(scores[winner]), breakdowns[winner] 