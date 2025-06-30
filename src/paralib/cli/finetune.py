"""
Comandos de fine-tuning para PARA System.
Maneja todo el flujo de fine-tuning de modelos de IA.
"""

import logging
from pathlib import Path
from typing import Any

from paralib.log_center import log_center
from paralib.logger import log_exceptions
from paralib.debug_config import should_show

logger = logging.getLogger(__name__)


class FinetuneCommands:
    """Comandos relacionados con fine-tuning de modelos de IA."""
    
    def __init__(self, cli_instance):
        """Inicializa con referencia a la instancia CLI principal."""
        self.cli = cli_instance
    
    @log_exceptions
    def cmd_finetune(self, *args):
        """
        Sistema centralizado y automatizado para fine-tuning de modelos de IA.
        
        Uso:
            python para_cli.py finetune export                    # Exportar datos
            python para_cli.py finetune openai <archivo>         # Fine-tuning en OpenAI
            python para_cli.py finetune huggingface <archivo>    # Fine-tuning en HuggingFace
            python para_cli.py finetune status <plataforma> [job_id]  # Estado del fine-tuning
            python para_cli.py finetune auto                     # Proceso completo automatizado
        """
        try:
            log_center.log_info("Iniciando comando finetune", "CLI-Finetune", {"args": args})
            
            if not args:
                print("\n❌ Uso: finetune <comando> [opciones]")
                print("\nComandos disponibles:")
                print("\n  export                    - Exportar datos para fine-tuning")
                print("\n  openai <archivo>          - Fine-tuning en OpenAI")
                print("\n  huggingface <archivo>     - Fine-tuning en HuggingFace")
                print("\n  status <plataforma> [job] - Estado del fine-tuning")
                print("\n  auto                      - Proceso completo automatizado")
                return
            
            command = args[0].lower()
            
            # Obtener vault
            vault = self.cli._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Inicializar FinetuneManager
            from paralib.finetune_manager import get_finetune_manager
            finetune_mgr = get_finetune_manager(str(vault))
            
            if command == "export":
                self._cmd_finetune_export(finetune_mgr)
            elif command == "openai":
                if len(args) < 2:
                    print("\n❌ Uso: finetune openai <archivo_openai.jsonl>")
                    return
                self._cmd_finetune_openai(finetune_mgr, args[1])
            elif command == "huggingface":
                if len(args) < 2:
                    print("\n❌ Uso: finetune huggingface <archivo_hf.jsonl>")
                    return
                self._cmd_finetune_huggingface(finetune_mgr, args[1])
            elif command == "status":
                if len(args) < 2:
                    print("\n❌ Uso: finetune status <plataforma> [job_id]")
                    return
                job_id = args[2] if len(args) > 2 else None
                self._cmd_finetune_status(finetune_mgr, args[1], job_id)
            elif command == "auto":
                self._cmd_finetune_auto(finetune_mgr)
            else:
                print(f"❌ Comando no reconocido: {command}")
                
        except Exception as e:
            log_center.log_error(f"Error en finetune: {e}", "CLI-Finetune")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()
    
    def _cmd_finetune_export(self, finetune_mgr):
        """Exporta todos los datos necesarios para fine-tuning."""
        print("\n📊 Exportando datos para fine-tuning...")
        
        results = finetune_mgr.export_all_data()
        
        if 'error' in results:
            print(f"❌ Error exportando datos: {results['error']}")
            return
        
        print("\n✅ Datos exportados exitosamente:")
        for key, path in results.items():
            file_size = Path(path).stat().st_size if Path(path).exists() else 0
            print(f"   📄 {key}: {path} ({file_size / 1024:.1f} KB)")
        
        # Crear reporte
        report_path = finetune_mgr.create_finetune_report(results)
        print(f"\n📋 Reporte generado: {report_path}")
        
        print("\n💡 Próximos pasos:")
        print("\n   python para_cli.py finetune openai <archivo_openai_format>")
        print("\n   python para_cli.py finetune huggingface <archivo_hf_format>")
    
    def _cmd_finetune_openai(self, finetune_mgr, data_file):
        """Ejecuta fine-tuning en OpenAI."""
        print(f"🚀 Iniciando fine-tuning OpenAI con: {data_file}")
        
        if not Path(data_file).exists():
            print(f"❌ Archivo no encontrado: {data_file}")
            return
        
        result = finetune_mgr.run_openai_finetune(data_file)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("\n✅ Fine-tuning iniciado exitosamente:")
            print(f"   🆔 Job ID: {result.get('job_id', 'N/A')}")
            print(f"   🤖 Modelo: {result.get('model', 'N/A')}")
            print(f"   📊 Estado: {result.get('status', 'N/A')}")
            
            print(f"\n💡 Para monitorear el progreso:")
            print(f"   python para_cli.py finetune status openai {result.get('job_id', '')}")
    
    def _cmd_finetune_huggingface(self, finetune_mgr, data_file):
        """Ejecuta fine-tuning en HuggingFace."""
        print(f"🚀 Iniciando fine-tuning HuggingFace con: {data_file}")
        
        if not Path(data_file).exists():
            print(f"❌ Archivo no encontrado: {data_file}")
            return
        
        # Verificar dependencias
        try:
            import transformers
            import torch
            import datasets
        except ImportError:
            print("\n❌ Dependencias faltantes. Instala con:")
            print("\n   pip install transformers datasets torch")
            return
        
        result = finetune_mgr.run_huggingface_finetune(data_file)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("\n✅ Fine-tuning completado exitosamente:")
            print(f"   🤖 Modelo: {result.get('model', 'N/A')}")
            print(f"   📊 Estado: {result.get('status', 'N/A')}")
            
            print(f"\n💡 Modelo guardado en: ./para_finetuned_model")
    
    def _cmd_finetune_status(self, finetune_mgr, platform, job_id=None):
        """Obtiene el estado del fine-tuning."""
        print(f"📊 Consultando estado de fine-tuning en {platform}...")
        
        result = finetune_mgr.get_finetune_status(platform, job_id)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("\n✅ Estado del fine-tuning:")
            print(f"   🏢 Plataforma: {result.get('platform', 'N/A')}")
            print(f"   🆔 Job ID: {result.get('job_id', 'N/A')}")
            print(f"   📊 Estado: {result.get('status', 'N/A')}")
            
            if result.get('model_path'):
                print(f"   📁 Modelo: {result.get('model_path')}")
    
    def _cmd_finetune_auto(self, finetune_mgr):
        """Proceso completo automatizado de fine-tuning."""
        print("🤖 Iniciando proceso completo automatizado de fine-tuning...")

        # Paso 1: Exportar datos
        print("\n📊 Paso 1: Exportando datos...")
        results = finetune_mgr.export_all_data()

        if 'error' in results:
            print(f"❌ Error exportando datos: {results['error']}")
            return

        print("✅ Datos exportados exitosamente")

        # Paso 2: Crear reporte
        print("\n📋 Paso 2: Generando reporte...")
        report_path = finetune_mgr.create_finetune_report(results)
        print(f"✅ Reporte generado: {report_path}")

        # Paso 3: Detectar plataforma automáticamente
        print("\n🔍 Paso 3: Detectando plataforma disponible...")
        platforms = finetune_mgr.detect_available_platforms()

        # Priorizar Ollama (el que usa el sistema actualmente)
        if platforms.get('ollama'):
            print("✅ Ollama detectado - usando fine-tuning local")
            if 'huggingface_format' in results:
                print("\n🚀 Iniciando fine-tuning Ollama...")
                result = finetune_mgr.run_ollama_finetune(results['huggingface_format'])

                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print("✅ Fine-tuning Ollama completado exitosamente")
                    print("   🤖 Modelo: para-finetuned")
                    print("   💡 Para usar: ollama run para-finetuned")

                    # Evaluación automática
                    print("\n🧪 Evaluando modelo fine-tuned...")
                    try:
                        eval_result = finetune_mgr.evaluate_local_model(results['huggingface_format'])
                        print(f"   🎯 Accuracy: {eval_result['accuracy']*100:.1f}% ({eval_result['correct']}/{eval_result['total']})")
                        for ex in eval_result['examples'][:3]:  # Mostrar solo 3 ejemplos
                            status = '✅' if ex['correct'] else '❌'
                            print(f"   {status} Esperado: {ex['expected']} | Predicho: {ex['predicted']}")
                        if eval_result['accuracy'] > 0.7:
                            print("\n✅ El modelo local aprendió correctamente y supera el 70% de acierto.")
                        else:
                            print("\n⚠️ El modelo local no alcanzó el nivel esperado. Revisa los ejemplos.")
                    except Exception as e:
                        print(f"   ⚠️ No se pudo evaluar el modelo: {e}")

        elif platforms.get('huggingface'):
            print("✅ HuggingFace detectado - usando fine-tuning local")
            if 'huggingface_format' in results:
                print("\n🚀 Iniciando fine-tuning HuggingFace...")
                result = finetune_mgr.run_huggingface_finetune(results['huggingface_format'])

                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print("✅ Fine-tuning HuggingFace completado exitosamente")
                    print("   📁 Modelo guardado en: ./para_finetuned_model")

                    # Evaluación automática
                    print("\n🧪 Evaluando modelo fine-tuned...")
                    eval_result = finetune_mgr.evaluate_local_model(results['huggingface_format'])
                    print(f"   🎯 Accuracy: {eval_result['accuracy']*100:.1f}% ({eval_result['correct']}/{eval_result['total']})")
                    for ex in eval_result['examples'][:3]:
                        status = '✅' if ex['correct'] else '❌'
                        print(f"   {status} Esperado: {ex['expected']} | Predicho: {ex['predicted']}")
                    if eval_result['accuracy'] > 0.7:
                        print("\n✅ El modelo local aprendió correctamente y supera el 70% de acierto.")
                    else:
                        print("\n⚠️ El modelo local no alcanzó el nivel esperado. Revisa los ejemplos.")

        elif platforms.get('openai'):
            print("✅ OpenAI detectado - usando fine-tuning en la nube")
            if 'openai_format' in results:
                print("\n🚀 Iniciando fine-tuning OpenAI...")
                result = finetune_mgr.run_openai_finetune(results['openai_format'])

                if 'error' in result:
                    print(f"❌ Error: {result['error']}")
                else:
                    print("✅ Fine-tuning OpenAI iniciado exitosamente")
                    print(f"   🆔 Job ID: {result.get('job_id', 'N/A')}")
                    print(f"\n💡 Para monitorear el progreso:")
                    print(f"   python para_cli.py finetune status openai {result.get('job_id', '')}")
        else:
            print("❌ No se detectó ninguna plataforma de fine-tuning disponible")
            print("💡 Instala Ollama, OpenAI CLI, o HuggingFace para continuar")
            return

        print("\n✅ Proceso automatizado completado")
        print(f"📋 Revisa el reporte: {report_path}") 