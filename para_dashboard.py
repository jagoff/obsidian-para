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
    import subprocess
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
            console.print(f"[red]Error adding note to database: {e}[/red]")
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
            console.print(f"[red]Error searching database: {e}[/red]")
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
            console.print(f"[red]Error getting stats: {e}[/red]")
            return {"projects": 0, "areas": 0, "resources": 0, "archive": 0, "inbox": 0}
    
    def _generate_id(self, note_path: str) -> str:
        """Generate unique ID for note"""
        return hashlib.md5(note_path.encode()).hexdigest()

class PARAOrganizer:
    """Enhanced PARA organizer with Chroma database and dashboard"""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or self._detect_vault()
        self.db = ChromaPARADatabase()
        self.stats = PARAStats()
        self.status_queue = queue.Queue()
        self.ollama_client = ollama.Client(host='http://localhost:11434')
        
        # PARA folder structure
        self.para_folders = {
            "01-projects": "Projects",
            "02-areas": "Areas", 
            "03-resources": "Resources",
            "04-archive": "Archive",
            "00-inbox": "Inbox"
        }
    
    def _detect_vault(self) -> str:
        """Detect Obsidian vault automatically"""
        possible_paths = [
            os.path.expanduser("~/Documents/Obsidian"),
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents"),
            os.path.expanduser("~/Dropbox/Obsidian"),
            os.path.expanduser("~/OneDrive/Obsidian")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                # Look for .obsidian folder
                for root, dirs, files in os.walk(path):
                    if ".obsidian" in dirs:
                        console.print(f"[green]Found Obsidian vault: {root}[/green]")
                        return root
        
        # If not found, ask user
        console.print("[yellow]No Obsidian vault detected automatically[/yellow]")
        return input("Please enter your Obsidian vault path: ").strip()
    
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
            Classify this note into one of these PARA categories:
            - PROJECTS: Active projects with deadlines and specific outcomes
            - AREAS: Ongoing responsibilities and life areas
            - RESOURCES: Reference materials, knowledge, and tools
            - ARCHIVE: Completed projects and inactive items
            - INBOX: Unprocessed items that need review

            Note filename: {filename}
            Note content: {content[:500]}...

            Respond with ONLY the category name (PROJECTS, AREAS, RESOURCES, ARCHIVE, or INBOX).
            """
            
            response = self.ollama_client.chat(
                model='llama3.2:3b',
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            category = response['message']['content'].strip().upper()
            
            # Validate category
            valid_categories = ['PROJECTS', 'AREAS', 'RESOURCES', 'ARCHIVE', 'INBOX']
            if category not in valid_categories:
                console.print(f"[yellow]Invalid AI response '{category}', defaulting to INBOX[/yellow]")
                return 'INBOX'
            
            return category
            
        except Exception as e:
            console.print(f"[red]AI classification error: {e}[/red]")
            return 'INBOX'
    
    def organize_notes(self, dry_run: bool = True):
        """Organize notes using PARA methodology with real-time updates"""
        self.stats.reset()
        self.stats.start_time = datetime.now()
        self.stats.status = "running"
        
        # Create PARA structure
        self.create_para_structure()
        
        # Find all markdown files
        markdown_files = []
        for root, dirs, files in os.walk(self.vault_path):
            # Skip PARA folders and system folders
            dirs[:] = [d for d in dirs if not d.startswith(('.', '00-', '01-', '02-', '03-', '04-'))]
            
            for file in files:
                if file.endswith('.md') and not file.startswith('.'):
                    markdown_files.append(os.path.join(root, file))
        
        self.stats.total_notes = len(markdown_files)
        console.print(f"[blue]Found {self.stats.total_notes} markdown files[/blue]")
        
        # Process each file
        for i, file_path in enumerate(markdown_files):
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
    
    # Create Gradio interface
    with gr.Blocks(title="PARA Organizer Dashboard", theme=gr.themes.Soft()) as dashboard:
        gr.Markdown("# 🗂️ PARA Organizer Dashboard")
        gr.Markdown("Organize your Obsidian vault using the PARA methodology with AI-powered classification")
        
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
        
        # Event handlers
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
        
        # Auto-refresh stats every 5 seconds
        dashboard.load(get_stats, outputs=[stats_output])
    
    return dashboard

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
