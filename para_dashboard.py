#!/usr/bin/env python3
"""
PARA Dashboard with Chroma Vector Database
Real-time monitoring and organization of Obsidian vaults using PARA methodology
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import queue
import shutil
from paralib.logger import logger
import subprocess

# Try to import required packages, install if missing
try:
    import chromadb
    from chromadb.config import Settings
    import gradio as gr
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import ollama
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
except ImportError as e:
    print(f"Installing required packages: {e}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "chromadb", "gradio", "sentence-transformers", "ollama", "rich"])
    import chromadb
    from chromadb.config import Settings
    import gradio as gr
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import ollama
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text

console = Console()

# Decorador para loguear errores automáticamente
def log_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper

class PARAStats:
    """Statistics tracking for PARA organization"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_notes = 0
        self.processed_notes = 0
        self.projects = 0
        self.areas = 0
        self.resources = 0
        self.archive = 0
        self.inbox = 0
        self.errors = 0
        self.start_time = None
        self.end_time = None
        self.current_note = ""
        self.status = "idle"
    
    def to_dict(self):
        return {
            "total_notes": self.total_notes,
            "processed_notes": self.processed_notes,
            "projects": self.projects,
            "areas": self.areas,
            "resources": self.resources,
            "archive": self.archive,
            "inbox": self.inbox,
            "errors": self.errors,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "current_note": self.current_note,
            "status": self.status,
            "progress_percentage": (self.processed_notes / self.total_notes * 100) if self.total_notes > 0 else 0
        }

class ChromaPARADatabase:
    """Chroma vector database for PARA note management"""
    
    def __init__(self, db_path: str = "./para_chroma_db"):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="para_notes",
            metadata={"description": "PARA note organization database"}
        )
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def add_note(self, note_path: str, content: str, category: str, metadata: Dict = None):
        """Add a note to the vector database"""
        try:
            # Create embedding
            embedding = self.embedding_model.encode(content[:1000])  # Limit content for embedding
            
            # Prepare metadata
            note_metadata = {
                "path": note_path,
                "category": category,
                "filename": os.path.basename(note_path),
                "content_length": len(content),
                "added_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # Add to collection
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[content[:500]],  # Store first 500 chars as document
                metadatas=[note_metadata],
                ids=[self._generate_id(note_path)]
            )
            
            return True
        except Exception as e:
            logger.error(f"Error adding note to database: {e}")
            return False
    
    def search_similar_notes(self, query: str, n_results: int = 5):
        """Search for similar notes"""
        try:
            query_embedding = self.embedding_model.encode(query)
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results
            )
            return results
        except Exception as e:
            logger.error(f"Error searching database: {e}")
            return None
    
    def get_category_stats(self):
        """Get statistics by category"""
        try:
            all_metadata = self.collection.get()["metadatas"]
            stats = {"projects": 0, "areas": 0, "resources": 0, "archive": 0, "inbox": 0}
            
            for metadata in all_metadata:
                category = metadata.get("category", "inbox").lower()
                if category in stats:
                    stats[category] += 1
            
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"projects": 0, "areas": 0, "resources": 0, "archive": 0, "inbox": 0}
    
    def _generate_id(self, note_path: str) -> str:
        """Generate unique ID for note"""
        return hashlib.md5(note_path.encode()).hexdigest()

