#!/usr/bin/env python3
"""
test_plugin_system.py

Script de prueba para el sistema de plugins.
"""
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from paralib.plugin_system import PARAPluginManager
from paralib.logger import logger

def test_plugin_system():
    """Prueba el sistema de plugins."""
    print("🧪 Probando Sistema de Plugins...")
    
    # Crear gestor de plugins
    plugin_manager = PARAPluginManager()
    
    # Descubrir plugins
    plugins = plugin_manager.discover_plugins()
    print(f"📁 Plugins descubiertos: {len(plugins)}")
    for plugin in plugins:
        print(f"  - {plugin}")
    
    # Cargar plugins
    print("\n🔄 Cargando plugins...")
    plugin_manager.load_all_plugins()
    
    # Mostrar plugins cargados
    loaded_plugins = plugin_manager.list_plugins()
    print(f"\n✅ Plugins cargados: {len(loaded_plugins)}")
    for name, plugin in loaded_plugins.items():
        print(f"  - {name} v{plugin.version} ({'✅' if plugin.enabled else '❌'})")
    
    # Mostrar comandos registrados
    commands = plugin_manager.list_commands()
    print(f"\n🎯 Comandos registrados: {len(commands)}")
    for name, command in commands.items():
        print(f"  - {name} (plugin: {command.plugin_name})")
    
    # Mostrar hooks registrados
    hooks = plugin_manager.hooks
    print(f"\n🔗 Hooks registrados: {sum(len(hook_list) for hook_list in hooks.values())}")
    for hook_name, hook_list in hooks.items():
        print(f"  - {hook_name}: {len(hook_list)} hooks")
    
    # Mostrar estadísticas
    stats = plugin_manager.get_plugin_stats()
    print(f"\n📊 Estadísticas:")
    print(f"  - Total plugins: {stats['total_plugins']}")
    print(f"  - Plugins habilitados: {stats['enabled_plugins']}")
    print(f"  - Total comandos: {stats['total_commands']}")
    print(f"  - Total hooks: {stats['total_hooks']}")
    print(f"  - Plugins con errores: {stats['plugins_with_errors']}")
    
    # Probar ejecución de hooks
    print(f"\n🧪 Probando hooks...")
    results = plugin_manager.execute_hook("note_processed", Path("test_note.md"), {"category": "test"})
    print(f"  - Hook 'note_processed' ejecutado, resultados: {len(results)}")
    
    print("\n✅ Prueba del sistema de plugins completada!")

if __name__ == "__main__":
    test_plugin_system() 