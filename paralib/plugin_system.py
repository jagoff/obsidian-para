"""
paralib/plugin_system.py

Sistema de Plugins/Extensiones para PARA CLI.
Permite extender la funcionalidad sin modificar el código core.
"""
import os
import sys
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

from paralib.logger import logger

@dataclass
class PluginInfo:
    """Información de un plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    enabled: bool = True
    loaded_at: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None

@dataclass
class PluginCommand:
    """Comando registrado por un plugin."""
    name: str
    plugin_name: str
    function: Callable
    help_text: str
    aliases: List[str] = field(default_factory=list)

@dataclass
class PluginHook:
    """Hook registrado por un plugin."""
    name: str
    plugin_name: str
    function: Callable
    priority: int = 0

class PARAPluginManager:
    """Gestor principal del sistema de plugins."""
    
    def __init__(self, plugins_dir: Path = None):
        self.plugins_dir = plugins_dir or Path("plugins")
        self.plugins_dir.mkdir(exist_ok=True)
        
        self.plugins: Dict[str, PluginInfo] = {}
        self.commands: Dict[str, PluginCommand] = {}
        self.hooks: Dict[str, List[PluginHook]] = {}
        self.loaded_modules: Dict[str, Any] = {}
        
        # Configuración de plugins
        self.config_file = self.plugins_dir / "plugins_config.json"
        self.load_config()
        
        # Registrar hooks del sistema
        self._register_system_hooks()
    
    def _register_system_hooks(self):
        """Registra hooks del sistema core."""
        self.register_hook("note_processed", self._log_note_processed, priority=100)
        self.register_hook("classification_completed", self._log_classification, priority=100)
        self.register_hook("error_occurred", self._log_error, priority=100)
        self.register_hook("vault_changed", self._log_vault_change, priority=100)
    
    def _log_note_processed(self, note_path: Path, result: Dict):
        """Hook para logging de notas procesadas."""
        logger.info(f"[PLUGIN-SYSTEM] Nota procesada: {note_path.name}")
    
    def _log_classification(self, note_path: Path, classification: Dict):
        """Hook para logging de clasificaciones."""
        logger.info(f"[PLUGIN-SYSTEM] Clasificación completada: {note_path.name} -> {classification.get('category', 'Unknown')}")
    
    def _log_error(self, error: Exception, context: str):
        """Hook para logging de errores."""
        logger.error(f"[PLUGIN-SYSTEM] Error en {context}: {error}")
    
    def _log_vault_change(self, old_vault: Path, new_vault: Path):
        """Hook para logging de cambios de vault."""
        logger.info(f"[PLUGIN-SYSTEM] Vault cambiado: {old_vault} -> {new_vault}")
    
    def load_config(self):
        """Carga la configuración de plugins."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for plugin_name, plugin_config in config.items():
                        self.plugins[plugin_name] = PluginInfo(**plugin_config)
            except Exception as e:
                logger.error(f"Error cargando configuración de plugins: {e}")
    
    def save_config(self):
        """Guarda la configuración de plugins."""
        try:
            config = {}
            for name, plugin in self.plugins.items():
                config[name] = {
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'author': plugin.author,
                    'dependencies': plugin.dependencies,
                    'commands': plugin.commands,
                    'hooks': plugin.hooks,
                    'enabled': plugin.enabled,
                    'error_count': plugin.error_count,
                    'last_error': plugin.last_error
                }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando configuración de plugins: {e}")
    
    def discover_plugins(self) -> List[Path]:
        """Descubre plugins disponibles en el directorio."""
        plugins = []
        if self.plugins_dir.exists():
            for item in self.plugins_dir.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    plugins.append(item)
                elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                    plugins.append(item)
        return plugins
    
    def load_plugin(self, plugin_path: Path) -> bool:
        """Carga un plugin específico."""
        try:
            plugin_name = plugin_path.stem if plugin_path.is_file() else plugin_path.name
            
            # Verificar si ya está cargado
            if plugin_name in self.loaded_modules:
                logger.warning(f"Plugin {plugin_name} ya está cargado")
                return True
            
            # Cargar el módulo
            if plugin_path.is_file():
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                module = importlib.import_module(f"plugins.{plugin_name}")
            
            self.loaded_modules[plugin_name] = module
            
            # Verificar que el plugin tenga la interfaz correcta
            if not hasattr(module, 'PARAPlugin'):
                logger.error(f"Plugin {plugin_name} no tiene la clase PARAPlugin")
                return False
            
            plugin_instance = module.PARAPlugin()
            
            # Registrar información del plugin
            plugin_info = PluginInfo(
                name=plugin_name,
                version=getattr(plugin_instance, 'version', '1.0.0'),
                description=getattr(plugin_instance, 'description', 'Sin descripción'),
                author=getattr(plugin_instance, 'author', 'Desconocido'),
                dependencies=getattr(plugin_instance, 'dependencies', []),
                loaded_at=datetime.now()
            )
            
            self.plugins[plugin_name] = plugin_info
            
            # Registrar comandos del plugin
            if hasattr(plugin_instance, 'register_commands'):
                plugin_instance.register_commands(self)
            
            # Registrar hooks del plugin
            if hasattr(plugin_instance, 'register_hooks'):
                plugin_instance.register_hooks(self)
            
            logger.info(f"Plugin {plugin_name} cargado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando plugin {plugin_path}: {e}")
            if plugin_name in self.plugins:
                self.plugins[plugin_name].error_count += 1
                self.plugins[plugin_name].last_error = str(e)
            return False
    
    def load_all_plugins(self):
        """Carga todos los plugins disponibles."""
        plugin_paths = self.discover_plugins()
        loaded_count = 0
        
        for plugin_path in plugin_paths:
            if self.load_plugin(plugin_path):
                loaded_count += 1
        
        logger.info(f"Cargados {loaded_count}/{len(plugin_paths)} plugins")
        self.save_config()
    
    def register_command(self, name: str, function: Callable, help_text: str = "", 
                        aliases: List[str] = None, plugin_name: str = "system"):
        """Registra un comando del plugin."""
        command = PluginCommand(
            name=name,
            plugin_name=plugin_name,
            function=function,
            help_text=help_text,
            aliases=aliases or []
        )
        
        self.commands[name] = command
        
        # Registrar aliases
        for alias in aliases or []:
            self.commands[alias] = command
        
        logger.info(f"Comando {name} registrado por plugin {plugin_name}")
    
    def register_hook(self, hook_name: str, function: Callable, priority: int = 0, 
                     plugin_name: str = "system"):
        """Registra un hook del plugin."""
        hook = PluginHook(
            name=hook_name,
            plugin_name=plugin_name,
            function=function,
            priority=priority
        )
        
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(hook)
        
        # Ordenar por prioridad (mayor prioridad primero)
        self.hooks[hook_name].sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Hook {hook_name} registrado por plugin {plugin_name} (prioridad: {priority})")
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Ejecuta todos los hooks registrados para un evento."""
        results = []
        
        if hook_name in self.hooks:
            for hook in self.hooks[hook_name]:
                try:
                    result = hook.function(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error ejecutando hook {hook_name} del plugin {hook.plugin_name}: {e}")
                    if hook.plugin_name in self.plugins:
                        self.plugins[hook.plugin_name].error_count += 1
                        self.plugins[hook.plugin_name].last_error = str(e)
        
        return results
    
    def get_command(self, name: str) -> Optional[PluginCommand]:
        """Obtiene un comando registrado."""
        return self.commands.get(name)
    
    def list_commands(self) -> Dict[str, PluginCommand]:
        """Lista todos los comandos registrados."""
        return self.commands.copy()
    
    def list_plugins(self) -> Dict[str, PluginInfo]:
        """Lista todos los plugins cargados."""
        return self.plugins.copy()
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Habilita un plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = True
            self.save_config()
            logger.info(f"Plugin {plugin_name} habilitado")
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Deshabilita un plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].enabled = False
            self.save_config()
            logger.info(f"Plugin {plugin_name} deshabilitado")
            return True
        return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Descarga un plugin."""
        try:
            if plugin_name in self.loaded_modules:
                # Remover comandos del plugin
                commands_to_remove = [
                    name for name, cmd in self.commands.items() 
                    if cmd.plugin_name == plugin_name
                ]
                for cmd_name in commands_to_remove:
                    del self.commands[cmd_name]
                
                # Remover hooks del plugin
                for hook_name, hooks in self.hooks.items():
                    self.hooks[hook_name] = [
                        hook for hook in hooks if hook.plugin_name != plugin_name
                    ]
                
                # Remover módulo
                del self.loaded_modules[plugin_name]
                
                logger.info(f"Plugin {plugin_name} descargado")
                return True
        except Exception as e:
            logger.error(f"Error descargando plugin {plugin_name}: {e}")
        
        return False
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los plugins."""
        total_plugins = len(self.plugins)
        enabled_plugins = sum(1 for p in self.plugins.values() if p.enabled)
        total_commands = len(self.commands)
        total_hooks = sum(len(hooks) for hooks in self.hooks.values())
        
        return {
            'total_plugins': total_plugins,
            'enabled_plugins': enabled_plugins,
            'disabled_plugins': total_plugins - enabled_plugins,
            'total_commands': total_commands,
            'total_hooks': total_hooks,
            'plugins_with_errors': sum(1 for p in self.plugins.values() if p.error_count > 0)
        }
    
    def get_plugin_commands(self, plugin_name: str) -> list:
        """Devuelve la lista de comandos registrados por un plugin (nombre, aliases, descripción)."""
        cmds = []
        for cmd in self.commands.values():
            if cmd.plugin_name == plugin_name:
                cmds.append({
                    'name': cmd.name,
                    'aliases': getattr(cmd, 'aliases', []),
                    'description': getattr(cmd, 'help_text', '')
                })
        return cmds

class PARAPlugin:
    """Clase base para todos los plugins."""
    
    name = "Base Plugin"
    version = "1.0.0"
    description = "Plugin base para PARA CLI"
    author = "PARA Team"
    dependencies = []
    
    def __init__(self):
        self.plugin_manager = None
    
    def register_commands(self, plugin_manager: PARAPluginManager):
        """Registra comandos del plugin. Debe ser implementado por subclases."""
        self.plugin_manager = plugin_manager
        pass
    
    def register_hooks(self, plugin_manager: PARAPluginManager):
        """Registra hooks del plugin. Debe ser implementado por subclases."""
        self.plugin_manager = plugin_manager
        pass
    
    def on_enable(self):
        """Llamado cuando el plugin se habilita."""
        pass
    
    def on_disable(self):
        """Llamado cuando el plugin se deshabilita."""
        pass
    
    def on_note_processed(self, note_path: Path, result: Dict):
        """Hook llamado cuando se procesa una nota."""
        pass
    
    def on_classification_completed(self, note_path: Path, classification: Dict):
        """Hook llamado cuando se completa una clasificación."""
        pass
    
    def on_error_occurred(self, error: Exception, context: str):
        """Hook llamado cuando ocurre un error."""
        pass
    
    def on_vault_changed(self, old_vault: Path, new_vault: Path):
        """Hook llamado cuando cambia el vault."""
        pass 