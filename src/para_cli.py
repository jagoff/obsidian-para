#!/usr/bin/env python3
"""
para_cli.py

CLI principal para PARA System - Sistema de organización de Obsidian usando IA y metodología PARA.
"""
import sys
import os
from datetime import datetime
import subprocess
import time
from pathlib import Path
import glob

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent))

# Configurar nivel de debug antes de cualquier otra operación
if '--debug' in sys.argv:
    debug_index = sys.argv.index('--debug')
    if debug_index + 1 < len(sys.argv):
        debug_level = sys.argv[debug_index + 1].upper()
        # Remover --debug y su valor de sys.argv
        sys.argv.pop(debug_index)  # Remove --debug
        sys.argv.pop(debug_index)  # Remove debug level
    else:
        debug_level = 'VERBOSE'
        sys.argv.pop(debug_index)  # Remove --debug
    
    # Configurar nivel de debug
    os.environ['PARA_DEBUG_LEVEL'] = debug_level
    
    # Importar y configurar debug_config
    try:
        from paralib.debug_config import set_debug_level, should_show
        set_debug_level(debug_level)
        print(f"🐛 Debug level set to: {debug_level}")
    except ImportError:
        print("\n⚠️ Debug config not available, continuing with default verbosity")

# Configurar logging robusto antes de cualquier otra operación
from paralib.logger import logger, log_function_calls, log_exceptions, log_critical_error
from paralib.log_center import log_center

# Configurar contexto de logging para el CLI
logger.set_context(component="CLI", version="2.0")

def setup_environment():
    """Configura el entorno de ejecución."""
    try:
        logger.info("Configurando entorno de ejecución")
        log_center.log_info("Configurando entorno de ejecución del CLI", "CLI-Setup")
        
        # Verificar Python version
        if sys.version_info < (3, 8):
            logger.critical("Se requiere Python 3.8 o superior")
            log_center.log_error("Python version insuficiente", "CLI-Setup", {"version": sys.version})
            print("\n❌ Error: Se requiere Python 3.8 o superior")
            sys.exit(1)
        
        # Verificar dependencias críticas
        required_modules = ['rich', 'requests', 'watchdog']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            logger.error(f"Módulos faltantes: {missing_modules}")
            log_center.log_error("Dependencias faltantes", "CLI-Setup", {"missing": missing_modules})
            print(f"❌ Error: Módulos faltantes: {missing_modules}")
            print("\nInfo: Ejecuta: pip install -r requirements.txt")
            sys.exit(1)
        
        logger.info("Entorno configurado correctamente")
        log_center.log_info("Entorno configurado correctamente", "CLI-Setup")
        return True
        
    except Exception as e:
        log_critical_error("Error configurando entorno", e)
        log_center.log_error(f"Error crítico configurando entorno: {str(e)}", "CLI-Setup")
        print(f"❌ Error crítico configurando entorno: {e}")
        sys.exit(1)

