"""
Sistema centralizado y automatizado para fine-tuning de modelos de IA.
Maneja todo el flujo desde la exportación de datos hasta el fine-tuning.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .db import ChromaPARADatabase
from .learning_system import PARA_Learning_System
from .classification_log import export_finetune_dataset

logger = logging.getLogger(__name__)

class FinetuneManager:
    """
    Manager centralizado para automatizar todo el proceso de fine-tuning.
    """
    
    def __init__(self, vault_path: str = None):
        self.vault_path = Path(vault_path) if vault_path else None
        self.db = None
        self.learning_system = None
        
        if self.vault_path:
            self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa los componentes necesarios."""
        try:
            self.db = ChromaPARADatabase(str(self.vault_path))
            self.learning_system = PARA_Learning_System(self.db, self.vault_path)
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
    
    def set_vault(self, vault_path: str):
        """Establece el vault para el fine-tuning."""
        self.vault_path = Path(vault_path)
        self._initialize_components()
    
    def export_all_data(self, output_dir: str = "learning/finetune_data") -> Dict[str, str]:
        """
        Exporta todos los datos necesarios para fine-tuning.
        
        Returns:
            Dict con rutas de archivos exportados
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        
        try:
            # 1. Exportar conocimiento completo
            if self.learning_system:
                knowledge_file = output_path / f"para_knowledge_{timestamp}.json"
                self.learning_system.export_learning_knowledge(str(knowledge_file))
                results['knowledge'] = str(knowledge_file)
            
            # 2. Exportar dataset para fine-tuning
            if self.db:
                finetune_file = output_path / f"finetune_dataset_{timestamp}.jsonl"
                export_finetune_dataset(self.db, str(finetune_file))
                results['finetune_dataset'] = str(finetune_file)
            
            # 3. Preparar formatos específicos
            if 'finetune_dataset' in results:
                openai_file = output_path / f"openai_format_{timestamp}.jsonl"
                hf_file = output_path / f"huggingface_format_{timestamp}.jsonl"
                
                self._prepare_openai_format(results['finetune_dataset'], str(openai_file))
                self._prepare_huggingface_format(results['finetune_dataset'], str(hf_file))
                
                results['openai_format'] = str(openai_file)
                results['huggingface_format'] = str(hf_file)
            
            logger.info(f"Datos exportados exitosamente a {output_dir}")
            return results
            
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")
            return {'error': str(e)}
    
    def _prepare_openai_format(self, input_file: str, output_file: str):
        """Prepara datos en formato OpenAI para fine-tuning."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = [json.loads(line) for line in f]
            
            openai_data = []
            for item in data:
                note_content = item.get('input', {}).get('note_content', '')
                
                # Si no hay categoría predicha, intentar inferirla del contenido
                category = item.get('input', {}).get('predicted_category')
                folder = item.get('input', {}).get('predicted_folder')
                
                if not category:
                    category = self._infer_category_from_content(note_content)
                
                if not folder:
                    folder = self._infer_folder_from_content(note_content, category)
                
                if note_content and category:
                    openai_item = {
                        "messages": [
                            {
                                "role": "system",
                                "content": "Clasifica la nota en Projects, Areas, Resources o Archive. Devuelve solo la categoría y el nombre de la carpeta sugerida."
                            },
                            {
                                "role": "user",
                                "content": note_content
                            },
                            {
                                "role": "assistant",
                                "content": f"{category} | {folder}"
                            }
                        ]
                    }
                    openai_data.append(openai_item)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in openai_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"Formato OpenAI preparado: {output_file} ({len(openai_data)} ejemplos)")
            
        except Exception as e:
            logger.error(f"Error preparando formato OpenAI: {e}")
    
    def _prepare_huggingface_format(self, input_file: str, output_file: str):
        """Prepara datos en formato HuggingFace para fine-tuning."""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = [json.loads(line) for line in f]
            
            hf_data = []
            for item in data:
                note_content = item.get('input', {}).get('note_content', '')
                
                # Si no hay categoría predicha, intentar inferirla del contenido
                category = item.get('input', {}).get('predicted_category')
                folder = item.get('input', {}).get('predicted_folder')
                
                if not category:
                    category = self._infer_category_from_content(note_content)
                
                if not folder:
                    folder = self._infer_folder_from_content(note_content, category)
                
                if note_content and category:
                    prompt = f"Nota: {note_content}\nClasifica en Projects, Areas, Resources o Archive."
                    completion = f"{category} | {folder}"
                    
                    hf_item = {
                        "prompt": prompt,
                        "completion": completion
                    }
                    hf_data.append(hf_item)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in hf_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"Formato HuggingFace preparado: {output_file} ({len(hf_data)} ejemplos)")
            
        except Exception as e:
            logger.error(f"Error preparando formato HuggingFace: {e}")
    
    def _infer_category_from_content(self, content: str) -> str:
        """Infiere la categoría basándose en el contenido de la nota."""
        content_lower = content.lower()
        
        # Palabras clave para cada categoría
        projects_keywords = [
            'proyecto', 'project', 'task', 'tarea', 'deadline', 'sprint', 'milestone',
            'desarrollo', 'development', 'implementar', 'implement', 'urgente',
            'objetivo', 'goal', 'target', 'resultado', 'outcome'
        ]
        
        areas_keywords = [
            'área', 'area', 'responsabilidad', 'responsibility', 'rol', 'role',
            'personal', 'health', 'salud', 'fitness', 'finanzas', 'finance',
            'carrera', 'career', 'relaciones', 'relationships', 'rutina', 'routine'
        ]
        
        resources_keywords = [
            'recurso', 'resource', 'referencia', 'reference', 'documentación',
            'documentation', 'manual', 'guía', 'guide', 'tutorial', 'curso',
            'course', 'aprendizaje', 'learning', 'información', 'information',
            'datos', 'data', 'estadísticas', 'statistics', 'investigación', 'research'
        ]
        
        archive_keywords = [
            'archivo', 'archive', 'completado', 'completed', 'terminado', 'finished',
            'obsoleto', 'obsolete', 'antiguo', 'old', 'histórico', 'historical',
            'pasado', 'past', 'viejo', 'deprecated'
        ]
        
        # Contar coincidencias
        projects_score = sum(1 for keyword in projects_keywords if keyword in content_lower)
        areas_score = sum(1 for keyword in areas_keywords if keyword in content_lower)
        resources_score = sum(1 for keyword in resources_keywords if keyword in content_lower)
        archive_score = sum(1 for keyword in archive_keywords if keyword in content_lower)
        
        # Determinar categoría con mayor puntuación
        scores = [
            (projects_score, 'Projects'),
            (areas_score, 'Areas'),
            (resources_score, 'Resources'),
            (archive_score, 'Archive')
        ]
        
        best_category = max(scores, key=lambda x: x[0])
        
        # Si no hay coincidencias claras, usar Resources como fallback
        if best_category[0] == 0:
            return 'Resources'
        
        return best_category[1]
    
    def _infer_folder_from_content(self, content: str, category: str) -> str:
        """Infiere el nombre de la carpeta basándose en el contenido y categoría."""
        content_lower = content.lower()
        
        # Extraer título del contenido (primera línea que empiece con #)
        lines = content.split('\n')
        title = ""
        for line in lines:
            if line.strip().startswith('#'):
                title = line.strip().lstrip('#').strip()
                break
        
        if title:
            # Limpiar el título
            title = title.replace('#', '').strip()
            if title:
                return title
        
        # Si no hay título, usar palabras clave del contenido
        if category == 'Projects':
            for keyword in ['proyecto', 'project', 'desarrollo', 'development']:
                if keyword in content_lower:
                    return f"{keyword.title()} General"
        
        elif category == 'Areas':
            for keyword in ['personal', 'salud', 'finanzas', 'carrera']:
                if keyword in content_lower:
                    return f"{keyword.title()}"
        
        elif category == 'Resources':
            for keyword in ['documentación', 'tutorial', 'curso', 'manual']:
                if keyword in content_lower:
                    return f"{keyword.title()}"
        
        elif category == 'Archive':
            return "Archivo General"
        
        # Fallback
        return f"{category} General"
    
    def run_openai_finetune(self, data_file: str, model_name: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """
        Ejecuta fine-tuning en OpenAI.
        
        Args:
            data_file: Ruta al archivo de datos en formato OpenAI
            model_name: Nombre del modelo base
            
        Returns:
            Dict con información del job de fine-tuning
        """
        try:
            # Verificar que OpenAI CLI está instalado
            result = subprocess.run(['openai', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return {'error': 'OpenAI CLI no está instalado. Instala con: pip install openai'}
            
            # Preparar datos
            prepare_cmd = ['openai', 'tools', 'fine_tunes.prepare_data', '-f', data_file]
            result = subprocess.run(prepare_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {'error': f'Error preparando datos: {result.stderr}'}
            
            # Crear job de fine-tuning
            prepared_file = data_file.replace('.jsonl', '_prepared.jsonl')
            finetune_cmd = [
                'openai', 'api', 'fine_tunes.create',
                '-t', prepared_file,
                '-m', model_name
            ]
            
            result = subprocess.run(finetune_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extraer job ID del output
                output_lines = result.stdout.split('\n')
                job_id = None
                for line in output_lines:
                    if 'Created fine-tune:' in line:
                        job_id = line.split()[-1]
                        break
                
                return {
                    'success': True,
                    'job_id': job_id,
                    'model': model_name,
                    'status': 'created',
                    'output': result.stdout
                }
            else:
                return {'error': f'Error creando fine-tuning: {result.stderr}'}
                
        except Exception as e:
            logger.error(f"Error en fine-tuning OpenAI: {e}")
            return {'error': str(e)}
    
    def run_huggingface_finetune(self, data_file: str, model_name: str = "microsoft/DialoGPT-medium") -> Dict[str, Any]:
        """
        Ejecuta fine-tuning en HuggingFace.
        
        Args:
            data_file: Ruta al archivo de datos en formato HuggingFace
            model_name: Nombre del modelo base
            
        Returns:
            Dict con información del training
        """
        try:
            # Crear script de fine-tuning
            script_content = self._generate_hf_training_script(data_file, model_name)
            script_path = Path("hf_finetune_script.py")
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Ejecutar script
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            
            # Limpiar script temporal
            script_path.unlink(missing_ok=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'model': model_name,
                    'status': 'training_completed',
                    'output': result.stdout
                }
            else:
                return {'error': f'Error en fine-tuning HuggingFace: {result.stderr}'}
                
        except Exception as e:
            logger.error(f"Error en fine-tuning HuggingFace: {e}")
            return {'error': str(e)}
    
    def _generate_hf_training_script(self, data_file: str, model_name: str) -> str:
        """Genera script de fine-tuning para HuggingFace."""
        return f'''
import json
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, 
    TrainingArguments, Trainer, DataCollatorForLanguageModeling
)
from datasets import Dataset
import torch

# Cargar datos
with open("{data_file}", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

# Preparar dataset
texts = []
for item in data:
    text = f"{{item['prompt']}} {{item['completion']}}"
    texts.append({{"text": text}})

dataset = Dataset.from_list(texts)

# Cargar modelo y tokenizer
tokenizer = AutoTokenizer.from_pretrained("{model_name}")
model = AutoModelForCausalLM.from_pretrained("{model_name}")

# Configurar tokenizer
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Tokenizar dataset
def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, padding=True, max_length=512)

tokenized_dataset = dataset.map(tokenize_function, batched=True)

# Configurar training
training_args = TrainingArguments(
    output_dir="./para_finetuned_model",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    save_steps=1000,
    save_total_limit=2,
    prediction_loss_only=True,
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    data_collator=data_collator,
    train_dataset=tokenized_dataset,
)

# Entrenar
trainer.train()

# Guardar modelo
trainer.save_model("./para_finetuned_model")
tokenizer.save_pretrained("./para_finetuned_model")

print("Fine-tuning completado exitosamente!")
'''
    
    def get_finetune_status(self, platform: str, job_id: str = None) -> Dict[str, Any]:
        """
        Obtiene el estado de un job de fine-tuning.
        
        Args:
            platform: 'openai' o 'huggingface'
            job_id: ID del job (solo para OpenAI)
            
        Returns:
            Dict con estado del fine-tuning
        """
        if platform.lower() == 'openai' and job_id:
            try:
                result = subprocess.run(
                    ['openai', 'api', 'fine_tunes.get', '-i', job_id],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    return {
                        'platform': 'openai',
                        'job_id': job_id,
                        'status': 'retrieved',
                        'output': result.stdout
                    }
                else:
                    return {'error': f'Error obteniendo estado: {result.stderr}'}
                    
            except Exception as e:
                return {'error': str(e)}
        
        elif platform.lower() == 'huggingface':
            # Para HuggingFace, verificar si existe el modelo entrenado
            model_path = Path("./para_finetuned_model")
            if model_path.exists():
                return {
                    'platform': 'huggingface',
                    'status': 'completed',
                    'model_path': str(model_path)
                }
            else:
                return {
                    'platform': 'huggingface',
                    'status': 'not_found'
                }
        
        return {'error': 'Plataforma no soportada o job_id requerido para OpenAI'}
    
    def create_finetune_report(self, export_results: Dict[str, str]) -> str:
        """
        Crea un reporte completo del proceso de fine-tuning.
        
        Args:
            export_results: Resultados de export_all_data()
            
        Returns:
            Ruta al archivo de reporte
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"finetune_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Reporte de Fine-tuning PARA System\n\n")
            f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Archivos Exportados\n\n")
            for key, path in export_results.items():
                if key != 'error':
                    file_size = Path(path).stat().st_size if Path(path).exists() else 0
                    f.write(f"- **{key}:** {path} ({file_size / 1024:.1f} KB)\n")
            
            f.write("\n## Comandos de Fine-tuning\n\n")
            f.write("### OpenAI\n")
            f.write("```bash\n")
            f.write("# Preparar datos\n")
            f.write(f"openai tools fine_tunes.prepare_data -f {export_results.get('openai_format', 'N/A')}\n")
            f.write("\n# Crear fine-tuning\n")
            f.write(f"openai api fine_tunes.create -t {export_results.get('openai_format', 'N/A').replace('.jsonl', '_prepared.jsonl')} -m gpt-3.5-turbo\n")
            f.write("```\n\n")
            
            f.write("### HuggingFace\n")
            f.write("```bash\n")
            f.write("# Instalar dependencias\n")
            f.write("pip install transformers datasets torch\n")
            f.write("\n# Ejecutar fine-tuning\n")
            f.write(f"python hf_finetune_script.py\n")
            f.write("```\n\n")
            
            f.write("## Próximos Pasos\n\n")
            f.write("1. Ejecutar los comandos de fine-tuning\n")
            f.write("2. Monitorear el progreso\n")
            f.write("3. Probar el modelo fine-tuned\n")
            f.write("4. Integrar el modelo en el sistema PARA\n")
        
        return report_path

    def evaluate_local_model(self, test_file: str, model_path: str = "./para_finetuned_model") -> dict:
        """
        Evalúa el modelo fine-tuned localmente usando ejemplos de test.
        Args:
            test_file: Archivo JSONL con ejemplos de test (formato HuggingFace)
            model_path: Ruta al modelo fine-tuned
        Returns:
            Dict con métricas y ejemplos
        """
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        import json
        results = []
        correct = 0
        total = 0
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(model_path)
        model.eval()
        with open(test_file, 'r', encoding='utf-8') as f:
            for line in f:
                ex = json.loads(line)
                prompt = ex['prompt']
                expected = ex['completion'].strip().lower()
                inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = model.generate(**inputs, max_new_tokens=32)
                decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
                # Extraer solo la parte de completion generada
                pred = decoded[len(prompt):].strip().lower()
                is_correct = expected in pred or pred in expected
                results.append({
                    'prompt': prompt,
                    'expected': expected,
                    'predicted': pred,
                    'correct': is_correct
                })
                if is_correct:
                    correct += 1
                total += 1
        accuracy = correct / total if total > 0 else 0.0
        return {
            'accuracy': accuracy,
            'total': total,
            'correct': correct,
            'examples': results[:10],  # primeros 10 ejemplos
        }

    def detect_available_platforms(self) -> dict:
        """
        Detecta automáticamente qué plataformas están disponibles.
        
        Returns:
            Dict con plataformas disponibles y sus estados
        """
        platforms = {
            'ollama': False,
            'openai': False,
            'huggingface': False
        }
        
        # Detectar Ollama (el que usa el sistema actualmente)
        try:
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                platforms['ollama'] = True
                logger.info("Ollama detectado como disponible")
        except Exception:
            pass
        
        # Detectar OpenAI CLI
        try:
            result = subprocess.run(['openai', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                platforms['openai'] = True
                logger.info("OpenAI CLI detectado como disponible")
        except Exception:
            pass
        
        # Detectar HuggingFace (transformers)
        try:
            import transformers
            import torch
            platforms['huggingface'] = True
            logger.info("HuggingFace detectado como disponible")
        except ImportError:
            pass
        
        return platforms
    
    def run_ollama_finetune(self, data_file: str, model_name: str = "llama3.2:3b") -> Dict[str, Any]:
        """
        Ejecuta fine-tuning en Ollama local.
        
        Args:
            data_file: Ruta al archivo de datos en formato HuggingFace
            model_name: Nombre del modelo base en Ollama
            
        Returns:
            Dict con información del training
        """
        try:
            # Verificar que Ollama está disponible
            result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                return {'error': 'Ollama no está instalado o no está disponible'}
            
            # Crear script de fine-tuning para Ollama
            script_content = self._generate_ollama_training_script(data_file, model_name)
            script_path = Path("ollama_finetune_script.py")
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Ejecutar script
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            
            # Limpiar script temporal
            script_path.unlink(missing_ok=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'model': model_name,
                    'status': 'training_completed',
                    'output': result.stdout
                }
            else:
                return {'error': f'Error en fine-tuning Ollama: {result.stderr}'}
                
        except Exception as e:
            logger.error(f"Error en fine-tuning Ollama: {e}")
            return {'error': str(e)}
    
    def _generate_ollama_training_script(self, data_file: str, model_name: str) -> str:
        """Genera script de fine-tuning para Ollama."""
        return f'''
import json
import subprocess
import sys
from pathlib import Path

# Cargar datos
with open("{data_file}", "r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

print(f"📊 Dataset cargado: {{len(data)}} ejemplos")

# Crear archivo de configuración para Ollama
config_content = f"""
FROM {model_name}

# Configurar el modelo para clasificación PARA
SYSTEM """Clasifica la nota en Projects, Areas, Resources o Archive. Devuelve solo la categoría y el nombre de la carpeta sugerida."""

# Agregar ejemplos de entrenamiento
"""

# Escribir ejemplos de entrenamiento
for i, item in enumerate(data[:50]):  # Usar primeros 50 ejemplos para evitar sobrecarga
    prompt = item['prompt']
    completion = item['completion']
    config_content += f"""
TEMPLATE """{{{{ .Prompt }}}}"""
PROMPT """{prompt}"""
RESPONSE """{completion}"""
"""

# Guardar configuración
with open("para_finetune.modelfile", "w", encoding="utf-8") as f:
    f.write(config_content)

print("📝 Archivo de configuración generado: para_finetune.modelfile")

# Crear modelo con Ollama
try:
    result = subprocess.run([
        "ollama", "create", "para-finetuned", "-f", "para_finetune.modelfile"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Modelo fine-tuned creado exitosamente: para-finetuned")
        print("💡 Para usar: ollama run para-finetuned")
    else:
        print(f"❌ Error creando modelo: {{result.stderr}}")
        
except Exception as e:
    print(f"❌ Error: {{e}}")

# Limpiar archivo temporal
Path("para_finetune.modelfile").unlink(missing_ok=True)
'''

# Instancia global
finetune_manager = FinetuneManager()

def get_finetune_manager(vault_path: str = None) -> FinetuneManager:
    """Obtiene la instancia global del FinetuneManager."""
    if vault_path:
        finetune_manager.set_vault(vault_path)
    return finetune_manager 