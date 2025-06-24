"""
paralib/ai_engine.py

Motor AI centralizado para PARA CLI.
Reutiliza y centraliza todas las funciones AI existentes.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import ollama
from rich.console import Console
from rich.prompt import Confirm

from paralib.logger import logger
from paralib.ui import list_ollama_models

console = Console()

@dataclass
class AICommand:
    """Comando interpretado por AI."""
    command: str
    args: List[str]
    confidence: float
    reasoning: str
    original_prompt: str

@dataclass
class IntentExample:
    """Ejemplo de intent para entrenamiento."""
    prompt: str
    command: str
    args: List[str]
    description: str

class AIEngine:
    """Motor AI centralizado para interpretación de prompts y análisis."""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        self.model_name = model_name
        self.intent_examples: List[IntentExample] = []
        self.prompt_history: List[Dict] = []
        
        # Cargar ejemplos de intents predefinidos
        self._load_default_intents()
    
    def _load_default_intents(self):
        """Carga ejemplos de intents predefinidos para mejor interpretación."""
        default_intents = [
            IntentExample(
                prompt="re clasifica todas mis notas",
                command="reclassify-all",
                args=[],
                description="Reclasificar todas las notas del vault"
            ),
            IntentExample(
                prompt="reclasifica todas las notas",
                command="reclassify-all", 
                args=[],
                description="Reclasificar todas las notas del vault"
            ),
            IntentExample(
                prompt="re",
                command="reclassify-all",
                args=[],
                description="Comando corto para reclasificar"
            ),
            IntentExample(
                prompt="clasifica esta nota",
                command="classify",
                args=[""],
                description="Clasificar una nota específica"
            ),
            IntentExample(
                prompt="classify",
                command="classify",
                args=[""],
                description="Comando directo para clasificar"
            ),
            IntentExample(
                prompt="analiza esta nota",
                command="analyze",
                args=[""],
                description="Analizar una nota específica"
            ),
            IntentExample(
                prompt="analyze",
                command="analyze",
                args=[""],
                description="Comando directo para analizar"
            ),
            IntentExample(
                prompt="muéstrame las notas recientes",
                command="obsidian-notes",
                args=["stats"],
                description="Mostrar estadísticas de notas recientes"
            ),
            IntentExample(
                prompt="notes",
                command="obsidian-notes",
                args=["stats"],
                description="Comando corto para notas"
            ),
            IntentExample(
                prompt="muéstrame los plugins de obsidian",
                command="obsidian-plugins",
                args=["list"],
                description="Listar plugins de Obsidian"
            ),
            IntentExample(
                prompt="plugins",
                command="plugins",
                args=[],
                description="Listar plugins del sistema"
            ),
            IntentExample(
                prompt="busca en mis notas",
                command="obsidian-search",
                args=[""],
                description="Buscar en las notas"
            ),
            IntentExample(
                prompt="search",
                command="obsidian-search",
                args=[""],
                description="Comando directo para buscar"
            ),
            IntentExample(
                prompt="crea un backup",
                command="obsidian-backup",
                args=[],
                description="Crear backup del vault"
            ),
            IntentExample(
                prompt="backup",
                command="obsidian-backup",
                args=[],
                description="Comando corto para backup"
            ),
            IntentExample(
                prompt="limpiar vault",
                command="clean",
                args=[],
                description="Limpiar el vault"
            ),
            IntentExample(
                prompt="clean",
                command="clean",
                args=[],
                description="Comando directo para limpiar"
            ),
            IntentExample(
                prompt="aprende de mis clasificaciones",
                command="learn",
                args=["review"],
                description="Revisar y aprender de clasificaciones"
            ),
            IntentExample(
                prompt="learn",
                command="learn",
                args=["review"],
                description="Comando directo para aprender"
            ),
            IntentExample(
                prompt="muéstrame los logs",
                command="logs",
                args=["analyze"],
                description="Analizar logs del sistema"
            ),
            IntentExample(
                prompt="logs",
                command="logs",
                args=["analyze"],
                description="Comando directo para logs"
            ),
            IntentExample(
                prompt="abre el dashboard",
                command="dashboard",
                args=[],
                description="Abrir el dashboard web"
            ),
            IntentExample(
                prompt="dashboard",
                command="dashboard",
                args=[],
                description="Comando directo para dashboard"
            ),
            IntentExample(
                prompt="diagnostica el sistema",
                command="doctor",
                args=[],
                description="Diagnosticar problemas del sistema"
            ),
            IntentExample(
                prompt="doctor",
                command="doctor",
                args=[],
                description="Comando directo para diagnosticar"
            ),
            IntentExample(
                prompt="ayuda",
                command="help",
                args=[],
                description="Mostrar ayuda"
            ),
            IntentExample(
                prompt="help",
                command="help",
                args=[],
                description="Comando directo para ayuda"
            ),
            IntentExample(
                prompt="versión",
                command="version",
                args=[],
                description="Mostrar versión"
            ),
            IntentExample(
                prompt="version",
                command="version",
                args=[],
                description="Comando directo para versión"
            )
        ]
        
        self.intent_examples.extend(default_intents)
    
    def check_model_availability(self) -> bool:
        """Verifica si el modelo AI está disponible."""
        try:
            ollama.show(self.model_name)
            return True
        except Exception as e:
            if "model" in str(e) and "not found" in str(e):
                console.print(f"[bold red]Error: Modelo de IA '{self.model_name}' no encontrado.[/bold red]")
                console.print(f"Por favor, asegúrate de que Ollama esté corriendo y ejecuta: [bold cyan]ollama pull {self.model_name}[/bold cyan]")
            else:
                console.print(f"[bold red]Error al contactar con Ollama: {e}[/bold red]")
            return False
    
    def interpret_prompt(self, user_input: str, available_commands: List[str]) -> Optional[AICommand]:
        """
        Interpreta un prompt en lenguaje natural y lo mapea a un comando CLI.
        """
        if not self.check_model_availability():
            return None
        
        # Detectar prompts muy cortos o incompletos
        if len(user_input.strip()) <= 2:
            return self._handle_short_prompt(user_input, available_commands)
        
        # Primero intentar coincidencia exacta con ejemplos
        for example in self.intent_examples:
            if user_input.lower().strip() == example.prompt.lower().strip():
                return AICommand(
                    command=example.command,
                    args=example.args.copy(),
                    confidence=0.95,
                    reasoning=f"Coincidencia exacta con ejemplo: {example.description}",
                    original_prompt=user_input
                )
        
        # Si no hay coincidencia exacta, usar AI para interpretar
        try:
            # Crear prompt para el modelo
            system_prompt = self._create_interpretation_prompt(available_commands)
            
            user_prompt = f"""
            El usuario escribió: "{user_input}"
            
            Interpreta qué comando de la CLI quiere ejecutar y devuelve un JSON con:
            {{
                "command": "nombre_del_comando",
                "args": ["arg1", "arg2"],
                "confidence": 0.85,
                "reasoning": "explicación de por qué elegiste este comando"
            }}
            
            Comandos disponibles: {', '.join(available_commands)}
            
            Si no estás seguro, usa el comando más apropiado o "help" para mostrar ayuda.
            """
            
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                options={'temperature': 0.1}
            )
            
            content = response['message']['content']
            
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Validar que el comando existe
                if result.get('command') in available_commands:
                    return AICommand(
                        command=result['command'],
                        args=result.get('args', []),
                        confidence=result.get('confidence', 0.5),
                        reasoning=result.get('reasoning', 'Interpretación de AI'),
                        original_prompt=user_input
                    )
                else:
                    # Si el comando no existe, sugerir help
                    return AICommand(
                        command='help',
                        args=[],
                        confidence=0.3,
                        reasoning=f"Comando '{result.get('command')}' no encontrado. Mostrando ayuda.",
                        original_prompt=user_input
                    )
            else:
                # Si no se puede parsear JSON, sugerir help
                return AICommand(
                    command='help',
                    args=[],
                    confidence=0.2,
                    reasoning="No se pudo interpretar el prompt. Mostrando ayuda.",
                    original_prompt=user_input
                )
                
        except Exception as e:
            logger.error(f"Error interpretando prompt: {e}")
            return None
    
    def _handle_short_prompt(self, user_input: str, available_commands: List[str]) -> AICommand:
        """Maneja prompts muy cortos o incompletos."""
        short_input = user_input.lower().strip()
        
        # Mapeo directo para comandos cortos comunes
        short_commands = {
            're': 'reclassify-all',
            'cl': 'classify',
            'an': 'analyze',
            'cl': 'clean',
            'le': 'learn',
            'lo': 'logs',
            'da': 'dashboard',
            'do': 'doctor',
            'pl': 'plugins',
            'he': 'help',
            've': 'version',
            'no': 'obsidian-notes',
            'se': 'obsidian-search',
            'ba': 'obsidian-backup',
            'sy': 'obsidian-sync',
            'va': 'obsidian-vault'
        }
        
        if short_input in short_commands:
            command = short_commands[short_input]
            if command in available_commands:
                return AICommand(
                    command=command,
                    args=[],
                    confidence=0.8,
                    reasoning=f"Comando corto '{short_input}' interpretado como '{command}'",
                    original_prompt=user_input
                )
        
        # Si no se puede mapear, sugerir completar el prompt
        return AICommand(
            command='help',
            args=[],
            confidence=0.1,
            reasoning=f"Prompt muy corto '{short_input}'. Mostrando ayuda para completar el comando.",
            original_prompt=user_input
        )
    
    def _create_interpretation_prompt(self, available_commands: List[str]) -> str:
        """Crea el prompt del sistema para interpretación."""
        return f"""
        Eres un asistente experto en interpretar comandos de la CLI PARA.
        
        Tu tarea es interpretar lo que el usuario quiere hacer y mapearlo al comando CLI correcto.
        
        Comandos disponibles: {', '.join(available_commands)}
        
        Reglas importantes:
        1. Si el usuario quiere clasificar notas, usa "classify" o "reclassify-all"
        2. Si el usuario quiere analizar, usa "analyze"
        3. Si el usuario quiere ver información de Obsidian, usa comandos que empiecen con "obsidian-"
        4. Si el usuario quiere limpiar, usa "clean"
        5. Si el usuario quiere aprender, usa "learn"
        6. Si el usuario quiere ver logs, usa "logs"
        7. Si el usuario quiere abrir el dashboard, usa "dashboard"
        8. Si el usuario quiere diagnosticar, usa "doctor"
        9. Si el usuario quiere ver plugins, usa "plugins"
        10. Si no estás seguro, usa "help"
        
        Siempre devuelve un JSON válido con los campos requeridos.
        """
    
    def robust_json_parse(self, content: str) -> Optional[dict]:
        """
        Extrae y parsea un JSON robustamente desde una respuesta de LLM.
        Tolera bloques de código, texto extra y errores comunes.
        """
        # Quitar bloque de código si existe
        if content.startswith("```json"):
            content = content.strip("`\n ")
            content = content.replace("json", "", 1).strip()
        # Buscar el primer objeto JSON en el texto
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception:
                pass
        # Intentar parsear todo el contenido si parece JSON
        try:
            return json.loads(content)
        except Exception:
            return None
    
    def classify_note_with_llm(self, note_content: str, user_directive: str, system_prompt: str) -> Optional[Dict]:
        """
        Clasifica una nota usando LLM (reutiliza función existente).
        """
        console.print(f"🤖 [dim]Consultando IA ({self.model_name}) para clasificación...[/dim]")
        prompt = f"""High-level directive: \"{user_directive}\"\n\nNote content:\n---\n{note_content[:4000]}"""
        try:
            response = ollama.chat(
                model=self.model_name, 
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt},
                ],
                options={'temperature': 0.0}
            )
            content = response['message']['content']
            result = self.robust_json_parse(content)
            if isinstance(result, dict):
                console.print(f"✅ [dim]IA clasificó como: {result.get('category', 'Unknown')} -> {result.get('folder_name', 'Unknown')}[/dim]")
                logger.debug(f"[LLM] Clasificación exitosa: {result.get('category', 'Unknown')} -> {result.get('folder_name', 'Unknown')}")
            else:
                logger.error(f"[LLM] JSON inválido devuelto por modelo {self.model_name}")
                console.print("[bold red]Error: El LLM no devolvió un JSON válido.[/bold red]")
                return None
            return result
        except Exception as e:
            if "model" in str(e) and "not found" in str(e):
                logger.error(f"[LLM] Modelo no encontrado: {self.model_name}")
                console.print(f"[bold red]Error: Modelo de IA '{self.model_name}' no encontrado. Asegurate de que Ollama esté corriendo y hayas ejecutado 'ollama pull {self.model_name}'.[/bold red]")
            else:
                logger.error(f"[LLM] Error al contactar con Ollama: {e}")
                console.print(f"[bold red]Error al contactar con Ollama: {e}[/bold red]")
            return None
    
    def suggest_autocomplete(self, partial_text: str, context: str = "", max_suggestions: int = 5) -> List[str]:
        """
        Sugiere autocompletado basado en el texto parcial y contexto.
        """
        try:
            prompt = f"""
            El usuario está escribiendo: "{partial_text}"
            Contexto: {context}
            
            Sugiere {max_suggestions} posibles autocompletados para esta frase.
            Devuelve solo una lista de frases, una por línea, sin numeración.
            """
            
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.3}
            )
            
            suggestions = response['message']['content'].strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()][:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error generando sugerencias: {e}")
            return []
    
    def analyze_content(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Analiza contenido usando AI.
        """
        try:
            prompts = {
                "general": "Analiza este contenido y proporciona un resumen de los puntos principales.",
                "sentiment": "Analiza el sentimiento y tono de este contenido.",
                "topics": "Identifica los temas principales de este contenido.",
                "action_items": "Identifica elementos accionables en este contenido."
            }
            
            prompt = prompts.get(analysis_type, prompts["general"])
            full_prompt = f"{prompt}\n\nContenido:\n{content[:2000]}"
            
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': full_prompt}],
                options={'temperature': 0.2}
            )
            
            return {
                "analysis_type": analysis_type,
                "result": response['message']['content'],
                "model": self.model_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analizando contenido: {e}")
            return {"error": str(e)}
    
    def register_intent_example(self, prompt: str, command: str, args: List[str], description: str):
        """Registra un nuevo ejemplo de intent para aprendizaje."""
        example = IntentExample(prompt=prompt, command=command, args=args, description=description)
        self.intent_examples.append(example)
        logger.info(f"Intent example registered: {prompt} -> {command}")
    
    def record_prompt_execution(self, original_prompt: str, interpreted_command: AICommand, success: bool):
        """Registra la ejecución de un prompt para aprendizaje futuro."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "original_prompt": original_prompt,
            "interpreted_command": {
                "command": interpreted_command.command,
                "args": interpreted_command.args,
                "confidence": interpreted_command.confidence,
                "reasoning": interpreted_command.reasoning
            },
            "success": success
        }
        self.prompt_history.append(record)
        logger.info(f"Prompt execution recorded: {original_prompt} -> {interpreted_command.command} (success: {success})")
    
    def get_prompt_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de prompts interpretados."""
        if not self.prompt_history:
            return {"total": 0, "success_rate": 0, "avg_confidence": 0}
        
        total = len(self.prompt_history)
        successful = sum(1 for record in self.prompt_history if record["success"])
        avg_confidence = sum(record["interpreted_command"]["confidence"] for record in self.prompt_history) / total
        
        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total,
            "avg_confidence": avg_confidence
        }
    
    def list_available_models(self) -> list:
        """Devuelve una lista de modelos Ollama locales disponibles (nombre y tamaño)."""
        return list_ollama_models()

# Instancia global del motor AI
ai_engine = AIEngine() 