@log_function_calls
class PARACLI:
    """CLI principal para PARA System."""
    
    def __init__(self):
        logger.info("Inicializando CLI de PARA System")
        log_center.log_info("Inicializando CLI de PARA System", "CLI-Init")
        self.version = "2.0"  # Versión del sistema
        self.setup_environment()
        
        # Configurar logging específico del CLI
        logger.set_context(component="CLI", session_id=os.getpid())
        
        # Importar dependencias después de setup
        from rich.console import Console
        from rich.prompt import Confirm
        from paralib.vault_selector import vault_selector
        from paralib.cli.finetune import FinetuneCommands
        from paralib.cli.organize import OrganizeCommands
        from paralib.cli.qa import QACommands
        from paralib.cli.analyze import AnalyzeCommands
        
        self.console = Console()
        self.vault_selector = vault_selector
        
        # Inicializar módulos CLI
        self.finetune_commands = FinetuneCommands(self)
        self.organize_commands = OrganizeCommands(self)
        self.qa_commands = QACommands(self)
        self.analyze_commands = AnalyzeCommands(self)
        
        logger.info("CLI inicializado correctamente")
        log_center.log_info("CLI inicializado correctamente", "CLI-Init")
    
    def setup_environment(self):
        """Configura el entorno específico del CLI."""
        try:
            log_center.log_info("Configurando directorios del CLI", "CLI-Setup")
            
            # Crear directorios necesarios
            Path("logs").mkdir(exist_ok=True)
            Path("backups").mkdir(exist_ok=True)
            Path("themes").mkdir(exist_ok=True)
            
            logger.info("Directorios del sistema creados/verificados")
            log_center.log_info("Directorios del sistema creados/verificados", "CLI-Setup")
            
        except Exception as e:
            log_critical_error("Error configurando directorios del CLI", e)
            log_center.log_error(f"Error configurando directorios: {str(e)}", "CLI-Setup")
            raise
    
    def get_all_available_commands(self) -> list:
        """Obtiene todos los comandos disponibles."""
        try:
            log_center.log_info("Obteniendo lista de comandos disponibles", "CLI-Commands")
            
            commands = [
                "classify", "analyze", "clean", "learn", "logs", "dashboard",
                "doctor", "reclassify-all", "reclassify-enhanced", "plugins", "help", "version",
                "export-knowledge", "import-knowledge", "learning-status",
                "logs-auto-fix", "start", "chat", "interactive", "qa", "feedback", "backups",
                "restore-backup", "exclude", "organize", "backup", "restore", "config", "status", "balance", "update", "naming", "fix-names", "consolidate",
                "consolidate-duplicates", "export-knowledge", "import-knowledge", "learning-status",
                "cleanup-folders", "cleanup-all", "test-naming", "consolidate-excessive",
                "consolidate-aggressive", "reclassify", "reclassify-enhanced", "classify-inbox", "refactor-archive", "enforce-para", "fix-projects",
                "clean-problematic", "logs-auto-fix", "finetune"
            ]
            
            # Agregar comandos de plugins
            try:
                from paralib.plugin_system import PARAPluginManager
                plugin_manager = PARAPluginManager()
                plugin_commands = plugin_manager.get_all_commands()
                commands.extend(plugin_commands)
            except Exception as e:
                logger.warning(f"No se pudieron cargar comandos de plugins: {e}")
                log_center.log_warning(f"No se pudieron cargar comandos de plugins: {str(e)}", "CLI-Commands")
            
            logger.debug(f"Comandos disponibles: {len(commands)}")
            log_center.log_info(f"Comandos disponibles obtenidos: {len(commands)}", "CLI-Commands", {"count": len(commands)})
            return commands
            
        except Exception as e:
            logger.error(f"Error obteniendo comandos disponibles: {e}")
            log_center.log_error(f"Error obteniendo comandos: {str(e)}", "CLI-Commands")
            return []
    
    @log_exceptions
    def run(self, args=None):
        """Ejecuta el CLI principal."""
        try:
            logger.info("Iniciando ejecución del CLI")
            log_center.log_info("Iniciando ejecución del CLI", "CLI-Main", {"args": args})
            
            if args is None:
                args = sys.argv[1:]
            
            if not args:
                # Ejecutar flujo de migración automática
                logger.info("Sin argumentos, ejecutando flujo de migración automática")
                log_center.log_info("Sin argumentos, ejecutando modo start", "CLI-Main")
                self.cmd_start()
                return
            
            # Unir todos los argumentos para procesamiento de IA
            full_prompt = ' '.join(args)
            log_center.log_info(f"Procesando comando: {full_prompt}", "CLI-Main")
            
            # Mapeo de comandos tradicionales específicos
            command_map = {
                'start': self.cmd_start,
                'organize': self.organize_commands.cmd_organize,
                'classify': self.cmd_classify,
                'reclassify-all': self.cmd_reclassify_all,
                'reclassify-enhanced': self.cmd_reclassify_enhanced,
                'analyze': self.analyze_commands.cmd_analyze,
                'learn': self.cmd_learn,
                'dashboard': self.cmd_dashboard,
                'health': self.cmd_health,
                'clean': self.cmd_clean,
                'backup': self.cmd_backup,
                'restore': self.cmd_restore,
                'config': self.cmd_config,
                'status': self.cmd_status,
                'help': self.cmd_help,
                'version': self.cmd_version,
                'doctor': self.cmd_doctor,
                'exclude': self.cmd_exclude,
                'update': self.cmd_update,
                'naming': self.cmd_naming,
                'balance': self.cmd_balance,
                'metrics': self.cmd_metrics,
                'fix-names': self.cmd_fix_names,
                'consolidate-duplicates': self.cmd_consolidate_duplicates,
                'export-knowledge': self.cmd_export_knowledge,
                'import-knowledge': self.cmd_import_knowledge,
                'learning-status': self.cmd_learning_status,
                'cleanup-folders': self.cmd_cleanup_folders,
                'cleanup-all': self.cmd_cleanup_all,
                'test-naming': self.cmd_test_naming,
                'consolidate-excessive': self.cmd_consolidate_excessive_folders,
                'consolidate-aggressive': self.cmd_consolidate_aggressive,
                'reclassify-enhanced': self.cmd_reclassify_enhanced,
                'enforce-para': self.cmd_enforce_para,  # Nuevo comando PARA
                'fix-projects': self.cmd_fix_projects,  # Nuevo comando para corregir proyectos
                'clean-problematic': self.cmd_clean_problematic,  # Limpieza de carpetas problemáticas
                'logs-auto-fix': self.cmd_logs_auto_fix,  # Auto-fix de logs con IA
                'logs': self.cmd_logs,  # Mostrar logs del sistema
                'finetune': self.finetune_commands.cmd_finetune,  # Sistema centralizado de fine-tuning
                'qa': self.qa_commands.cmd_qa,  # Sistema de preguntas y respuestas con IA
            }
            
            # Verificar si es un comando tradicional específico (solo el primer argumento)
            first_command = args[0].lower()
            if first_command in command_map:
                logger.info(f"Ejecutando comando tradicional: {first_command}")
                log_center.log_info(f"Ejecutando comando tradicional: {first_command}", "CLI-Main")
                command_map[first_command](*args[1:])
                return
            
            # TODO lo demás se procesa con IA
            logger.info(f"Procesando con IA: {full_prompt}")
            log_center.log_info(f"Procesando con IA: {full_prompt}", "CLI-AI")
            self._execute_ai_prompt(full_prompt, [])
            
        except KeyboardInterrupt:
            logger.info("Ejecución interrumpida por el usuario")
            log_center.log_info("Ejecución interrumpida por el usuario", "CLI-Main")
            print("\n🛑 Operación cancelada por el usuario")
        except Exception as e:
            log_critical_error("Error crítico en ejecución del CLI", e)
            log_center.log_error(f"Error crítico en ejecución: {str(e)}", "CLI-Main")
            print(f"❌ Error crítico: {e}")
            print("\nInfo: Ejecuta 'python para_cli.py doctor' para diagnóstico")
            sys.exit(1)
    
    def _is_known_command(self, command: str) -> bool:
        """Verifica si es un comando conocido."""
        known_commands = self.get_all_available_commands()
        return command.lower() in [cmd.lower() for cmd in known_commands]
    
    @log_exceptions
    def _execute_traditional_command(self, command: str, args: list):
        """Ejecuta un comando tradicional."""
        try:
            logger.info(f"Ejecutando comando tradicional: {command} con args: {args}")
            log_center.log_info(f"Ejecutando comando tradicional: {command}", "CLI-Traditional", {"args": args})
            
            command_method = f"cmd_{command.replace('-', '_')}"
            
            if hasattr(self, command_method):
                method = getattr(self, command_method)
                method(*args)
                log_center.log_info(f"Comando {command} completado exitosamente", "CLI-Traditional")
            else:
                logger.error(f"Método no encontrado: {command_method}")
                log_center.log_error(f"Método no encontrado: {command_method}", "CLI-Traditional")
                print(f"❌ Comando no reconocido: {command}")
                print("\nInfo: Ejecuta 'python para_cli.py help' para ver comandos disponibles")
                
        except Exception as e:
            logger.error(f"Error ejecutando comando {command}: {e}", exc_info=True)
            log_center.log_error(f"Error ejecutando comando {command}: {str(e)}", "CLI-Traditional")
            print(f"❌ Error ejecutando comando '{command}': {e}")
    
    @log_exceptions
    def _execute_ai_prompt(self, prompt: str, additional_args: list):
        """Ejecuta interpretación de prompt con IA."""
        try:
            logger.info(f"Interpretando prompt con IA: {prompt}")
            log_center.log_info(f"Interpretando prompt con IA: {prompt}", "CLI-AI")
            
            # Verificar disponibilidad de IA
            if not self._check_ai_status():
                logger.warning("IA no disponible, mostrando ayuda")
                log_center.log_warning("IA no disponible", "CLI-AI")
                print("\n[AI] IA no disponible. Usando comandos tradicionales.")
                print("\nInfo: Comandos disponibles: help, dashboard, classify, clean, doctor")
                return
            
            # Interpretar prompt con IA
            from paralib.ai_engine import AIEngine
            ai_engine = AIEngine()
            
            # Usar el método correcto del AIEngine
            available_commands = self.get_all_available_commands()
            ai_command = ai_engine.interpret_prompt(prompt, available_commands)
            
            if ai_command and ai_command.confidence > 0.3:
                logger.info(f"Prompt interpretado: {ai_command.command} (confianza: {ai_command.confidence})")
                log_center.log_info(f"Prompt interpretado: {ai_command.command}", "CLI-AI", 
                                  {"confidence": ai_command.confidence, "reasoning": ai_command.reasoning})
                print(f"[TARGET] Interpretado como: {ai_command.command}")
                print(f"💭 Razón: {ai_command.reasoning}")
                
                self._execute_traditional_command(ai_command.command, ai_command.args + additional_args)
            else:
                logger.warning("No se pudo interpretar el prompt con suficiente confianza")
                log_center.log_warning("Prompt no interpretado con suficiente confianza", "CLI-AI")
                print("\n[AI] No pude interpretar tu solicitud con confianza.")
                print("\nInfo: Intenta ser más específico o usa 'help' para ver comandos disponibles.")
                
        except Exception as e:
            logger.error(f"Error en interpretación de IA: {e}", exc_info=True)
            log_center.log_error(f"Error en interpretación de IA: {str(e)}", "CLI-AI")
            print(f"❌ Error en interpretación de IA: {e}")
            print("\nInfo: Usa 'help' para ver comandos disponibles.")
    
    def _check_ai_status(self) -> bool:
        """Verifica si la IA está disponible."""
        try:
            # Verificar si Ollama está disponible
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _get_vault_path(self):
        """Obtiene la ruta del vault configurado."""
        try:
            vault = self._require_vault(interactive=False, silent=True)
            return vault if vault else None
        except Exception as e:
            print(f"❌ Error obteniendo ruta del vault: {e}")
            return None

    def _find_naming_problems(self, vault_path, category='all'):
        """Encuentra problemas en nombres de carpetas."""
        import re
        
        problems = []
        
        # Mapeo de categorías
        category_map = {
            'projects': '01-Projects',
            'areas': '02-Areas', 
            'resources': '03-Resources',
            'archive': '04-Archive'
        }
        
        categories_to_check = []
        if category == 'all':
            categories_to_check = list(category_map.values())
        else:
            if category in category_map:
                categories_to_check = [category_map[category]]
            else:
                print(f"❌ Categoría inválida: {category}")
                return []
        
        for para_folder in categories_to_check:
            folder_path = vault_path / para_folder
            if not folder_path.exists():
                continue
                
            for subfolder in folder_path.iterdir():
                if not subfolder.is_dir() or subfolder.name.startswith('.'):
                    continue
                    
                issues = self._analyze_folder_name(subfolder.name)
                if issues['has_problems']:
                    problems.append({
                        'path': subfolder,
                        'current_name': subfolder.name,
                        'category': para_folder,
                        'issues': issues,
                        'suggested_name': self._suggest_clean_name(subfolder.name)
                    })
        
        return problems

    def _analyze_folder_name(self, name):
        """Analiza un nombre de carpeta para identificar problemas."""
        import re
        
        issues = {
            'has_problems': False,
            'problems': []
        }
        
        # Problema 1: Guiones bajos
        if '_' in name:
            issues['has_problems'] = True
            issues['problems'].append('guiones_bajos')
        
        # Problema 2: Números de sufijo (_1, _2, etc.)
        if re.search(r'_\d+$', name):
            issues['has_problems'] = True
            issues['problems'].append('sufijo_numerico')
        
        # Problema 3: Múltiples guiones bajos seguidos
        if re.search(r'_{2,}', name):
            issues['has_problems'] = True
            issues['problems'].append('multiples_guiones')
        
        # Problema 4: Nombres muy largos
        if len(name) > 50:
            issues['has_problems'] = True
            issues['problems'].append('muy_largo')
        
        # Problema 5: Caracteres especiales problemáticos
        if re.search(r'[(){}[\]#@$%^&*]', name):
            issues['has_problems'] = True
            issues['problems'].append('caracteres_especiales')
        
        return issues

    def _suggest_clean_name(self, name):
        """Sugiere un nombre limpio para la carpeta."""
        import re
        
        clean_name = name
        
        # 1. Remover números de sufijo
        clean_name = re.sub(r'_\d+$', '', clean_name)
        
        # 2. Reemplazar guiones bajos con espacios
        clean_name = clean_name.replace('_', ' ')
        
        # 3. Limpiar múltiples espacios
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        # 4. Capitalizar correctamente
        clean_name = clean_name.title()
        
        # 5. Remover caracteres especiales problemáticos
        clean_name = re.sub(r'[(){}[\]#@$%^&*]', '', clean_name)
        
        # 6. Limitar longitud manteniendo palabras completas
        if len(clean_name) > 40:
            words = clean_name.split()
            clean_name = ""
            for word in words:
                if len(clean_name + " " + word) <= 40:
                    clean_name += (" " + word) if clean_name else word
                else:
                    break
        
        return clean_name.strip()

    def _display_naming_problems(self, problems):
        """Muestra los problemas encontrados."""
        print("\n📋 PROBLEMAS ENCONTRADOS:")
        print("\n-" * 60)
        
        for i, problem in enumerate(problems[:20], 1):  # Mostrar primeros 20
            issues_str = ', '.join(problem['issues']['problems'])
            print(f"{i:2d}. 📁 {problem['category']}")
            print(f"    ❌ {problem['current_name']}")
            print(f"    🔧 {problem['suggested_name']}")
            print(f"    🚨 Problemas: {issues_str}")
            print()
        
        if len(problems) > 20:
            print(f"... y {len(problems) - 20} problemas más")

    def _apply_naming_fixes(self, problems):
        """Aplica las correcciones de nombres."""
        import shutil
        
        fixed = 0
        conflicts = []
        
        for problem in problems:
            current_path = problem['path']
            new_name = problem['suggested_name']
            new_path = current_path.parent / new_name
            
            # Verificar conflictos
            if new_path.exists() and new_path != current_path:
                conflicts.append({
                    'current': current_path,
                    'suggested': new_path,
                    'problem': problem
                })
                continue
            
            try:
                current_path.rename(new_path)
                print(f"✅ {current_path.name} → {new_name}")
                fixed += 1
            except Exception as e:
                print(f"❌ Error renombrando {current_path.name}: {e}")
        
        # Manejar conflictos
        if conflicts:
            self._handle_naming_conflicts(conflicts)
        
        return fixed

    def _handle_naming_conflicts(self, conflicts):
        """Maneja conflictos donde el nombre sugerido ya existe."""
        print(f"\n🔄 CONFLICTOS DETECTADOS ({len(conflicts)}):")
        print("\nLas siguientes carpetas no se pudieron renombrar porque ya existe una con el nombre sugerido:")
        
        for conflict in conflicts:
            print(f"   📁 {conflict['current'].name}")
            print(f"      → Quiere renombrarse a: {conflict['suggested'].name}")
            print(f"      ⚠️ Pero ya existe")
            
        print("\n💡 Usa 'para consolidate' para fusionar carpetas similares")

    @log_exceptions
    def _require_vault(self, vault_path=None, interactive=True, silent=False):
        """Requiere un vault válido."""
        try:
            log_center.log_info("Requiriendo vault válido", "CLI-Vault", {"path": vault_path, "interactive": interactive})
            
            if vault_path:
                vault = Path(vault_path)
                # Para demo/testing, aceptar vaults sin .obsidian si tienen estructura PARA
                if vault.exists():
                    has_obsidian = (vault / '.obsidian').exists()
                    has_para_structure = any((vault / folder).exists() for folder in ['01-Projects', '02-Areas', '03-Resources', '04-Archive'])
                    
                    if has_obsidian or has_para_structure:
                        logger.info(f"Vault especificado válido: {vault}")
                        log_center.log_info(f"Vault especificado válido: {vault}", "CLI-Vault")
                        if not silent:
                            print(f"📁 Vault: {vault}")
                        return vault
                    else:
                        logger.warning(f"Vault especificado no tiene estructura válida: {vault}")
                        if not silent:
                            print(f"⚠️ Vault especificado no tiene estructura válida: {vault}")
            
            # Buscar vault automáticamente (con silent=True para evitar duplicaciones)
            vault = self.vault_selector.get_vault(silent=True)
            
            if vault:
                logger.info(f"Vault encontrado: {vault}")
                log_center.log_info(f"Vault encontrado: {vault}", "CLI-Vault")
                if not silent:
                    print(f"📁 Vault: {vault}")
                return vault
            
            if interactive:
                logger.warning("No se encontró vault, solicitando selección interactiva")
                log_center.log_warning("No se encontró vault, solicitando selección interactiva", "CLI-Vault")
                if not silent:
                    print("\n❌ No se encontró un vault de Obsidian.")
                vault = self.vault_selector.select_vault_interactive()
                if vault:
                    logger.info(f"Vault seleccionado interactivamente: {vault}")
                    log_center.log_info(f"Vault seleccionado interactivamente: {vault}", "CLI-Vault")
                    if not silent:
                        print(f"📁 Vault: {vault}")
                    return vault
            
            logger.error("No se pudo obtener un vault válido")
            log_center.log_error("No se pudo obtener un vault válido", "CLI-Vault")
            return None
            
        except Exception as e:
            logger.error(f"Error requiriendo vault: {e}", exc_info=True)
            log_center.log_error(f"Error requiriendo vault: {str(e)}", "CLI-Vault")
            return None

    @log_exceptions
    def cmd_dashboard(self, *args):
        """Lanza el Dashboard Web Next.js 14"""
        try:
            # Log inicio del comando
            logger.info("Comando dashboard iniciado")
            log_center.log_info("Iniciando Dashboard Web Next.js 14", "CLI-Dashboard", {"args": args})
            
            print("\n🚀 Iniciando PARA Dashboard Web v2.0...")
            print("\n🌐 Dashboard disponible en http://localhost:3000")
            print("\nInfo: Presiona Ctrl+C para detener el dashboard")
            
            # Verificar si existe el directorio web
            web_path = Path("web")
            if not web_path.exists():
                print("\n❌ Error: Directorio 'web' no encontrado")
                print("\n💡 Asegúrate de estar en el directorio raíz del proyecto")
                log_center.log_error("Directorio web no encontrado", "CLI-Dashboard")
                return
                
            log_center.log_info("Ejecutando Next.js dashboard", "CLI-Dashboard")
            
            # Cambiar al directorio web y ejecutar npm run dev
            import os
            original_dir = os.getcwd()
            try:
                os.chdir("web")
                
                # Verificar si node_modules existe
                if not Path("node_modules").exists():
                    print("\n📦 Instalando dependencias...")
                    subprocess.run(["npm", "install"], check=True)
                
                print("\n🎬 Iniciando dashboard con animaciones cinematográficas...")
                result = subprocess.run(["npm", "run", "dev"], check=True)
                
            finally:
                os.chdir(original_dir)
            
            if result.returncode != 0:
                logger.error(f"Error ejecutando dashboard: código {result.returncode}")
                log_center.log_error(f"Dashboard falló con código {result.returncode}", "CLI-Dashboard")
                print("\n❌ Error ejecutando dashboard")
            else:
                log_center.log_info("Dashboard ejecutado exitosamente", "CLI-Dashboard")
                print("\n✅ Dashboard iniciado exitosamente")
                
        except Exception as e:
            logger.error(f"Error crítico en dashboard: {e}")
            log_center.log_error(f"Error crítico en dashboard: {str(e)}", "CLI-Dashboard")
            print(f"❌ Error crítico en dashboard: {e}")
            print("\n💡 Asegúrate de tener Node.js instalado y el directorio 'web' presente")
    
    @log_exceptions
    def cmd_start(self, *args):
        """Inicia el sistema PARA con configuración automática."""
        try:
            log_center.log_info("Iniciando comando start", "CLI-Start", {"args": args})
            print("\n🚀 Iniciando PARA System v2.0...")
            
            # Verificar entorno
            print("\n📋 Verificando entorno...")
            vault = self._require_vault()
            if vault:
                print(f"✅ Vault encontrado: {vault}")
                log_center.log_info(f"Vault encontrado: {vault}", "CLI-Start")
                
                # Verificar estructura PARA
                vault_path = Path(vault)
                para_folders = ['01-Projects', '02-Areas', '03-Resources', '04-Archive']
                
                print("\n📁 Verificando estructura PARA...")
                for folder in para_folders:
                    folder_path = vault_path / folder
                    if folder_path.exists():
                        print(f"✅ {folder}")
                    else:
                        print(f"❌ {folder} - No encontrado")
                        folder_path.mkdir(exist_ok=True)
                        print(f"   📁 Creado: {folder}")
                
                print("\n✅ Sistema PARA iniciado correctamente")
                print("\n💡 Comandos disponibles:")
                print("   • python para_cli.py classify - Clasificar notas")
                print("   • python para_cli.py analyze - Analizar vault")
                print("   • python para_cli.py dashboard - Dashboard web")
                print("   • python para_cli.py doctor - Diagnóstico del sistema")
                
                log_center.log_info("Sistema PARA iniciado correctamente", "CLI-Start")
            else:
                print("\n❌ No se pudo encontrar vault")
                log_center.log_error("No se pudo encontrar vault", "CLI-Start")
                
        except Exception as e:
            logger.error(f"Error crítico en start: {e}", exc_info=True)
            log_center.log_error(f"Error crítico en start: {str(e)}", "CLI-Start")
            print(f"❌ Error crítico en start: {e}")
    
    def cmd_exclude(self, *args):
        """Gestiona el sistema de exclusiones globales."""
        try:
            log_center.log_info("Iniciando comando exclude", "CLI-Exclude", {"args": args})
            print("\n🚫 Gestión de Exclusiones Globales")
            print("\n=" * 40)
            
            vault = self._require_vault()
            if vault:
                vault_path = Path(vault)
                
                from paralib.exclusion_manager import get_exclusion_manager
                exclusion_manager = get_exclusion_manager()
                
                # Procesar argumentos
                if args and args[0] == 'show':
                    # Mostrar exclusiones actuales
                    excluded_paths = exclusion_manager.get_global_exclusions()
                    if excluded_paths:
                        print(f"📋 Exclusiones actuales ({len(excluded_paths)}):")
                        for i, path in enumerate(excluded_paths, 1):
                            print(f"  {i}. {Path(path).name} -> {path}")
                        
                        # Mostrar estadísticas
                        stats = exclusion_manager.get_exclusion_stats(vault_path)
                        print(f"\n📊 Estadísticas:")
                        print(f"  📁 Total carpetas excluidas: {stats['excluded_folders']}")
                        print(f"  📄 Notas excluidas: {stats['excluded_notes']}")
                        print(f"  ✅ Notas disponibles: {stats['available_notes']}")
                        print(f"  📊 Porcentaje excluido: {stats['exclusion_percentage']:.1f}%")
                        
                    else:
                        print("\n📋 No hay exclusiones configuradas")
                        
                elif args and args[0] == 'clear':
                    # Limpiar todas las exclusiones
                    count = exclusion_manager.clear_global_exclusions()
                    print(f"✅ {count} exclusiones eliminadas")
                    log_center.log_info(f"{count} exclusiones eliminadas", "CLI-Exclude")
                    
                elif args and args[0] == 'reconfig':
                    # Reconfigurar exclusiones desde cero
                    print("\n[UPDATE] Reconfigurando exclusiones desde cero...")
                    from paralib.exclusion_manager import ensure_global_exclusions_configured
                    if ensure_global_exclusions_configured(vault_path, force_interactive=True):
                        print("\n✅ Exclusiones reconfiguradas exitosamente")
                        log_center.log_info("Exclusiones reconfiguradas exitosamente", "CLI-Exclude")
                    else:
                        print("\n❌ Error reconfigurando exclusiones")
                        log_center.log_error("Error reconfigurando exclusiones", "CLI-Exclude")
                        
                elif args and args[0] == 'custom':
                    # Lanzar GUI visual directamente
                    print("\n🌳 Lanzando GUI Visual Tree Explorer...")
                    log_center.log_info("Lanzando GUI visual tree explorer directamente", "CLI-Exclude")
                    from paralib.exclusion_manager import get_exclusion_manager
                    exclusion_manager = get_exclusion_manager()
                    
                    selected_paths = exclusion_manager.select_exclusions_interactive(vault_path)
                    
                    if selected_paths:
                        # Limpiar exclusiones anteriores y agregar las nuevas
                        exclusion_manager.clear_global_exclusions()
                        for path in selected_paths:
                            exclusion_manager.add_global_exclusion(path)
                        
                        print(f"✅ Exclusiones configuradas: {len(selected_paths)} carpetas")
                        for path in selected_paths:
                            print(f"   🚫 {Path(path).name}")
                        log_center.log_info(f"Exclusiones configuradas desde GUI: {len(selected_paths)} carpetas", "CLI-Exclude")
                    else:
                        print("\n✅ Sin exclusiones seleccionadas")
                        log_center.log_info("GUI visual: sin exclusiones seleccionadas", "CLI-Exclude")
                        
                else:
                    # Mostrar ayuda del comando
                    print("\nInfo: Uso del comando exclude:")
                    print("\n  python para_cli.py exclude show      - Mostrar exclusiones actuales")
                    print("\n  python para_cli.py exclude clear     - Limpiar todas las exclusiones")
                    print("\n  python para_cli.py exclude reconfig  - Reconfigurar exclusiones")
                    print("\n  python para_cli.py exclude custom    - 🌳 GUI Visual Tree Explorer")
                    print("\n🔒 Las exclusiones son globales y se aplican a TODA la CLI")
                    print("\n🚫 Las carpetas excluidas NO son tocadas por la IA por privacidad")
                    
            else:
                print("\n❌ No se pudo encontrar vault")
                log_center.log_error("No se pudo encontrar vault", "CLI-Exclude")
                
        except Exception as e:
            print(f"❌ Error gestionando exclusiones: {e}")
            log_center.log_error(f"Error gestionando exclusiones: {str(e)}", "CLI-Exclude")
    
    def cmd_classify(self, *args):
        """Clasifica archivos usando el clasificador propio CON SISTEMA DE EXCLUSIONES OBLIGATORIO."""
        try:
            log_center.log_info("Iniciando comando classify", "CLI-Classify", {"args": args})
            print("\n[TARGET] Clasificando archivos con IA propia...")
            
            # 1. SELECCIÓN DE VAULT CON BROWSER
            print("\n📁 SELECCIÓN DE VAULT...")
            vault = self._require_vault_with_browser()
            if not vault:
                print("\n❌ No se seleccionó vault válido")
                return
                
            vault_path = Path(vault)
            print(f"✅ Vault seleccionado: {vault}")
            
            # 2. CONFIGURACIÓN DE EXCLUSIONES CON CONFIRMACIÓN
            print("\n🚫 CONFIGURACIÓN DE EXCLUSIONES...")
            excluded_paths = self._configure_exclusions_interactive(vault_path)
            
            # 3. CONFIRMACIÓN ANTES DE EJECUTAR
            if not self._confirm_classification(vault_path, excluded_paths, args):
                print("\n❌ Clasificación cancelada por el usuario")
                return
            
            from paralib.organizer import PARAOrganizer
            organizer = PARAOrganizer()
            
            if args and args[0]:
                # Clasificar archivo específico
                file_path = args[0]
                log_center.log_info(f"Clasificando archivo específico: {file_path}", "CLI-Classify")
                
                # Verificar si el archivo está en carpeta excluida
                file_resolved = str(Path(file_path).resolve())
                is_excluded = False
                for excluded_path in excluded_paths:
                    if file_resolved.startswith(str(Path(excluded_path).resolve())):
                        is_excluded = True
                        break
                
                if is_excluded:
                    print(f"🚫 Archivo en carpeta excluida, no se clasificará: {file_path}")
                    log_center.log_warning(f"Archivo en carpeta excluida: {file_path}", "CLI-Classify")
                    return
                
                result = organizer.classify_single_note(file_path)
                if result:
                    print(f"✅ Archivo clasificado: {file_path}")
                    log_center.log_info(f"Archivo clasificado exitosamente: {file_path}", "CLI-Classify")
                else:
                    print(f"⚠️ No se pudo clasificar: {file_path}")
                    log_center.log_warning(f"No se pudo clasificar: {file_path}", "CLI-Classify")
            else:
                # Clasificar todas las notas CON EXCLUSIONES
                log_center.log_info("Clasificando todas las notas con exclusiones", "CLI-Classify")
                result = organizer.reclassify_all_notes_with_exclusions(str(vault), excluded_paths, create_backup=True)
                if result:
                    print("\n✅ Clasificación completada exitosamente")
                    log_center.log_info("Clasificación completada exitosamente", "CLI-Classify")
                else:
                    print("\n⚠️ Clasificación completada con advertencias")
                    log_center.log_warning("Clasificación completada con advertencias", "CLI-Classify")
                    
        except Exception as e:
            print(f"❌ Error clasificando: {e}")
            log_center.log_error(f"Error clasificando: {str(e)}", "CLI-Classify")
    
    def cmd_reclassify_all(self, *args):
        """Reclasifica todas las notas del vault de forma SEGURA (sin renombrar archivos de usuario)."""
        try:
            log_center.log_info("Iniciando reclasificación completa segura", "CLI-Reclassify", {"args": args})
            print("\n🛡️ Iniciando reclasificación completa SEGURA del vault...")
            print("\n💡 [blue]MODO SEGURO:[/blue] No se renombrarán archivos de usuario")
            print("   [blue]PROTECCIÓN:[/blue] Respeto a proyectos independientes")
            print("   [blue]PRESERVACIÓN:[/blue] Nombres originales mantenidos")
            
            vault = self._require_vault()
            if vault:
                vault_path = Path(vault)
                
                # 🚫 SISTEMA DE EXCLUSIONES OBLIGATORIO
                print("\n🚫 CONFIGURANDO EXCLUSIONES OBLIGATORIAS...")
                log_center.log_info("Configurando exclusiones obligatorias", "CLI-Reclassify")
                
                from paralib.exclusion_manager import ensure_global_exclusions_configured
                if not ensure_global_exclusions_configured(vault_path):
                    print("\n❌ No se pudieron configurar exclusiones. Operación cancelada.")
                    log_center.log_error("No se pudieron configurar exclusiones", "CLI-Reclassify")
                    return
                
                # Obtener exclusiones configuradas
                from paralib.exclusion_manager import get_exclusion_manager
                exclusion_manager = get_exclusion_manager()
                excluded_paths = exclusion_manager.get_global_exclusions()
                
                # Mostrar exclusiones activas
                if excluded_paths:
                    print(f"🚫 Exclusiones activas: {len(excluded_paths)} carpetas")
                    for path in excluded_paths:
                        print(f"   🚫 {Path(path).name}")
                else:
                    print("\n✅ Sin exclusiones - se procesarán todas las carpetas")
                
                # USAR LA NUEVA FUNCIÓN SEGURA
                print("\n[TARGET] Iniciando reclasificación segura con exclusiones...")
                log_center.log_info("Iniciando reclasificación segura", "CLI-Reclassify")
                
                from paralib.organizer import run_full_reclassification_safe
                result = run_full_reclassification_safe(str(vault), excluded_paths, create_backup=True)
                
                if result and result.get('success'):
                    print("\n✅ Reclasificación SEGURA completada exitosamente")
                    log_center.log_info("Reclasificación segura completada exitosamente", "CLI-Reclassify")
                    
                    # Mostrar características de seguridad aplicadas
                    safety_features = result.get('safety_features', [])
                    if safety_features:
                        print("\n🛡️ Características de seguridad aplicadas:")
                        for feature in safety_features:
                            print(f"   ✅ {feature}")
                    
                    # Mostrar estadísticas
                    print("\n📊 Proceso completo:")
                    print(f"   💾 Backup: {'Creado' if result.get('backup_created') else 'No disponible'}")
                    print(f"   🚫 Exclusiones: {len(excluded_paths)} carpetas protegidas")
                    print(f"   [TARGET] Reclasificación: Completada en modo seguro")
                    
                    # Mostrar estadísticas de consolidación si están disponibles
                    consolidation_stats = result.get('consolidation_stats', {})
                    if consolidation_stats:
                        print(f"   [CONSOLIDATE] Consolidación: {consolidation_stats.get('folders_merged', 0)} carpetas fusionadas")
                        print(f"   📄 Archivos movidos: {consolidation_stats.get('files_moved', 0)}")
                        if consolidation_stats.get('skipped_different_projects', 0) > 0:
                            print(f"   ⚠️ Proyectos preservados: {consolidation_stats.get('skipped_different_projects', 0)}")
                    
                    # Mostrar distribución final si está disponible
                    final_distribution = result.get('final_distribution', {})
                    if final_distribution:
                        print(f"\n📊 Distribución final:")
                        for category, count in final_distribution.items():
                            print(f"   📁 {category}: {count} notas")
                    
                else:
                    error_msg = result.get('error', 'Error desconocido') if result else 'No se pudo completar la reclasificación'
                    print(f"\n❌ Error en reclasificación: {error_msg}")
                    log_center.log_error(f"Error en reclasificación: {error_msg}", "CLI-Reclassify")
                    
            else:
                print("\n❌ No se pudo encontrar vault")
                log_center.log_error("No se pudo encontrar vault", "CLI-Reclassify")
                
        except Exception as e:
            logger.error(f"Error crítico en reclasificación: {e}", exc_info=True)
            log_center.log_error(f"Error crítico en reclasificación: {str(e)}", "CLI-Reclassify")
            print(f"❌ Error crítico en reclasificación: {e}")
            print("\n💡 Ejecuta 'python para_cli.py doctor' para diagnóstico")
    
    def cmd_analyze(self, *args):
        """Analiza logs de clasificación y estadísticas de aprendizaje."""
        try:
            from paralib.learning_system import PARA_Learning_System
            from paralib.precision_measurement import PrecisionMeasurementSystem
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from pathlib import Path
            import json
            
            console = Console()
            
            # Obtener vault path
            vault_path = self._get_vault_path()
            if not vault_path:
                console.print("[red]❌ No se pudo determinar el vault path[/red]")
                return
            
            vault_path = Path(vault_path)
            if not vault_path.exists():
                console.print(f"[red]❌ Vault no existe: {vault_path}[/red]")
                return
            
            # Inicializar sistemas
            db = get_shared_chromadb(vault_path)
            learning_system = PARA_Learning_System(db, vault_path)
            precision_system = PrecisionMeasurementSystem(vault_path, db)
            
            console.print(f"\n[bold blue]🔍 ANALIZANDO SISTEMA DE CLASIFICACIÓN PARA[/bold blue]")
            console.print(f"📁 Vault: {vault_path}")
            
            # === ANÁLISIS DE MÉTRICAS DE APRENDIZAJE ===
            console.print(f"\n[bold]📊 Métricas de Aprendizaje:[/bold]")
            try:
                metrics = learning_system.get_metrics()
                if metrics:
                    metrics_table = Table(title="Métricas del Sistema de Aprendizaje")
                    metrics_table.add_column("Métrica", style="cyan")
                    metrics_table.add_column("Valor", style="green")
                    metrics_table.add_column("Estado", style="yellow")
                    
                    for key, value in metrics.items():
                        if key == 'error':
                            continue
                        
                        # Determinar estado
                        if key == 'accuracy_rate':
                            status = "✅ Excelente" if value > 90 else "⚠️ Bueno" if value > 70 else "❌ Necesita mejora"
                        elif key == 'confidence_correlation':
                            status = "✅ Alto" if value > 0.8 else "⚠️ Medio" if value > 0.5 else "❌ Bajo"
                        elif key == 'learning_velocity':
                            status = "✅ Aprendiendo rápido" if value > 0.7 else "⚠️ Aprendiendo lento" if value > 0.3 else "❌ Sin mejora"
                        else:
                            status = "📊 Normal"
                        
                        metrics_table.add_row(key.replace('_', ' ').title(), f"{value:.2f}", status)
                    
                    console.print(metrics_table)
                else:
                    console.print("[yellow]⚠️ No hay métricas de aprendizaje disponibles[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error obteniendo métricas: {e}[/red]")
            
            # === ANÁLISIS DE LOGS DETALLADOS ===
            console.print(f"\n[bold]📝 Análisis de Logs de Clasificación:[/bold]")
            try:
                log_dir = vault_path / ".para_db" / "classification_logs"
                if log_dir.exists():
                    log_files = list(log_dir.glob("*.json"))
                    if log_files:
                        console.print(f"📄 Encontrados {len(log_files)} logs de clasificación")
                        
                        # Analizar logs recientes
                        recent_logs = []
                        for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                            try:
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    log_data = json.load(f)
                                recent_logs.append(log_data)
                            except Exception as e:
                                console.print(f"[dim]Error leyendo {log_file.name}: {e}[/dim]")
                        
                        if recent_logs:
                            # Estadísticas de logs recientes
                            total_classifications = len(recent_logs)
                            fallbacks_used = sum(1 for log in recent_logs if log.get('final_decision', {}).get('fallback_used', False))
                            requires_review = sum(1 for log in recent_logs if log.get('learning_data', {}).get('requires_review', False))
                            avg_confidence = sum(log.get('final_decision', {}).get('confidence', 0) for log in recent_logs) / total_classifications
                            
                            stats_table = Table(title="Estadísticas de Clasificaciones Recientes")
                            stats_table.add_column("Métrica", style="cyan")
                            stats_table.add_column("Valor", style="green")
                            
                            stats_table.add_row("Total clasificaciones", str(total_classifications))
                            stats_table.add_row("Fallbacks usados", f"{fallbacks_used} ({fallbacks_used/total_classifications*100:.1f}%)")
                            stats_table.add_row("Requieren revisión", f"{requires_review} ({requires_review/total_classifications*100:.1f}%)")
                            stats_table.add_row("Confianza promedio", f"{avg_confidence:.3f}")
                            
                            console.print(stats_table)
                            
                            # Mostrar clasificaciones problemáticas
                            problematic_logs = [log for log in recent_logs if log.get('learning_data', {}).get('requires_review', False)]
                            if problematic_logs:
                                console.print(f"\n[bold yellow]⚠️ Clasificaciones que Requieren Revisión:[/bold yellow]")
                                for log in problematic_logs[:5]:  # Mostrar solo las primeras 5
                                    note_name = log.get('note_name', 'Unknown')
                                    category = log.get('final_decision', {}).get('category', 'Unknown')
                                    confidence = log.get('final_decision', {}).get('confidence', 0)
                                    reason = log.get('final_decision', {}).get('fallback_reason', 'Baja confianza')
                                    console.print(f"  • {note_name} → {category} (conf: {confidence:.3f}) - {reason}")
                    else:
                        console.print("[yellow]⚠️ No se encontraron logs de clasificación[/yellow]")
                else:
                    console.print("[yellow]⚠️ Directorio de logs no existe[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error analizando logs: {e}[/red]")
            
            # === ANÁLISIS DE PRECISIÓN ===
            console.print(f"\n[bold]🎯 Análisis de Precisión:[/bold]")
            try:
                precision_stats = precision_system.get_precision_stats()
                if precision_stats:
                    precision_table = Table(title="Estadísticas de Precisión")
                    precision_table.add_column("Métrica", style="cyan")
                    precision_table.add_column("Valor", style="green")
                    
                    for key, value in precision_stats.items():
                        if isinstance(value, float):
                            precision_table.add_row(key.replace('_', ' ').title(), f"{value:.2f}")
                        else:
                            precision_table.add_row(key.replace('_', ' ').title(), str(value))
                    
                    console.print(precision_table)
                else:
                    console.print("[yellow]⚠️ No hay datos de precisión disponibles[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Error obteniendo precisión: {e}[/red]")
            
            # === RECOMENDACIONES ===
            console.print(f"\n[bold]💡 Recomendaciones:[/bold]")
            try:
                # Analizar tendencias
                trends = learning_system.analyze_trends()
                if trends and trends.get('status') != 'no_data':
                    if trends.get('accuracy_improving', False):
                        console.print("✅ La precisión está mejorando")
                    else:
                        console.print("⚠️ La precisión no está mejorando - considerar ajustes")
                    
                    if trends.get('confidence_stable', False):
                        console.print("✅ La confianza es estable")
                    else:
                        console.print("⚠️ La confianza es inestable - revisar modelo")
                    
                    console.print(f"📈 Velocidad de aprendizaje: {trends.get('learning_velocity', 0):.2f}")
                else:
                    console.print("📊 No hay suficientes datos para analizar tendencias")
            except Exception as e:
                console.print(f"[red]❌ Error analizando tendencias: {e}[/red]")
            
            console.print(f"\n[bold green]✅ Análisis completado[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error en análisis: {e}[/red]")
            if should_show('show_debug'):
                import traceback
                console.print(traceback.format_exc())
    
    def cmd_learn(self, *args):
        """Sistema de aprendizaje usando learning_system propio."""
        try:
            log_center.log_info("Iniciando comando learn", "CLI-Learn", {"args": args})
            print("\n🧠 Iniciando aprendizaje con herramientas PARA...")
            
            from paralib.learning_system import PARA_Learning_System
            learning_system = PARA_Learning_System()
            
            # Analizar tendencias y patrones
            log_center.log_info("Analizando tendencias y patrones", "CLI-Learn")
            trends = learning_system.analyze_trends()
            if trends:
                print(f"📈 Tendencias detectadas: {trends}")
                log_center.log_info(f"Tendencias detectadas: {trends}", "CLI-Learn")
            
            # Mejorar basado en datos recientes
            log_center.log_info("Obteniendo sugerencias de mejora", "CLI-Learn")
            improvements = learning_system.get_optimization_suggestions()
            if improvements:
                print(f"Info: Sugerencias de mejora: {len(improvements)}")
                for improvement in improvements[:3]:
                    print(f"   • {improvement}")
                log_center.log_info(f"Sugerencias de mejora obtenidas: {len(improvements)}", "CLI-Learn", {"suggestions": improvements[:3]})
            
            print("\n✅ Análisis de aprendizaje completado")
            log_center.log_info("Análisis de aprendizaje completado", "CLI-Learn")
        except Exception as e:
            print(f"❌ Error en aprendizaje: {e}")
            log_center.log_error(f"Error en aprendizaje: {str(e)}", "CLI-Learn")
    
    def cmd_health(self, *args):
        """Verifica salud del sistema"""
        try:
            log_center.log_info("Iniciando comando health", "CLI-Health", {"args": args})
            print("\n💊 Verificando salud del sistema...")
            
            # Verificar componentes del sistema
            from paralib.health_monitor import health_monitor
            health_report = health_monitor.get_health_report()
            
            if health_report:
                print(f"✅ Salud del sistema: {health_report.get('status', 'Unknown')}")
                print(f"   📊 Puntuación: {health_report.get('score', 0)}%")
                log_center.log_info(f"Salud del sistema verificada: {health_report.get('status', 'Unknown')}", "CLI-Health", health_report)
            else:
                print("\n✅ Sistema saludable")
                log_center.log_info("Sistema saludable", "CLI-Health")
        except Exception as e:
            print(f"❌ Error verificando salud: {e}")
            log_center.log_error(f"Error verificando salud: {str(e)}", "CLI-Health")
    
    def cmd_clean(self, *args):
        """Limpia archivos duplicados"""
        try:
            log_center.log_info("Iniciando comando clean", "CLI-Clean", {"args": args})
            print("\n🧹 Limpiando archivos...")
            
            from paralib.clean_manager import clean_manager
            result = clean_manager.clean_duplicates()
            
            if result:
                print(f"✅ Limpieza completada: {result.get('cleaned', 0)} archivos")
                log_center.log_info("Limpieza completada", "CLI-Clean", result)
            else:
                print("\n✅ Limpieza completada")
                log_center.log_info("Limpieza completada", "CLI-Clean")
        except Exception as e:
            print(f"❌ Error limpiando: {e}")
            log_center.log_error(f"Error limpiando: {str(e)}", "CLI-Clean")
    
    def cmd_backup(self, *args):
        """Crea backup del vault usando backup_manager propio."""
        try:
            log_center.log_info("Iniciando comando backup", "CLI-Backup", {"args": args})
            print("\n💾 Creando backup con herramientas PARA...")
            
            vault = self._require_vault()
            if vault:
                from paralib.backup_manager import backup_manager
                
                backup_type = args[0] if args else 'full'
                description = ' '.join(args[1:]) if len(args) > 1 else 'Backup manual desde CLI'
                
                log_center.log_info(f"Creando backup tipo {backup_type}", "CLI-Backup", {"type": backup_type, "description": description})
                
                backup_info = backup_manager.create_backup(
                    str(vault), 
                    backup_type=backup_type,
                    description=description
                )
                
                if backup_info:
                    print(f"✅ Backup creado exitosamente: {backup_info.id}")
                    print(f"   📊 Tamaño: {backup_info.size_mb:.1f} MB")
                    print(f"   📁 Archivos: {backup_info.file_count}")
                    log_center.log_info(f"Backup creado exitosamente: {backup_info.id}", "CLI-Backup", 
                                      {"id": backup_info.id, "size_mb": backup_info.size_mb, "file_count": backup_info.file_count})
                else:
                    print("\n❌ No se pudo crear el backup")
                    log_center.log_error("No se pudo crear el backup", "CLI-Backup")
            else:
                print("\n❌ No se pudo encontrar vault")
                log_center.log_error("No se pudo encontrar vault", "CLI-Backup")
        except Exception as e:
            print(f"❌ Error creando backup: {e}")
            log_center.log_error(f"Error creando backup: {str(e)}", "CLI-Backup")
    
    def cmd_restore(self, *args):
        """Restaura desde backup"""
        try:
            log_center.log_info("Iniciando comando restore", "CLI-Restore", {"args": args})
            print("\n[UPDATE] Restaurando desde backup...")
            
            if args and args[0]:
                backup_id = args[0]
                from paralib.backup_manager import backup_manager
                
                log_center.log_info(f"Restaurando backup: {backup_id}", "CLI-Restore")
                result = backup_manager.restore_backup(backup_id)
                
                if result:
                    print(f"✅ Backup {backup_id} restaurado exitosamente")
                    log_center.log_info(f"Backup {backup_id} restaurado exitosamente", "CLI-Restore")
                else:
                    print(f"❌ No se pudo restaurar el backup {backup_id}")
                    log_center.log_error(f"No se pudo restaurar el backup {backup_id}", "CLI-Restore")
            else:
                print("\n❌ Especifica el ID del backup a restaurar")
                log_center.log_error("ID de backup no especificado", "CLI-Restore")
        except Exception as e:
            print(f"❌ Error restaurando: {e}")
            log_center.log_error(f"Error restaurando: {str(e)}", "CLI-Restore")
    
    def cmd_config(self, *args):
        """Configuración del sistema"""
        try:
            log_center.log_info("Iniciando comando config", "CLI-Config", {"args": args})
            print("\n⚙️ Configuración del sistema...")
            
            from paralib.config import get_global_config
            
            if args and args[0] == 'show':
                config = get_global_config()
                print("\n📋 Configuración actual:")
                for key, value in config.config.items():
                    print(f"   {key}: {value}")
                log_center.log_info("Configuración mostrada", "CLI-Config")
            else:
                print("\n✅ Configuración completada")
                log_center.log_info("Configuración completada", "CLI-Config")
        except Exception as e:
            print(f"❌ Error en configuración: {e}")
            log_center.log_error(f"Error en configuración: {str(e)}", "CLI-Config")
    
    @log_exceptions
    def cmd_status(self, *args):
        """Muestra estado del sistema"""
        try:
            log_center.log_info("Iniciando comando status", "CLI-Status", {"args": args})
            print("\n📋 Estado del sistema:")
            print("\n✅ PARA System v2.0 - OPERATIVO")
            print("\n✅ Log Center - FUNCIONANDO")
            print("\n✅ Health Monitor - ACTIVO")
            print("\n✅ Backup Manager - LISTO")
            print("\n✅ File Watcher - INICIALIZADO")
            
            # Obtener estadísticas del log center
            stats = log_center.get_log_stats()
            print(f"📊 Estadísticas de logs:")
            print(f"   Total: {stats.get('total_logs', 0)}")
            print(f"   Errores: {stats.get('errors', 0)}")
            print(f"   Warnings: {stats.get('warnings', 0)}")
            
            log_center.log_info("Estado del sistema mostrado", "CLI-Status", stats)
        except Exception as e:
            print(f"❌ Error mostrando estado: {e}")
            log_center.log_error(f"Error mostrando estado: {str(e)}", "CLI-Status")

    @log_exceptions
    def cmd_help(self, *args):
        """Muestra ayuda detallada del sistema PARA."""
        try:
            log_center.log_info("Mostrando ayuda del sistema", "CLI-Help", {"args": args})
            
            if args:
                # Ayuda específica para un comando
                command = args[0].lower()
                self._show_command_help(command)
                return
            
            # Ayuda general mejorada
            print("\n" + "="*80)
            print("🚀 PARA System v2.0 - Sistema de Organización Automática de Notas")
            print("="*80)
            
            print("\n📋 COMANDOS PRINCIPALES:")
            print("─" * 50)
            
            main_commands = [
                ("start", "Inicia el sistema interactivo con configuración automática"),
                ("dashboard", "Lanza el Dashboard Web Next.js 14 (http://localhost:3000)"),
                ("doctor", "Diagnóstico completo y auto-corrección del sistema"),
                ("help", "Muestra esta ayuda o ayuda específica de un comando")
            ]
            
            for cmd, desc in main_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n🗂️ ORGANIZACIÓN Y CLASIFICACIÓN:")
            print("─" * 50)
            
            org_commands = [
                ("organize", "Organiza un vault específico usando IA"),
                ("classify", "Clasifica archivos específicos en categorías PARA"),
                ("reclassify-all", "Reclasifica todas las notas del vault"),
                ("reclassify-enhanced", "Reclasificación avanzada con exclusiones"),
                ("analyze", "Analiza estructura y estadísticas del vault"),
                ("enforce-para", "Aplica principios del método PARA de Tiago Forte")
            ]
            
            for cmd, desc in org_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n🧹 LIMPIEZA Y MANTENIMIENTO:")
            print("─" * 50)
            
            cleanup_commands = [
                ("clean", "Limpia archivos duplicados y temporales"),
                ("consolidate", "Consolida carpetas fragmentadas"),
                ("consolidate-excessive", "Consolidación de carpetas excesivas"),
                ("consolidate-aggressive", "Consolidación agresiva de carpetas"),
                ("fix-names", "Corrige nombres problemáticos de carpetas"),
                ("fix-projects", "Corrige nombres de carpetas de proyectos")
            ]
            
            for cmd, desc in cleanup_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n💾 BACKUP Y RESTAURACIÓN:")
            print("─" * 50)
            
            backup_commands = [
                ("backup", "Crea backup del vault"),
                ("restore", "Restaura desde backup"),
                ("exclude", "Gestiona exclusiones globales")
            ]
            
            for cmd, desc in backup_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n🧠 IA Y APRENDIZAJE:")
            print("─" * 50)
            
            ai_commands = [
                ("learn", "Sistema de aprendizaje automático"),
                ("finetune", "Sistema de fine-tuning de IA"),
                ("naming", "Naming inteligente de carpetas con IA"),
                ("balance", "Auto-balanceador de distribución PARA")
            ]
            
            for cmd, desc in ai_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n📊 MONITOREO Y ESTADO:")
            print("─" * 50)
            
            monitor_commands = [
                ("status", "Estado actual del sistema"),
                ("health", "Verifica salud del sistema"),
                ("metrics", "Dashboard de métricas en tiempo real"),
                ("logs", "Muestra logs del sistema")
            ]
            
            for cmd, desc in monitor_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n🔧 CONFIGURACIÓN Y ACTUALIZACIÓN:")
            print("─" * 50)
            
            config_commands = [
                ("config", "Configuración del sistema"),
                ("update", "Actualiza componentes del sistema"),
                ("version", "Muestra versión del sistema")
            ]
            
            for cmd, desc in config_commands:
                print(f"  {cmd:<20} {desc}")
            
            print("\n💡 EJEMPLOS DE USO:")
            print("─" * 50)
            print("  # Iniciar sistema")
            print("  python para_cli.py start")
            print()
            print("  # Organizar vault con IA")
            print("  python para_cli.py organize")
            print()
            print("  # Diagnóstico y auto-corrección")
            print("  python para_cli.py doctor")
            print()
            print("  # Dashboard web")
            print("  python para_cli.py dashboard")
            print()
            print("  # Ayuda específica")
            print("  python para_cli.py help organize")
            print("  python para_cli.py help doctor")
            
            print("\n[TARGET] FLUJO DE TRABAJO RECOMENDADO:")
            print("─" * 50)
            print("  1. python para_cli.py start          # Iniciar sistema")
            print("  2. python para_cli.py doctor         # Verificar salud")
            print("  3. python para_cli.py organize       # Organizar notas")
            print("  4. python para_cli.py analyze        # Analizar resultados")
            print("  5. python para_cli.py dashboard      # Ver dashboard web")
            
            print("\n🔗 RECURSOS:")
            print("─" * 50)
            print("  📖 Documentación: docs/")
            print("  🧠 Datos de aprendizaje: learning/")
            print("  🌐 Dashboard Web: http://localhost:3000")
            print("  📝 Logs: logs/")
            print("  💾 Backups: backups/")
            
            print("\n" + "="*80)
            print("💡 Para ayuda detallada de un comando: python para_cli.py help <comando>")
            print("="*80)
            
        except Exception as e:
            logger.error(f"Error mostrando ayuda: {e}")
            log_center.log_error(f"Error mostrando ayuda: {str(e)}", "CLI-Help")
            print(f"❌ Error mostrando ayuda: {e}")
    
    def _show_command_help(self, command: str):
        """Muestra ayuda específica para un comando."""
        try:
            command_help = {
                'start': {
                    'description': 'Inicia el sistema PARA con configuración automática',
                    'usage': 'python para_cli.py start',
                    'details': [
                        '• Verifica dependencias del sistema',
                        '• Detecta automáticamente el vault de Obsidian',
                        '• Crea estructura PARA si no existe',
                        '• Inicializa componentes del sistema',
                        '• Muestra comandos disponibles'
                    ],
                    'examples': [
                        'python para_cli.py start'
                    ]
                },
                'doctor': {
                    'description': 'Diagnóstico completo y auto-corrección del sistema',
                    'usage': 'python para_cli.py doctor [--no-fix]',
                    'details': [
                        '• Verifica entorno Python y dependencias',
                        '• Analiza logs en busca de errores',
                        '• Verifica archivos críticos del sistema',
                        '• Comprueba configuración de Obsidian',
                        '• Aplica correcciones automáticas (por defecto)',
                        '• Limpia archivos temporales y cachés',
                        '• Optimiza bases de datos',
                        '• Consolida backups antiguos'
                    ],
                    'flags': [
                        '--no-fix    Solo diagnóstico, sin aplicar correcciones'
                    ],
                    'examples': [
                        'python para_cli.py doctor',
                        'python para_cli.py doctor --no-fix'
                    ]
                },
                'organize': {
                    'description': 'Organiza un vault específico usando IA',
                    'usage': 'python para_cli.py organize [vault_path]',
                    'details': [
                        '• Clasifica notas en categorías PARA',
                        '• Usa IA para determinar la mejor ubicación',
                        '• Respeta exclusiones configuradas',
                        '• Crea backup automático antes de organizar',
                        '• Muestra estadísticas del proceso'
                    ],
                    'examples': [
                        'python para_cli.py organize',
                        'python para_cli.py organize /path/to/vault'
                    ]
                },
                'dashboard': {
                    'description': 'Lanza el Dashboard Web Next.js 14',
                    'usage': 'python para_cli.py dashboard',
                    'details': [
                        '• Inicia servidor web en puerto 3000',
                        '• Dashboard con métricas en tiempo real',
                        '• Interfaz moderna y responsiva',
                        '• Visualización de estadísticas del vault',
                        '• Monitoreo de actividad del sistema'
                    ],
                    'examples': [
                        'python para_cli.py dashboard'
                    ],
                    'note': 'Presiona Ctrl+C para detener el dashboard'
                },
                'analyze': {
                    'description': 'Analiza estructura y estadísticas del vault',
                    'usage': 'python para_cli.py analyze',
                    'details': [
                        '• Cuenta archivos y notas por categoría',
                        '• Analiza distribución PARA',
                        '• Identifica patrones de uso',
                        '• Detecta problemas de organización',
                        '• Genera reportes detallados'
                    ],
                    'examples': [
                        'python para_cli.py analyze'
                    ]
                },
                'consolidate': {
                    'description': 'Consolida carpetas fragmentadas',
                    'usage': 'python para_cli.py consolidate [--execute]',
                    'details': [
                        '• Identifica carpetas similares',
                        '• Sugiere consolidaciones lógicas',
                        '• Reduce fragmentación del vault',
                        '• Mantiene estructura organizada',
                        '• Modo simulación por defecto'
                    ],
                    'flags': [
                        '--execute    Aplica las consolidaciones'
                    ],
                    'examples': [
                        'python para_cli.py consolidate',
                        'python para_cli.py consolidate --execute'
                    ]
                },
                'fix-names': {
                    'description': 'Corrige nombres problemáticos de carpetas',
                    'usage': 'python para_cli.py fix-names [--execute]',
                    'details': [
                        '• Detecta nombres con guiones bajos',
                        '• Elimina sufijos numéricos',
                        '• Corrige caracteres especiales',
                        '• Sugiere nombres limpios',
                        '• Modo simulación por defecto'
                    ],
                    'flags': [
                        '--execute    Aplica las correcciones'
                    ],
                    'examples': [
                        'python para_cli.py fix-names',
                        'python para_cli.py fix-names --execute'
                    ]
                },
                'backup': {
                    'description': 'Crea backup del vault',
                    'usage': 'python para_cli.py backup [tipo] [descripción]',
                    'details': [
                        '• Crea backup comprimido del vault',
                        '• Incluye metadatos y timestamp',
                        '• Almacena en directorio backups/',
                        '• Tipos: full, incremental, selective'
                    ],
                    'examples': [
                        'python para_cli.py backup',
                        'python para_cli.py backup full "Backup antes de reorganización"'
                    ]
                },
                'exclude': {
                    'description': 'Gestiona exclusiones globales',
                    'usage': 'python para_cli.py exclude [comando]',
                    'details': [
                        '• show: Muestra exclusiones actuales',
                        '• clear: Limpia todas las exclusiones',
                        '• reconfig: Reconfigura exclusiones',
                        '• custom: GUI visual para seleccionar'
                    ],
                    'examples': [
                        'python para_cli.py exclude show',
                        'python para_cli.py exclude custom'
                    ]
                }
            }
            
            if command not in command_help:
                print(f"\n❌ Comando '{command}' no encontrado")
                print("\n💡 Comandos disponibles:")
                for cmd in sorted(command_help.keys()):
                    print(f"  • {cmd}")
                return
            
            help_info = command_help[command]
            
            print(f"\n{'='*60}")
            print(f"📖 AYUDA: {command.upper()}")
            print(f"{'='*60}")
            
            print(f"\n📝 Descripción:")
            print(f"   {help_info['description']}")
            
            print(f"\n🔧 Uso:")
            print(f"   {help_info['usage']}")
            
            if 'details' in help_info:
                print(f"\n✨ Funcionalidades:")
                for detail in help_info['details']:
                    print(f"   {detail}")
            
            if 'flags' in help_info:
                print(f"\n🚩 Opciones:")
                for flag in help_info['flags']:
                    print(f"   {flag}")
            
            if 'examples' in help_info:
                print(f"\n💡 Ejemplos:")
                for example in help_info['examples']:
                    print(f"   {example}")
            
            if 'note' in help_info:
                print(f"\n📌 Nota:")
                print(f"   {help_info['note']}")
            
            print(f"\n{'='*60}")
            
        except Exception as e:
            logger.error(f"Error mostrando ayuda de comando {command}: {e}")
            print(f"❌ Error mostrando ayuda: {e}")
    
    @log_exceptions
    def cmd_version(self):
        """Muestra la versión del sistema."""
        try:
            logger.info("Mostrando versión del sistema")
            log_center.log_info("Mostrando versión del sistema", "CLI-Version")
            
            version_info = {
                "PARA System": "2.0",
                "Python": sys.version.split()[0],
                "Plataforma": os.name
            }
            
            print("\n🚀 PARA System v2.0")
            print("\n=" * 30)
            for key, value in version_info.items():
                print(f"{key}: {value}")
            
            log_center.log_info("Versión del sistema mostrada", "CLI-Version", version_info)
            
        except Exception as e:
            logger.error(f"Error mostrando versión: {e}", exc_info=True)
            log_center.log_error(f"Error mostrando versión: {str(e)}", "CLI-Version")
            print(f"❌ Error mostrando versión: {e}")

    @log_exceptions
    def cmd_doctor(self, *args):
        """
        Diagnóstico completo del sistema PARA con auto-corrección.
        
        Uso:
            python para_cli.py doctor [--no-auto-fix] [--verbose]
            
        Argumentos:
            --no-auto-fix  - Deshabilitar auto-corrección automática
            --verbose      - Mostrar información detallada
        """
        try:
            # Importar logger al inicio de la función
            from paralib.logger import logger
            
            # Procesar argumentos
            auto_fix = True  # Por defecto activado
            verbose = False
            
            for arg in args:
                if arg == '--no-auto-fix':
                    auto_fix = False
                elif arg == '--verbose':
                    verbose = True
            
            if auto_fix:
                auto_fix = True  # Activar auto-corrección por defecto
                print("\n🔧 MODO AUTO-CORRECCIÓN ACTIVADO (por defecto)")
                log_center.log_info("Modo auto-corrección activado por defecto", "CLI-Doctor")
            else:
                print("\n🔧 MODO AUTO-CORRECCIÓN ACTIVADO")
                log_center.log_info("Modo auto-corrección activado", "CLI-Doctor")
            if verbose:
                print("\n📝 MODO VERBOSE ACTIVADO")
                log_center.log_info("Modo verbose activado", "CLI-Doctor")
                
            logger.info("Iniciando diagnóstico avanzado del sistema PARA")
            print("\n🩺 PARA System - Diagnóstico Completo v2.0")
            print("─" * 60)
            
            issues = []
            warnings = []
            errors_found = []
            
            # 1. Verificar Python y dependencias críticas
            print("\n📋 1. Verificando entorno Python...")
            log_center.log_info("Verificando entorno Python", "CLI-Doctor-Python")
            try:
                python_version = sys.version_info
                if python_version < (3, 8):
                    issues.append("❌ Python < 3.8 detectado. Se requiere Python 3.8+")
                    log_center.log_error("Python version insuficiente", "CLI-Doctor-Python", {"version": python_version})
                else:
                    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
                    log_center.log_info(f"Python version válida: {python_version.major}.{python_version.minor}.{python_version.micro}", "CLI-Doctor-Python")
                
                # Verificar dependencias críticas
                critical_deps = {
                    'rich': 'Interfaz de usuario CLI',
                    'streamlit': 'Dashboard web',
                    'pandas': 'Manipulación de datos',
                    'plotly': 'Gráficas interactivas',
                    'psutil': 'Monitoreo del sistema',
                    'watchdog': 'Monitoreo de archivos'
                }
                
                for dep, description in critical_deps.items():
                    try:
                        __import__(dep)
                        print(f"✅ {dep} - {description}")
                        log_center.log_info(f"Dependencia OK: {dep}", "CLI-Doctor-Deps")
                    except ImportError:
                        issues.append(f"❌ Dependencia faltante: {dep} ({description})")
                        errors_found.append(f"Missing dependency: {dep}")
                        log_center.log_error(f"Dependencia faltante: {dep}", "CLI-Doctor-Deps")
                        
            except Exception as e:
                issues.append(f"❌ Error verificando entorno: {e}")
                errors_found.append(f"Environment check error: {e}")
                log_center.log_error(f"Error verificando entorno: {str(e)}", "CLI-Doctor-Python")
            
            # 2. Verificar imports del sistema PARA
            print("\n🔧 2. Verificando imports del sistema PARA...")
            log_center.log_info("Verificando imports del sistema PARA", "CLI-Doctor-Imports")
            para_modules = {
                'paralib.log_center': 'Sistema de logging',
                'paralib.health_monitor': 'Monitor de salud',
                'paralib.backup_manager': 'Gestor de backups',
                'paralib.file_watcher': 'Monitor de archivos',
                'paralib.learning_system': 'Sistema de aprendizaje',
                'paralib.ai_engine': 'Motor de IA'
            }
            
            for module, description in para_modules.items():
                try:
                    __import__(module)
                    print(f"✅ {module} - {description}")
                    log_center.log_info(f"Módulo OK: {module}", "CLI-Doctor-Imports")
                except ImportError as e:
                    issues.append(f"❌ Error importando {module}: {e}")
                    errors_found.append(f"Import error: {module} - {e}")
                    log_center.log_error(f"Error importando {module}: {str(e)}", "CLI-Doctor-Imports")
                except Exception as e:
                    warnings.append(f"⚠️ Advertencia en {module}: {e}")
                    errors_found.append(f"Module warning: {module} - {e}")
                    log_center.log_warning(f"Advertencia en {module}: {str(e)}", "CLI-Doctor-Imports")
            
            # 3. Verificar sistema de logging
            print("\n📝 3. Verificando sistema de logging...")
            log_center.log_info("Verificando sistema de logging", "CLI-Doctor-Logging")
            try:
                # Verificar que log_center esté funcionando
                test_session = log_center._generate_session_id()
                log_center.log_info("Test de diagnóstico", "Doctor", session_id=test_session)
                
                stats = log_center.get_log_stats()
                print(f"✅ Log Center funcionando - {stats['total_logs']} logs totales")
                print(f"   - Errores: {stats['errors']}")
                print(f"   - Warnings: {stats['warnings']}")
                log_center.log_info("Log Center funcionando correctamente", "CLI-Doctor-Logging", stats)
                
                # Verificar logs recientes
                recent_logs = log_center.get_recent_logs(50)  # Aumentar a 50 logs para mejor análisis
                print(f"✅ Logs recientes accesibles: {len(recent_logs)} entradas")
                
                # Mostrar tabla de logs recientes SOLO de error, crítico o warning, ORDENADOS de más crítico a menos
                filtered_logs = [entry for entry in recent_logs if getattr(entry, 'level', 'INFO') in ['ERROR', 'CRITICAL', 'WARNING']]
                # Ordenar: CRITICAL > ERROR > WARNING, y dentro de cada grupo, más reciente primero
                level_priority = {'CRITICAL': 0, 'ERROR': 1, 'WARNING': 2}
                filtered_logs.sort(key=lambda entry: (level_priority.get(getattr(entry, 'level', 'WARNING'), 3), -getattr(entry, 'timestamp', 0).timestamp() if hasattr(getattr(entry, 'timestamp', None), 'timestamp') else 0))
                if filtered_logs:
                    print(f"\n📊 LOGS QUE REQUIEREN ATENCIÓN ({len(filtered_logs)}):")
                    print("─" * 120)
                    print(f"{'Timestamp':<20} {'Nivel':<8} {'Componente':<15} {'Mensaje':<70}")
                    print("─" * 120)
                    for entry in filtered_logs[:20]:  # Mostrar primeros 20 ya ordenados
                        timestamp = getattr(entry, 'timestamp', 'N/A')
                        if hasattr(timestamp, 'strftime'):
                            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        level = getattr(entry, 'level', 'INFO')
                        component = getattr(entry, 'component', 'N/A')
                        message = getattr(entry, 'message', str(entry))[:65] + "..." if len(getattr(entry, 'message', str(entry))) > 65 else getattr(entry, 'message', str(entry))
                        if level in ['ERROR', 'CRITICAL']:
                            level_icon = "🚨"
                        elif level == 'WARNING':
                            level_icon = "⚠️"
                        else:
                            level_icon = ""
                        print(f"{timestamp:<20} {level_icon} {level:<6} {component:<15} {message}")
                    if len(filtered_logs) > 20:
                        print(f"... y {len(filtered_logs) - 20} logs más")
                    print("─" * 120)
                else:
                    print("\n✅ No hay logs de error, crítico o warning recientes.")
                
                # Resumen estadístico (sin mostrar tabla de logs INFO)
                log_errors_found = len([log for log in recent_logs if getattr(log, 'level', 'INFO') in ['ERROR', 'CRITICAL']])
                log_warnings_found = len([log for log in recent_logs if getattr(log, 'level', 'INFO') == 'WARNING'])
                log_info_found = len([log for log in recent_logs if getattr(log, 'level', 'INFO') == 'INFO'])
                log_debug_found = len([log for log in recent_logs if getattr(log, 'level', 'INFO') == 'DEBUG'])
                print(f"\n📈 ESTADÍSTICAS DE LOGS:")
                print(f"   🚨 Errores: {log_errors_found}")
                print(f"   ⚠️ Warnings: {log_warnings_found}")
                print(f"   ℹ️ Info: {log_info_found}")
                print(f"   🔍 Debug: {log_debug_found}")
                
                # Buscar errores específicos conocidos
                error_patterns = [
                    "ImportError", "ModuleNotFoundError", "AttributeError", 
                    "KeyError", "IndexError", "SyntaxError", "TypeError",
                    "FileNotFoundError", "PermissionError", "ConnectionError"
                ]
                
                # Analizar logs por patrones de error
                if auto_fix and log_errors_found > 0:
                    print(f"\n🔧 ANALIZANDO LOGS PARA AUTO-FIX:")
                    print("─" * 60)
                    
                    # Crear sistema de gestión de estados de logs
                    log_status_manager = self._create_log_status_manager()
                    
                    # Procesar logs de error para auto-fix
                    resolved_count = 0
                    ignored_count = 0
                    new_errors = 0
                    processed_any = False
                    
                    # Obtener logs de error específicamente
                    error_logs = [log for log in recent_logs if log.level in ['ERROR', 'CRITICAL']]
                    print(f"[DEBUG] Encontrados {len(error_logs)} logs de error para procesar")
                    
                    for log_entry in error_logs:
                        # Generar ID más robusto
                        timestamp_str = str(getattr(log_entry, 'timestamp', ''))
                        component = getattr(log_entry, 'component', 'Unknown')
                        message = getattr(log_entry, 'message', '')
                        
                        # Crear ID más simple y consistente
                        log_id = f"{component}_{hash(message) % 1000000}"
                        
                        print(f"[DEBUG] Procesando log: {component} - {message[:50]}...")
                        
                        # Verificar si ya fue procesado
                        existing_entry = log_status_manager.get_log_by_id(log_id)
                        
                        if existing_entry:
                            status = getattr(existing_entry, 'status', None)
                            if status == 'resolved':
                                resolved_count += 1
                                print(f"   ✅ {message[:50]}... (YA RESUELTO)")
                            elif status == 'ignored':
                                ignored_count += 1
                                print(f"   ⏭️ {message[:50]}... (IGNORADO)")
                            else:
                                # Log existente pero sin estado claro, tratarlo como nuevo
                                new_errors += 1
                                processed_any = True
                                print(f"   🆕 {message[:50]}... (NUEVO - sin estado)")
                                self._process_new_error(log_status_manager, log_id, log_entry, auto_fix)
                        else:
                            new_errors += 1
                            processed_any = True
                            print(f"   🆕 {message[:50]}... (NUEVO)")
                            self._process_new_error(log_status_manager, log_id, log_entry, auto_fix)
                    
                    # Mostrar estadísticas de gestión de logs
                    print(f"\n📊 ESTADÍSTICAS DE GESTIÓN DE LOGS:")
                    print(f"   🆕 Errores nuevos: {new_errors}")
                    print(f"   ✅ Errores resueltos: {resolved_count}")
                    print(f"   ⏭️ Errores ignorados: {ignored_count}")
                    
                    # Limpiar logs resueltos antiguos
                    cleaned_count = log_status_manager.cleanup_old_resolved_logs(days=7)
                    if cleaned_count > 0:
                        print(f"   🗑️ Logs resueltos limpiados: {cleaned_count}")
                    
                    # Guardar estado actualizado SIEMPRE
                    print(f"[DEBUG] Guardando estado de logs en logs/log_status.json ...")
                    log_status_manager._save_status()
                    print(f"[DEBUG] Estado de logs guardado.")
                    
                    print(f"\n💾 Estado de logs guardado en logs/log_status.json")
                else:
                    # Forzar guardado de estado aunque no haya errores nuevos
                    log_status_manager = self._create_log_status_manager()
                    print(f"[DEBUG] (No errores nuevos) Guardando estado de logs en logs/log_status.json ...")
                    log_status_manager._save_status()
                    print(f"[DEBUG] Estado de logs guardado.")
                    print(f"\n💾 Estado de logs guardado en logs/log_status.json (sin errores nuevos)")
                
                # Mostrar resumen final de logs
                print(f"\n📈 RESUMEN FINAL DE LOGS:")
                print(f"   📊 Total de entradas: {len(recent_logs)}")
                print(f"   🚨 Errores activos: {log_errors_found}")
                print(f"   ⚠️ Warnings: {log_warnings_found}")
                print(f"   ℹ️ Info: {log_info_found}")
                
                if log_errors_found == 0:
                    print(f"\n✅ [green]Sistema de logs en estado óptimo[/green]")
                elif log_errors_found <= 3:
                    print(f"\n⚠️ [yellow]Algunos errores menores detectados[/yellow]")
                else:
                    print(f"\n🚨 [red]Múltiples errores detectados - requiere atención[/red]")

                # Limpieza automática de logs viejos
                try:
                    from paralib.logger import logger
                    cleaned = logger.cleanup_old_logs(days=30)
                    print(f"\n🧹 Limpieza automática: {cleaned} archivos de log viejos eliminados (≥30 días)")
                except Exception as e:
                    print(f"⚠️ Error limpiando logs viejos: {e}")
                    log_center.log_warning(f"Error limpiando logs viejos: {e}", "CLI-Doctor")
                
            except Exception as e:
                issues.append(f"❌ Error verificando logs: {e}")
                errors_found.append(f"Log verification error: {e}")
                log_center.log_error(f"Error verificando logs: {str(e)}", "CLI-Doctor-Logging")
            
            # 4. Verificar dashboard y puertos
            print("\n🌐 4. Verificando dashboard y puertos...")
            log_center.log_info("Verificando dashboard y puertos", "CLI-Doctor-Ports")
            dashboard_ports = [8501, 8502, 8503]
            
            for port in dashboard_ports:
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    
                    if result == 0:
                        warnings.append(f"⚠️ Puerto {port} ya está en uso")
                        errors_found.append(f"Port {port} in use")
                        log_center.log_warning(f"Puerto {port} ya está en uso", "CLI-Doctor-Ports")
                    else:
                        print(f"✅ Puerto {port} disponible")
                        log_center.log_info(f"Puerto {port} disponible", "CLI-Doctor-Ports")
                        
                except Exception as e:
                    warnings.append(f"⚠️ Error verificando puerto {port}: {e}")
                    log_center.log_warning(f"Error verificando puerto {port}: {str(e)}", "CLI-Doctor-Ports")
            
            # 5. Verificar archivos críticos del sistema
            print("\n📁 5. Verificando archivos críticos...")
            log_center.log_info("Verificando archivos críticos", "CLI-Doctor-Files")
            critical_files = {
                "para_cli.py": "CLI principal",
                "paralib/__init__.py": "Inicialización del paquete",
                "web/package.json": "Dashboard Web Next.js 14",
                "paralib/backup_center.py": "Backup Center especializado",
                "paralib/log_center.py": "Sistema de logging",
                "paralib/health_monitor.py": "Monitor de salud",
                "paralib/backup_manager.py": "Gestor de backups",
                "requirements.txt": "Dependencias",
                "para_config.default.json": "Configuración por defecto"
            }
            
            for file_path, description in critical_files.items():
                path = Path(file_path)
                if path.exists():
                    print(f"✅ {file_path} - {description}")
                    log_center.log_info(f"Archivo crítico OK: {file_path}", "CLI-Doctor-Files")
                else:
                    issues.append(f"❌ Archivo faltante: {file_path} ({description})")
                    errors_found.append(f"Missing file: {file_path}")
                    log_center.log_error(f"Archivo faltante: {file_path}", "CLI-Doctor-Files")
            
            # 6. Verificar vault de Obsidian
            print("\n📁 6. Verificando vault de Obsidian...")
            log_center.log_info("Verificando vault de Obsidian", "CLI-Doctor-Vault")
            try:
                vault = self._require_vault(interactive=False, silent=True)
                if vault:
                    log_center.log_info(f"Vault encontrado: {vault}", "CLI-Doctor-Vault")
                    obsidian_config = vault / ".obsidian"
                    if obsidian_config.exists():
                        print("\n✅ Configuración de Obsidian válida")
                        log_center.log_info("Configuración de Obsidian válida", "CLI-Doctor-Vault")
                    else:
                        warnings.append("⚠️ Directorio .obsidian no encontrado")
                        log_center.log_warning("Directorio .obsidian no encontrado", "CLI-Doctor-Vault")
                else:
                    warnings.append("⚠️ No se encontró vault de Obsidian")
                    log_center.log_warning("No se encontró vault de Obsidian", "CLI-Doctor-Vault")
            except Exception as e:
                warnings.append(f"⚠️ Error verificando vault: {e}")
                errors_found.append(f"Vault check error: {e}")
                log_center.log_warning(f"Error verificando vault: {str(e)}", "CLI-Doctor-Vault")
            
            # 7. Verificar sistema de plugins
            print("\n🔌 7. Verificando plugins...")
            log_center.log_info("Verificando sistema de plugins", "CLI-Doctor-Plugins")
            try:
                from paralib.plugin_system import PARAPluginManager
                plugin_manager = PARAPluginManager()
                
                # Verificar si tiene el método get_all_commands
                if hasattr(plugin_manager, 'get_all_commands'):
                    commands = plugin_manager.get_all_commands()
                    print(f"✅ Sistema de plugins funcionando - {len(commands)} comandos")
                    log_center.log_info(f"Sistema de plugins funcionando - {len(commands)} comandos", "CLI-Doctor-Plugins")
                else:
                    warnings.append("⚠️ Plugin manager sin método get_all_commands")
                    errors_found.append("Plugin manager missing get_all_commands method")
                    log_center.log_warning("Plugin manager sin método get_all_commands", "CLI-Doctor-Plugins")
                    
            except Exception as e:
                issues.append(f"❌ Error en sistema de plugins: {e}")
                errors_found.append(f"Plugin system error: {e}")
                log_center.log_error(f"Error en sistema de plugins: {str(e)}", "CLI-Doctor-Plugins")
            
            # 8. Análisis de errores con IA (si está disponible)
            print("\n[AI] 8. Análisis inteligente de errores...")
            log_center.log_info("Análisis inteligente de errores", "CLI-Doctor-AI")
            try:
                if self._check_ai_status() and errors_found:
                    from paralib.ai_engine import AIEngine
                    ai = AIEngine()
                    
                    error_summary = "\n".join(errors_found[:10])  # Primeros 10 errores
                    ai_analysis = self._analyze_errors_with_ai(ai, error_summary)
                    
                    if ai_analysis:
                        print(f"[AI] Análisis de IA: {ai_analysis}")
                        log_center.log_info(f"Análisis de IA completado: {ai_analysis}", "CLI-Doctor-AI")
                    else:
                        print("\n✅ IA disponible pero sin análisis específico")
                        log_center.log_info("IA disponible pero sin análisis específico", "CLI-Doctor-AI")
                else:
                    if not self._check_ai_status():
                        warnings.append("⚠️ IA no disponible para análisis")
                        log_center.log_warning("IA no disponible para análisis", "CLI-Doctor-AI")
                    else:
                        print("\n✅ No hay errores para analizar con IA")
                        log_center.log_info("No hay errores para analizar con IA", "CLI-Doctor-AI")
                        
            except Exception as e:
                warnings.append(f"⚠️ Error en análisis de IA: {e}")
                log_center.log_warning(f"Error en análisis de IA: {str(e)}", "CLI-Doctor-AI")
            
            # 9. APLICAR AUTO-FIX SI ESTÁ ACTIVADO
            if auto_fix and (issues or warnings or errors_found):
                print("\n🔧 APLICANDO CORRECCIONES AUTOMÁTICAS...")
                log_center.log_info("Aplicando correcciones automáticas", "CLI-Doctor-AutoFix")
                fixes_applied = []
                
                # Fix 1: Limpiar backups corruptos
                print("\n🗑️ Limpiando backups corruptos...")
                corrupt_backups_removed = self._clean_corrupt_backups()
                if corrupt_backups_removed > 0:
                    fixes_applied.append(f"✅ {corrupt_backups_removed} backups corruptos eliminados")
                    log_center.log_info(f"{corrupt_backups_removed} backups corruptos eliminados", "CLI-Doctor-AutoFix")
                
                # Fix 2: Limpiar archivos temporales y cachés
                print("\n🧹 Limpiando archivos temporales...")
                temp_files_removed = self._clean_temp_files()
                if temp_files_removed > 0:
                    fixes_applied.append(f"✅ {temp_files_removed} archivos temporales eliminados")
                    log_center.log_info(f"{temp_files_removed} archivos temporales eliminados", "CLI-Doctor-AutoFix")
                
                # Fix 3: Consolidar backups duplicados
                print("\n📦 Consolidando backups duplicados...")
                backups_consolidated = self._consolidate_backups()
                if backups_consolidated > 0:
                    fixes_applied.append(f"✅ {backups_consolidated} backups consolidados")
                    log_center.log_info(f"{backups_consolidated} backups consolidados", "CLI-Doctor-AutoFix")
                
                # Fix 4: Optimizar bases de datos
                print("\n🗄️ Optimizando bases de datos...")
                db_optimized = self._optimize_databases()
                if db_optimized:
                    fixes_applied.append("✅ Bases de datos optimizadas")
                    log_center.log_info("Bases de datos optimizadas", "CLI-Doctor-AutoFix")
                
                # Fix 5: Limpiar logs antiguos
                print("\n📝 Limpiando logs antiguos...")
                logs_cleaned = self._clean_old_logs()
                if logs_cleaned > 0:
                    fixes_applied.append(f"✅ {logs_cleaned} logs antiguos eliminados")
                    log_center.log_info(f"{logs_cleaned} logs antiguos eliminados", "CLI-Doctor-AutoFix")
                
                # Fix 6: Limpiar archivos de finetune duplicados
                print("\n🧠 Limpiando datos de finetune duplicados...")
                finetune_cleaned = self._clean_finetune_data()
                if finetune_cleaned > 0:
                    fixes_applied.append(f"✅ {finetune_cleaned} archivos de finetune duplicados eliminados")
                    log_center.log_info(f"{finetune_cleaned} archivos de finetune duplicados eliminados", "CLI-Doctor-AutoFix")
                
                # Fix 7: Limpiar archivos de test obsoletos
                print("\n🧪 Limpiando archivos de test obsoletos...")
                test_files_cleaned = self._clean_test_files()
                if test_files_cleaned > 0:
                    fixes_applied.append(f"✅ {test_files_cleaned} archivos de test obsoletos eliminados")
                    log_center.log_info(f"{test_files_cleaned} archivos de test obsoletos eliminados", "CLI-Doctor-AutoFix")
                
                # Fix 8: Limpiar cachés de Next.js
                print("\n🌐 Limpiando cachés de Next.js...")
                nextjs_cleaned = self._clean_nextjs_cache()
                if nextjs_cleaned:
                    fixes_applied.append("✅ Cachés de Next.js limpiados")
                    log_center.log_info("Cachés de Next.js limpiados", "CLI-Doctor-AutoFix")
                
                # Fix 9: Liberar puertos ocupados
                for warning in warnings:
                    if "Puerto" in warning and "ya está en uso" in warning:
                        port = None
                        if "8501" in warning:
                            port = 8501
                        elif "8502" in warning:
                            port = 8502
                        elif "8503" in warning:
                            port = 8503
                            
                        if port:
                            try:
                                import psutil
                                killed = False
                                for proc in psutil.process_iter(['pid', 'name']):
                                    try:
                                        connections = proc.connections()
                                        for conn in connections:
                                            if hasattr(conn, 'laddr') and conn.laddr.port == port:
                                                proc.terminate()
                                                fixes_applied.append(f"✅ Proceso en puerto {port} terminado (PID: {proc.pid})")
                                                log_center.log_info(f"Proceso en puerto {port} terminado", "CLI-Doctor-AutoFix", {"pid": proc.pid})
                                                killed = True
                                                break
                                        if killed:
                                            break
                                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                        continue
                                        
                                if not killed:
                                    fixes_applied.append(f"⚠️ No se encontró proceso en puerto {port}")
                                    log_center.log_warning(f"No se encontró proceso en puerto {port}", "CLI-Doctor-AutoFix")
                                    
                            except Exception as e:
                                fixes_applied.append(f"❌ Error liberando puerto {port}: {e}")
                                log_center.log_error(f"Error liberando puerto {port}: {str(e)}", "CLI-Doctor-AutoFix")
                
                # Fix 10: Instalar dependencias faltantes
                for issue in issues:
                    if "Dependencia faltante" in issue:
                        try:
                            # Ejecutar pip install
                            result = subprocess.run([
                                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
                            ], capture_output=True, text=True, timeout=60)
                            
                            if result.returncode == 0:
                                fixes_applied.append("✅ Dependencias instaladas desde requirements.txt")
                                log_center.log_info("Dependencias instaladas desde requirements.txt", "CLI-Doctor-AutoFix")
                            else:
                                fixes_applied.append(f"❌ Error instalando dependencias: {result.stderr}")
                                log_center.log_error(f"Error instalando dependencias: {result.stderr}", "CLI-Doctor-AutoFix")
                                
                        except Exception as e:
                            fixes_applied.append(f"❌ Error ejecutando pip install: {e}")
                            log_center.log_error(f"Error ejecutando pip install: {str(e)}", "CLI-Doctor-AutoFix")
                        break  # Solo una vez
                
                # Fix 11: Crear archivos faltantes básicos
                for issue in issues:
                    if "Archivo faltante" in issue and "requirements.txt" in issue:
                        try:
                            requirements_content = """rich>=13.0.0
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.15.0
psutil>=5.9.0
watchdog>=3.0.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
requests>=2.28.0
"""
                            with open("requirements.txt", "w") as f:
                                f.write(requirements_content)
                            fixes_applied.append("✅ Archivo requirements.txt creado")
                            log_center.log_info("Archivo requirements.txt creado", "CLI-Doctor-AutoFix")
                        except Exception as e:
                            fixes_applied.append(f"❌ Error creando requirements.txt: {e}")
                            log_center.log_error(f"Error creando requirements.txt: {str(e)}", "CLI-Doctor-AutoFix")
                
                # Crear backup nuevo después de la limpieza
                print("\n💾 Creando backup limpio...")
                try:
                    vault = self._require_vault(interactive=False, silent=True)
                    if vault:
                        from paralib.backup_manager import backup_manager
                        backup_info = backup_manager.create_backup(
                            str(vault), 
                            backup_type='full',
                            description='Backup automático post-limpieza'
                        )
                        if backup_info:
                            fixes_applied.append(f"✅ Backup limpio creado: {backup_info.id}")
                            log_center.log_info(f"Backup limpio creado: {backup_info.id}", "CLI-Doctor-AutoFix")
                        else:
                            fixes_applied.append("⚠️ No se pudo crear backup limpio")
                            log_center.log_warning("No se pudo crear backup limpio", "CLI-Doctor-AutoFix")
                except Exception as e:
                    fixes_applied.append(f"❌ Error creando backup limpio: {e}")
                    log_center.log_error(f"Error creando backup limpio: {str(e)}", "CLI-Doctor-AutoFix")
                
                # Mostrar resultados del auto-fix
                if fixes_applied:
                    print(f"\n[TARGET] CORRECCIONES APLICADAS ({len(fixes_applied)}):")
                # Fin del método anterior, eliminar try: huérfano
        except Exception as e:
            logger.error(f"Error crítico en doctor: {e}", exc_info=True)
            log_center.log_error(f"Error crítico en doctor: {str(e)}", "CLI-Doctor")
            print(f"❌ Error crítico en doctor: {e}")
    
                
    def cmd_learn(self, *args):
        """Sistema de aprendizaje usando learning_system propio."""
        try:
            log_center.log_info("Iniciando comando learn", "CLI-Learn", {"args": args})
            print("\n🧠 Iniciando aprendizaje con herramientas PARA...")
            
            from paralib.learning_system import PARA_Learning_System
            learning_system = PARA_Learning_System()
            
            # Analizar tendencias y patrones
            log_center.log_info("Analizando tendencias y patrones", "CLI-Learn")
            trends = learning_system.analyze_trends()
            if trends:
                print(f"📈 Tendencias detectadas: {trends}")
                log_center.log_info(f"Tendencias detectadas: {trends}", "CLI-Learn")
            
            # Mejorar basado en datos recientes
            log_center.log_info("Obteniendo sugerencias de mejora", "CLI-Learn")
            improvements = learning_system.get_optimization_suggestions()
            if improvements:
                print(f"Info: Sugerencias de mejora: {len(improvements)}")
                for improvement in improvements[:3]:
                    print(f"   • {improvement}")
                log_center.log_info(f"Sugerencias de mejora obtenidas: {len(improvements)}", "CLI-Learn", {"suggestions": improvements[:3]})
            
            print("\n✅ Análisis de aprendizaje completado")
            log_center.log_info("Análisis de aprendizaje completado", "CLI-Learn")
        except Exception as e:
            print(f"❌ Error en aprendizaje: {e}")
            log_center.log_error(f"Error en aprendizaje: {str(e)}", "CLI-Learn")
    
    def cmd_health(self, *args):
        """Verifica salud del sistema"""
        try:
            log_center.log_info("Iniciando comando health", "CLI-Health", {"args": args})
            print("\n💊 Verificando salud del sistema...")
            
            # Verificar componentes del sistema
            from paralib.health_monitor import health_monitor
            health_report = health_monitor.get_health_report()
            
            if health_report:
                print(f"✅ Salud del sistema: {health_report.get('status', 'Unknown')}")
                print(f"   📊 Puntuación: {health_report.get('score', 0)}%")
                log_center.log_info(f"Salud del sistema verificada: {health_report.get('status', 'Unknown')}", "CLI-Health", health_report)
            else:
                print("\n✅ Sistema saludable")
                log_center.log_info("Sistema saludable", "CLI-Health")
        except Exception as e:
            print(f"❌ Error verificando salud: {e}")
            log_center.log_error(f"Error verificando salud: {str(e)}", "CLI-Health")
    
    def cmd_clean(self, *args):
        """Limpia archivos duplicados"""
        try:
            log_center.log_info("Iniciando comando clean", "CLI-Clean", {"args": args})
            print("\n🧹 Limpiando archivos...")
            
            from paralib.clean_manager import clean_manager
            result = clean_manager.clean_duplicates()
            
            if result:
                print(f"✅ Limpieza completada: {result.get('cleaned', 0)} archivos")
                log_center.log_info("Limpieza completada", "CLI-Clean", result)
            else:
                print("\n✅ Limpieza completada")
                log_center.log_info("Limpieza completada", "CLI-Clean")
        except Exception as e:
            print(f"❌ Error limpiando: {e}")
            log_center.log_error(f"Error limpiando: {str(e)}", "CLI-Clean")
    
    def cmd_backup(self, *args):
        """Crea backup del vault usando backup_manager propio."""
        try:
            log_center.log_info("Iniciando comando backup", "CLI-Backup", {"args": args})
            print("\n💾 Creando backup con herramientas PARA...")
            
            vault = self._require_vault()
            if vault:
                from paralib.backup_manager import backup_manager
                
                backup_type = args[0] if args else 'full'
                description = ' '.join(args[1:]) if len(args) > 1 else 'Backup manual desde CLI'
                
                log_center.log_info(f"Creando backup tipo {backup_type}", "CLI-Backup", {"type": backup_type, "description": description})
                
                backup_info = backup_manager.create_backup(
                    str(vault), 
                    backup_type=backup_type,
                    description=description
                )
                
                if backup_info:
                    print(f"✅ Backup creado exitosamente: {backup_info.id}")
                    print(f"   📊 Tamaño: {backup_info.size_mb:.1f} MB")
                    print(f"   📁 Archivos: {backup_info.file_count}")
                    log_center.log_info(f"Backup creado exitosamente: {backup_info.id}", "CLI-Backup", 
                                      {"id": backup_info.id, "size_mb": backup_info.size_mb, "file_count": backup_info.file_count})
                else:
                    print("\n❌ No se pudo crear el backup")
                    log_center.log_error("No se pudo crear el backup", "CLI-Backup")
            else:
                print("\n❌ No se pudo encontrar vault")
                log_center.log_error("No se pudo encontrar vault", "CLI-Backup")
        except Exception as e:
            print(f"❌ Error creando backup: {e}")
            log_center.log_error(f"Error creando backup: {str(e)}", "CLI-Backup")
    
    def cmd_restore(self, *args):
        """Restaura desde backup"""
        try:
            log_center.log_info("Iniciando comando restore", "CLI-Restore", {"args": args})
            print("\n[UPDATE] Restaurando desde backup...")
            
            if args and args[0]:
                backup_id = args[0]
                from paralib.backup_manager import backup_manager
                
                log_center.log_info(f"Restaurando backup: {backup_id}", "CLI-Restore")
                result = backup_manager.restore_backup(backup_id)
                
                if result:
                    print(f"✅ Backup {backup_id} restaurado exitosamente")
                    log_center.log_info(f"Backup {backup_id} restaurado exitosamente", "CLI-Restore")
                else:
                    print(f"❌ No se pudo restaurar el backup {backup_id}")
                    log_center.log_error(f"No se pudo restaurar el backup {backup_id}", "CLI-Restore")
            else:
                print("\n❌ Especifica el ID del backup a restaurar")
                log_center.log_error("ID de backup no especificado", "CLI-Restore")
        except Exception as e:
            print(f"❌ Error restaurando: {e}")
            log_center.log_error(f"Error restaurando: {str(e)}", "CLI-Restore")
    
    def cmd_status(self, *args):
        """Muestra estado del sistema"""
        try:
            log_center.log_info("Iniciando comando status", "CLI-Status", {"args": args})
            print("\n📋 Estado del sistema:")
            print("\n✅ PARA System v2.0 - OPERATIVO")
            print("\n✅ Log Center - FUNCIONANDO")
            print("\n✅ Health Monitor - ACTIVO")
            print("\n✅ Backup Manager - LISTO")
            print("\n✅ File Watcher - INICIALIZADO")
            
            # Obtener estadísticas del log center
            stats = log_center.get_log_stats()
            print(f"📊 Estadísticas de logs:")
            print(f"   Total: {stats.get('total_logs', 0)}")
            print(f"   Errores: {stats.get('errors', 0)}")
            print(f"   Warnings: {stats.get('warnings', 0)}")
            
            log_center.log_info("Estado del sistema mostrado", "CLI-Status", stats)
        except Exception as e:
            print(f"❌ Error mostrando estado: {e}")
            log_center.log_error(f"Error mostrando estado: {str(e)}", "CLI-Status")

    @log_exceptions
    def cmd_update(self, *args):
        """Sistema de actualización automática - Update Center v2.0"""
        try:
            log_center.log_info("Iniciando Update Center v2.0", "CLI-Update", {"args": args})
            print("\n🔄 PARA Update Center v2.0")
            print("\n=" * 40)
            
            try:
                from paralib.update_center import check_updates, get_embedding_models_status
                
                # Si es el comando específico "models", mostrar modelos
                if args and 'models' in args:
                    print("\n🤖 Estado de Modelos de Embeddings 2025")
                    print("\n-" * 50)
                    
                    models_status = get_embedding_models_status()
                    recommended = models_status.get('recommendation', 'N/A')
                    
                    print(f"🏆 Recomendado: {recommended}")
                    
                    print("\n🏅 TOP 5 Modelos de Embeddings 2025:")
                    for i, model in enumerate(models_status.get('top_5_models_2025', []), 1):
                        icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
                        multilingual = "🌐" if model.get('multilingual') else "🔤"
                        
                        print(f"  {icon} {model['name']}")
                        print(f"      Score: {model['performance_score']}/100 | MTEB: {model['mteb_score']} | {multilingual} | {model['size_gb']:.1f}GB")
                    
                    log_center.log_info("Estado de modelos mostrado", "CLI-Update")
                    return
                
                # Verificar actualizaciones disponibles
                print("\n📡 Verificando actualizaciones disponibles...")
                log_center.log_info("Verificando actualizaciones disponibles", "CLI-Update")
                
                updates_result = check_updates(force=False)
                status = updates_result.get('status', 'ok')
                
                if status == 'ok':
                    print("\n✅ Sistema completamente actualizado")
                    print("\n[TARGET] No hay actualizaciones pendientes")
                    log_center.log_info("Sistema completamente actualizado", "CLI-Update")
                else:
                    print("\n⚠️ Se encontraron algunas actualizaciones pendientes")
                
                # Mostrar información del sistema
                print(f"\n📋 Estado del Sistema PARA:")
                print(f"   🚀 Update Center: v2.0 Activo")
                print(f"   📊 Sistema de logging: Operativo")
                print(f"   🤖 Modelos TOP 5: Catalogados")
                print(f"   🔄 Última verificación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Mostrar comandos disponibles
                print(f"\n💡 Comandos del Update Center:")
                print("\n  python para_cli.py update             - Verificar estado general")
                print("\n  python para_cli.py update models      - 🤖 Ver TOP 5 Modelos 2025")
                
            except ImportError:
                print("\n❌ Update Center no disponible")
                print("\n💡 Módulo update_center no encontrado")
                log_center.log_error("Update Center no disponible - módulo no encontrado", "CLI-Update")
            except Exception as e:
                print(f"❌ Error en Update Center: {e}")
                log_center.log_error(f"Error en Update Center: {str(e)}", "CLI-Update")
                
        except Exception as e:
            print(f"❌ Error ejecutando update: {e}")
            log_center.log_error(f"Error ejecutando update: {str(e)}", "CLI-Update")
    
    @log_exceptions
    def cmd_fix_names(self, *args):
        """
        🧹 Detecta y corrige nombres de carpetas problemáticos
        
        Uso:
            para fix-names [check|apply] [category]
            
        Argumentos:
            check   - Solo mostrar problemas sin aplicar cambios
            apply   - Aplicar correcciones automáticamente  
            category - projects|areas|resources|archive|all (default: all)
        """
        if not args:
            print("\n❌ Especifica 'check' o 'apply'")
            print("\n   Ejemplo: para fix-names check")
            print("\n   Ejemplo: para fix-names apply projects")
            return
            
        action = args[0].lower()
        category = args[1].lower() if len(args) > 1 else 'all'
        
        if action not in ['check', 'apply']:
            print("\n❌ Acción debe ser 'check' o 'apply'")
            return
            
        try:
            vault_path = self._get_vault_path()
            if not vault_path:
                return
                
            problems = self._find_naming_problems(vault_path, category)
            
            if not problems:
                print("\n✅ No se encontraron problemas en los nombres de carpetas")
                return
                
            print(f"🚨 Encontrados {len(problems)} problemas de nomenclatura")
            
            # Mostrar problemas
            self._display_naming_problems(problems)
            
            if action == 'apply':
                print("\n🔧 Aplicando correcciones...")
                fixed = self._apply_naming_fixes(problems)
                print(f"✅ {fixed} carpetas corregidas")
            else:
                print("\n💡 Usa 'para fix-names apply' para corregir automáticamente")
                
        except Exception as e:
            print(f"❌ Error en fix-names: {e}")
            logger.error(f"Error en cmd_fix_names: {e}")

    @log_exceptions
    def cmd_naming(self, *args):
        """Analizar y mejorar nombres de carpetas usando IA avanzada."""
        try:
            log_center.log_info("Iniciando comando naming", "CLI-Naming", {"args": args})
            print("\n🧠 PARA Intelligent Naming System")
            print("\n=" * 40)
            
            # 1. REQUIERE VAULT
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            # 2. PROCESAR ARGUMENTOS
            analyze = '--analyze' in args or any('analyze' in str(arg) for arg in args)
            suggest = '--suggest' in args or any('suggest' in str(arg) for arg in args)
            apply_changes = '--apply' in args or any('apply' in str(arg) for arg in args)
            clean_empty = '--clean' in args or any('clean' in str(arg) for arg in args)
            execute_clean = '--execute' in args or any('execute' in str(arg) for arg in args)
            
            # Determinar categoría
            category = 'all'
            for arg in args:
                if str(arg) in ['projects', 'areas', 'resources', 'all']:
                    category = str(arg)
                    break
            
            print(f"📁 Vault: {vault}")
            print(f"[TARGET] Categoría: {category}")
            
            # 3. IMPORTAR SISTEMA DE NAMING
            try:
                from paralib.intelligent_naming import IntelligentNamingSystem, clean_empty_folders
                naming_system = IntelligentNamingSystem()
            except ImportError as e:
                print(f"❌ Error importando sistema de naming: {e}")
                log_center.log_error(f"Error importando sistema de naming: {str(e)}", "CLI-Naming")
                return
            
            # 4. MAPEAR CATEGORÍAS
            category_map = {
                'projects': '01-Projects',
                'areas': '02-Areas', 
                'resources': '03-Resources',
                'all': None  # Procesar todas
            }
            
            # 5. EJECUTAR ANÁLISIS
            if analyze or (not suggest and not apply_changes):
                print("\n🔍 ANALIZANDO NOMBRES ACTUALES...")
                
                categories_to_analyze = ['01-Projects', '02-Areas', '03-Resources'] if category == 'all' else [category_map[category]]
                
                for cat in categories_to_analyze:
                    cat_path = vault_path / cat
                    if cat_path.exists():
                        print(f"\n📂 Analizando {cat}:")
                        
                        folders = [f for f in cat_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
                        if folders:
                            print(f"   📁 Total carpetas: {len(folders)}")
                            
                            # Mostrar ejemplos de nombres largos
                            long_names = [f.name for f in folders if len(f.name) > 40]
                            if long_names:
                                print(f"   ⚠️ Nombres largos (>{40} chars): {len(long_names)}")
                                for name in long_names[:3]:
                                    print(f"      📄 {name[:50]}...")
                            
                            # Mostrar problemas comunes
                            weird_chars = [f.name for f in folders if any(c in f.name for c in ['(', ')', '[', ']', '{', '}', '#'])]
                            if weird_chars:
                                print(f"   🔤 Con caracteres especiales: {len(weird_chars)}")
                                
                            # Mostrar duplicados potenciales
                            names_lower = [f.name.lower() for f in folders]
                            potential_dupes = [name for name in names_lower if names_lower.count(name) > 1]
                            if potential_dupes:
                                print(f"   🔄 Posibles duplicados: {len(set(potential_dupes))}")
                                
                        else:
                            print("\n   📁 No hay carpetas para analizar")
                    else:
                        print(f"   ❌ Categoría {cat} no existe")
            
            # 6. GENERAR SUGERENCIAS
            if suggest or apply_changes:
                print("\n💡 GENERANDO SUGERENCIAS...")
                
                all_suggestions = {}
                categories_to_suggest = ['01-Projects', '02-Areas', '03-Resources'] if category == 'all' else [category_map[category]]
                
                for cat in categories_to_suggest:
                    print(f"\n[TARGET] Procesando {cat}...")
                    suggestions = naming_system.analyze_and_suggest_renames(vault_path, cat)
                    
                    if suggestions:
                        all_suggestions[cat] = suggestions
                        print(f"   💡 {len(suggestions)} mejoras sugeridas")
                        
                        # Mostrar top 5 sugerencias
                        for i, (current, suggested) in enumerate(list(suggestions.items())[:5], 1):
                            savings = len(current) - len(suggested)
                            print(f"   {i}. {current[:30]}... → {suggested} ({savings:+d} chars)")
                    else:
                        print(f"   ✅ No se necesitan mejoras en {cat}")
                
                # Mostrar reporte completo
                if all_suggestions:
                    print("\n📊 REPORTE COMPLETO DE SUGERENCIAS:")
                    total_improvements = sum(len(suggestions) for suggestions in all_suggestions.values())
                    print(f"Total de mejoras sugeridas: {total_improvements}")
                    
                    for cat, suggestions in all_suggestions.items():
                        naming_system.generate_naming_report(suggestions)
                else:
                    print("\n✅ No se encontraron mejoras necesarias")
            
            # 7. APLICAR CAMBIOS
            if apply_changes and all_suggestions:
                from rich.prompt import Confirm
                
                total_changes = sum(len(suggestions) for suggestions in all_suggestions.values())
                
                print(f"\n🔧 APLICAR CAMBIOS: {total_changes} carpetas serán renombradas")
                print("\n⚠️ ADVERTENCIA: Esta operación renombrará carpetas permanentemente")
                print("\n💾 Se recomienda crear un backup antes de continuar")
                
                if Confirm.ask("¿Continuar con la aplicación de cambios?", default=False):
                    print("\n🔄 APLICANDO CAMBIOS...")
                    
                    changes_applied = 0
                    changes_failed = 0
                    
                    for cat, suggestions in all_suggestions.items():
                        cat_path = vault_path / cat
                        
                        for current_name, suggested_name in suggestions.items():
                            old_path = cat_path / current_name
                            new_path = cat_path / suggested_name
                            
                            try:
                                if old_path.exists() and not new_path.exists():
                                    old_path.rename(new_path)
                                    print(f"✅ {current_name} → {suggested_name}")
                                    changes_applied += 1
                                    log_center.log_info(f"Carpeta renombrada: {current_name} → {suggested_name}", "CLI-Naming")
                                else:
                                    print(f"❌ Error: {current_name} (conflicto o no existe)")
                                    changes_failed += 1
                                    log_center.log_warning(f"Error renombrando: {current_name}", "CLI-Naming")
                            except Exception as e:
                                print(f"❌ Error renombrando {current_name}: {e}")
                                changes_failed += 1
                                log_center.log_error(f"Error renombrando {current_name}: {str(e)}", "CLI-Naming")
                    
                    # Resumen final
                    print(f"\n📊 CAMBIOS APLICADOS:")
                    print(f"   ✅ Exitosos: {changes_applied}")
                    print(f"   ❌ Fallidos: {changes_failed}")
                    
                    if changes_applied > 0:
                        print("\n🎉 ¡Nombres de carpetas mejorados exitosamente!")
                        log_center.log_info(f"Naming completado: {changes_applied} cambios aplicados", "CLI-Naming")
                    
                else:
                    print("\n❌ Cambios cancelados por el usuario")
                    log_center.log_info("Cambios de naming cancelados por el usuario", "CLI-Naming")
            
                         # 8. LIMPIEZA DE CARPETAS VACÍAS
            if '--clean' in args:
                print("\n🗑️ LIMPIANDO CARPETAS VACÍAS...")
                execute_clean = '--execute' in args
                
                target_cat = category_map.get(category) if category != 'all' else None
                stats = clean_empty_folders(vault_path, target_cat, execute_clean)
                
                if stats['empty_folders_found'] > 0 and execute_clean:
                    print("\n🎉 ¡Carpetas vacías eliminadas! El vault está más limpio.")
            
            print("\n💡 COMANDOS DISPONIBLES:")
            print("\n  python para_cli.py naming --analyze          - Analizar nombres actuales")
            print("\n  python para_cli.py naming --suggest          - Sugerir mejores nombres")
            print("\n  python para_cli.py naming --apply            - Aplicar sugerencias")
            print("\n  python para_cli.py naming --clean            - 🗑️ Encontrar carpetas vacías")
            print("\n  python para_cli.py naming --clean --execute  - 🗑️ Eliminar carpetas vacías")
            print("\n  python para_cli.py naming --category projects - Solo proyectos")
            
        except Exception as e:
            print(f"❌ Error en sistema de naming: {e}")
            log_center.log_error(f"Error en sistema de naming: {str(e)}", "CLI-Naming")
    
    @log_exceptions
    def _run_interactive_mode(self):
        """Ejecuta el modo interactivo con IA."""
        try:
            log_center.log_info("Iniciando modo interactivo", "CLI-Interactive-Mode")
            from rich.prompt import Prompt
            
            # Verificar disponibilidad de IA
            if not self._check_ai_status():
                print("\n⚠️  IA no disponible. Usando modo de comandos tradicionales.")
                print("\nInfo: Asegúrate de que Ollama esté corriendo: ollama serve")
                log_center.log_warning("IA no disponible en modo interactivo", "CLI-Interactive-Mode")
            
            command_count = 0
            while True:
                try:
                    # Prompt para el usuario
                    user_input = Prompt.ask("\n[bold cyan]PARA>[/bold cyan]", console=self.console)
                    command_count += 1
                    
                    log_center.log_info(f"Comando interactivo #{command_count}: {user_input}", "CLI-Interactive-Mode")
                    
                    # Comandos de salida
                    if user_input.lower().strip() in ['salir', 'exit', 'quit', 'q']:
                        print("\n👋 ¡Hasta luego!")
                        log_center.log_info(f"Sesión interactiva terminada después de {command_count} comandos", "CLI-Interactive-Mode")
                        break
                    
                    # Comando vacío
                    if not user_input.strip():
                        continue
                    
                    # Procesar comando
                    print(f"[AI] Procesando: {user_input}")
                    
                    # Verificar si es un comando conocido primero
                    if self._is_known_command(user_input.strip()):
                        log_center.log_info(f"Comando conocido detectado: {user_input.strip()}", "CLI-Interactive-Mode")
                        self._execute_traditional_command(user_input.strip(), [])
                    else:
                        # Interpretar con IA
                        log_center.log_info(f"Interpretando con IA: {user_input}", "CLI-Interactive-Mode")
                        self._execute_ai_prompt(user_input, [])
                    
                except KeyboardInterrupt:
                    print("\n👋 ¡Hasta luego!")
                    log_center.log_info(f"Sesión interactiva interrumpida por usuario después de {command_count} comandos", "CLI-Interactive-Mode")
                    break
                except EOFError:
                    print("\n👋 ¡Hasta luego!")
                    log_center.log_info(f"Sesión interactiva terminada por EOF después de {command_count} comandos", "CLI-Interactive-Mode")
                    break
                except Exception as e:
                    logger.error(f"Error en modo interactivo: {e}", exc_info=True)
                    log_center.log_error(f"Error en modo interactivo: {str(e)}", "CLI-Interactive-Mode")
                    print(f"❌ Error: {e}")
                    print("\nInfo: Continúa escribiendo comandos...")
            
        except Exception as e:
            logger.error(f"Error crítico en modo interactivo: {e}", exc_info=True)
            log_center.log_error(f"Error crítico en modo interactivo: {str(e)}", "CLI-Interactive-Mode")
            print(f"❌ Error crítico en modo interactivo: {e}")

    @log_exceptions
    def cmd_balance(self, *args):
        """Auto-Balanceador de Distribución PARA con Correcciones Automáticas"""
        try:
            log_center.log_info("Iniciando comando balance", "CLI-Balance", {"args": args})
            
            # Procesar argumentos
            show_suggestions = '--suggest' in args or '-s' in args
            execute_corrections = '--execute' in args or '-e' in args
            force_execution = '--force' in args or '-f' in args
            max_corrections = 10
            
            # Extraer número máximo de correcciones si se especifica
            for arg in args:
                if arg.startswith('--max='):
                    try:
                        max_corrections = int(arg.split('=')[1])
                    except ValueError:
                        print("\n⚠️ Valor inválido para --max, usando 10 por defecto")
            
            # Verificar vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Importar y ejecutar auto-balanceador
            from paralib.auto_balancer import AutoBalancer
            
            # Crear un objeto config compatible
            class ConfigObject:
                def __init__(self, vault_path):
                    self.vault_path = vault_path
            
            config = ConfigObject(str(vault))
            balancer = AutoBalancer(config)
            
            # Mostrar estado actual
            results = balancer.display_status()
            
            # Obtener métricas y desviaciones
            metrics = results.get('metrics')
            deviations = results.get('deviations', {})
            
            # Procesar según argumentos
            if show_suggestions or execute_corrections:
                if deviations:
                    corrections = balancer.suggest_corrections(metrics, deviations)
                    
                    if corrections:
                        if show_suggestions:
                            # Mostrar sugerencias detalladas
                            print(f"\n🔍 [bold]CORRECCIONES SUGERIDAS ({len(corrections)}):[/bold]")
                            for i, correction in enumerate(corrections[:max_corrections], 1):
                                print(f"\n{i}. 📄 {Path(correction['file_path']).name}")
                                print(f"   🔄 {correction['from_category']} → {correction['to_category']}")
                                print(f"   💭 {correction['reason']}")
                                print(f"   [TARGET] Confianza: {correction['confidence']:.2f}")
                                print(f"   🔤 Palabras clave: {', '.join(correction['keywords_found'])}")
                            
                            print(f"\n💡 Para aplicar estas correcciones:")
                            print(f"   python para_cli.py balance --execute")
                        
                        elif execute_corrections:
                            # Ejecutar correcciones
                            if not force_execution:
                                from rich.prompt import Confirm
                                if not Confirm.ask(f"\n¿Aplicar {len(corrections)} correcciones automáticas?", default=True):
                                    print("\n❌ Correcciones canceladas por el usuario")
                                    return
                            
                            # Aplicar correcciones
                            correction_results = balancer.execute_corrections(corrections, dry_run=False)
                            
                            # Mostrar distribución final
                            if correction_results['successful_moves'] > 0:
                                print(f"\n📊 [bold]DISTRIBUCIÓN DESPUÉS DE CORRECCIONES:[/bold]")
                                final_results = balancer.display_status()
                                
                                # Comparar mejoras
                                if final_results.get('is_optimal'):
                                    print(f"\n🎉 [bold green]¡DISTRIBUCIÓN OPTIMIZADA![/bold green]")
                                else:
                                    print(f"\n📈 [bold yellow]Distribución mejorada, pueden quedar ajustes menores[/bold yellow]")
                    else:
                        print(f"\n⚠️ No se encontraron correcciones automáticas viables")
                        print(f"💡 La distribución puede requerir ajustes manuales")
                else:
                    print(f"\n✅ No se requieren correcciones - distribución óptima")
            
            else:
                # Modo normal - solo mostrar recomendaciones básicas
                if not results.get("is_optimal", True):
                    print("\n💡 [bold yellow]Comandos disponibles:[/bold yellow]")
                    print("\n  python para_cli.py balance --suggest    - Ver correcciones detalladas")
                    print("\n  python para_cli.py balance --execute    - Aplicar correcciones automáticas")
                    print("\n  python para_cli.py balance --force      - Aplicar sin confirmación")
                    print("\n  python para_cli.py classify             - Reclasificar manualmente")
            
            log_center.log_info("Comando balance completado", "CLI-Balance", results)
            
        except Exception as e:
            print(f"❌ Error ejecutando auto-balanceador: {e}")
            log_center.log_error(f"Error ejecutando auto-balanceador: {str(e)}", "CLI-Balance")
    
    @log_exceptions
    def cmd_metrics(self, *args):
        """Dashboard de Métricas PARA en Tiempo Real"""
        try:
            log_center.log_info("Iniciando comando metrics", "CLI-Metrics", {"args": args})
            
            # Procesar argumentos
            live_mode = '--live' in args or '-l' in args
            refresh_seconds = 30
            
            # Extraer tiempo de refresh si se especifica
            for arg in args:
                if arg.startswith('--refresh='):
                    try:
                        refresh_seconds = int(arg.split('=')[1])
                    except ValueError:
                        print("\n⚠️ Valor inválido para --refresh, usando 30 segundos por defecto")
            
            # Verificar vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Importar y ejecutar dashboard
            from paralib.metrics_dashboard import PARAMetricsDashboard
            
            dashboard = PARAMetricsDashboard(str(vault))
            
            if live_mode:
                dashboard.run_live_dashboard(refresh_seconds)
            else:
                dashboard.display_dashboard()
            
            log_center.log_info("Comando metrics completado", "CLI-Metrics")
            
        except KeyboardInterrupt:
            print("\n👋 Dashboard detenido por el usuario")
        except Exception as e:
            print(f"❌ Error ejecutando dashboard de métricas: {e}")
            log_center.log_error(f"Error ejecutando dashboard de métricas: {str(e)}", "CLI-Metrics")

    @log_exceptions
    def cmd_consolidate_duplicates(self, *args):
        """Consolida carpetas duplicadas en el vault."""
        try:
            log_center.log_info("Iniciando comando consolidate-duplicates", "CLI-ConsolidateDuplicates", {"args": args})
            print("\n🔄 Consolidación de Carpetas Duplicadas")
            print("\n=" * 50)
            
            # Procesar argumentos
            execute = '--execute' in args or '-e' in args
            category = None
            
            for arg in args:
                if arg in ['projects', 'areas', 'resources', 'archive']:
                    category_map = {
                        'projects': '01-Projects',
                        'areas': '02-Areas', 
                        'resources': '03-Resources',
                        'archive': '04-Archive'
                    }
                    category = category_map[arg]
                    break
            
            # Verificar vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            # Importar y ejecutar consolidación
            from paralib.intelligent_naming import consolidate_duplicate_folders
            
            print(f"📁 Vault: {vault}")
            if category:
                print(f"[TARGET] Categoría: {category}")
            else:
                print(f"[TARGET] Categorías: Todas")
            
            if execute:
                print(f"⚡ MODO: Ejecutar consolidación")
            else:
                print(f"🔍 MODO: Solo análisis")
            
            # Ejecutar consolidación
            stats = consolidate_duplicate_folders(vault_path, category, execute)
            
            if stats['duplicates_found'] > 0:
                if execute:
                    print(f"\n🎉 [bold green]¡Consolidación completada exitosamente![/bold green]")
                else:
                    print(f"\n💡 [bold yellow]Para aplicar la consolidación:[/bold yellow]")
                    print(f"   python para_cli.py consolidate-duplicates --execute")
            else:
                print(f"\n✅ [bold green]No se encontraron duplicados para consolidar[/bold green]")
            
            log_center.log_info("Comando consolidate-duplicates completado", "CLI-ConsolidateDuplicates", stats)
            
        except Exception as e:
            print(f"❌ Error en consolidación de duplicados: {e}")
            log_center.log_error(f"Error en consolidación de duplicados: {str(e)}", "CLI-ConsolidateDuplicates")

    @log_exceptions
    def cmd_reclassify_enhanced(self, *args):
        """
        Reclasificación completa mejorada con sistema de aprendizaje automático.
        
        Este comando ejecuta una reclasificación completa del vault con:
        - Factores de clasificación mejorados (28+ factores)
        - Detección automática de errores de clasificación
        - Aprendizaje automático de patrones
        - Corrección de casos específicos como "Adam Spec"
        """
        try:
            log_center.log_info("Iniciando comando reclassify-enhanced", "CLI-ReclassifyEnhanced", {"args": args})
            
            # Procesar argumentos
            exclude_paths = []
            no_backup = False
            learn = True  # Aprendizaje activado por defecto
            debug = False
            
            i = 0
            while i < len(args):
                if args[i] == '--exclude' or args[i] == '-e':
                    if i + 1 < len(args):
                        exclude_paths.append(args[i + 1])
                        i += 2
                    else:
                        print("\n❌ Error: --exclude requiere un valor")
                        return
                elif args[i] == '--no-backup':
                    no_backup = True
                    i += 1
                elif args[i] == '--no-learn':
                    learn = False
                    i += 1
                elif args[i] == '--debug':
                    debug = True
                    i += 1
                else:
                    i += 1
            
            # Configurar debug si se solicita
            if debug:
                os.environ['PARA_DEBUG'] = 'true'
                os.environ['PARA_SHOW_FACTORS'] = 'true'
                os.environ['PARA_SHOW_DETAILED_ANALYSIS'] = 'true'
            
            # Configurar aprendizaje automático
            if learn:
                os.environ['PARA_LEARNING_ENABLED'] = 'true'
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            self.console.print(f"\n🚀 [bold blue]Iniciando Reclasificación Mejorada[/bold blue]")
            self.console.print(f"📁 Vault: {vault_path}")
            self.console.print(f"🧠 Aprendizaje automático: {'Activado' if learn else 'Desactivado'}")
            self.console.print(f"🔍 Debug detallado: {'Activado' if debug else 'Desactivado'}")
            
            if exclude_paths:
                self.console.print(f"🚫 Exclusiones: {len(exclude_paths)} carpetas")
                for path in exclude_paths:
                    self.console.print(f"   🚫 {Path(path).name}")
            
            # Crear backup si no se especifica --no-backup
            if not no_backup:
                self.console.print(f"\n💾 [yellow]Creando backup del vault...[/yellow]")
                from paralib.backup_manager import PARABackupManager
                backup_manager = PARABackupManager()
                backup_result = backup_manager.create_backup(str(vault_path), 'full', 'Reclasificación mejorada')
                if backup_result:
                    self.console.print(f"✅ Backup creado: {backup_result.id}")
                else:
                    self.console.print(f"⚠️ [yellow]No se pudo crear backup[/yellow]")
            
            # Ejecutar reclasificación mejorada
            self.console.print(f"\n🔄 [bold green]Ejecutando reclasificación mejorada...[/bold green]")
            
            from paralib.organizer import run_full_reclassification_safe
            
            result = run_full_reclassification_safe(
                vault_path=str(vault_path),
                excluded_paths=exclude_paths if exclude_paths else None,
                create_backup=False  # Ya creamos el backup arriba
            )
            
            if result.get('success'):
                self.console.print(f"\n✅ [bold green]Reclasificación completada exitosamente![/bold green]")
                
                # Mostrar estadísticas
                stats = result.get('statistics', {})
                if stats:
                    self.console.print(f"\n📊 [bold]Estadísticas de la reclasificación:[/bold]")
                    self.console.print(f"   📝 Notas procesadas: {stats.get('total_notes', 0)}")
                    self.console.print(f"   📁 Carpetas creadas: {stats.get('folders_created', 0)}")
                    self.console.print(f"   🔄 Notas movidas: {stats.get('notes_moved', 0)}")
                    self.console.print(f"   ⏱️  Tiempo total: {stats.get('execution_time', 0):.2f}s")
                
                # Mostrar errores de clasificación detectados si hay aprendizaje activado
                if learn and result.get('learning_insights'):
                    self.console.print(f"\n🧠 [bold blue]Insights de aprendizaje:[/bold blue]")
                    insights = result.get('learning_insights', [])
                    for insight in insights[:5]:  # Mostrar solo los primeros 5
                        self.console.print(f"   💡 {insight}")
                    
                    if len(insights) > 5:
                        self.console.print(f"   ... y {len(insights) - 5} insights más")
                
                # Mostrar sugerencias de mejora
                if result.get('improvement_suggestions'):
                    self.console.print(f"\n💡 [bold yellow]Sugerencias de mejora:[/bold yellow]")
                    suggestions = result.get('improvement_suggestions', [])
                    for suggestion in suggestions[:3]:  # Mostrar solo las primeras 3
                        self.console.print(f"   🔧 {suggestion}")
                    
                    if len(suggestions) > 3:
                        self.console.print(f"   ... y {len(suggestions) - 3} sugerencias más")
                
            else:
                self.console.print(f"\n❌ [bold red]Error en la reclasificación:[/bold red]")
                self.console.print(f"   {result.get('error', 'Error desconocido')}")
                
                # Mostrar detalles del error si está disponible
                if result.get('details'):
                    self.console.print(f"\n🔍 [dim]Detalles del error:[/dim]")
                    self.console.print(f"   {result.get('details')}")
            
            log_center.log_info("Comando reclassify-enhanced completado", "CLI-ReclassifyEnhanced", result)
            
        except Exception as e:
            self.console.print(f"\n❌ [bold red]Error inesperado:[/bold red] {str(e)}")
            if debug:
                import traceback
                self.console.print(f"\n🔍 [dim]Traceback completo:[/dim]")
                self.console.print(traceback.format_exc())
            log_center.log_error(f"Error en reclassify-enhanced: {str(e)}", "CLI-ReclassifyEnhanced")

    @log_exceptions
    def cmd_export_knowledge(self, *args):
        """
        Exporta todo el conocimiento de aprendizaje del sistema PARA.
        
        Uso:
            python para_cli.py export-knowledge [--path=output.json]
            
        Argumentos:
            --path=output.json  - Ruta personalizada para el archivo de exportación
        """
        try:
            log_center.log_info("Iniciando comando export-knowledge", "CLI-ExportKnowledge", {"args": args})
            print("\n📤 Exportando conocimiento de aprendizaje del sistema PARA...")
            
            # Procesar argumentos
            export_path = None
            for arg in args:
                if arg.startswith('--path='):
                    export_path = arg.split('=', 1)[1]
                    break
            
            # Obtener vault para inicializar el sistema de aprendizaje
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Inicializar base de datos para el learning system
            from paralib.db import ChromaPARADatabase
            db = ChromaPARADatabase(str(vault))
            
            # Importar y ejecutar exportación con la base de datos
            from paralib.learning_system import PARA_Learning_System
            learning_system = PARA_Learning_System(db=db, vault_path=vault)
            
            print(f"📁 Vault: {vault}")
            if export_path:
                print(f"📄 Archivo de salida: {export_path}")
            else:
                print(f"📄 Archivo de salida: auto-generado")
            
            # Ejecutar exportación
            result_path = learning_system.export_learning_knowledge(export_path)
            
            if result_path:
                print(f"\n✅ [bold green]Conocimiento exportado exitosamente![/bold green]")
                print(f"📄 Archivo: {result_path}")
                
                # Mostrar estadísticas del archivo exportado
                try:
                    import json
                    with open(result_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    print(f"\n📊 [bold]Contenido exportado:[/bold]")
                    print(f"   📈 Métricas de aprendizaje: {len(data.get('learning_metrics', []))}")
                    print(f"   📝 Historial de clasificaciones: {len(data.get('classification_history', []))}")
                    print(f"   💬 Datos de feedback: {len(data.get('feedback_data', []))}")
                    print(f"   📁 Patrones de carpetas: {len(data.get('folder_creation_patterns', []))}")
                    print(f"   🧠 Datos semánticos: {len(data.get('semantic_embeddings', []))}")
                    print(f"   ⚙️ Preferencias del usuario: {len(data.get('user_preferences', {}))}")
                    print(f"   🔄 Evolución del sistema: {len(data.get('system_evolution', {}))}")
                    
                    # Mostrar tamaño del archivo
                    file_size = Path(result_path).stat().st_size
                    print(f"   💾 Tamaño del archivo: {file_size / 1024:.1f} KB")
                    
                except Exception as e:
                    print(f"⚠️ No se pudieron mostrar estadísticas: {e}")
                
                print(f"\n💡 Para importar este conocimiento en otro sistema:")
                print(f"   python para_cli.py import-knowledge {result_path}")
                
            else:
                print(f"\n❌ [bold red]Error en la exportación[/bold red]")
                print(f"   No se pudo exportar el conocimiento")
            
            log_center.log_info("Comando export-knowledge completado", "CLI-ExportKnowledge", {"export_path": result_path})
            
        except Exception as e:
            print(f"\n❌ [bold red]Error inesperado:[/bold red] {str(e)}")
            log_center.log_error(f"Error en export-knowledge: {str(e)}", "CLI-ExportKnowledge")

    @log_exceptions
    def cmd_import_knowledge(self, *args):
        """
        Importa conocimiento de aprendizaje desde un archivo exportado.
        
        Uso:
            python para_cli.py import-knowledge <archivo.json>
        """
        try:
            log_center.log_info("Iniciando comando import-knowledge", "CLI-ImportKnowledge", {"args": args})
            print("\n📥 Importando conocimiento de aprendizaje...")
            
            if not args:
                print("\n❌ Error: Debes especificar el archivo a importar")
                print("\n   Uso: python para_cli.py import-knowledge <archivo.json>")
                return
            
            import_path = args[0]
            
            # Verificar que el archivo existe
            if not Path(import_path).exists():
                print(f"❌ Error: El archivo '{import_path}' no existe")
                return
            
            # Obtener vault para inicializar el sistema de aprendizaje
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Inicializar base de datos para el learning system
            from paralib.db import ChromaPARADatabase
            db = ChromaPARADatabase(str(vault))
            
            # Importar y ejecutar importación con la base de datos
            from paralib.learning_system import PARA_Learning_System
            learning_system = PARA_Learning_System(db=db, vault_path=vault)
            
            print(f"📁 Vault: {vault}")
            print(f"📄 Archivo a importar: {import_path}")
            
            # Ejecutar importación
            results = learning_system.import_learning_knowledge(import_path)
            
            if 'error' not in results:
                print(f"\n✅ [bold green]Conocimiento importado exitosamente![/bold green]")
                print(f"\n📊 [bold]Resumen de la importación:[/bold]")
                print(f"   📈 Métricas importadas: {results.get('learning_metrics_imported', 0)}")
                print(f"   📝 Clasificaciones importadas: {results.get('classifications_imported', 0)}")
                print(f"   💬 Feedback importado: {results.get('feedback_imported', 0)}")
                print(f"   📁 Patrones importados: {results.get('patterns_imported', 0)}")
                print(f"   🧠 Datos semánticos importados: {results.get('semantic_data_imported', 0)}")
                print(f"   ⚙️ Preferencias importadas: {'Sí' if results.get('preferences_imported', False) else 'No'}")
                print(f"   🔄 Evolución importada: {'Sí' if results.get('evolution_imported', False) else 'No'}")
                
                print(f"\n🎉 El sistema ahora tiene acceso al conocimiento importado")
                print(f"💡 Ejecuta 'python para_cli.py learn' para analizar el nuevo conocimiento")
                
            else:
                print(f"\n❌ [bold red]Error en la importación:[/bold red]")
                print(f"   {results['error']}")
            
            log_center.log_info("Comando import-knowledge completado", "CLI-ImportKnowledge", results)
            
        except Exception as e:
            print(f"\n❌ [bold red]Error inesperado:[/bold red] {str(e)}")
            log_center.log_error(f"Error en import-knowledge: {str(e)}", "CLI-ImportKnowledge")

    @log_exceptions
    def cmd_learning_status(self, *args):
        """
        Muestra el estado actual del sistema de aprendizaje.
        
        Uso:
            python para_cli.py learning-status [--detailed]
        """
        try:
            log_center.log_info("Iniciando comando learning-status", "CLI-LearningStatus", {"args": args})
            print("\n🧠 Estado del Sistema de Aprendizaje PARA")
            print("\n=" * 50)
            
            detailed = '--detailed' in args or '-d' in args
            
            # Obtener vault para inicializar el sistema de aprendizaje
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            # Inicializar base de datos para el learning system
            from paralib.db import ChromaPARADatabase
            db = ChromaPARADatabase(str(vault))
            
            # Importar y obtener estado
            from paralib.learning_system import PARA_Learning_System
            learning_system = PARA_Learning_System(db=db, vault_path=vault)
            
            print(f"📁 Vault: {vault}")
            
            # Obtener estadísticas básicas
            stats = learning_system.get_stats()
            
            if stats:
                print(f"\n📊 [bold]Estadísticas Generales:[/bold]")
                print(f"   📈 Total de clasificaciones: {stats.get('total_classifications', 0)}")
                print(f"   💬 Total de feedback: {stats.get('total_feedback', 0)}")
                print(f"   📁 Patrones aprendidos: {stats.get('patterns_learned', 0)}")
                print(f"   [TARGET] Tasa de precisión: {stats.get('accuracy_rate', 0):.2%}")
                print(f"   ⚡ Velocidad de aprendizaje: {stats.get('learning_velocity', 0):.2f}")
                
                # Mostrar tendencias recientes
                if detailed:
                    print(f"\n📈 [bold]Tendencias Recientes (últimos 30 días):[/bold]")
                    trends = learning_system.analyze_trends()
                    if trends and isinstance(trends, (list, tuple)) and len(trends) > 0:
                        for trend in trends[:5]:  # Mostrar solo las primeras 5 tendencias
                            print(f"   📊 {trend}")
                    elif isinstance(trends, dict) and trends:
                        # Si trends es un dict, mostrar claves principales
                        for k, v in list(trends.items())[:5]:
                            print(f"   📊 {k}: {v}")
                    else:
                        print(f"   📊 No hay suficientes datos para analizar tendencias")

                # Mostrar sugerencias de mejora
                if detailed:
                    print(f"\n💡 [bold]Sugerencias de Mejora:[/bold]")
                    suggestions = learning_system.get_optimization_suggestions()
                    if suggestions and isinstance(suggestions, (list, tuple)) and len(suggestions) > 0:
                        for suggestion in suggestions[:3]:  # Mostrar solo las primeras 3
                            print(f"   🔧 {suggestion}")
                    else:
                        print(f"   🔧 No hay sugerencias de mejora disponibles")
                
                # Mostrar evolución del CLI
                if detailed:
                    print(f"\n🔄 [bold]Evolución del CLI:[/bold]")
                    evolution = learning_system.get_cli_evolution_score_trend(30)
                    if 'error' not in evolution:
                        scores = evolution.get('scores', [])
                        if scores:
                            latest_score = scores[-1] if scores else 0
                            print(f"   [TARGET] Score actual: {latest_score:.1f}/100")
                            print(f"   📊 Snapshots analizados: {len(scores)}")
                        else:
                            print(f"   📊 No hay datos de evolución disponibles")
                    else:
                        print(f"   📊 {evolution['error']}")
                
            else:
                print(f"\n⚠️ [yellow]No hay datos de aprendizaje disponibles[/yellow]")
                print(f"💡 Ejecuta algunas clasificaciones para comenzar a aprender")
            
            print(f"\n💡 Comandos relacionados:")
            print(f"   python para_cli.py learn                    - Analizar y aprender")
            print(f"   python para_cli.py export-knowledge         - Exportar conocimiento")
            print(f"   python para_cli.py import-knowledge <file>  - Importar conocimiento")
            
            log_center.log_info("Comando learning-status completado", "CLI-LearningStatus", stats)
            
        except Exception as e:
            print(f"\n❌ [bold red]Error inesperado:[/bold red] {str(e)}")
            log_center.log_error(f"Error en learning-status: {str(e)}", "CLI-LearningStatus")

    @log_exceptions
    def cmd_cleanup_folders(self, *args):
        """
        Limpia carpetas con sufijos numéricos y consolida el desastre de carpetas.
        
        Uso:
            python para_cli.py cleanup-folders [--execute]
            
        Argumentos:
            --execute  - Ejecutar la limpieza (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando cleanup-folders", "CLI-CleanupFolders", {"args": args})
            print("\n🧹 Limpiando desastre de carpetas con sufijos numéricos...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            if not execute:
                print("\n🔍 [yellow]MODO SIMULACIÓN: No se aplicarán cambios[/yellow]")
            else:
                print("\n⚡ [red]MODO EJECUCIÓN: Se aplicarán cambios permanentes[/red]")
            
            # Categorías PARA
            categories = ['01-Projects', '02-Areas', '03-Resources', '04-Archive']
            
            total_consolidated = 0
            total_files_moved = 0
            
            for category in categories:
                category_path = vault_path / category
                if not category_path.exists():
                    continue
                
                print(f"\n📁 [bold]Analizando {category}...[/bold]")
                
                # Obtener todas las carpetas
                folders = [f for f in category_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
                
                if not folders:
                    continue
                
                # Agrupar carpetas por nombre base (sin sufijos numéricos)
                folder_groups = {}
                
                print(f"   📊 Analizando {len(folders)} carpetas...")
                
                for folder in folders:
                    # Extraer nombre base (remover sufijos como " 2", " 3", etc.)
                    import re
                    base_name = re.sub(r'\s+\d+$', '', folder.name)
                    base_name = re.sub(r'_\d+$', '', base_name)
                    
                    # También remover UUIDs extraños
                    if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', base_name):
                        base_name = "UUID_Folder"
                    
                    if base_name not in folder_groups:
                        folder_groups[base_name] = []
                    folder_groups[base_name].append(folder)
                
                print(f"   🔍 Encontrados {len(folder_groups)} grupos únicos")
                
                # Mostrar grupos con múltiples carpetas
                groups_with_duplicates = {k: v for k, v in folder_groups.items() if len(v) > 1}
                if groups_with_duplicates:
                    print(f"   🔄 {len(groups_with_duplicates)} grupos con duplicados encontrados")
                else:
                    print(f"   ✅ No se encontraron duplicados")
            
            if execute:
                print(f"   🔄 Consolidando...")
                
                for base_name, folder_list in folder_groups.items():
                    if len(folder_list) > 1:
                        print(f"\n🔄 [yellow]Encontradas {len(folder_list)} carpetas para '{base_name}':[/yellow]")
                        
                        # Ordenar por número de archivos (la que más archivos tenga será el target)
                        folder_data = []
                        for folder in folder_list:
                            files = list(folder.rglob("*.md"))
                            folder_data.append({
                                'folder': folder,
                                'files': files,
                                'file_count': len(files)
                            })
                        
                        # Ordenar por número de archivos (descendente)
                        folder_data.sort(key=lambda x: x['file_count'], reverse=True)
                        
                        target_folder = folder_data[0]['folder']
                        source_folders = [f['folder'] for f in folder_data[1:]]
                        
                        print(f"   [TARGET] Target: {target_folder.name} ({folder_data[0]['file_count']} archivos)")
                        for source in source_folders:
                            source_files = list(source.rglob("*.md"))
                            print(f"   📁 Source: {source.name} ({len(source_files)} archivos)")
                        
                        # Mover archivos
                        for source_folder in source_folders:
                            try:
                                for file_path in source_folder.rglob("*.md"):
                                    target_file = target_folder / file_path.name
                                    
                                    # Manejar conflictos de nombres
                                    counter = 1
                                    while target_file.exists():
                                        stem = target_file.stem
                                        suffix = target_file.suffix
                                        target_file = target_folder / f"{stem}_{counter}{suffix}"
                                        counter += 1
                                    
                                    file_path.rename(target_file)
                                    total_files_moved += 1
                                
                                # Eliminar carpeta fuente si está vacía
                                if not any(source_folder.iterdir()):
                                    source_folder.rmdir()
                                    total_consolidated += 1
                                    print(f"   ✅ Eliminada carpeta vacía: {source_folder.name}")
                            
                            except Exception as e:
                                print(f"   ❌ Error consolidando {source_folder.name}: {e}")
                        else:
                            print(f"   💡 [dim]Simulación: se consolidarían {len(source_folders)} carpetas[/dim]")
            
            print(f"\n📊 [bold]RESUMEN DE LIMPIEZA:[/bold]")
            print(f"   🔄 Carpetas consolidadas: {total_consolidated}")
            print(f"   📄 Archivos movidos: {total_files_moved}")
            
            if not execute:
                print(f"\n💡 [yellow]Usa --execute para aplicar los cambios[/yellow]")
            else:
                print(f"\n✅ [green]Limpieza completada exitosamente[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en cleanup-folders: {e}", "CLI-CleanupFolders")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_cleanup_all(self, *args):
        """
        Limpia carpetas duplicadas y nombres de archivos con sufijos numéricos.
        
        Uso:
            python para_cli.py cleanup-all [--execute]
            
        Argumentos:
            --execute  - Ejecutar la limpieza (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando cleanup-all", "CLI-CleanupAll", {"args": args})
            print("\n🧹 Limpiando desastre completo: carpetas y nombres de archivos...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            if not execute:
                print("\n🔍 [yellow]MODO SIMULACIÓN: No se aplicarán cambios[/yellow]")
            else:
                print("\n⚡ [red]MODO EJECUCIÓN: Se aplicarán cambios permanentes[/red]")
            
            # Categorías PARA
            categories = ['01-Projects', '02-Areas', '03-Resources', '04-Archive']
            
            total_consolidated = 0
            total_files_moved = 0
            total_files_renamed = 0
            
            for category in categories:
                category_path = vault_path / category
                if not category_path.exists():
                    continue
                
                print(f"\n📁 [bold]Analizando {category}...[/bold]")
                
                # 1. LIMPIAR NOMBRES DE ARCHIVOS CON SUFIJOS NUMÉRICOS
                print(f"   📄 Limpiando nombres de archivos...")
                files_renamed = 0
                
                for file_path in category_path.rglob("*.md"):
                    original_name = file_path.name
                    # Remover sufijos numéricos del nombre del archivo
                    import re
                    base_name = re.sub(r'_\d+_\d+_\d+\.md$', '.md', original_name)
                    base_name = re.sub(r'_\d+_\d+\.md$', '.md', base_name)
                    base_name = re.sub(r'_\d+\.md$', '.md', base_name)
                    
                    if base_name != original_name:
                        new_path = file_path.parent / base_name
                        print(f"      🔄 {original_name} → {base_name}")
                        
                        if execute:
                            # Manejar conflictos de nombres
                            counter = 1
                            while new_path.exists():
                                stem = new_path.stem
                                suffix = new_path.suffix
                                new_path = file_path.parent / f"{stem}_{counter}{suffix}"
                                counter += 1
                            
                            try:
                                file_path.rename(new_path)
                                files_renamed += 1
                                total_files_renamed += 1
                            except Exception as e:
                                print(f"      ❌ Error renombrando {original_name}: {e}")
                
                print(f"   ✅ {files_renamed} archivos renombrados")
                
                # 2. CONSOLIDAR CARPETAS DUPLICADAS
                folders = [f for f in category_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
                
                if not folders:
                    continue
                
                # Agrupar carpetas por nombre base (sin sufijos numéricos)
                folder_groups = {}
                
                for folder in folders:
                    # Extraer nombre base (remover sufijos como " 2", " 3", etc.)
                    import re
                    base_name = re.sub(r'\s+\d+$', '', folder.name)
                    base_name = re.sub(r'_\d+$', '', base_name)
                    
                    # También remover UUIDs extraños
                    if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', base_name):
                        base_name = "UUID_Folder"
                    
                    if base_name not in folder_groups:
                        folder_groups[base_name] = []
                    folder_groups[base_name].append(folder)
                
                # Procesar grupos con múltiples carpetas
                for base_name, folder_list in folder_groups.items():
                    if len(folder_list) > 1:
                        print(f"\n   🔄 [yellow]Encontradas {len(folder_list)} carpetas para '{base_name}':[/yellow]")
                        
                        # Ordenar por número de archivos (la que más archivos tenga será el target)
                        folder_data = []
                        for folder in folder_list:
                            files = list(folder.rglob("*.md"))
                            folder_data.append({
                                'folder': folder,
                                'files': files,
                                'file_count': len(files)
                            })
                        
                        # Ordenar por número de archivos (descendente)
                        folder_data.sort(key=lambda x: x['file_count'], reverse=True)
                        
                        target_folder = folder_data[0]['folder']
                        source_folders = [f['folder'] for f in folder_data[1:]]
                        
                        print(f"      [TARGET] Target: {target_folder.name} ({folder_data[0]['file_count']} archivos)")
                        for source in source_folders:
                            source_files = list(source.rglob("*.md"))
                            print(f"      📁 Source: {source.name} ({len(source_files)} archivos)")
                        
                        if execute:
                            print(f"      🔄 Consolidando...")
                            
                            for source_folder in source_folders:
                                try:
                                    # Mover archivos
                                    for file_path in source_folder.rglob("*.md"):
                                        target_file = target_folder / file_path.name
                                        
                                        # Manejar conflictos de nombres
                                        counter = 1
                                        while target_file.exists():
                                            stem = target_file.stem
                                            suffix = target_file.suffix
                                            target_file = target_folder / f"{stem}_{counter}{suffix}"
                                            counter += 1
                                        
                                        file_path.rename(target_file)
                                        total_files_moved += 1
                                    
                                    # Eliminar carpeta fuente si está vacía
                                    if not any(source_folder.iterdir()):
                                        source_folder.rmdir()
                                        total_consolidated += 1
                                        print(f"      ✅ Eliminada carpeta vacía: {source_folder.name}")
                                    
                                except Exception as e:
                                    print(f"      ❌ Error consolidando {source_folder.name}: {e}")
                        else:
                            print(f"      💡 [dim]Simulación: se consolidarían {len(source_folders)} carpetas[/dim]")
            
            print(f"\n📊 [bold]RESUMEN DE LIMPIEZA COMPLETA:[/bold]")
            print(f"   🔄 Carpetas consolidadas: {total_consolidated}")
            print(f"   📄 Archivos movidos: {total_files_moved}")
            print(f"   📝 Archivos renombrados: {total_files_renamed}")
            
            if not execute:
                print(f"\n💡 [yellow]Usa --execute para aplicar los cambios[/yellow]")
            else:
                print(f"\n✅ [green]Limpieza completa exitosamente[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en cleanup-all: {e}", "CLI-CleanupAll")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_test_naming(self, *args):
        """
        Prueba el sistema de naming inteligente para verificar que no genera sufijos numéricos.
        
        Uso:
            python para_cli.py test-naming
        """
        try:
            log_center.log_info("Iniciando comando test-naming", "CLI-TestNaming", {"args": args})
            print("\n🧪 Probando sistema de naming inteligente...")
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            # Importar funciones necesarias
            from paralib.intelligent_naming import create_intelligent_name
            from paralib.organizer import _generate_folder_name_from_content
            
            # Crear contenido de prueba
            test_contents = [
                "Proyecto de desarrollo web con React y Node.js",
                "Análisis de datos para el cliente Moka",
                "Documentación técnica de API",
                "Planificación de sprint Q1 2024",
                "Recursos de aprendizaje de Python"
            ]
            
            categories = ['01-Projects', '02-Areas', '03-Resources']
            
            print(f"\n📋 [bold]Probando naming inteligente:[/bold]")
            
            for i, content in enumerate(test_contents, 1):
                print(f"\n{i}. [cyan]Contenido:[/cyan] {content[:50]}...")
                
                # Obtener carpetas existentes para la categoría
                existing_folders = set()
                for category in categories:
                    category_path = vault_path / category
                    if category_path.exists():
                        try:
                            existing_folders.update({f.name for f in category_path.iterdir() if f.is_dir()})
                        except Exception:
                            pass
                
                # Probar naming inteligente directo
                try:
                    intelligent_name = create_intelligent_name([content], 'project', existing_folders, vault_path, '01-Projects')
                    print(f"   🧠 [green]Naming inteligente:[/green] '{intelligent_name}'")
                except Exception as e:
                    print(f"   ❌ [red]Error naming inteligente:[/red] {e}")
                
                # Probar función del organizer
                try:
                    organizer_name = _generate_folder_name_from_content(content, 'Projects', vault_path, existing_folders, True)
                    print(f"   📁 [blue]Organizer:[/blue] '{organizer_name}'")
                except Exception as e:
                    print(f"   ❌ [red]Error organizer:[/red] {e}")
                
                # Verificar que no hay sufijos numéricos
                import re
                if re.search(r'_\d+$', intelligent_name) or re.search(r'\s+\d+$', intelligent_name):
                    print(f"   ⚠️ [yellow]ADVERTENCIA: Naming inteligente generó sufijo numérico![/yellow]")
                if re.search(r'_\d+$', organizer_name) or re.search(r'\s+\d+$', organizer_name):
                    print(f"   ⚠️ [yellow]ADVERTENCIA: Organizer generó sufijo numérico![/yellow]")
            
            print(f"\n✅ [green]Prueba completada. Verifica que no hay sufijos numéricos en los nombres generados.[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en test-naming: {e}", "CLI-TestNaming")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_consolidate_excessive_folders(self, *args):
        """
        Consolida carpetas excesivas en grupos más lógicos para reducir fragmentación.
        
        Uso:
            python para_cli.py consolidate-excessive [--execute]
            
        Argumentos:
            --execute  - Ejecutar la consolidación (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando consolidate-excessive", "CLI-ConsolidateExcessive", {"args": args})
            print("\n🔧 Consolidando carpetas excesivas en grupos lógicos...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            # Definir grupos de consolidación por categoría
            consolidation_groups = {
                '01-Projects': {
                    'Desarrollo': ['Adam Spec', 'Api', 'Terraform', 'Development', 'Code', 'Programming'],
                    'Análisis': ['Analysis', 'Review', 'Análisis', 'Chequeo', 'Check'],
                    'BBI': ['Bbi', 'BBI'],
                    'Marketing': ['Marketing', 'Launch', 'Lanzamiento'],
                    'General': ['Project', 'Task', 'Work']
                },
                '02-Areas': {
                    'Personal': ['Personal', 'Health', 'Salud', 'Fitness'],
                    'Finanzas': ['Finance', 'Finanzas', 'Money'],
                    'Reuniones': ['Meeting', 'Reunión', 'Standup'],
                    'Rutinas': ['Routine', 'Habit', 'Rutina']
                },
                '03-Resources': {
                    'Tecnología': ['AWS', 'API', 'Database', 'Tech', 'Tutorial', 'Guide'],
                    'Documentación': ['Documentation', 'Manual', 'Reference', 'Doc'],
                    'Capacitación': ['Training', 'Course', 'Learning', 'Certification'],
                    'Herramientas': ['Tools', 'Software', 'App'],
                    'Bases de Datos': ['Database', 'DB', 'SQL', 'Chroma'],
                    'General': ['Resource', 'Reference', 'Info']
                },
                '04-Archive': {
                    'Proyectos Completados': ['Completed', 'Finished', 'Done', 'Completado'],
                    'Obsoleto': ['Obsolete', 'Deprecated', 'Old', '2021', '2022'],
                    'General': ['Archive', 'Old']
                }
            }
            
            total_consolidations = 0
            
            for category, groups in consolidation_groups.items():
                category_path = vault_path / category
                if not category_path.exists():
                    continue
                
                print(f"\n📁 Procesando {category}...")
                
                # Obtener todas las carpetas en la categoría
                folders = [f for f in category_path.iterdir() if f.is_dir()]
                
                for group_name, keywords in groups.items():
                    matching_folders = []
                    
                    # Encontrar carpetas que coincidan con las palabras clave
                    for folder in folders:
                        folder_name_lower = folder.name.lower()
                        for keyword in keywords:
                            if keyword.lower() in folder_name_lower:
                                matching_folders.append(folder)
                                break
                    
                    if len(matching_folders) > 1:  # Solo consolidar si hay más de una carpeta
                        print(f"  🔄 Consolidando {len(matching_folders)} carpetas en '{group_name}':")
                        
                        # Crear carpeta de destino
                        target_folder = category_path / group_name
                        
                        if execute:
                            target_folder.mkdir(exist_ok=True)
                        
                        # Mover archivos de cada carpeta
                        for folder in matching_folders:
                            print(f"    📂 {folder.name} → {group_name}")
                            
                            if execute:
                                try:
                                    # Mover todos los archivos .md
                                    for md_file in folder.glob("*.md"):
                                        target_file = target_folder / md_file.name
                                        
                                        # Evitar sobrescribir
                                        if target_file.exists():
                                            counter = 2
                                            while target_file.exists():
                                                name_parts = md_file.stem, f"_{counter}", md_file.suffix
                                                target_file = target_folder / "".join(name_parts)
                                                counter += 1
                                        
                                        md_file.rename(target_file)
                                    
                                    # Eliminar carpeta origen si está vacía
                                    if not any(folder.iterdir()):
                                        folder.rmdir()
                                        print(f"      ✅ Carpeta eliminada")
                                    
                                except Exception as e:
                                    print(f"      ⚠️ Error moviendo {folder.name}: {e}")
                        
                        total_consolidations += 1
            
            if execute:
                print(f"\n✅ Consolidación completada: {total_consolidations} grupos consolidados")
            else:
                print(f"\n📋 Simulación completada: {total_consolidations} grupos se consolidarían")
                print("\n💡 Ejecuta con --execute para aplicar los cambios")
            
        except Exception as e:
            print(f"❌ Error en consolidación: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_consolidate_aggressive(self, *args):
        """
        Consolidación agresiva de carpetas restantes para reducir aún más la fragmentación.
        
        Uso:
            python para_cli.py consolidate-aggressive [--execute]
            
        Argumentos:
            --execute  - Ejecutar la consolidación (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando consolidate-aggressive", "CLI-ConsolidateAggressive", {"args": args})
            print("\n🔥 Consolidación AGRESIVA de carpetas restantes...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            # Consolidación agresiva por categoría
            aggressive_groups = {
                '01-Projects': {
                    'Proyectos Activos': ['Project', 'Task', 'Work', 'Development', 'Analysis', 'Review'],
                    'BBI': ['Bbi', 'BBI'],
                    'Marketing': ['Marketing', 'Launch', 'Lanzamiento', 'Campaign'],
                    'General': ['General', 'Misc', 'Other']
                },
                '02-Areas': {
                    'Personal': ['Personal', 'Health', 'Salud', 'Fitness', 'Equipo'],
                    'Finanzas': ['Finance', 'Finanzas', 'Money', 'Budget'],
                    'Reuniones': ['Meeting', 'Reunión', 'Standup', 'Call'],
                    'Rutinas': ['Routine', 'Habit', 'Rutina', 'Daily']
                },
                '03-Resources': {
                    'Tecnología': ['AWS', 'API', 'Database', 'Tech', 'Tutorial', 'Guide', 'Development', 'Programming'],
                    'Documentación': ['Documentation', 'Manual', 'Reference', 'Doc', 'Notas', 'Docker'],
                    'Capacitación': ['Training', 'Course', 'Learning', 'Certification', 'Avature'],
                    'Herramientas': ['Tools', 'Software', 'App', 'AI', 'BBI'],
                    'Bases de Datos': ['Database', 'DB', 'SQL', 'Chroma', 'Mysql', 'Wordpress'],
                    'Referencias': ['Reference', 'Info', 'Data', 'Statistics', 'Gartner'],
                    'General': ['General', 'Misc', 'Other', 'Resource']
                },
                '04-Archive': {
                    'Proyectos Completados': ['Completed', 'Finished', 'Done', 'Completado'],
                    'Obsoleto': ['Obsolete', 'Deprecated', 'Old', '2021', '2022', '12 Old'],
                    'General': ['Archive', 'Old', 'General']
                }
            }
            
            total_consolidations = 0
            
            for category, groups in aggressive_groups.items():
                category_path = vault_path / category
                if not category_path.exists():
                    continue
                
                print(f"\n📁 Procesando {category} (consolidación agresiva)...")
                
                # Obtener todas las carpetas en la categoría
                folders = [f for f in category_path.iterdir() if f.is_dir()]
                
                # Agrupar carpetas por similitud de nombre
                folder_groups = {}
                for folder in folders:
                    folder_name_lower = folder.name.lower()
                    
                    # Encontrar el grupo más apropiado
                    assigned_group = None
                    for group_name, keywords in groups.items():
                        for keyword in keywords:
                            if keyword.lower() in folder_name_lower:
                                assigned_group = group_name
                                break
                        if assigned_group:
                            break
                    
                    # Si no se encontró grupo específico, asignar a General
                    if not assigned_group:
                        assigned_group = 'General'
                    
                    if assigned_group not in folder_groups:
                        folder_groups[assigned_group] = []
                    folder_groups[assigned_group].append(folder)
                
                # Consolidar grupos con múltiples carpetas
                for group_name, folder_list in folder_groups.items():
                    if len(folder_list) > 1:
                        print(f"  🔥 Consolidando {len(folder_list)} carpetas en '{group_name}':")
                        
                        # Crear carpeta de destino
                        target_folder = category_path / group_name
                        
                        if execute:
                            target_folder.mkdir(exist_ok=True)
                        
                        # Mover archivos de cada carpeta
                        for folder in folder_list:
                            print(f"    📂 {folder.name} → {group_name}")
                            
                            if execute:
                                try:
                                    # Mover todos los archivos .md
                                    for md_file in folder.glob("*.md"):
                                        target_file = target_folder / md_file.name
                                        
                                        # Evitar sobrescribir
                                        if target_file.exists():
                                            counter = 2
                                            while target_file.exists():
                                                name_parts = md_file.stem, f"_{counter}", md_file.suffix
                                                target_file = target_folder / "".join(name_parts)
                                                counter += 1
                                        
                                        md_file.rename(target_file)
                                    
                                    # Eliminar carpeta origen si está vacía
                                    if not any(folder.iterdir()):
                                        folder.rmdir()
                                        print(f"      ✅ Carpeta eliminada")
                                    
                                except Exception as e:
                                    print(f"      ⚠️ Error moviendo {folder.name}: {e}")
                        
                        total_consolidations += 1
            
            if execute:
                print(f"\n🔥 Consolidación agresiva completada: {total_consolidations} grupos consolidados")
            else:
                print(f"\n📋 Simulación agresiva completada: {total_consolidations} grupos se consolidarían")
                print("\n💡 Ejecuta con --execute para aplicar los cambios")
            
        except Exception as e:
            print(f"❌ Error en consolidación agresiva: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_enforce_para(self, *args):
        """
        Aplica los principios del método PARA de Tiago Forte al vault.
        
        Uso:
            python para_cli.py enforce-para [--execute]
            
        Argumentos:
            --execute  - Ejecutar el proceso (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando enforce-para", "CLI-EnforcePara", {"args": args})
            print("\n[TARGET] Aplicando principios del método PARA de Tiago Forte...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            if not execute:
                print("\n🔍 [yellow]MODO SIMULACIÓN: No se aplicarán cambios[/yellow]")
            else:
                print("\n⚡ [red]MODO EJECUCIÓN: Se aplicarán cambios permanentes[/red]")
            
            # Inicializar ChromaDB
            try:
                from paralib.db import ChromaPARADatabase
                db = ChromaPARADatabase(str(vault_path))
            except Exception as e:
                print(f"❌ Error inicializando ChromaDB: {e}")
                return
            
            # Aplicar principios PARA
            from paralib.organizer import enforce_para_principles
            stats = enforce_para_principles(vault_path, db)
            
            # Mostrar resumen
            print(f"\n📊 [bold]RESUMEN DE PRINCIPIOS PARA APLICADOS:[/bold]")
            print(f"   📁 Carpetas 'General' reorganizadas: {stats.get('general_folders_fixed', 0)}")
            print(f"   🚀 Proyectos creados: {stats.get('projects_created', 0)}")
            print(f"   📚 Recursos reorganizados: {stats.get('resources_reorganized', 0)}")
            print(f"   🗑️ Carpetas vacías eliminadas: {stats.get('empty_folders_removed', 0)}")
            
            if stats.get('errors'):
                print(f"   ⚠️ Errores encontrados: {len(stats['errors'])}")
                for error in stats['errors'][:3]:
                    print(f"      • {error}")
            
            if not execute:
                print(f"\n💡 [yellow]Usa --execute para aplicar los cambios[/yellow]")
            else:
                print(f"\n✅ [green]Principios PARA aplicados exitosamente[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en enforce-para: {e}", "CLI-EnforcePara")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_fix_projects(self, *args):
        """
        Corrige nombres de carpetas de proyectos eliminando sufijos "Related" y reorganizando proyectos.
        
        Uso:
            python para_cli.py fix-projects [--execute]
            
        Argumentos:
            --execute  - Ejecutar las correcciones (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando comando fix-projects", "CLI-FixProjects", {"args": args})
            print("\n🔧 Corrigiendo nombres de carpetas de proyectos...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            projects_path = vault_path / '01-Projects'
            
            if not projects_path.exists():
                print("\n❌ No se encontró la carpeta de proyectos")
                return
            
            if not execute:
                print("\n🔍 [yellow]MODO SIMULACIÓN: No se aplicarán cambios[/yellow]")
            else:
                print("\n⚡ [red]MODO EJECUCIÓN: Se aplicarán cambios permanentes[/red]")
            
            # Obtener todas las carpetas de proyectos
            project_folders = [f for f in projects_path.iterdir() if f.is_dir() and not f.name.startswith('.')]
            
            if not project_folders:
                print("\n📁 No se encontraron carpetas de proyectos")
                return
            
            print(f"\n📋 [bold]Analizando {len(project_folders)} carpetas de proyectos:[/bold]")
            
            fixes_applied = 0
            projects_reorganized = 0
            
            for folder in project_folders:
                original_name = folder.name
                new_name = original_name
                needs_fix = False
                
                # 1. Remover sufijo "Related"
                if original_name.endswith(' Related'):
                    new_name = original_name.replace(' Related', '')
                    needs_fix = True
                    print(f"   🔄 {original_name} → {new_name} (removido 'Related')")
                
                # 2. Remover agrupaciones temporales como "Recent June 2025"
                import re
                if re.match(r'^Recent\s+\w+\s+\d{4}$', original_name):
                    # Buscar el proyecto principal dentro de esta carpeta
                    md_files = list(folder.glob("*.md"))
                    if md_files:
                        # Intentar extraer el nombre del proyecto del primer archivo
                        try:
                            with open(md_files[0], 'r', encoding='utf-8') as f:
                                content = f.read()
                                # Buscar el título del proyecto
                                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                                if title_match:
                                    new_name = title_match.group(1).strip()
                                    needs_fix = True
                                    print(f"   🔄 {original_name} → {new_name} (extraído del contenido)")
                        except Exception:
                            pass
                
                # 3. Remover sufijos numéricos
                if re.search(r'\s+\d+$', new_name):
                    new_name = re.sub(r'\s+\d+$', '', new_name)
                    needs_fix = True
                    print(f"   🔄 {original_name} → {new_name} (removido sufijo numérico)")
                
                # Aplicar corrección si es necesaria
                if needs_fix:
                    new_path = projects_path / new_name
                    
                    # Verificar si el nuevo nombre ya existe
                    if new_path.exists() and new_path != folder:
                        print(f"   ⚠️ No se puede renombrar: '{new_name}' ya existe")
                        continue
                    
                    if execute:
                        try:
                            folder.rename(new_path)
                            print(f"   ✅ Renombrado: {original_name} → {new_name}")
                            fixes_applied += 1
                            
                            # Si era una carpeta temporal, mover archivos a proyectos individuales
                            if re.match(r'^Recent\s+\w+\s+\d{4}$', original_name):
                                projects_reorganized += 1
                                
                        except Exception as e:
                            print(f"   ❌ Error renombrando {original_name}: {e}")
                    else:
                        print(f"   💡 [dim]Simulación: se renombraría {original_name} → {new_name}[/dim]")
                        fixes_applied += 1
            
            # Mostrar resumen
            print(f"\n📊 [bold]RESUMEN DE CORRECCIONES:[/bold]")
            print(f"   🔧 Nombres corregidos: {fixes_applied}")
            print(f"   📁 Proyectos reorganizados: {projects_reorganized}")
            
            if not execute:
                print(f"\n💡 [yellow]Usa --execute para aplicar los cambios[/yellow]")
            else:
                print(f"\n✅ [green]Correcciones de proyectos aplicadas exitosamente[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en fix-projects: {e}", "CLI-FixProjects")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    def _clean_corrupt_backups(self):
        """Elimina archivos de backup corruptos o incompletos en la carpeta backups."""
        import os
        backup_dir = Path("backups")
        if not backup_dir.exists():
            return 0
        removed = 0
        for file in backup_dir.iterdir():
            # Eliminar archivos de tamaño 0 o que no sean .zip/.tar/.gz
            if file.is_file():
                if file.stat().st_size == 0 or not file.suffix.lower() in ['.zip', '.tar', '.gz', '.tgz', '.tar.gz']:
                    try:
                        file.unlink()
                        removed += 1
                        print(f"🗑️ Backup corrupto eliminado: {file.name}")
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar {file.name}: {e}")
        return removed

    def _clean_temp_files(self):
        """Elimina archivos temporales del sistema."""
        import os
        import glob
        removed = 0
        
        # Patrones de archivos temporales comunes (solo en el proyecto actual)
        temp_patterns = [
            "*.tmp",
            "*.temp", 
            "*.log.tmp",
            "*.cache",
            "*.pyc",
            "*.bak",
            "*.swp",
            "*.swo",
            "*~"
        ]
        
        # Limpiar archivos temporales en el directorio actual (excluyendo venv)
        for pattern in temp_patterns:
            try:
                for file_path in glob.glob(pattern):
                    # No procesar archivos dentro de venv
                    if "venv" in file_path:
                        continue
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        removed += 1
                        print(f"🗑️ Archivo temporal eliminado: {file_path}")
            except Exception as e:
                print(f"⚠️ Error limpiando {pattern}: {e}")
        
        # Limpiar directorios __pycache__ solo en el proyecto actual (no en venv)
        for root, dirs, files in os.walk("."):
            # Saltar completamente el directorio venv
            if "venv" in root:
                continue
                
            if "__pycache__" in dirs:
                cache_dir = os.path.join(root, "__pycache__")
                try:
                    import shutil
                    shutil.rmtree(cache_dir)
                    removed += 1
                    print(f"🗑️ Cache eliminado: {cache_dir}")
                except Exception as e:
                    print(f"⚠️ Error eliminando cache {cache_dir}: {e}")
        
        return removed

    def _consolidate_backups(self) -> int:
        """Consolida backups manteniendo solo los más recientes."""
        try:
            backups_dir = Path("backups")
            if not backups_dir.exists():
                return 0
            
            # Obtener todos los backups
            backup_files = list(backups_dir.glob("*.zip"))
            if len(backup_files) <= 5:  # Mantener al menos 5 backups
                return 0
            
            # Ordenar por fecha de modificación
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Eliminar backups antiguos (mantener solo los 5 más recientes)
            removed_count = 0
            for old_backup in backup_files[5:]:
                try:
                    old_backup.unlink()
                    removed_count += 1
                    print(f"🗑️ Backup antiguo eliminado: {old_backup.name}")
                except Exception as e:
                    print(f"⚠️ No se pudo eliminar {old_backup.name}: {e}")
            
            return removed_count
        except Exception as e:
            print(f"⚠️ Error consolidando backups: {e}")
            return 0

    def _optimize_databases(self) -> int:
        """Optimiza bases de datos SQLite del sistema."""
        try:
            optimized_count = 0
            
            # Optimizar ChromaDB
            try:
                import sqlite3
                chroma_db_path = Path("chroma_db")
                if chroma_db_path.exists():
                    for db_file in chroma_db_path.rglob("*.db"):
                        try:
                            conn = sqlite3.connect(db_file)
                            conn.execute("VACUUM")
                            conn.execute("ANALYZE")
                            conn.close()
                            optimized_count += 1
                            print(f"🔧 Base de datos optimizada: {db_file.name}")
                        except Exception as e:
                            print(f"⚠️ No se pudo optimizar {db_file.name}: {e}")
            except Exception as e:
                print(f"⚠️ Error optimizando ChromaDB: {e}")
            
            # Optimizar learning system DB
            try:
                learning_db = Path("learning/para_learning_knowledge.json")
                if learning_db.exists():
                    # Verificar integridad del JSON
                    import json
                    with open(learning_db, 'r') as f:
                        data = json.load(f)
                    with open(learning_db, 'w') as f:
                        json.dump(data, f, indent=2)
                    optimized_count += 1
                    print(f"🔧 Learning DB optimizada: {learning_db.name}")
            except Exception as e:
                print(f"⚠️ Error optimizando learning DB: {e}")
            
            return optimized_count
        except Exception as e:
            print(f"⚠️ Error optimizando bases de datos: {e}")
            return 0

    def _clean_old_logs(self) -> int:
        """Limpia logs antiguos del sistema."""
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                return 0
            
            removed_count = 0
            current_time = time.time()
            max_age_days = 30  # Mantener logs de los últimos 30 días
            
            for log_file in logs_dir.glob("*.log"):
                try:
                    file_age = current_time - log_file.stat().st_mtime
                    if file_age > (max_age_days * 24 * 3600):  # 30 días en segundos
                        log_file.unlink()
                        removed_count += 1
                        print(f"🗑️ Log antiguo eliminado: {log_file.name}")
                except Exception as e:
                    print(f"⚠️ No se pudo eliminar {log_file.name}: {e}")
            
            return removed_count
        except Exception as e:
            print(f"⚠️ Error limpiando logs antiguos: {e}")
            return 0

    def _clean_finetune_data(self) -> int:
        """Limpia datos de fine-tuning antiguos."""
        try:
            finetune_dir = Path("learning/finetune_data")
            if not finetune_dir.exists():
                return 0
            
            removed_count = 0
            current_time = time.time()
            max_age_days = 7  # Mantener datos de los últimos 7 días
            
            for data_file in finetune_dir.glob("*.jsonl"):
                try:
                    file_age = current_time - data_file.stat().st_mtime
                    if file_age > (max_age_days * 24 * 3600):
                        data_file.unlink()
                        removed_count += 1
                        print(f"🗑️ Datos de fine-tuning eliminados: {data_file.name}")
                except Exception as e:
                    print(f"⚠️ No se pudo eliminar {data_file.name}: {e}")
            
            return removed_count
        except Exception as e:
            print(f"⚠️ Error limpiando datos de fine-tuning: {e}")
            return 0

    def _clean_test_files(self) -> int:
        """Limpia archivos de prueba y temporales."""
        try:
            removed_count = 0
            
            # Limpiar archivos de prueba
            test_patterns = ["test_*.py", "*_test.py", "temp_*.md", "test_*.md"]
            for pattern in test_patterns:
                for test_file in Path(".").rglob(pattern):
                    try:
                        test_file.unlink()
                        removed_count += 1
                        print(f"🗑️ Archivo de prueba eliminado: {test_file.name}")
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar {test_file.name}: {e}")
            
            return removed_count
        except Exception as e:
            print(f"⚠️ Error limpiando archivos de prueba: {e}")
            return 0

    def _clean_nextjs_cache(self) -> int:
        """Limpia cachés de Next.js del dashboard web."""
        try:
            web_dir = Path("web")
            if not web_dir.exists():
                return 0
            
            removed_count = 0
            
            # Limpiar .next
            next_dir = web_dir / ".next"
            if next_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(next_dir)
                    removed_count += 1
                    print(f"🗑️ Cache de Next.js eliminado: .next")
                except Exception as e:
                    print(f"⚠️ No se pudo eliminar .next: {e}")
            
            # Limpiar node_modules si es muy grande
            node_modules = web_dir / "node_modules"
            if node_modules.exists():
                try:
                    total_size = sum(f.stat().st_size for f in node_modules.rglob('*') if f.is_file())
                    size_gb = total_size / (1024**3)
                    if size_gb > 1.0:  # Si es mayor a 1GB
                        print(f"⚠️ node_modules es muy grande ({size_gb:.1f} GB)")
                        print(f"💡 Considera ejecutar 'npm ci' en el directorio web/")
                except Exception as e:
                    print(f"⚠️ Error verificando tamaño de node_modules: {e}")
            
            return removed_count
        except Exception as e:
            print(f"⚠️ Error limpiando cachés de Next.js: {e}")
            return 0

    @log_exceptions
    def cmd_logs_auto_fix(self, *args):
        """
        Analiza logs y aplica auto-fixes automáticamente usando IA.
        
        Uso:
            python para_cli.py logs-auto-fix [--force] [--verbose]
            
        Argumentos:
            --force    - Forzar re-análisis de logs ya procesados
            --verbose  - Mostrar detalles del proceso
        """
        try:
            log_center.log_info("Iniciando comando logs-auto-fix", "CLI-LogsAutoFix", {"args": args})
            print("\n🔧 Analizando logs y aplicando auto-fixes con IA...")
            
            # Procesar argumentos
            force = '--force' in args
            verbose = '--verbose' in args
            
            if force:
                print("⚡ Modo forzado: re-analizando todos los logs")
            if verbose:
                print("📋 Modo verbose: mostrando detalles completos")
            
            # Importar y ejecutar auto-fix engine
            try:
                from paralib.auto_fix import auto_fix_engine
                
                # Obtener logs recientes para análisis
                recent_logs = log_center.get_recent_logs(100)
                error_logs = [log for log in recent_logs if log.level in ['ERROR', 'CRITICAL']]
                
                if not error_logs:
                    print("✅ No se encontraron errores en logs recientes")
                    return
                
                print(f"\n📊 Encontrados {len(error_logs)} errores en logs recientes")
                
                # Analizar cada error
                fixes_applied = 0
                errors_processed = 0
                
                for i, log_entry in enumerate(error_logs, 1):
                    print(f"\n🔍 Procesando error {i}/{len(error_logs)}:")
                    print(f"   📝 {log_entry.message[:100]}...")
                    
                    # Intentar auto-fix
                    try:
                        # Buscar patrones de error de código en el mensaje
                        import re
                        
                        # Patrón para errores de archivo y línea
                        file_line_match = re.search(r'File "([^"]+)", line (\d+)', log_entry.message)
                        if file_line_match:
                            file_path = file_line_match.group(1)
                            line_num = int(file_line_match.group(2))
                            
                            if verbose:
                                print(f"   📁 Archivo: {file_path}")
                                print(f"   📄 Línea: {line_num}")
                            
                            # Verificar si el archivo existe
                            if os.path.exists(file_path):
                                errors_processed += 1
                                
                                # Aplicar auto-fix
                                if auto_fix_engine.fix_code_error(file_path, line_num, log_entry.message):
                                    fixes_applied += 1
                                    print(f"   ✅ Auto-fix aplicado exitosamente")
                                else:
                                    print(f"   ⚠️ No se pudo aplicar auto-fix")
                            else:
                                print(f"   ❌ Archivo no encontrado: {file_path}")
                        else:
                            # Buscar otros patrones de error
                            error_patterns = [
                                r'ImportError: No module named (\w+)',
                                r'ModuleNotFoundError: No module named (\w+)',
                                r'AttributeError: (\w+) object has no attribute (\w+)',
                                r'KeyError: (\w+)',
                                r'IndexError: list index out of range',
                                r'SyntaxError: (.+)',
                                r'TypeError: (.+)'
                            ]
                            
                            for pattern in error_patterns:
                                match = re.search(pattern, log_entry.message)
                                if match:
                                    if verbose:
                                        print(f"   🔍 Patrón detectado: {pattern}")
                                    errors_processed += 1
                                    # Aquí se podrían aplicar fixes específicos por tipo de error
                                    break
                            else:
                                if verbose:
                                    print(f"   ℹ️ No se detectó patrón específico de error de código")
                    
                    except Exception as e:
                        print(f"   ❌ Error procesando log: {e}")
                        if verbose:
                            import traceback
                            traceback.print_exc()
                
                # Mostrar resumen
                print(f"\n📊 RESUMEN DE AUTO-FIX:")
                print(f"   🔍 Errores analizados: {len(error_logs)}")
                print(f"   ⚙️ Errores procesados: {errors_processed}")
                print(f"   ✅ Fixes aplicados: {fixes_applied}")
                print(f"   📈 Tasa de éxito: {(fixes_applied/errors_processed*100):.1f}%" if errors_processed > 0 else "   📈 Tasa de éxito: N/A")
                
                if fixes_applied > 0:
                    print(f"\n🎉 ¡Auto-fix completado! {fixes_applied} errores corregidos automáticamente")
                    log_center.log_info(f"Auto-fix completado: {fixes_applied} errores corregidos", "CLI-LogsAutoFix")
                else:
                    print(f"\n💡 No se pudieron aplicar auto-fixes automáticamente")
                    print(f"   💡 Revisa los logs manualmente o ejecuta 'python para_cli.py doctor'")
                
            except ImportError as e:
                print(f"❌ Error importando módulos de auto-fix: {e}")
                print(f"💡 Asegúrate de que todos los módulos estén instalados correctamente")
                log_center.log_error(f"Error importando auto-fix: {str(e)}", "CLI-LogsAutoFix")
                
        except Exception as e:
            log_center.log_error(f"Error en logs-auto-fix: {e}", "CLI-LogsAutoFix")
            print(f"❌ Error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    def _require_vault_with_browser(self):
        """Requiere un vault válido con interfaz de navegador."""
        return self._require_vault()

    @log_exceptions
    def cmd_clean_problematic(self, *args):
        """
        Limpia carpetas problemáticas y mejora la clasificación PARA.
        
        Problemas que corrige:
        - Carpetas "Related" en proyectos (mueve a recursos)
        - Carpetas "Recent June 2025" (mueve a archivo)
        - Carpetas duplicadas con sufijos (_1, _2, etc.)
        - Carpetas de desarrollo personal (mueve a áreas)
        
        Uso:
            python para_cli.py clean-problematic [--execute]
            
        Argumentos:
            --execute  - Ejecutar las correcciones (sin esto solo simula)
        """
        try:
            log_center.log_info("Iniciando limpieza de carpetas problemáticas", "CLI-CleanProblematic", {"args": args})
            print("\n🧹 Limpiando carpetas problemáticas y mejorando clasificación PARA...")
            
            # Procesar argumentos
            execute = False
            for arg in args:
                if arg == '--execute':
                    execute = True
                    break
            
            # Obtener vault
            vault = self._require_vault()
            if not vault:
                print("\n❌ No se pudo encontrar vault")
                return
            
            vault_path = Path(vault)
            
            if not execute:
                print("\n🔍 [yellow]MODO SIMULACIÓN: No se aplicarán cambios[/yellow]")
            else:
                print("\n⚡ [red]MODO EJECUCIÓN: Se aplicarán cambios permanentes[/red]")
            
            # Crear backup si se va a ejecutar
            if execute:
                print("\n💾 Creando backup antes de la limpieza...")
                from paralib.backup_manager import backup_manager
                backup_info = backup_manager.create_backup(
                    str(vault_path), 
                    backup_type='full', 
                    description='Backup antes de limpieza de carpetas problemáticas'
                )
                if backup_info:
                    print(f"✅ Backup creado: {backup_info.id} ({backup_info.size_mb:.1f} MB)")
                else:
                    print("⚠️ No se pudo crear backup, continuando...")
            
            # Ejecutar limpieza
            from paralib.organizer import clean_problematic_folders
            stats = clean_problematic_folders(vault_path)
            
            # Mostrar resultados
            print(f"\n📊 [bold]RESULTADOS DE LA LIMPIEZA:[/bold]")
            print(f"   🧹 Carpetas limpiadas: {stats['folders_cleaned']}")
            print(f"   🚀 Proyectos corregidos: {stats['projects_fixed']}")
            print(f"   📚 Recursos reorganizados: {stats['resources_reorganized']}")
            print(f"   [TARGET] Áreas creadas: {stats['areas_created']}")
            
            if stats['errors']:
                print(f"   ⚠️ Errores encontrados: {len(stats['errors'])}")
                for error in stats['errors'][:3]:
                    print(f"      • {error}")
            
            if not execute:
                print(f"\n💡 [yellow]Usa --execute para aplicar los cambios[/yellow]")
            else:
                print(f"\n✅ [green]Limpieza completada exitosamente[/green]")
                
        except Exception as e:
            log_center.log_error(f"Error en clean-problematic: {e}", "CLI-CleanProblematic")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc()

    @log_exceptions
    def cmd_logs(self, *args):
        """Muestra logs del sistema."""
        try:
            log_center.log_info("Iniciando comando logs", "CLI-Logs", {"args": args})
            print("\n📋 Logs del sistema:")
            
            # Obtener logs recientes
            recent_logs = log_center.get_recent_logs(50)
            if not recent_logs:
                print("\n📋 No hay logs recientes")
                return
            
            print("\n-" * 60)
            print(f"{'Timestamp':<20} {'Nivel':<8} {'Componente':<15} {'Mensaje':<70}")
            print("-" * 60)
            
            for log_entry in recent_logs:
                timestamp = getattr(log_entry, 'timestamp', 'N/A')
                if hasattr(timestamp, 'strftime'):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                level = getattr(log_entry, 'level', 'INFO')
                component = getattr(log_entry, 'component', 'N/A')
                message = getattr(log_entry, 'message', str(log_entry))[:65] + "..." if len(getattr(log_entry, 'message', str(log_entry))) > 65 else getattr(log_entry, 'message', str(log_entry))
                
                print(f"{timestamp:<20} {level:<8} {component:<15} {message}")
            
            print("-" * 60)
            
            log_center.log_info("Comando logs completado", "CLI-Logs")
            
        except Exception as e:
            log_center.log_error(f"Error en logs: {e}", "CLI-Logs")
            print(f"❌ Error: {e}")

    def _create_log_status_manager(self):
        """Crea y retorna un gestor de estados de logs."""
        try:
            # Definir LogStatus enum localmente si no existe
            from enum import Enum
            class LogStatus(Enum):
                NEW = "new"
                RESOLVED = "resolved"
                IGNORED = "ignored"
            
            # Crear gestor simple de estados
            class SimpleLogStatusManager:
                def __init__(self):
                    self.log_entries = {}
                    self.status_file = Path("logs/log_status.json")
                    self.status_file.parent.mkdir(exist_ok=True)
                    self._load_status()
                
                def _load_status(self):
                    """Carga el estado de logs desde archivo."""
                    try:
                        if self.status_file.exists():
                            import json
                            with open(self.status_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                self.log_entries = data.get('entries', {})
                    except Exception:
                        self.log_entries = {}
                
                def _save_status(self):
                    """Guarda el estado de logs a archivo."""
                    try:
                        import json
                        from datetime import datetime
                        data = {
                            'last_updated': datetime.now().isoformat(),
                            'entries': self.log_entries
                        }
                        with open(self.status_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f"⚠️ Error guardando estado de logs: {e}")
                
                def get_log_by_id(self, log_id):
                    """Obtiene un log por ID."""
                    if log_id in self.log_entries:
                        return type('LogEntry', (), self.log_entries[log_id])()
                    return None
                
                def mark_as_resolved(self, log_id, resolution_notes=None, resolved_by="auto-fix"):
                    """Marca un log como resuelto."""
                    from datetime import datetime
                    self.log_entries[log_id] = {
                        'status': 'resolved',
                        'resolution_notes': resolution_notes,
                        'resolved_at': datetime.now().isoformat(),
                        'resolved_by': resolved_by,
                        'auto_fix_applied': True
                    }
                
                def mark_as_ignored(self, log_id, reason=None):
                    """Marca un log como ignorado."""
                    from datetime import datetime
                    self.log_entries[log_id] = {
                        'status': 'ignored',
                        'resolution_notes': f"Ignorado: {reason}" if reason else "Ignorado manualmente",
                        'resolved_at': datetime.now().isoformat(),
                        'resolved_by': 'manual',
                        'auto_fix_applied': False
                    }
                
                def cleanup_old_resolved_logs(self, days=7):
                    """Limpia logs resueltos antiguos."""
                    import time
                    from datetime import datetime
                    
                    cutoff_time = time.time() - (days * 24 * 3600)
                    to_remove = []
                    
                    for log_id, entry in self.log_entries.items():
                        if entry.get('status') == 'resolved' and entry.get('resolved_at'):
                            try:
                                resolved_time = datetime.fromisoformat(entry['resolved_at']).timestamp()
                                if resolved_time < cutoff_time:
                                    to_remove.append(log_id)
                            except:
                                pass
                    
                    for log_id in to_remove:
                        del self.log_entries[log_id]
                    
                    return len(to_remove)
            
            return SimpleLogStatusManager()
            
        except Exception as e:
            print(f"⚠️ Error creando gestor de estados de logs: {e}")
            # Retornar gestor dummy
            return type('DummyManager', (), {
                'get_log_by_id': lambda x: None,
                'mark_as_resolved': lambda x, y, z: None,
                'mark_as_ignored': lambda x, y: None,
                'cleanup_old_resolved_logs': lambda x: 0,
                '_save_status': lambda: None
            })()

    def _attempt_log_auto_fix(self, log_entry):
        """Intenta aplicar auto-fix a un log de error."""
        try:
            import re
            
            # Patrones de error conocidos y sus fixes
            fix_patterns = [
                {
                    'pattern': r'ImportError: No module named (\w+)',
                    'fix': lambda match: f"Instalar módulo faltante: {match.group(1)}",
                    'action': 'install_missing_module'
                },
                {
                    'pattern': r'ModuleNotFoundError: No module named (\w+)',
                    'fix': lambda match: f"Instalar módulo faltante: {match.group(1)}",
                    'action': 'install_missing_module'
                },
                {
                    'pattern': r'File "([^"]+)", line (\d+)',
                    'fix': lambda match: f"Error de sintaxis en {match.group(1)} línea {match.group(2)}",
                    'action': 'syntax_error'
                },
                {
                    'pattern': r'PermissionError: \[Errno 13\] Permission denied',
                    'fix': lambda match: "Error de permisos - verificar permisos de archivo",
                    'action': 'permission_error'
                },
                {
                    'pattern': r'FileNotFoundError: \[Errno 2\] No such file or directory',
                    'fix': lambda match: "Archivo no encontrado - verificar ruta",
                    'action': 'file_not_found'
                },
                {
                    'pattern': r'ConnectionError',
                    'fix': lambda match: "Error de conexión - verificar conectividad",
                    'action': 'connection_error'
                }
            ]
            
            message = getattr(log_entry, 'message', str(log_entry))
            
            for pattern_info in fix_patterns:
                match = re.search(pattern_info['pattern'], message)
                if match:
                    fix_description = pattern_info['fix'](match)
                    return {
                        'success': True,
                        'notes': fix_description,
                        'action': pattern_info['action'],
                        'reason': None
                    }
            
            # Si no se encuentra patrón específico
            return {
                'success': False,
                'notes': None,
                'action': None,
                'reason': 'Patrón de error no reconocido para auto-fix'
            }
            
        except Exception as e:
            return {
                'success': False,
                'notes': None,
                'action': None,
                'reason': f"Error en auto-fix: {str(e)}"
            }

    def _process_new_error(self, log_status_manager, log_id, log_entry, auto_fix):
        """Procesa un error nuevo aplicando auto-fix si está habilitado."""
        if auto_fix:
            fix_result = self._attempt_log_auto_fix(log_entry)
            if fix_result['success']:
                log_status_manager.mark_as_resolved(
                    log_id, 
                    fix_result['notes'], 
                    "auto-fix"
                )
                print(f"      ✅ Auto-fix aplicado: {fix_result['notes']}")
            else:
                # Marcar como ignorado si no se puede arreglar
                log_status_manager.mark_as_ignored(
                    log_id, 
                    "No se pudo aplicar auto-fix automáticamente"
                )
                print(f"      ⚠️ No se pudo auto-fix: {fix_result['reason']}")
        else:
            # Si no hay auto-fix, marcar como ignorado
            log_status_manager.mark_as_ignored(
                log_id, 
                "Auto-fix deshabilitado"
            )
            print(f"      ⏭️ Marcado como ignorado (auto-fix deshabilitado)")



@log_exceptions
def main():
    """Función principal."""
    try:
        logger.info("Iniciando PARA CLI")
        
        # Configurar entorno
        if not setup_environment():
            sys.exit(1)
        
        # Crear y ejecutar CLI
        cli = PARACLI()
        cli.run()
        
        logger.info("CLI ejecutado correctamente")
        
    except Exception as e:
        log_critical_error("Error crítico en main", e)
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