class PARAOrganizer:
    """Enhanced PARA organizer with Chroma database and dashboard"""
    
    def __init__(self, vault_path: str = None, debug_mode: bool = False):
        self.vault_path = vault_path or self._detect_vault()
        self.db = ChromaPARADatabase()
        self.stats = PARAStats()
        self.status_queue = queue.Queue()
        self.ollama_client = ollama.Client(host='http://localhost:11434')
        self.debug_mode = debug_mode
        
        # PARA folder structure
        self.para_folders = {
            "01-projects": "Projects",
            "02-areas": "Areas", 
            "03-resources": "Resources",
            "04-archive": "Archive",
            "00-inbox": "Inbox"
        }
    
    def debug(self, msg: str, level: str = "INFO"):
        """Debug function that only prints when debug_mode is True"""
        if not self.debug_mode:
            return
        console.print(f"[{level.upper()}] {msg}")
    
    def _count_markdown_files(self, path: str) -> int:
        """Count markdown files in a directory recursively"""
        try:
            count = 0
            for root, dirs, files in os.walk(path):
                # Skip system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git', 'venv']]
                
                for file in files:
                    if file.endswith('.md'):
                        count += 1
                
                # Limit depth
                if root.count(os.sep) - path.count(os.sep) > 2:
                    dirs.clear()
            return count
        except Exception:
            return 0
    
    def _is_likely_obsidian_vault(self, path: str) -> bool:
        """Check if a directory is likely an Obsidian vault based on multiple indicators"""
        try:
            current_script_dir = os.getcwd()
            # Explicitly ignore the script's directory and its parents
            if path in [current_script_dir, os.path.dirname(current_script_dir), os.path.dirname(os.path.dirname(current_script_dir))]:
                 return False

            # Must have .obsidian folder (definitive indicator)
            obsidian_config = os.path.join(path, ".obsidian")
            if os.path.exists(obsidian_config) and os.path.isdir(obsidian_config):
                return True
            
            # Skip obvious non-vault directories
            path_name = os.path.basename(path).lower()
            skip_patterns = ['repositories', 'projects', 'code', 'src', 'node_modules', 'venv', '__pycache__', '.git']
            if any(pattern in path_name for pattern in skip_patterns):
                return False
            
            # Skip system directories and home directory more reliably
            home_dir = os.path.expanduser("~")
            if path == home_dir or path == os.path.dirname(home_dir): # Ignore ~ and /Users
                return False
            
            # Skip the current script directory more reliably
            if path.startswith(current_script_dir) and path != current_script_dir:
                 # This allows subfolders of the repo to be vaults, but not the repo folder itself
                 pass
            elif path == current_script_dir:
                 return False

            # Check for other Obsidian indicators
            try:
                items = os.listdir(path)
            except PermissionError:
                return False
            
            # Check for PARA structure first (strong indicator)
            para_folders = ['00 inbox', '01 projects', '02 areas', '03 resources', '04 archive', 
                          '00-inbox', '01-projects', '02-areas', '03-resources', '04-archive',
                          'inbox', 'projects', 'areas', 'resources', 'archive']
            para_matches = [d.lower() in [item.lower() for item in items] for d in para_folders]
            has_para_structure = any(para_matches)
            
            # Count markdown files recursively
            md_count = 0
            try:
                for root, dirs, files in os.walk(path):
                    # Skip system directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git', 'venv']]
                    
                    for file in files:
                        if file.endswith('.md'):
                            md_count += 1
                    
                    # Limit depth to avoid infinite recursion
                    if root.count(os.sep) - path.count(os.sep) > 3:
                        dirs.clear()
            except Exception:
                pass
            
            # Must have markdown files
            if md_count == 0:
                return False
            
            # Check for multiple Obsidian indicators
            indicators = 0
            
            # Check for PARA structure (very strong indicator)
            if has_para_structure:
                indicators += 4  # Very strong indicator - this is likely a vault
            
            # Check for common Obsidian folder names
            obsidian_folders = ['attachments', 'images', 'assets', 'media', 'templates', 'daily notes', 'moc', '.obsidian', '.git']
            if any(d in items for d in obsidian_folders):
                indicators += 1
            
            # Check for common Obsidian file names
            obsidian_files = ['README.md', 'index.md', 'home.md', 'daily notes', 'templates', 'moc.md']
            if any(f in items for f in obsidian_files):
                indicators += 1
            
            # Check if path name suggests it's an Obsidian vault
            if 'obsidian' in path_name or 'vault' in path_name or 'notes' in path_name:
                indicators += 2
            
            # Check for reasonable number of markdown files (not too many, not too few)
            if 10 <= md_count <= 500:  # More reasonable range for a vault
                indicators += 1
            
            # Check if it's in a cloud storage location (Google Drive, iCloud, etc.)
            cloud_indicators = ['googledrive', 'icloud', 'dropbox', 'onedrive', 'cloudstorage']
            if any(indicator in path.lower() for indicator in cloud_indicators):
                indicators += 1
            
            # If it has PARA structure, it's very likely a vault
            if has_para_structure:
                return indicators >= 2  # Higher threshold even for PARA-structured directories
            
            # Must have at least 3 indicators to be considered a likely vault (more strict)
            return indicators >= 3
            
        except Exception:
            return False
    
    def _shorten_path(self, path: str, max_len: int = 60) -> str:
        """Shorten a path to be more readable in the UI"""
        try:
            # Replace home directory with ~
            home = os.path.expanduser("~")
            if path.startswith(home):
                path = "~" + path[len(home):]

            if len(path) <= max_len:
                return path

            # Shorten the middle of the path
            parts = path.split(os.sep)
            if len(parts) > 4:
                # Keep first 2 and last 2 parts
                shortened_path = os.sep.join(parts[:2]) + f"{os.sep}...{os.sep}" + os.sep.join(parts[-2:])
                return shortened_path
            
            return path
        except Exception:
            return path # Return original path on error
    
    def _detect_vault(self):
        """Detect Obsidian vault automatically with enhanced detection for multiple vaults"""
        console.print("[blue]🔍 Detecting Obsidian vaults...[/blue]")
        
        # Common Obsidian vault locations across different OS
        possible_paths = [
            # macOS common locations
            os.path.expanduser("~/Documents/Obsidian"),
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents"),
            os.path.expanduser("~/Library/CloudStorage/iCloud Drive/Obsidian"),
            os.path.expanduser("~/Dropbox/Obsidian"),
            os.path.expanduser("~/OneDrive/Obsidian"),
            os.path.expanduser("~/Google Drive/Obsidian"),
            os.path.expanduser("~/Desktop/Obsidian"),
            os.path.expanduser("~/Downloads/Obsidian"),
            os.path.expanduser("~/Library/Application Support/Obsidian"),
            os.path.expanduser("~/Library/Preferences/Obsidian"),
            
            # Google Drive specific paths (macOS)
            os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Mi unidad/Obsidian"),
            os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive/Obsidian"),
            os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/Mi unidad"),
            os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive"),
            
            # Linux common locations
            os.path.expanduser("~/Documents/Obsidian"),
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Dropbox/Obsidian"),
            os.path.expanduser("~/OneDrive/Obsidian"),
            os.path.expanduser("~/Google Drive/Obsidian"),
            os.path.expanduser("~/Desktop/Obsidian"),
            os.path.expanduser("~/Downloads/Obsidian"),
            
            # Windows common locations (for cross-platform compatibility)
            os.path.expanduser("~/Documents/Obsidian"),
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Dropbox/Obsidian"),
            os.path.expanduser("~/OneDrive/Obsidian"),
            os.path.expanduser("~/Google Drive/Obsidian"),
            os.path.expanduser("~/Desktop/Obsidian"),
            os.path.expanduser("~/Downloads/Obsidian"),
            
            # Check current directory and parents
            os.getcwd(),
            os.path.dirname(os.getcwd()),
            os.path.dirname(os.path.dirname(os.getcwd())),
            os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd())))
        ]
        
        # Remove duplicates and non-existent paths
        checked_paths = []
        for path in possible_paths:
            if path and path not in checked_paths:
                # Handle wildcard paths (like Google Drive)
                if '*' in path:
                    import glob
                    expanded_paths = glob.glob(path)
                    for expanded_path in expanded_paths:
                        if os.path.exists(expanded_path) and expanded_path not in checked_paths:
                            checked_paths.append(expanded_path)
                elif os.path.exists(path):
                    checked_paths.append(path)
        
        console.print(f"[dim]Checking {len(checked_paths)} possible locations...[/dim]")
        
        # Find all potential vaults
        found_vaults = []
        
        # First pass: Look for .obsidian folder (definitive vault detection)
        for path in checked_paths:
            console.print(f"[dim]Checking: {path}[/dim]")
            
            # Check if this path itself is a vault (has .obsidian folder)
            obsidian_config = os.path.join(path, ".obsidian")
            if os.path.exists(obsidian_config) and os.path.isdir(obsidian_config):
                console.print(f"[green]✓ Found Obsidian vault: {path}[/green]")
                found_vaults.append({
                    'path': path,
                    'type': 'definitive',
                    'confidence': 'high',
                    'md_count': self._count_markdown_files(path)
                })
                continue
            
            # Check subdirectories for vaults
            try:
                for root, dirs, files in os.walk(path):
                    # Skip system directories
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git', 'venv', '__pycache__']]
                    
                    if ".obsidian" in dirs:
                        console.print(f"[green]✓ Found Obsidian vault: {root}[/green]")
                        found_vaults.append({
                            'path': root,
                            'type': 'definitive',
                            'confidence': 'high',
                            'md_count': self._count_markdown_files(root)
                        })
                    
                    # Limit depth to avoid infinite recursion
                    if root.count(os.sep) - path.count(os.sep) > 3:
                        dirs.clear()
            except PermissionError:
                console.print(f"[yellow]⚠ Permission denied accessing: {path}[/yellow]")
                continue
            except Exception as e:
                console.print(f"[yellow]⚠ Error checking {path}: {e}[/yellow]")
                continue
        
        # Second pass: Look for directories that are likely Obsidian vaults
        console.print("[blue]🔍 Searching for likely Obsidian vaults...[/blue]")
        for path in checked_paths:
            try:
                # Only check if this path is likely an Obsidian vault
                if self._is_likely_obsidian_vault(path):
                    md_count = self._count_markdown_files(path)
                    
                    # Check if this path is not already in found_vaults
                    if not any(vault['path'] == path for vault in found_vaults):
                        console.print(f"[yellow]⚠ Found likely Obsidian vault: {path}[/yellow]")
                        console.print(f"[dim]Contains {md_count} markdown files[/dim]")
                        found_vaults.append({
                            'path': path,
                            'type': 'likely',
                            'confidence': 'medium',
                            'md_count': md_count
                        })
                        
            except Exception as e:
                continue
        
        # Handle found vaults
        if not found_vaults:
            console.print("[red]❌ No Obsidian vaults detected automatically[/red]")
            console.print("[yellow]💡 Common Obsidian vault locations:[/yellow]")
            console.print("  • ~/Documents/Obsidian")
            console.print("  • ~/Obsidian") 
            console.print("  • ~/Library/Mobile Documents/iCloud~md~obsidian/Documents")
            console.print("  • ~/Dropbox/Obsidian")
            console.print("  • ~/OneDrive/Obsidian")
            console.print("  • ~/Google Drive/Obsidian")
            
            return self._manual_vault_input()
        
        # Sort vaults by confidence and markdown count
        found_vaults.sort(key=lambda x: (x['confidence'] == 'high', x['md_count']), reverse=True)
        
        if len(found_vaults) == 1:
            # Only one vault found, use it automatically
            selected_vault = found_vaults[0]
            console.print(f"[green]✓ Auto-selected vault: {selected_vault['path']}[/green]")
            console.print(f"[dim]Contains {selected_vault['md_count']} markdown files[/dim]")
            return selected_vault['path']
        
        # Multiple vaults found, let user choose
        console.print(f"[blue]Found {len(found_vaults)} potential Obsidian vaults:[/blue]")
        
        for i, vault in enumerate(found_vaults, 1):
            confidence_icon = "✓" if vault['confidence'] == 'high' else "⚠"
            display_path = self._shorten_path(vault['path'])
            console.print(f"  {i}. {confidence_icon} {display_path}")
            console.print(f"     [dim]Type: {vault['type']}, Files: {vault['md_count']} markdown, Path: {vault['path']}[/dim]")
        
        while True:
            try:
                choice = input(f"\nSelect vault (1-{len(found_vaults)}) or 'm' for manual input: ").strip()
                
                if choice.lower() == 'm':
                    return self._manual_vault_input()
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(found_vaults):
                    selected_vault = found_vaults[choice_num - 1]
                    console.print(f"[green]✓ Selected vault: {selected_vault['path']}[/green]")
                    return selected_vault['path']
                else:
                    console.print(f"[red]Invalid choice. Please enter 1-{len(found_vaults)} or 'm'[/red]")
            except ValueError:
                console.print(f"[red]Invalid input. Please enter 1-{len(found_vaults)} or 'm'[/red]")
    
    def _manual_vault_input(self) -> str:
        """Handle manual vault path input with validation"""
        while True:
            vault_path = input("\nPlease enter your Obsidian vault path: ").strip()
            
            # Expand user path if needed
            if vault_path.startswith('~'):
                vault_path = os.path.expanduser(vault_path)
            
            if os.path.exists(vault_path):
                # Check if it has markdown files or .obsidian folder
                has_md = any(f.endswith('.md') for f in os.listdir(vault_path) if os.path.isfile(os.path.join(vault_path, f)))
                has_obsidian = os.path.exists(os.path.join(vault_path, '.obsidian'))
                
                if has_md or has_obsidian:
                    console.print(f"[green]✓ Valid Obsidian vault: {vault_path}[/green]")
                    return vault_path
                else:
                    console.print(f"[red]❌ Path exists but doesn't appear to be an Obsidian vault[/red]")
                    console.print(f"[yellow]No markdown files or .obsidian folder found in: {vault_path}[/yellow]")
            else:
                console.print(f"[red]❌ Path does not exist: {vault_path}[/red]")
            
            retry = input("Try again? (y/n): ").strip().lower()
            if retry not in ['y', 'yes']:
                raise ValueError("No valid Obsidian vault path provided")
    
    def backup_vault(self, vault_path: str) -> bool:
        """Create a backup of the vault before any operations"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            vault_name = os.path.basename(vault_path)
            backup_filename = f"backup_{vault_name}_{timestamp}"
            backup_path = os.path.join(os.getcwd(), "backups", backup_filename)
            
            # Create backups directory if it doesn't exist
            os.makedirs(os.path.join(os.getcwd(), "backups"), exist_ok=True)
            
            console.print(f"[blue]🔄 Creating backup of vault: {vault_path}[/blue]")
            console.print(f"[dim]Backup location: {backup_path}.zip[/dim]")
            
            # Create zip backup
            shutil.make_archive(backup_path, 'zip', vault_path)
            
            console.print(f"[green]✓ Backup created successfully: {backup_path}.zip[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def create_para_structure(self):
        """Create PARA folder structure"""
        console.print("[blue]Creating PARA folder structure...[/blue]")
        
        for folder_name, description in self.para_folders.items():
            folder_path = os.path.join(self.vault_path, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                console.print(f"[green]Created: {folder_name} ({description})[/green]")
            else:
                console.print(f"[yellow]Exists: {folder_name} ({description})[/yellow]")
    
    def classify_note_with_ai(self, content: str, filename: str) -> str:
        """Classify note using Ollama AI"""
        try:
            prompt = f"""
            Eres un experto en el método de organización PARA de Tiago Forte.
            Tu tarea es analizar el contenido y el título de una nota y clasificarla en una de las siguientes 5 categorías: PROJECTS, AREAS, RESOURCES, ARCHIVE, o INBOX.

            - **PROJECTS:** Tiene un objetivo específico y un final definido. Es accionable.
            - **AREAS:** Es una esfera de responsabilidad sin fecha de fin (ej: 'Salud', 'Finanzas').
            - **RESOURCES:** Es un tema de interés, notas de referencia, o material de soporte.
            - **ARCHIVE:** Es un proyecto o área que ya no está activa o se ha completado.
            - **INBOX:** Úsalo si no puedes determinar la categoría con certeza.

            Analiza la siguiente nota:
            ---
            Título: {filename}
            Contenido: {content[:1000]}...
            ---

            Responde **solamente** con el nombre de la categoría (PROJECTS, AREAS, RESOURCES, ARCHIVE, o INBOX).
            """
            
            response = self.ollama_client.chat(
                model='llama3.2:latest',
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            category = response['message']['content'].strip().upper()
            
            # Validate category
            valid_categories = ['PROJECTS', 'AREAS', 'RESOURCES', 'ARCHIVE', 'INBOX']
            if category not in valid_categories:
                self.debug(f"Invalid AI response '{category}', defaulting to INBOX", "WARN")
                return 'INBOX'
            
            return category
            
        except Exception as e:
            self.debug(f"AI classification error: {e}", "ERROR")
            return 'INBOX'
    
    def organize_notes(self, dry_run: bool = True):
        """Organize notes using PARA methodology with real-time updates"""
        self.stats.reset()
        self.stats.start_time = datetime.now()
        self.stats.status = "running"
        
        # ALWAYS create backup before any operations
        console.print("[yellow]⚠️  IMPORTANT: Creating backup before any operations...[/yellow]")
        if not self.backup_vault(self.vault_path):
            console.print("[red]❌ Backup failed! Aborting operation for safety.[/red]")
            console.print("[yellow]💡 Please ensure you have write permissions and try again.[/yellow]")
            return
        
        console.print("[green]✓ Backup completed successfully. Proceeding with organization...[/green]")
        
        # Create PARA structure
        self.create_para_structure()
        
        # Obtener el recuento de notas por categoría y proyecto, excluyendo el inbox
        # para no duplicar el recuento
        all_notes = get_all_notes(self.vault_path)
        
        # Buscar solo notas en el Inbox
        inbox_folders = ["05-Inbox", "00-Inbox", "Inbox"]
        inbox_notes = [
            note for note in all_notes
            if any(folder in Path(note).parts for folder in inbox_folders)
        ]
        inbox_count = len(inbox_notes)
        
        # Definir carpetas de sistema a excluir del "estado del vault"
        system_folders = [
            "01-Projects", "02-Areas", "03-Resources", "04-Archive", "05-Inbox",
            ".obsidian", "attachments", "images", "assets", "media", "templates",
            "backups", ".para_db", ".git"
        ]
        
        # Calcular notas fuera de la estructura PARA
        other_notes_count = 0
        for note in all_notes:
            if not any(folder in system_folders for folder in Path(note).parts):
                other_notes_count += 1
        
        self.stats.total_notes = len(all_notes)
        total_md_files = len([f for f in os.listdir(self.vault_path) if f.endswith('.md')])
        console.print(f"[blue]Found {self.stats.total_notes} notes in total out of {total_md_files} total markdown files[/blue]")
        
        if not all_notes:
            console.print("[yellow]No notes found to process.[/yellow]")
            return
        
        # Process each file
        for i, file_path in enumerate(all_notes):
            try:
                self.stats.current_note = os.path.basename(file_path)
                self.status_queue.put(self.stats.to_dict())
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Classify with AI
                category = self.classify_note_with_ai(content, os.path.basename(file_path))
                
                # Determine destination folder
                if category == 'PROJECTS':
                    dest_folder = '01-projects'
                    self.stats.projects += 1
                elif category == 'AREAS':
                    dest_folder = '02-areas'
                    self.stats.areas += 1
                elif category == 'RESOURCES':
                    dest_folder = '03-resources'
                    self.stats.resources += 1
                elif category == 'ARCHIVE':
                    dest_folder = '04-archive'
                    self.stats.archive += 1
                else:  # INBOX
                    dest_folder = '00-inbox'
                    self.stats.inbox += 1
                
                # Add to vector database
                self.db.add_note(file_path, content, category.lower())
                
                # Move file (if not dry run)
                if not dry_run:
                    dest_path = os.path.join(self.vault_path, dest_folder, os.path.basename(file_path))
                    if file_path != dest_path:
                        os.rename(file_path, dest_path)
                        console.print(f"[green]Moved: {os.path.basename(file_path)} → {dest_folder}[/green]")
                else:
                    console.print(f"[cyan]Would move: {os.path.basename(file_path)} → {dest_folder}[/cyan]")
                
                self.stats.processed_notes += 1
                
            except Exception as e:
                console.print(f"[red]Error processing {file_path}: {e}[/red]")
                self.stats.errors += 1
                self.stats.processed_notes += 1
        
        self.stats.end_time = datetime.now()
        self.stats.status = "completed"
        self.status_queue.put(self.stats.to_dict())
        
        # Print final statistics
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print final organization statistics"""
        console.print("\n[bold blue]PARA Organization Complete![/bold blue]")
        
        table = Table(title="Organization Results")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_column("Percentage", style="green")
        
        total = self.stats.processed_notes
        if total > 0:
            table.add_row("Projects", str(self.stats.projects), f"{self.stats.projects/total*100:.1f}%")
            table.add_row("Areas", str(self.stats.areas), f"{self.stats.areas/total*100:.1f}%")
            table.add_row("Resources", str(self.stats.resources), f"{self.stats.resources/total*100:.1f}%")
            table.add_row("Archive", str(self.stats.archive), f"{self.stats.archive/total*100:.1f}%")
            table.add_row("Inbox", str(self.stats.inbox), f"{self.stats.inbox/total*100:.1f}%")
            table.add_row("Errors", str(self.stats.errors), f"{self.stats.errors/total*100:.1f}%")
        
        console.print(table)
        
        if self.stats.start_time and self.stats.end_time:
            duration = self.stats.end_time - self.stats.start_time
            console.print(f"[blue]Total time: {duration}[/blue]")

