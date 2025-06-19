#!/usr/bin/env python3
import sys
import os
import argparse
from pathlib import Path
import shutil
from datetime import datetime
import json
import requests

# --- CONFIGURACIÓN DE OLLAMA ---
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"  # Asegúrate de tener este modelo con `ollama pull llama3.2`
OLLAMA_PROMPT_TEMPLATE = """
Eres un experto en el método de organización PARA de Tiago Forte.
Tu tarea es analizar el contenido y el título de una nota y clasificarla en una de las siguientes 5 categorías: Project, Area, Resource, Archive, o Inbox.

- **Project:** Tiene un objetivo específico y un final definido. Es accionable.
- **Area:** Es una esfera de responsabilidad sin fecha de fin (ej: 'Salud', 'Finanzas').
- **Resource:** Es un tema de interés, notas de referencia, o material de soporte.
- **Archive:** Es un proyecto o área que ya no está activa o se ha completado.
- **Inbox:** Úsalo si no puedes determinar la categoría con certeza.

Si clasificas la nota como 'Project', debes derivar un nombre de carpeta corto y descriptivo para el proyecto.

Analiza la siguiente nota:
---
Título: {title}
Contenido:
{content}
---

Responde **solamente** con un objeto JSON válido, sin ninguna otra explicación. El formato debe ser:
{{"category": "...", "project_name": "..."}}

Si la categoría no es 'Project', el valor de "project_name" debe ser null.
"""

# --- FUNCIONES PRINCIPALES ---

def debug(msg, level="INFO"):
    print(f"[{level.upper()}] {msg}", flush=True)

def backup_vault(vault_path, repo_root):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{vault_path.name}_{timestamp}"
    backup_path = repo_root / backup_filename
    
    debug(f"Creando copia de seguridad del vault en '{backup_path}.zip'...")
    try:
        shutil.make_archive(str(backup_path), 'zip', vault_path)
        debug("Copia de seguridad creada con éxito.", "SUCCESS")
        return True
    except Exception as e:
        debug(f"Error al crear la copia de seguridad: {e}", "ERROR")
        return False

