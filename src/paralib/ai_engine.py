"""
paralib/ai_engine.py

Motor AI centralizado para PARA CLI.
Reutiliza y centraliza todas las funciones AI existentes.
Soporta múltiples backends: Ollama (local) y Hugging Face.
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
import difflib
import threading

from paralib.logger import logger
from paralib.ui import list_ollama_models

console = Console()

# Importar configuración de debug
try:
    from .debug_config import should_show
except ImportError:
    # Fallback si no está disponible
    def should_show(feature: str) -> bool:
        return True

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
    
    def __init__(self, model_name: str = "llama3.2:3b", backend: str = "auto"):
        self.model_name = model_name
        self.backend = backend  # "ollama", "huggingface", "auto"
        self.intent_examples: List[IntentExample] = []
        self.prompt_history: List[Dict] = []
        
        # Cargar ejemplos de intents predefinidos
        self._load_default_intents()
        
        # Detectar backend automáticamente si es necesario
        if self.backend == "auto":
            self.backend = self._detect_best_backend()
    
    def _detect_best_backend(self) -> str:
        """Detecta el mejor backend disponible, priorizando Ollama local."""
        # Verificar Ollama primero
        if self._check_ollama_availability():
            logger.info("Backend detectado: Ollama (local)")
            return "ollama"
        
        # Verificar Hugging Face
        if self._check_huggingface_availability():
            logger.info("Backend detectado: Hugging Face")
            return "huggingface"
        
        # Fallback a Ollama
        logger.warning("No se detectó backend específico, usando Ollama por defecto")
        return "ollama"
    
    def _check_ollama_availability(self) -> bool:
        """Verifica si Ollama está disponible."""
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_huggingface_availability(self) -> bool:
        """Verifica si Hugging Face está disponible."""
        try:
            import transformers
            import torch
            return True
        except ImportError:
            return False
    
    def _load_default_intents(self):
        """Carga ejemplos de intents predefinidos para mejor interpretación."""
        default_intents = [
            IntentExample(
                prompt="re clasifica todas mis notas",
                command="organize",
                args=["--execute"],
                description="Reclasificar todas las notas del vault con backup"
            ),
            IntentExample(
                prompt="reclasifica todas las notas",
                command="organize",
                args=["--execute"],
                description="Reclasificar todas las notas del vault con backup"
            ),
            IntentExample(
                prompt="clasifica todas mis notas y haz backup antes",
                command="organize",
                args=["--execute"],
                description="Reclasificar todas las notas y hacer backup antes"
            ),
            IntentExample(
                prompt="clasifica todas mis notas",
                command="organize",
                args=["--execute"],
                description="Reclasificar todas las notas del vault"
            ),
            IntentExample(
                prompt="haz backup",
                command="backup",
                args=[],
                description="Crear backup del vault"
            ),
            IntentExample(
                prompt="crea un backup",
                command="backup",
                args=[],
                description="Crear backup del vault"
            ),
            IntentExample(
                prompt="re",
                command="organize",
                args=["--execute"],
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
                command="status",
                args=[],
                description="Mostrar estadísticas de notas recientes"
            ),
            IntentExample(
                prompt="notes",
                command="status",
                args=[],
                description="Comando corto para notas"
            ),
            IntentExample(
                prompt="muéstrame los plugins de obsidian",
                command="plugins",
                args=[],
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
                command="analyze",
                args=[""],
                description="Buscar en las notas"
            ),
            IntentExample(
                prompt="search",
                command="analyze",
                args=[""],
                description="Comando directo para buscar"
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
                args=[],
                description="Revisar y aprender de clasificaciones"
            ),
            IntentExample(
                prompt="learn",
                command="learn",
                args=[],
                description="Comando directo para aprender"
            ),
            IntentExample(
                prompt="muéstrame los logs",
                command="logs",
                args=[],
                description="Analizar logs del sistema"
            ),
            IntentExample(
                prompt="logs",
                command="logs",
                args=[],
                description="Comando directo para logs"
            ),
            IntentExample(
                prompt="fine-tune",
                command="finetune",
                args=["auto"],
                description="Fine-tuning local y muestra resultados de aprendizaje"
            ),
            IntentExample(
                prompt="finetune",
                command="finetune",
                args=["auto"],
                description="Fine-tuning local y muestra resultados de aprendizaje"
            ),
            IntentExample(
                prompt="entrena el modelo",
                command="finetune",
                args=["auto"],
                description="Fine-tuning local y muestra resultados de aprendizaje"
            ),
            IntentExample(
                prompt="qa",
                command="qa",
                args=[],
                description="Sistema de preguntas y respuestas con múltiples backends"
            ),
            IntentExample(
                prompt="pregunta",
                command="qa",
                args=[],
                description="Sistema de preguntas y respuestas"
            ),
        ]
        
        self.intent_examples.extend(default_intents)
    
    def check_model_availability(self) -> bool:
        """Verifica si el modelo AI está disponible en el backend actual."""
        if self.backend == "ollama":
            return self._check_ollama_model()
        elif self.backend == "huggingface":
            return self._check_huggingface_model()
        else:
            return self._check_ollama_model()  # Fallback
    
    def _check_ollama_model(self) -> bool:
        """Verifica si el modelo Ollama está disponible."""
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
    
    def _check_huggingface_model(self) -> bool:
        """Verifica si el modelo Hugging Face está disponible."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            # Intentar cargar el modelo (esto descargará si no está disponible)
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            return True
        except Exception as e:
            console.print(f"[bold red]Error con modelo Hugging Face '{self.model_name}': {e}[/bold red]")
            return False
    
    def _call_ai_with_timeout(self, system_prompt: str, user_prompt: str, timeout: int = 30) -> Dict:
        """Llama al backend AI correspondiente con timeout."""
        if self.backend == "ollama":
            return self._call_ollama_with_timeout(system_prompt, user_prompt, timeout)
        elif self.backend == "huggingface":
            return self._call_huggingface_with_timeout(system_prompt, user_prompt, timeout)
        else:
            return self._call_ollama_with_timeout(system_prompt, user_prompt, timeout)  # Fallback
    
    def _call_ollama_with_timeout(self, system_prompt, user_prompt, timeout=30):
        """Llama a ollama.chat con timeout explícito."""
        result = {}
        def target():
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ],
                    options={'temperature': 0.1}
                )
                result['response'] = response
            except Exception as e:
                result['error'] = str(e)
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return {'error': f"Timeout: la IA no respondió en {timeout} segundos"}
        return result.get('response', result)
    
    def _call_huggingface_with_timeout(self, system_prompt: str, user_prompt: str, timeout: int = 30) -> Dict:
        """Llama a Hugging Face con timeout."""
        result = {}
        def target():
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch
                
                # Cargar modelo y tokenizer
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForCausalLM.from_pretrained(self.model_name)
                
                # Preparar prompt
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                # Tokenizar
                inputs = tokenizer(full_prompt, return_tensors="pt", max_length=512, truncation=True)
                
                # Generar respuesta
                with torch.no_grad():
                    outputs = model.generate(
                        inputs["input_ids"],
                        max_length=inputs["input_ids"].shape[1] + 200,
                        temperature=0.1,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                
                # Decodificar respuesta
                response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                response_text = response_text[len(full_prompt):].strip()
                
                result['response'] = {
                    'message': {
                        'content': response_text
                    }
                }
            except Exception as e:
                result['error'] = str(e)
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return {'error': f"Timeout: Hugging Face no respondió en {timeout} segundos"}
        return result.get('response', result)
    
    def qa_system(self, question: str, context: str = "") -> Dict[str, Any]:
        """
        Sistema de preguntas y respuestas que intenta múltiples backends.
        Prioriza Ollama local, luego Hugging Face.
        """
        logger.info(f"Iniciando QA system con pregunta: {question[:50]}...")
        
        # Intentar con Ollama primero (local)
        if self._check_ollama_availability():
            try:
                logger.info("Intentando QA con Ollama (local)...")
                ollama_result = self._qa_with_ollama(question, context)
                if ollama_result and not ollama_result.get('error'):
                    return {
                        'answer': ollama_result.get('answer', ''),
                        'backend': 'ollama',
                        'model': self.model_name,
                        'confidence': ollama_result.get('confidence', 0.8),
                        'source': 'local'
                    }
            except Exception as e:
                logger.warning(f"Error con Ollama QA: {e}")
        
        # Fallback a Hugging Face
        if self._check_huggingface_availability():
            try:
                logger.info("Intentando QA con Hugging Face...")
                hf_result = self._qa_with_huggingface(question, context)
                if hf_result and not hf_result.get('error'):
                    return {
                        'answer': hf_result.get('answer', ''),
                        'backend': 'huggingface',
                        'model': self.model_name,
                        'confidence': hf_result.get('confidence', 0.7),
                        'source': 'cloud'
                    }
            except Exception as e:
                logger.warning(f"Error con Hugging Face QA: {e}")
        
        # Si ambos fallan
        return {
            'answer': 'Lo siento, no pude procesar tu pregunta. Verifica que Ollama esté corriendo o que tengas acceso a Hugging Face.',
            'backend': 'none',
            'model': 'none',
            'confidence': 0.0,
            'source': 'none',
            'error': 'No se pudo conectar con ningún backend AI'
        }
    
    def _qa_with_ollama(self, question: str, context: str = "") -> Dict[str, Any]:
        """QA específico para Ollama."""
        system_prompt = """Eres un asistente experto en el sistema PARA (Projects, Areas, Resources, Archive) para organización de notas en Obsidian. 
        Responde de manera clara, concisa y útil. Si no estás seguro de algo, indícalo."""
        
        user_prompt = f"Contexto: {context}\n\nPregunta: {question}"
        
        result = self._call_ollama_with_timeout(system_prompt, user_prompt, timeout=45)
        
        if 'error' in result:
            return {'error': result['error']}
        
        return {
            'answer': result['message']['content'],
            'confidence': 0.8
        }
    
    def _qa_with_huggingface(self, question: str, context: str = "") -> Dict[str, Any]:
        """QA específico para Hugging Face."""
        system_prompt = """Eres un asistente experto en el sistema PARA (Projects, Areas, Resources, Archive) para organización de notas en Obsidian. 
        Responde de manera clara, concisa y útil."""
        
        user_prompt = f"Contexto: {context}\n\nPregunta: {question}"
        
        result = self._call_huggingface_with_timeout(system_prompt, user_prompt, timeout=45)
        
        if 'error' in result:
            return {'error': result['error']}
        
        return {
            'answer': result['message']['content'],
            'confidence': 0.7
        }
    
    def interpret_prompt(self, user_input: str, available_commands: List[str]) -> Optional[AICommand]:
        """
        Interpreta un prompt en lenguaje natural y lo mapea a un comando CLI.
        Usa múltiples backends AI con fallback automático.
        """
        if not self.check_model_availability():
            return None
        
        # Detectar prompts muy cortos o incompletos
        if len(user_input.strip()) <= 2:
            return self._handle_short_prompt(user_input, available_commands)
        
        # 1. Coincidencia exacta con ejemplos
        for example in self.intent_examples:
            if user_input.lower().strip() == example.prompt.lower().strip():
                return AICommand(
                    command=example.command,
                    args=example.args.copy(),
                    confidence=0.98,
                    reasoning=f"Coincidencia exacta con ejemplo: {example.description}",
                    original_prompt=user_input
                )
        
        # 1.5. Detección dinámica de exclusión de carpetas (mejorada para comillas y espacios)
        exclude_patterns = [
            r"excepto la carpeta ['\"]?([\w\-\s]+)['\"]?",
            r"sin la carpeta ['\"]?([\w\-\s]+)['\"]?",
            r"excluyendo ['\"]?([\w\-\s]+)['\"]?",
            r"except ['\"]?([\w\-\s]+)['\"]?",
            r"sin ['\"]?([\w\-\s]+)['\"]?",
            r"excluir ['\"]?([\w\-\s]+)['\"]?",
            r"excepto ['\"]?([\w\-\s]+)['\"]?",
            r"sin ['\"]?([\w\-\s]+)['\"]?"
        ]
        exclude_args = []
        for pat in exclude_patterns:
            matches = re.findall(pat, user_input, re.IGNORECASE)
            for m in matches:
                folder = m.strip(' "\'')
                if folder:
                    exclude_args.extend(["--exclude", folder])
        # Si detecta exclusión y el prompt pide reclasificar todas las notas
        if ("reclasifica" in user_input.lower() or "clasifica" in user_input.lower()) and ("todas mis notas" in user_input.lower() or "todas las notas" in user_input.lower()):
            base_args = ["--execute"]
            if "backup" in user_input.lower():
                base_args.append("--backup")
            args = base_args + exclude_args
            return AICommand(
                command="reclassify-all",
                args=args,
                confidence=0.92,
                reasoning=f"Interpretación dinámica: reclasificar todas las notas excluyendo carpetas detectadas: {exclude_args}",
                original_prompt=user_input
            )
        
        # 2. Coincidencia parcial/fuzzy con ejemplos
        prompts = [ex.prompt for ex in self.intent_examples]
        close_matches = difflib.get_close_matches(user_input.lower().strip(), prompts, n=1, cutoff=0.7)
        if close_matches:
            for example in self.intent_examples:
                if close_matches[0] == example.prompt:
                    return AICommand(
                        command=example.command,
                        args=example.args.copy(),
                        confidence=0.85,
                        reasoning=f"Coincidencia parcial/fuzzy con ejemplo: {example.description}",
                        original_prompt=user_input
                    )
        
        # 3. Usar AI para interpretar, con reintentos y fallback entre backends
        import time
        max_attempts = 3
        
        # Intentar con el backend actual primero
        for attempt in range(max_attempts):
            try:
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
                
                ai_result = self._call_ai_with_timeout(system_prompt, user_prompt, timeout=30)
                if 'error' in ai_result:
                    logger.error(f"[LLM] {ai_result['error']}")
                    # Intentar con otro backend si es posible
                    if self.backend == "ollama" and self._check_huggingface_availability():
                        logger.info("Fallback a Hugging Face...")
                        self.backend = "huggingface"
                        continue
                    elif self.backend == "huggingface" and self._check_ollama_availability():
                        logger.info("Fallback a Ollama...")
                        self.backend = "ollama"
                        continue
                    
                    # Aprendizaje automático: registrar timeout/error
                    try:
                        from paralib.learning_system import PARA_Learning_System
                        PARA_Learning_System().record_command_execution(
                            command="interpret_prompt",
                            args=[user_input],
                            success=False,
                            confidence=0.0,
                            reasoning=f"Error/timeout IA: {ai_result['error']}",
                            error=ai_result['error']
                        )
                    except Exception as learn_error:
                        logger.warning(f"[LLM] Error registrando aprendizaje de timeout: {learn_error}")
                    continue
                
                response = ai_result
                content = response['message']['content']
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    if result.get('command') in available_commands:
                        return AICommand(
                            command=result['command'],
                            args=result.get('args', []),
                            confidence=result.get('confidence', 0.5),
                            reasoning=result.get('reasoning', 'Interpretación de AI'),
                            original_prompt=user_input
                        )
                    else:
                        return AICommand(
                            command='help',
                            args=[],
                            confidence=0.3,
                            reasoning=f"Comando '{result.get('command')}' no encontrado. Mostrando ayuda.",
                            original_prompt=user_input
                        )
                else:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"[LLM] Error interpretando prompt: {e}")
                # Aprendizaje automático: registrar error
                try:
                    from paralib.learning_system import PARA_Learning_System
                    PARA_Learning_System().record_command_execution(
                        command="interpret_prompt",
                        args=[user_input],
                        success=False,
                        confidence=0.0,
                        reasoning=f"Error IA: {e}",
                        error=str(e)
                    )
                except Exception as learn_error:
                    logger.warning(f"[LLM] Error registrando aprendizaje de error: {learn_error}")
                continue
        
        # 4. Si todo falla, sugerir ayuda y registrar el fallo
        logger.error(f"No se pudo interpretar el prompt: {user_input}")
        self.record_prompt_execution(user_input, AICommand(command='help', args=[], confidence=0.0, reasoning='Fallo total de interpretación', original_prompt=user_input), False)
        return AICommand(
            command='help',
            args=[],
            confidence=0.0,
            reasoning="No se pudo interpretar el prompt tras varios intentos. Mostrando ayuda.",
            original_prompt=user_input
        )
    
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
        Clasifica una nota usando LLM con múltiples backends y fallback automático.
        """
        # Si el modelo es 'default' o no existe, usar el más robusto disponible
        if self.model_name == 'default' or not self.model_name:
            if self.backend == "ollama":
                available_models = self.list_available_models()
                if available_models:
                    def model_score(m):
                        name = m['name']
                        size = m['size']
                        score = 0
                        if 'llama3' in name: score += 100
                        if 'mistral' in name: score += 80
                        if 'mixtral' in name: score += 70
                        if 'dolphin' in name: score += 60
                        if 'yi' in name: score += 50
                        try:
                            sz = float(size.replace('B','').replace('GB','').replace('MB',''))
                            if 'G' in size: sz *= 1000
                            score += sz
                        except: pass
                        return -score
                    sorted_models = sorted(available_models, key=model_score)
                    self.model_name = sorted_models[0]['name']
                    console.print(f"[yellow]⚠️ Usando modelo Ollama más robusto disponible: {self.model_name}[/yellow]")
                else:
                    console.print("[red]❌ No hay modelos robustos disponibles en Ollama. Intentando con Hugging Face...[/red]")
                    self.backend = "huggingface"
                    self.model_name = "microsoft/DialoGPT-medium"  # Modelo por defecto para HF
            elif self.backend == "huggingface":
                self.model_name = "microsoft/DialoGPT-medium"
        
        if should_show('show_ai_responses'):
            console.print(f"🤖 [dim]Consultando IA ({self.backend}: {self.model_name}) para clasificación...[/dim]")
        
        base_prompt = f"""High-level directive: \"{user_directive}\"\n\nNote content:\n---\n{note_content[:4000]}\n\nResponde SOLO con un JSON válido, sin texto adicional, sin explicaciones, sin bloques de código. Ejemplo:\n{{\"category\": \"Projects\", \"folder_name\": \"Mi Proyecto\"}}"""
        strict_prompt = base_prompt + "\n\nIMPORTANTE: Si no puedes clasificar, responde {\"category\": \"Unknown\", \"folder_name\": \"Unknown\"}"
        attempts = [strict_prompt, strict_prompt + "\n\nNO INCLUYAS NINGÚN TEXTO FUERA DEL JSON."]
        
        # Intentar con el backend actual
        for prompt in attempts:
            try:
                ai_result = self._call_ai_with_timeout(system_prompt, prompt, timeout=45)
                if 'error' in ai_result:
                    logger.error(f"[LLM] Error con {self.backend}: {ai_result['error']}")
                    # Intentar fallback a otro backend
                    if self.backend == "ollama" and self._check_huggingface_availability():
                        logger.info("Fallback a Hugging Face para clasificación...")
                        self.backend = "huggingface"
                        self.model_name = "microsoft/DialoGPT-medium"
                        continue
                    elif self.backend == "huggingface" and self._check_ollama_availability():
                        logger.info("Fallback a Ollama para clasificación...")
                        self.backend = "ollama"
                        # Usar el modelo más robusto disponible
                        available_models = self.list_available_models()
                        if available_models:
                            self.model_name = available_models[0]['name']
                        continue
                    else:
                        break
                
                content = ai_result['message']['content']
                result = self.robust_json_parse(content)
                if isinstance(result, dict):
                    if should_show('show_ai_responses'):
                        console.print(f"✅ [dim]IA ({self.backend}) clasificó como: {result.get('category', 'Unknown')} -> {result.get('folder_name', 'Unknown')}[/dim]")
                    logger.debug(f"[LLM] Clasificación exitosa con {self.backend}: {result.get('category', 'Unknown')} -> {result.get('folder_name', 'Unknown')}")
                    return result
                else:
                    logger.error(f"[LLM] JSON inválido devuelto por {self.backend} ({self.model_name})")
                    if should_show('show_ai_responses'):
                        console.print(f"[bold red]Error: El LLM ({self.backend}) no devolvió un JSON válido. Reintentando...[/bold red]")
            except Exception as e:
                logger.error(f"[LLM] Error con {self.backend}: {e}")
                console.print(f"[bold red]Error con {self.backend}: {e}[/bold red]")
        
        # Si todo falla, sugerir al usuario
        if self.backend == "ollama":
            console.print(f"[red]❌ Ningún modelo devolvió JSON válido. Verifica que Ollama esté corriendo o instala un modelo robusto.[/red]")
        elif self.backend == "huggingface":
            console.print(f"[red]❌ Error con Hugging Face. Verifica la conexión a internet o instala las dependencias necesarias.[/red]")
        
        logger.error(f"[LLM] Todos los intentos de clasificación fallaron con {self.backend}. Usando solo ChromaDB.")
        return None
    
    def suggest_autocomplete(self, partial_text: str, context: str = "", max_suggestions: int = 5) -> List[str]:
        """
        Sugiere autocompletado basado en el texto parcial y contexto.
        Usa múltiples backends AI con fallback automático.
        """
        try:
            prompt = f"""
            El usuario está escribiendo: "{partial_text}"
            Contexto: {context}
            
            Sugiere {max_suggestions} posibles autocompletados para esta frase.
            Devuelve solo una lista de frases, una por línea, sin numeración.
            """
            
            ai_result = self._call_ai_with_timeout("", prompt, timeout=30)
            if 'error' in ai_result:
                logger.error(f"Error generando sugerencias con {self.backend}: {ai_result['error']}")
                return []
            
            suggestions = ai_result['message']['content'].strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()][:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error generando sugerencias: {e}")
            return []
    
    def analyze_content(self, content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Analiza contenido usando AI con múltiples backends.
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
            
            ai_result = self._call_ai_with_timeout("", full_prompt, timeout=45)
            if 'error' in ai_result:
                logger.error(f"Error analizando contenido con {self.backend}: {ai_result['error']}")
                return {"error": ai_result['error']}
            
            return {
                "analysis_type": analysis_type,
                "result": ai_result['message']['content'],
                "model": self.model_name,
                "backend": self.backend,
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

    def is_available(self) -> bool:
        """Verifica si el motor de IA está disponible."""
        return self.check_model_availability()
    
    def classify_note(self, content: str, note_path: str, existing_folders: list = None, vault_path = None) -> Optional[Dict]:
        """
        Clasifica una nota usando el motor de IA con contexto de carpetas existentes.
        
        Args:
            content: Contenido de la nota
            note_path: Ruta de la nota
            existing_folders: Lista de carpetas existentes en el vault
            vault_path: Path del vault para detectar carpetas existentes
        
        Returns:
            Resultado de clasificación o None si falla
        """
        try:
            # Detectar carpetas existentes si no se proporcionan
            if existing_folders is None and vault_path:
                existing_folders = self._detect_existing_folders(vault_path)
            
            if not existing_folders:
                existing_folders = []
            
            # Extraer tags del contenido para análisis
            import re
            content_tags = re.findall(r'#([a-zA-Z0-9_\-]+)', content)
            
            # NUEVO: Analizar tags dominantes
            tags_analysis_text = ""
            if content_tags and vault_path:
                try:
                    # Usar TagAnalyzer singleton si ya existe en la base de datos
                    if hasattr(self, '_tag_analyzer_cache') and vault_path in self._tag_analyzer_cache:
                        tag_analyzer = self._tag_analyzer_cache[vault_path]
                    else:
                        # Crear nuevo analizador solo si no existe
                        if not hasattr(self, '_tag_analyzer_cache'):
                            self._tag_analyzer_cache = {}
                        
                        tag_analyzer = TagAnalyzer(vault_path)
                        # Solo analizar una vez
                        if not hasattr(tag_analyzer, '_analyzed'):
                            tag_analyzer.analyze_vault_tags()
                            tag_analyzer._analyzed = True
                        
                        self._tag_analyzer_cache[vault_path] = tag_analyzer
                    
                    # Buscar carpetas dominantes para estos tags
                    tag_recommendations = []
                    for tag in content_tags[:5]:  # Analizar top 5 tags
                        if tag in tag_analyzer.tag_folders:
                            folder_dist = tag_analyzer.tag_folders[tag]
                            dominant = max(folder_dist, key=folder_dist.get)
                            dominance = folder_dist[dominant] / sum(folder_dist.values())
                            if dominance > 0.7:
                                tag_recommendations.append(f"#{tag} → {dominant} ({dominance:.0%})")
                    
                    if tag_recommendations:
                        tags_analysis_text = f"""
ANÁLISIS DE TAGS DETECTADOS:
{chr(10).join(tag_recommendations)}

REGLA: Si un tag tiene >70% dominancia en una carpeta, USAR esa carpeta."""
                except Exception as e:
                    logger.debug(f"No se pudo analizar tags: {e}")
            
            # SYSTEM PROMPT CON CONTEXTO DE CARPETAS EXISTENTES
            existing_folders_text = ""
            if existing_folders:
                existing_folders_text = f"""
CARPETAS EXISTENTES EN EL VAULT:
{chr(10).join([f"- {folder}" for folder in existing_folders[:20]])}

REGLA CRÍTICA: USAR carpetas existentes cuando sea posible. NO crear carpetas nuevas si existe una similar."""
            
            system_prompt = f"""REGLA ABSOLUTA: DISTRIBUCIÓN REALISTA. USAR CARPETAS EXISTENTES. AGRUPAR contenido similar.

CATEGORÍAS CON EJEMPLOS ESPECÍFICOS:

📁 **PROJECTS** (objetivo 15-30%): Deadline específico + outcome definido + urgencia
EJEMPLOS CORRECTOS:
- "URGENTE: Implementar OAuth antes del viernes" → Projects
- "Lanzar campaña marketing para Q4 2024" → Projects  
- "Migrar base de datos antes del 15/12" → Projects
- "Completar MVP para demo cliente" → Projects
MAL CLASIFICADOS (evitar): Reuniones semanales, procesos continuos, documentación

📋 **AREAS** (objetivo 20-35%): Responsabilidades continuas (PRIORIDAD ALTA)
EJEMPLOS CORRECTOS:
- "Reuniones semanales del equipo" → Areas
- "Gestión finanzas personales" → Areas
- "Coaching y desarrollo personal" → Areas
- "Mantenimiento sistema" → Areas
- "Planificación mensual" → Areas
- "Rutinas de ejercicio" → Areas
MAL CLASIFICADOS (evitar): Tutoriales, deadlines urgentes, documentación

📚 **RESOURCES** (objetivo 25-40%): Documentación pura, tutoriales, referencias
EJEMPLOS CORRECTOS:
- "Tutorial: Configurar Docker" → Resources
- "Manual instalación MySQL" → Resources
- "Comandos útiles Git" → Resources
- "Documentación API REST" → Resources
- "Lista enlaces útiles" → Resources
MAL CLASIFICADOS (evitar): Procesos continuos, deadlines, reuniones

🗄️ **ARCHIVE** (objetivo 10-25%): Explícitamente completado/terminado
EJEMPLOS CORRECTOS:
- "Proyecto Website - COMPLETADO" → Archive
- "Notas 2021 - obsoletas" → Archive
- "Proceso anterior - deprecated" → Archive
MAL CLASIFICADOS (evitar): Contenido activo, procesos continuos

{existing_folders_text}

{tags_analysis_text}

REGLAS DE DECISIÓN MEJORADAS:
1. ¿Tiene DEADLINE urgente + outcome específico? → PROJECTS
2. ¿Es gestión/rutina/proceso continuo/reunión? → AREAS (PRIORIZAR)
3. ¿Es documentación/tutorial/referencia pura? → RESOURCES
4. ¿Dice explícitamente "completado/terminado"? → ARCHIVE
5. ¿En duda entre Projects/Areas? → AREAS (mejor distribución)

AGRUPACIÓN TEMÁTICA INTELIGENTE:
- Marketing (campañas, contenido, analytics, estrategias)
- Desarrollo (código, APIs, bugs, MVP, implementación)
- Finanzas (presupuesto, gastos, ROI, facturación)
- Salud Personal (ejercicio, nutrición, rutinas)
- Gestión Equipos (reuniones, procesos, onboarding)
- Tutoriales Técnicos (guías, manuales, comandos)

Responde: {{"category": "Projects|Areas|Resources|Archive", "folder_name": "Usar_carpeta_existente_o_nombre_agrupador"}}"""
            
            result = self.classify_note_with_llm(content, "", system_prompt)
            
            if result:
                # Normalizar resultado y agregar información de urgencia
                category = result.get('category', 'Unknown')
                folder_name = result.get('folder_name', 'General')
                
                # VALIDACIÓN: Forzar categorías PARA válidas
                valid_categories = ['Projects', 'Areas', 'Resources', 'Archive']
                if category not in valid_categories:
                    # Si devolvió una carpeta como categoría, inferir la categoría correcta
                    if 'finanzas' in category.lower() or 'marketing' in category.lower() or 'salud' in category.lower() or 'gestión' in category.lower():
                        category = 'Areas'
                    elif 'tutorial' in category.lower() or 'documentación' in category.lower():
                        category = 'Resources'
                    elif 'completado' in category.lower() or 'terminado' in category.lower():
                        category = 'Archive'
                    else:
                        category = 'Projects'  # Default fallback
                
                # Calcular score de urgencia para validación
                urgency_keywords = [
                    'urgent', 'urgente', 'critical', 'deadline', 'immediately', 'asap', 
                    'emergency', 'priority', 'prioridad', 'importante', 'importante'
                ]
                
                content_lower = content.lower()
                urgency_signals = sum(1 for keyword in urgency_keywords if keyword in content_lower)
                urgency_score = min(1.0, urgency_signals / 3.0)  # Normalizar a 0-1
                
                # Validar coherencia con Factor 16
                if urgency_score > 0.6 and category == 'Archive':
                    # Corrección: Archive con alta urgencia → Projects
                    category = 'Projects'
                    reasoning = f"Corregido por Factor 16: Alta urgencia ({urgency_score:.2f}) incompatible con Archive"
                elif urgency_score == 0 and category == 'Projects' and 'completado' in content_lower:
                    # Corrección: Proyecto completado sin urgencia → Archive
                    category = 'Archive'
                    reasoning = f"Corregido por Factor 16: Sin urgencia + completado = Archive"
                else:
                    reasoning = f"Clasificación con Factor 16: Urgencia {urgency_score:.2f}"
                
                # POST-PROCESAMIENTO: Forzar agrupación inteligente
                final_folder_name = self._force_intelligent_grouping(folder_name, content, existing_folders)
                
                return {
                    'category': category,
                    'folder_name': final_folder_name,
                    'confidence': min(0.95, 0.7 + (urgency_score * 0.25)),  # Boost confianza con urgencia
                    'reasoning': reasoning,
                    'urgency_score': urgency_score,
                    'original_folder_name': folder_name,  # Guardar nombre original del AI
                    'grouping_applied': final_folder_name != folder_name
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error clasificando nota: {e}")
            return None
    
    def _detect_existing_folders(self, vault_path) -> list:
        """Detecta carpetas existentes en el vault para agrupación inteligente."""
        from pathlib import Path
        
        existing_folders = []
        try:
            vault_path = Path(vault_path)
            
            # Buscar en las carpetas PARA principales
            para_folders = [
                vault_path / "01-Projects",
                vault_path / "02-Areas", 
                vault_path / "03-Resources",
                vault_path / "04-Archive"
            ]
            
            for para_folder in para_folders:
                if para_folder.exists():
                    # Obtener subcarpetas (proyectos/áreas específicas)
                    for subfolder in para_folder.iterdir():
                        if subfolder.is_dir() and not subfolder.name.startswith('.'):
                            # Filtrar carpetas del sistema
                            if subfolder.name not in ['.git', '.obsidian', '.para_db', '__pycache__', 'node_modules']:
                                existing_folders.append(subfolder.name)
            
            # Eliminar duplicados y ordenar
            existing_folders = sorted(list(set(existing_folders)))
            logger.debug(f"Carpetas existentes detectadas: {existing_folders}")
            
        except Exception as e:
            logger.error(f"Error detectando carpetas existentes: {e}")
            
        return existing_folders
    
    def _force_intelligent_grouping(self, folder_name: str, content: str, existing_folders: list) -> str:
        """Fuerza agrupación inteligente usando carpetas existentes y reglas temáticas."""
        if not existing_folders:
            existing_folders = []
        
        content_lower = content.lower()
        folder_lower = folder_name.lower()
        
        # PASO 1: Buscar carpetas existentes similares (fuzzy matching)
        for existing in existing_folders:
            existing_lower = existing.lower()
            
            # Matching directo por palabras clave
            if self._folders_are_similar(folder_lower, existing_lower, content_lower):
                logger.debug(f"Agrupación inteligente: '{folder_name}' → '{existing}' (carpeta existente)")
                return existing
        
        # PASO 2: Aplicar reglas de agrupación temática forzada
        forced_grouping = self._apply_forced_grouping_rules(content_lower, folder_lower)
        if forced_grouping:
            # Verificar si existe la carpeta forzada
            for existing in existing_folders:
                if existing.lower() == forced_grouping.lower():
                    logger.debug(f"Agrupación forzada: '{folder_name}' → '{existing}' (regla temática)")
                    return existing
            
            # Si no existe, usar el nombre forzado
            logger.debug(f"Agrupación forzada: '{folder_name}' → '{forced_grouping}' (nueva carpeta temática)")
            return forced_grouping
        
        # PASO 3: Aplicar consolidación por patrones
        consolidated = self._consolidate_by_patterns(folder_name, existing_folders)
        if consolidated:
            logger.debug(f"Consolidación: '{folder_name}' → '{consolidated}'")
            return consolidated
        
        # PASO 4: Si todo falla, usar el nombre original
        return folder_name
    
    def _folders_are_similar(self, folder1: str, folder2: str, content: str) -> bool:
        """Determina si dos carpetas son similares y deberían agruparse."""
        import difflib
        
        # 1. Matching de palabras clave exactas
        folder1_words = set(folder1.split())
        folder2_words = set(folder2.split())
        
        # Si comparten palabras significativas
        common_words = folder1_words.intersection(folder2_words)
        significant_words = {w for w in common_words if len(w) > 3}
        if significant_words:
            return True
        
        # 2. Similarity ratio alto
        similarity = difflib.SequenceMatcher(None, folder1, folder2).ratio()
        if similarity > 0.6:
            return True
        
        # 3. Misma temática basada en contenido
        if self._same_theme_by_content(folder1, folder2, content):
            return True
        
        return False
    
    def _apply_forced_grouping_rules(self, content: str, folder_name: str) -> str:
        """Aplica reglas de agrupación forzada por tema."""
        
        # Reglas temáticas para agrupación de carpetas (sin duplicados)
        theme_rules = {
            'Marketing': [
                'marketing', 'campaña', 'estrategia', 'plan', 'analisis', 'metricas', 
                'contenido', 'publicidad', 'promocion', 'branding', 'seo'
            ],
            'Desarrollo': [
                'desarrollo', 'implementar', 'refactorizar', 'bug fixes', 'code review', 
                'desarrollar', 'crear', 'planificacion', 'mvp', 'api', 'sistema'
            ],
            'Finanzas': [
                'finanzas', 'proceso', 'revision', 'presupuesto', 'facturacion', 'gestion', 
                'control', 'analisis', 'seguimiento', 'administracion', 'roi', 'gastos'
            ],
            'Salud Personal': [
                'salud', 'rutina', 'plan', 'registro', 'seguimiento', 'proceso', 'gestion',
                'control', 'habito', 'practica', 'mantenimiento', 'ejercicio', 'nutricion'
            ],
            'Gestión Equipos': [
                'reunion', 'meeting', 'proceso', 'onboarding', 'gestion', 'planning',
                'workflow', 'administracion', 'coordinacion', 'supervision', 'equipo'
            ],
            'Tutoriales Técnicos': [
                'tutorial', 'guide', 'howto', 'manual', 'curso', 'aprender',
                'reference', 'comandos', 'plantillas', 'lista', 'articulos', 'tips'
            ],
            'Documentación': [
                'documentacion', 'reference', 'guia', 'base conocimiento',
                'notas', 'apuntes', 'referencias', 'enlaces', 'recursos'
            ],
            'Proyectos Completados': [
                'completado', 'terminado', 'finalizado', 'completed', 'finished',
                'delivered', 'done', 'entregado', 'deployed'
            ]
        }
        
        # Buscar coincidencias temáticas
        for theme, keywords in theme_rules.items():
            score = sum(1 for keyword in keywords if keyword in content or keyword in folder_name)
            if score >= 2:  # Al menos 2 palabras clave coinciden
                return theme
        
        return None
    
    def _same_theme_by_content(self, folder1: str, folder2: str, content: str) -> bool:
        """Determina si las carpetas tienen la misma temática basándose en el contenido."""
        
        # Temas comunes
        themes = {
            'tech': ['api', 'code', 'programming', 'development', 'software', 'system'],
            'business': ['marketing', 'sales', 'revenue', 'customer', 'business'],
            'finance': ['budget', 'cost', 'money', 'financial', 'investment'],
            'health': ['health', 'fitness', 'exercise', 'nutrition', 'wellness'],
            'education': ['tutorial', 'learning', 'course', 'training', 'education']
        }
        
        content_words = content.lower().split()
        
        for theme, keywords in themes.items():
            if (any(kw in folder1 for kw in keywords) and 
                any(kw in folder2 for kw in keywords) and
                any(kw in content for kw in keywords)):
                return True
        
        return False
    
    def _consolidate_by_patterns(self, folder_name: str, existing_folders: list) -> str:
        """Consolida nombres basándose en patrones comunes."""
        
        # Patrones de consolidación
        consolidation_patterns = {
            r'tutorial.*python': 'Tutoriales Técnicos',
            r'tutorial.*': 'Tutoriales Técnicos', 
            r'.*tutorial': 'Tutoriales Técnicos',
            r'.*guide': 'Tutoriales Técnicos',
            r'documentation.*': 'Documentación',
            r'.*documentation': 'Documentación',
            r'proyecto.*completado': 'Proyectos Completados',
            r'.*completado': 'Proyectos Completados',
            r'marketing.*': 'Marketing',
            r'.*marketing': 'Marketing',
            r'desarrollo.*': 'Desarrollo',
            r'.*desarrollo': 'Desarrollo'
        }
        
        import re
        folder_lower = folder_name.lower()
        
        for pattern, consolidated_name in consolidation_patterns.items():
            if re.search(pattern, folder_lower):
                # Verificar si la carpeta consolidada ya existe
                for existing in existing_folders:
                    if existing.lower() == consolidated_name.lower():
                        return existing
                return consolidated_name
        
        return None

# Instancia global del motor AI
ai_engine = AIEngine()

def interpret_prompt_with_ai(prompt: str) -> str:
    """Interpreta un prompt/directiva con AI y devuelve el razonamiento en lenguaje natural."""
    # Obtener comandos disponibles (puede ser parametrizable en el futuro)
    available_commands = [
        'classify', 'analyze', 'clean', 'learn', 'logs', 'dashboard', 'doctor', 'plugins', 'help', 'version',
        'reclassify-all', 'export-knowledge', 'import-knowledge', 'learning-status', 'logs-auto-fix', 'exclude'
    ]
    result = ai_engine.interpret_prompt(prompt, available_commands)
    if result is None:
        return "No se pudo interpretar el prompt con IA."
    return f"Comando: {result.command}\nArgs: {result.args}\nConfianza: {result.confidence:.2f}\nRazonamiento: {result.reasoning}" 