#!/usr/bin/env python3
"""
PARA System Real-time Monitor
Monitors the PARA organization process and ChromaDB statistics
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Try to import required packages
try:
    import chromadb
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError as e:
    print(f"Installing required packages: {e}")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "chromadb", "rich", "plotly"])
    import chromadb
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    import plotly.graph_objects as go
    import plotly.express as px

console = Console()

class PARAChromaMonitor:
    """Monitor for PARA ChromaDB statistics"""
    
    def __init__(self, db_path: str = "./para_chroma_db"):
        self.db_path = db_path
        self.client = None
        self.collection = None
        self.last_stats = {}
        self.start_time = datetime.now()
        
        # Initialize database connection
        self._init_database()
    
    def _init_database(self):
        """Initialize ChromaDB connection"""
        try:
            if os.path.exists(self.db_path):
                self.client = chromadb.PersistentClient(path=self.db_path)
                self.collection = self.client.get_collection("para_notes")
                console.print(f"[green]Connected to ChromaDB: {self.db_path}[/green]")
            else:
                console.print(f"[yellow]ChromaDB not found at: {self.db_path}[/yellow]")
                console.print("[blue]Run the PARA organizer first to create the database[/blue]")
        except Exception as e:
            console.print(f"[red]Error connecting to ChromaDB: {e}[/red]")
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        if not self.collection:
            return self._get_empty_stats()
        
        try:
            all_data = self.collection.get()
            if not all_data or not all_data["metadatas"]:
                return self._get_empty_stats()
            
            # Basic category counts
            category_counts = {"projects": 0, "areas": 0, "resources": 0, "archive": 0, "inbox": 0}
            total_words = 0
            total_notes = len(all_data["metadatas"])
            notes_with_links = 0
            recent_notes = 0
            
            # Process each note
            for metadata in all_data["metadatas"]:
                category = metadata.get("category", "inbox").lower()
                if category in category_counts:
                    category_counts[category] += 1
                
                total_words += metadata.get("word_count", 0)
                
                if metadata.get("has_links", False):
                    notes_with_links += 1
                
                # Check if note was added in last 24 hours
                added_at = metadata.get("added_at")
                if added_at:
                    try:
                        note_time = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                        if datetime.now() - note_time < timedelta(days=1):
                            recent_notes += 1
                    except:
                        pass
            
            # Calculate averages
            avg_words = total_words / total_notes if total_notes > 0 else 0
            link_percentage = (notes_with_links / total_notes * 100) if total_notes > 0 else 0
            
            return {
                "total_notes": total_notes,
                "total_words": total_words,
                "avg_words_per_note": round(avg_words, 1),
                "notes_with_links": notes_with_links,
                "link_percentage": round(link_percentage, 1),
                "recent_notes_24h": recent_notes,
                "categories": category_counts,
                "database_size_mb": self._get_database_size(),
                "uptime": str(datetime.now() - self.start_time).split('.')[0]
            }
            
        except Exception as e:
            console.print(f"[red]Error getting database stats: {e}[/red]")
            return self._get_empty_stats()
    
    def _get_empty_stats(self) -> Dict:
        """Return empty statistics structure"""
        return {
            "total_notes": 0,
            "total_words": 0,
            "avg_words_per_note": 0,
            "notes_with_links": 0,
            "link_percentage": 0,
            "recent_notes_24h": 0,
            "categories": {"projects": 0, "areas": 0, "resources": 0, "archive": 0, "inbox": 0},
            "database_size_mb": 0,
            "uptime": str(datetime.now() - self.start_time).split('.')[0]
        }
    
    def _get_database_size(self) -> float:
        """Get database size in MB"""
        try:
            if os.path.exists(self.db_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.db_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        total_size += os.path.getsize(filepath)
                return round(total_size / (1024 * 1024), 2)
            return 0
        except:
            return 0
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent note activity"""
        if not self.collection:
            return []
        
        try:
            all_data = self.collection.get()
            if not all_data or not all_data["metadatas"]:
                return []
            
            # Sort by added_at timestamp
            sorted_data = sorted(
                zip(all_data["metadatas"], all_data["documents"]),
                key=lambda x: x[0].get("added_at", ""),
                reverse=True
            )
            
            recent_activity = []
            for metadata, doc in sorted_data[:limit]:
                recent_activity.append({
                    "filename": metadata.get("filename", "Unknown"),
                    "category": metadata.get("category", "Unknown"),
                    "added_at": metadata.get("added_at", "Unknown"),
                    "word_count": metadata.get("word_count", 0),
                    "preview": doc[:100] + "..." if len(doc) > 100 else doc
                })
            
            return recent_activity
            
        except Exception as e:
            console.print(f"[red]Error getting recent activity: {e}[/red]")
            return []
    
    def search_notes(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for notes using vector similarity"""
        if not self.collection:
            return []
        
        try:
            # Simple text search for now (could be enhanced with embeddings)
            all_data = self.collection.get()
            if not all_data or not all_data["metadatas"]:
                return []
            
            results = []
            query_lower = query.lower()
            
            for metadata, doc in zip(all_data["metadatas"], all_data["documents"]):
                filename = metadata.get("filename", "").lower()
                content = doc.lower()
                
                if query_lower in filename or query_lower in content:
                    results.append({
                        "filename": metadata.get("filename", "Unknown"),
                        "category": metadata.get("category", "Unknown"),
                        "word_count": metadata.get("word_count", 0),
                        "preview": doc[:150] + "..." if len(doc) > 150 else doc
                    })
                    
                    if len(results) >= n_results:
                        break
            
            return results
            
        except Exception as e:
            console.print(f"[red]Error searching notes: {e}[/red]")
            return []

def create_stats_table(stats: Dict) -> Table:
    """Create a rich table with PARA statistics"""
    table = Table(title="📊 PARA System Statistics")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta", justify="right")
    table.add_column("Details", style="green")
    
    # Overall stats
    table.add_row("Total Notes", str(stats["total_notes"]), "")
    table.add_row("Total Words", f"{stats['total_words']:,}", "")
    table.add_row("Avg Words/Note", str(stats["avg_words_per_note"]), "")
    table.add_row("Notes with Links", str(stats["notes_with_links"]), f"{stats['link_percentage']}%")
    table.add_row("Recent (24h)", str(stats["recent_notes_24h"]), "")
    table.add_row("Database Size", f"{stats['database_size_mb']} MB", "")
    table.add_row("Uptime", stats["uptime"], "")
    
    return table

def create_category_table(stats: Dict) -> Table:
    """Create a table showing category distribution"""
    table = Table(title="🗂️ Category Distribution")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta", justify="right")
    table.add_column("Percentage", style="green", justify="right")
    
    total = stats["total_notes"]
    if total > 0:
        for category, count in stats["categories"].items():
            percentage = (count / total * 100) if total > 0 else 0
            table.add_row(
                category.title(),
                str(count),
                f"{percentage:.1f}%"
            )
        table.add_row("Total", str(total), "100%")
    else:
        table.add_row("No notes processed yet", "0", "0%")
    
    return table

def create_activity_table(activity: List[Dict]) -> Table:
    """Create a table showing recent activity"""
    table = Table(title="📝 Recent Activity")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("File", style="magenta")
    table.add_column("Category", style="green")
    table.add_column("Words", style="yellow", justify="right")
    
    for item in activity:
        # Format timestamp
        try:
            timestamp = datetime.fromisoformat(item["added_at"].replace('Z', '+00:00'))
            time_str = timestamp.strftime("%H:%M:%S")
        except:
            time_str = "Unknown"
        
        table.add_row(
            time_str,
            item["filename"][:30] + "..." if len(item["filename"]) > 30 else item["filename"],
            item["category"].title(),
            str(item["word_count"])
        )
    
    return table

def create_layout(stats: Dict, activity: List[Dict]) -> Layout:
    """Create a rich layout with all information"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="stats", ratio=1),
        Layout(name="activity", ratio=1)
    )
    
    # Header
    header_text = Text("🗂️ PARA System Monitor", style="bold blue")
    header_text.append(f" | Database: {stats['database_size_mb']} MB | Uptime: {stats['uptime']}", style="dim")
    layout["header"].update(Panel(header_text, title="PARA System Status"))
    
    # Stats section
    stats_table = create_stats_table(stats)
    category_table = create_category_table(stats)
    stats_content = stats_table
    stats_content.add_row()  # Add spacing
    stats_content.add_row()  # Add spacing
    stats_content.extend(category_table)
    layout["stats"].update(Panel(stats_content, title="Statistics"))
    
    # Activity section
    activity_table = create_activity_table(activity)
    layout["activity"].update(Panel(activity_table, title="Recent Activity"))
    
    # Footer
    footer_text = Text("Press Ctrl+C to exit | Auto-refresh every 3 seconds", style="dim")
    layout["footer"].update(Panel(footer_text))
    
    return layout

def main():
    """Main monitoring function"""
    console.print("[bold blue]PARA System Real-time Monitor[/bold blue]")
    console.print("Monitoring ChromaDB statistics and recent activity...\n")
    
    monitor = PARAChromaMonitor()
    
    try:
        with Live(create_layout(monitor.get_database_stats(), monitor.get_recent_activity()), 
                 refresh_per_second=0.33, screen=True) as live:
            while True:
                stats = monitor.get_database_stats()
                activity = monitor.get_recent_activity()
                live.update(create_layout(stats, activity))
                time.sleep(3)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error in monitoring: {e}[/red]")

if __name__ == "__main__":
    main() 