def get_ai_classification(note_path):
    debug(f"Clasificando con IA: '{note_path.name}'...", "DETAIL")
    with open(note_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    prompt = OLLAMA_PROMPT_TEMPLATE.format(title=note_path.stem, content=content[:4000]) # Limitar contenido para no exceder
    
    try:
        response = requests.post(
            OLLAMA_ENDPOINT,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=60 # Timeout de 60 segundos
        )
        response.raise_for_status()
        
        # Ollama con format=json ya devuelve un objeto JSON parseado
        response_json = response.json()
        # El contenido real está en la clave 'response' como un string JSON que hay que parsear
        classification_data = json.loads(response_json.get('response', '{}'))

        category = classification_data.get('category', 'inbox').lower()
        project_name = classification_data.get('project_name')

        if category not in ['project', 'area', 'resource', 'archive', 'inbox']:
            debug(f"Categoría inválida '{category}' recibida de la IA. Usando 'inbox'.", "WARN")
            return {'category': 'inbox', 'detail': note_path.name}
        
        detail = project_name if category == 'project' and project_name else note_path.name
        return {'category': category, 'detail': detail}

    except requests.exceptions.Timeout:
        debug(f"Timeout al contactar a Ollama para la nota '{note_path.name}'.", "ERROR")
        return {'category': 'inbox', 'detail': note_path.name}
    except requests.exceptions.RequestException as e:
        debug(f"Error de red al contactar a Ollama: {e}", "ERROR")
        return {'category': 'inbox', 'detail': note_path.name}
    except json.JSONDecodeError:
        debug(f"Respuesta inválida (no es JSON) de Ollama para la nota '{note_path.name}'.", "ERROR")
        debug(f"Respuesta recibida: {response.text}", "DETAIL")
        return {'category': 'inbox', 'detail': note_path.name}


def main():
    global OLLAMA_MODEL
    parser = argparse.ArgumentParser(description="Organiza un vault de Obsidian usando IA local con Ollama.")
    parser.add_argument("vault_path", help="Ruta al vault de Obsidian.")
    parser.add_argument("--execute", action="store_true", help="Ejecuta los cambios. Por defecto es simulación.")
    parser.add_argument("--model", default=OLLAMA_MODEL, help=f"Nombre del modelo de Ollama a usar (por defecto: {OLLAMA_MODEL}).")
    args = parser.parse_args()

    # Actualizar el modelo si se pasa como argumento
    OLLAMA_MODEL = args.model

    vault_path = Path(args.vault_path).resolve()
    repo_root = Path.cwd()

    if not vault_path.is_dir():
        debug(f"La ruta '{vault_path}' no es un directorio válido.", "ERROR")
        sys.exit(1)
        
    if args.execute:
        if not backup_vault(vault_path, repo_root):
            if input("La copia de seguridad falló. ¿Continuar? (s/n): ").lower() != 's':
                sys.exit(1)
    
    debug(f"Iniciando organización para: {vault_path}")
    debug(f"Usando el modelo de Ollama: {OLLAMA_MODEL}", "INFO")
    debug(f"Modo: {'EJECUCIÓN REAL' if args.execute else 'SIMULACIÓN (Dry-Run)'}", "WARN")
    
    para_paths_list = ["01. Projects", "02. Areas", "03. Resources", "04. Archives", "05. Inbox"]
    para_paths = {p.lower().split('. ')[1]: Path(vault_path) / p for p in para_paths_list}
    for path in para_paths.values():
        path.mkdir(exist_ok=True)

    all_md_notes = list(vault_path.rglob("*.md"))
    notes_to_process = [note for note in all_md_notes if not any(p.name in note.parts for p in para_paths.values())]
    debug(f"Se procesarán {len(notes_to_process)} de {len(all_md_notes)} notas .md totales.")

    organization_plan = []
    for note in notes_to_process:
        classification = get_ai_classification(note)
        
        category = classification['category']
        target_folder = para_paths.get(category)
        
        if not target_folder:
            continue
            
        target_path = None
        project_folder = None
        if category == 'project':
            project_folder = target_folder / classification['detail']
            target_path = project_folder / note.name
        else:
            target_path = target_folder / note.name # Mover directamente a Areas, Resources, etc.
        
        organization_plan.append({
            'source': note,
            'target': target_path,
            'project_folder': project_folder,
            'category': category.upper()
        })

    print("\n" + "="*25 + " PLAN DE ORGANIZACIÓN (Generado por IA) " + "="*25)
    if not organization_plan:
        debug("No hay acciones de organización que realizar.")
    
    for plan in organization_plan:
        if plan['category'] == 'PROJECT':
            print(f"\n[PROYECTO]: '{plan['project_folder'].name}'")
            print(f"  └─ MOVER: '{plan['source'].relative_to(vault_path)}' -> '{plan['target'].relative_to(vault_path)}'")
        else:
            print(f"[{plan['category']}]: MOVER '{plan['source'].relative_to(vault_path)}' -> '{plan['target'].relative_to(vault_path)}'")
        
        if args.execute:
            try:
                if plan['project_folder']:
                    plan['project_folder'].mkdir(exist_ok=True)
                shutil.move(str(plan['source']), str(plan['target']))
            except Exception as e:
                debug(f"Error al mover {plan['source'].name}: {e}", "ERROR")

    print("="*80 + "\n")

    if not args.execute:
        debug("Simulación completada. No se ha modificado ningún archivo.", "WARN")
        debug("Para aplicar estos cambios, vuelva a ejecutar el script con el flag --execute", "WARN")
    else:
        debug("¡Organización completada!", "SUCCESS")

if __name__ == "__main__":
    main() 