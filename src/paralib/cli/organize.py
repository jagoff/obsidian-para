"""
Comandos de organización para PARA System.
Incluye cmd_organize y helpers relacionados.
"""

import logging
from pathlib import Path
from paralib.log_center import log_center
from paralib.logger import log_exceptions
from paralib.debug_config import should_show

logger = logging.getLogger(__name__)

class OrganizeCommands:
    """Comandos relacionados con la organización del vault."""
    def __init__(self, cli_instance):
        self.cli = cli_instance

    @log_exceptions
    def cmd_organize(self, *args):
        """Organiza un vault específico usando las herramientas propias CON SISTEMA DE EXCLUSIONES OBLIGATORIO."""
        try:
            log_center.log_info("Iniciando comando organize", "CLI-Organize", {"args": args})
            print("\n🗂️ Organizando vault con herramientas PARA...")
            
            # 1. SELECCIÓN Y CONFIRMACIÓN DE VAULT
            vault = self.cli._require_vault()
            if vault:
                vault_path = Path(vault)
                
                # CONFIRMACIÓN OBLIGATORIA DEL VAULT
                from rich.prompt import Confirm
                if not Confirm.ask("¿Confirmar que este es el vault correcto para organizar?", default=True):
                    print("\n❌ Operación cancelada por el usuario")
                    log_center.log_info("Organización cancelada por el usuario", "CLI-Organize")
                    return
                
                # 2. SISTEMA DE EXCLUSIONES OBLIGATORIO
                print("\n🚫 CONFIGURANDO EXCLUSIONES OBLIGATORIAS...")
                log_center.log_info("Configurando exclusiones obligatorias", "CLI-Organize")
                
                from paralib.exclusion_manager import ensure_global_exclusions_configured
                if not ensure_global_exclusions_configured(vault_path):
                    print("\n❌ No se pudo configurar exclusiones globales")
                    return
                
                # 3. ORGANIZACIÓN PRINCIPAL
                print("\n🔄 Ejecutando organización principal...")
                from paralib.organizer import run_full_reclassification_safe
                stats = run_full_reclassification_safe(str(vault_path))
                
                # 4. RESUMEN
                print(f"\n📊 [bold]RESUMEN DE ORGANIZACIÓN:[/bold]")
                print(f"   📁 Carpetas organizadas: {stats.get('folders_organized', 0)}")
                print(f"   📝 Notas movidas: {stats.get('notes_moved', 0)}")
                print(f"   🗑️ Carpetas vacías eliminadas: {stats.get('empty_folders_removed', 0)}")
                if stats.get('errors'):
                    print(f"   ⚠️ Errores encontrados: {len(stats['errors'])}")
                    for error in stats['errors'][:3]:
                        print(f"      • {error}")
                print(f"\n✅ Organización completada")
        except Exception as e:
            log_center.log_error(f"Error en organize: {e}", "CLI-Organize")
            print(f"❌ Error: {e}")
            if should_show('show_debug'):
                import traceback
                traceback.print_exc() 