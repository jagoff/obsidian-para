"""
Comandos de QA (Preguntas y Respuestas) para PARA System.
Sistema de preguntas y respuestas con múltiples backends AI.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from paralib.log_center import log_center
from paralib.logger import log_exceptions
from paralib.debug_config import should_show
from paralib.config import get_global_config

logger = logging.getLogger(__name__)


class QACommands:
    """Comandos relacionados con el sistema de preguntas y respuestas."""
    
    def __init__(self, cli_instance):
        """Inicializa con referencia a la instancia CLI principal."""
        self.cli = cli_instance
        self.config = get_global_config()
    
    @log_exceptions
    def cmd_qa(self, *args):
        """
        Sistema de preguntas y respuestas con múltiples backends AI.
        Prioriza Ollama local, luego Hugging Face como fallback.
        
        Uso:
            python para_cli.py qa <pregunta>                    # Pregunta directa
            python para_cli.py qa --context <archivo> <pregunta> # Con contexto
            python para_cli.py qa --backend ollama <pregunta>   # Forzar backend
            python para_cli.py qa --backend huggingface <pregunta> # Forzar backend
            python para_cli.py qa --status                      # Estado de backends
        """
        try:
            log_center.log_info("Iniciando comando QA", "CLI-QA", {"args": args})
            
            if not args:
                print("\n❌ Uso: qa <pregunta> [opciones]")
                print("\nOpciones:")
                print("\n  --context <archivo>     - Agregar contexto desde archivo")
                print("\n  --backend <backend>     - Forzar backend (ollama/huggingface)")
                print("\n  --status                - Mostrar estado de backends")
                print("\nEjemplos:")
                print("\n  python para_cli.py qa '¿Cómo funciona el sistema PARA?'")
                print("\n  python para_cli.py qa --context nota.md 'Analiza esta nota'")
                print("\n  python para_cli.py qa --backend ollama 'Clasifica esta nota'")
                return
            
            # Verificar si es comando de estado
            if args[0] == "--status":
                self._cmd_qa_status()
                return
            
            # Parsear argumentos
            question = ""
            context_file = None
            backend = None
            
            i = 0
            while i < len(args):
                if args[i] == "--context" and i + 1 < len(args):
                    context_file = args[i + 1]
                    i += 2
                elif args[i] == "--backend" and i + 1 < len(args):
                    backend = args[i + 1]
                    i += 2
                else:
                    question = args[i]
                    i += 1
            
            if not question:
                print("\n❌ Debes especificar una pregunta")
                return
            
            # Ejecutar QA
            self._cmd_qa_question(question, context_file, backend)
                
        except Exception as e:
            log_center.log_error(f"Error en QA: {e}", "CLI-QA")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()
    
    def _cmd_qa_status(self):
        """Muestra el estado de los backends AI disponibles."""
        print("\n🤖 Estado de Backends AI")
        print("=" * 50)
        
        # Verificar Ollama
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Ollama: Disponible (local)")
                # Mostrar modelos disponibles
                lines = result.stdout.strip().split('\n')[1:]  # Saltar header
                models = [line.split()[0] for line in lines if line.strip()]
                if models:
                    print(f"   📋 Modelos: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
                else:
                    print("   ⚠️ No hay modelos instalados")
            else:
                print("❌ Ollama: No disponible")
        except Exception as e:
            print(f"❌ Ollama: Error - {e}")
        
        # Verificar Hugging Face
        try:
            import transformers
            import torch
            print("✅ Hugging Face: Disponible (cloud)")
            print(f"   📋 Transformers: {transformers.__version__}")
            print(f"   🔥 PyTorch: {torch.__version__}")
        except ImportError as e:
            print(f"❌ Hugging Face: No disponible - {e}")
        
        # Mostrar configuración actual
        print(f"\n⚙️ Configuración actual:")
        print(f"   Backend: {self.config.get('ai_backend', 'auto')}")
        print(f"   Modelo Ollama: {self.config.get('ollama_model', 'llama3.2:3b')}")
        print(f"   Modelo HF: {self.config.get('huggingface_model', 'microsoft/DialoGPT-medium')}")
        print(f"   QA habilitado: {self.config.get('qa_system_enabled', True)}")
        print(f"   Fallback HF: {self.config.get('fallback_to_huggingface', True)}")
    
    def _cmd_qa_question(self, question: str, context_file: Optional[str] = None, backend: Optional[str] = None):
        """Ejecuta una pregunta en el sistema QA."""
        print(f"\n🤖 Sistema QA - Pregunta: {question}")
        
        # Cargar contexto si se especifica
        context = ""
        if context_file:
            try:
                context_path = Path(context_file)
                if not context_path.exists():
                    print(f"❌ Archivo de contexto no encontrado: {context_file}")
                    return
                
                with open(context_path, 'r', encoding='utf-8') as f:
                    context = f.read()
                print(f"📄 Contexto cargado desde: {context_file}")
            except Exception as e:
                print(f"❌ Error cargando contexto: {e}")
                return
        
        # Inicializar AI Engine con backend específico si se especifica
        from paralib.ai_engine import AIEngine
        
        if backend:
            if backend not in ["ollama", "huggingface", "auto"]:
                print(f"❌ Backend inválido: {backend}. Debe ser 'ollama', 'huggingface' o 'auto'")
                return
            
            if backend == "ollama":
                model_name = self.config.get('ollama_model', 'llama3.2:3b')
            elif backend == "huggingface":
                model_name = self.config.get('huggingface_model', 'microsoft/DialoGPT-medium')
            else:
                model_name = self.config.get('ollama_model', 'llama3.2:3b')
            
            ai_engine = AIEngine(model_name=model_name, backend=backend)
            print(f"🔧 Usando backend forzado: {backend} ({model_name})")
        else:
            # Usar configuración automática
            backend = self.config.get('ai_backend', 'auto')
            if backend == "ollama":
                model_name = self.config.get('ollama_model', 'llama3.2:3b')
            elif backend == "huggingface":
                model_name = self.config.get('huggingface_model', 'microsoft/DialoGPT-medium')
            else:
                model_name = self.config.get('ollama_model', 'llama3.2:3b')
            
            ai_engine = AIEngine(model_name=model_name, backend=backend)
            print(f"🔧 Backend automático: {backend} ({model_name})")
        
        # Ejecutar QA
        print("\n💭 Procesando pregunta...")
        result = ai_engine.qa_system(question, context)
        
        # Mostrar resultado
        print("\n" + "=" * 60)
        print("🤖 RESPUESTA")
        print("=" * 60)
        
        if result.get('error'):
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"📝 {result['answer']}")
        print(f"\n🔧 Backend usado: {result['backend']}")
        print(f"🤖 Modelo: {result['model']}")
        print(f"📊 Confianza: {result['confidence']:.1%}")
        print(f"🌐 Fuente: {result['source']}")
        
        # Log del resultado
        log_center.log_info(
            f"QA completado con {result['backend']}", 
            "CLI-QA", 
            {
                "question": question[:100],
                "backend": result['backend'],
                "confidence": result['confidence'],
                "source": result['source']
            }
        )