def create_dashboard():
    """Create Gradio dashboard for PARA organization"""
    organizer = PARAOrganizer()
    
    def start_organization(dry_run: bool):
        """Start the organization process"""
        def run_organization():
            organizer.organize_notes(dry_run=dry_run)
        
        # Run in separate thread
        thread = threading.Thread(target=run_organization)
        thread.start()
        
        return "Organization started! Check the console for progress."
    
    def get_stats():
        """Get current statistics"""
        try:
            stats = organizer.stats.to_dict()
            db_stats = organizer.db.get_category_stats()
            return json.dumps({**stats, "db_stats": db_stats}, indent=2)
        except:
            return "{}"
    
    def search_notes(query: str):
        """Search for similar notes"""
        try:
            results = organizer.db.search_similar_notes(query)
            if results and results['metadatas']:
                return json.dumps(results['metadatas'], indent=2)
            return "No results found"
        except:
            return "Search error"
    
    # --- NUEVO: Comandos principales PARA ---
    PARA_COMMANDS = [
        {"name": "Dashboard web", "cmd": "python para_dashboard.py", "desc": "Lanza el dashboard web interactivo."},
        {"name": "Monitor en terminal", "cmd": "python para_cli.py monitor", "desc": "Monitoriza el vault en tiempo real en la terminal."},
        {"name": "Clasificar notas", "cmd": "python para_cli.py classify", "desc": "Clasifica notas de Inbox/Archive usando IA."},
        {"name": "Refactorizar Archive", "cmd": "python para_cli.py refactor", "desc": "Re-evalúa y organiza notas desde Archive."},
        {"name": "Exportar dataset fine-tuning", "cmd": "python para_cli.py export-finetune-dataset", "desc": "Exporta el dataset de feedback para entrenamiento."},
        {"name": "Revisión de feedback", "cmd": "python para_cli.py review-feedback", "desc": "Revisión/corrección masiva de notas clasificadas."},
        {"name": "Ver logs", "cmd": "tail -n 40 logs/para.log", "desc": "Muestra los últimos logs del sistema."},
    ]

    def run_para_command(cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return result.stdout + ("\n" + result.stderr if result.stderr else "")
        except Exception as e:
            return f"Error ejecutando comando: {e}"

    # --- FIN NUEVO ---

    with gr.Blocks(title="PARA Organizer Dashboard", theme=gr.themes.Soft()) as dashboard:
        gr.Markdown("# 🗂️ PARA Organizer Dashboard")
        gr.Markdown("Organize your Obsidian vault using the PARA methodology with AI-powered classification")
        
        with gr.Tabs():
            with gr.Tab("Panel Principal"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 📊 Organization Control")
                        dry_run_checkbox = gr.Checkbox(label="Dry Run (Preview Only)", value=True)
                        start_btn = gr.Button("🚀 Start Organization", variant="primary")
                        status_output = gr.Textbox(label="Status", interactive=False)
                    with gr.Column():
                        gr.Markdown("## 📈 Statistics")
                        stats_output = gr.JSON(label="Current Stats")
                        refresh_stats_btn = gr.Button("🔄 Refresh Stats")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("## 🔍 Note Search")
                        search_query = gr.Textbox(label="Search Query")
                        search_btn = gr.Button("🔍 Search")
                        search_results = gr.JSON(label="Search Results")
                start_btn.click(
                    fn=start_organization,
                    inputs=[dry_run_checkbox],
                    outputs=[status_output]
                )
                refresh_stats_btn.click(
                    fn=get_stats,
                    outputs=[stats_output]
                )
                search_btn.click(
                    fn=search_notes,
                    inputs=[search_query],
                    outputs=[search_results]
                )
                dashboard.load(get_stats, outputs=[stats_output])
            with gr.Tab("Ayuda y Comandos"):
                gr.Markdown("# 🛠️ Comandos principales del sistema PARA")
                with gr.Row():
                    for cmd in PARA_COMMANDS:
                        with gr.Column():
                            gr.Markdown(f"**{cmd['name']}**\n{cmd['desc']}\n`{cmd['cmd']}`")
                            btn = gr.Button(f"Ejecutar {cmd['name']}")
                            output = gr.Textbox(label="Salida", lines=6)
                            btn.click(fn=lambda c=cmd['cmd']: run_para_command(c), outputs=output)
                gr.Markdown("---")
                gr.Markdown("## Terminal web (solo comandos listados)")
                terminal_cmd = gr.Dropdown([c['cmd'] for c in PARA_COMMANDS], label="Comando PARA", value=PARA_COMMANDS[0]['cmd'])
                terminal_btn = gr.Button("Ejecutar comando seleccionado")
                terminal_out = gr.Textbox(label="Salida de terminal", lines=10)
                terminal_btn.click(fn=run_para_command, inputs=terminal_cmd, outputs=terminal_out)
    return dashboard

# Captura global de excepciones no manejadas
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Excepción no capturada", exc_info=(exc_type, exc_value, exc_traceback))
    print(f"[red]Excepción no capturada: {exc_value}[/red]")
sys.excepthook = handle_exception

def main():
    """Main function"""
    console.print("[bold blue]PARA Organizer with Chroma Database[/bold blue]")
    
    # Check if Ollama is running
    try:
        ollama.Client(host='http://localhost:11434').list()
        console.print("[green]✓ Ollama is running[/green]")
    except:
        console.print("[red]✗ Ollama is not running. Please start Ollama first.[/red]")
        console.print("Install: https://ollama.ai")
        console.print("Start: ollama serve")
        return
    
    # Create and launch dashboard
    dashboard = create_dashboard()
    dashboard.launch(share=False, server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    main()
