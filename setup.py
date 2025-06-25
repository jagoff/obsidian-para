#!/usr/bin/env python3
"""
setup.py - Script de instalación y configuración completa del sistema PARA

Este script automatiza la instalación de todas las dependencias necesarias:
- Python packages (rich, ollama, chromadb, etc.)
- Ollama (si no está instalado)
- Configuración inicial del sistema
- Verificación de requisitos
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import json

class PARASetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.requirements_file = self.project_root / "requirements.txt"
        
    def print_header(self):
        """Imprime el header del setup."""
        print("=" * 60)
        print("🚀 PARA System - Instalación y Configuración")
        print("=" * 60)
        print()
    
    def check_python_version(self):
        """Verifica que la versión de Python sea compatible."""
        print("🔍 Verificando versión de Python...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Error: Se requiere Python 3.8 o superior. Versión actual: {version.major}.{version.minor}")
            sys.exit(1)
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        print()
    
    def create_virtual_environment(self):
        """Crea el entorno virtual si no existe."""
        print("🔧 Configurando entorno virtual...")
        
        if self.venv_path.exists():
            print("✅ Entorno virtual ya existe")
        else:
            print("📦 Creando entorno virtual...")
            try:
                subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], check=True)
                print("✅ Entorno virtual creado exitosamente")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error creando entorno virtual: {e}")
                sys.exit(1)
        print()
    
    def get_python_executable(self):
        """Obtiene la ruta al ejecutable de Python del entorno virtual."""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
    
    def get_pip_executable(self):
        """Obtiene la ruta al ejecutable de pip del entorno virtual."""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "pip"
        else:
            return self.venv_path / "bin" / "pip"
    
    def upgrade_pip(self):
        """Actualiza pip a la última versión."""
        print("📦 Actualizando pip...")
        pip_exe = self.get_pip_executable()
        try:
            subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], check=True)
            print("✅ Pip actualizado")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error actualizando pip: {e}")
        print()
    
    def install_python_packages(self):
        """Instala todos los paquetes de Python requeridos."""
        print("📦 Instalando paquetes de Python...")
        
        # Lista de paquetes esenciales
        essential_packages = [
            "rich>=14.0.0",
            "ollama>=0.1.0",
            "chromadb>=0.4.0",
            "streamlit>=1.28.0",
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "requests>=2.31.0",
            "sqlite3",  # Incluido en Python
            "pathlib",  # Incluido en Python
            "argparse",  # Incluido en Python
            "json",  # Incluido en Python
            "re",  # Incluido en Python
            "datetime",  # Incluido en Python
            "subprocess",  # Incluido en Python
            "platform",  # Incluido en Python
            "shutil",  # Incluido en Python
            "typing",  # Incluido en Python
        ]
        
        pip_exe = self.get_pip_executable()
        
        # Instalar paquetes desde requirements.txt si existe
        if self.requirements_file.exists():
            print("📋 Instalando desde requirements.txt...")
            try:
                subprocess.run([str(pip_exe), "install", "-r", str(self.requirements_file)], check=True)
                print("✅ Paquetes de requirements.txt instalados")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Error instalando desde requirements.txt: {e}")
        
        # Instalar paquetes esenciales
        print("📋 Instalando paquetes esenciales...")
        for package in essential_packages:
            if package not in ["sqlite3", "pathlib", "argparse", "json", "re", "datetime", "subprocess", "platform", "shutil", "typing"]:
                try:
                    subprocess.run([str(pip_exe), "install", package], check=True)
                    print(f"✅ {package} instalado")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Error instalando {package}: {e}")
        
        print("✅ Instalación de paquetes completada")
        print()
    
    def check_ollama_installation(self):
        """Verifica si Ollama está instalado y lo instala si es necesario."""
        print("🤖 Verificando instalación de Ollama...")
        
        # Verificar si ollama está en PATH
        if shutil.which("ollama"):
            print("✅ Ollama ya está instalado")
            return True
        
        print("📦 Ollama no encontrado, instalando...")
        
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        try:
            if system == "darwin":  # macOS
                print("🍎 Instalando Ollama en macOS...")
                subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"], shell=True, check=True)
            elif system == "linux":
                print("🐧 Instalando Ollama en Linux...")
                subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"], shell=True, check=True)
            elif system == "windows":
                print("🪟 Instalando Ollama en Windows...")
                # Para Windows, descargar el instalador
                subprocess.run(["winget", "install", "ollama.ollama"], check=True)
            else:
                print(f"⚠️ Sistema operativo no soportado: {system}")
                return False
            
            print("✅ Ollama instalado exitosamente")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando Ollama: {e}")
            print("💡 Instala Ollama manualmente desde: https://ollama.ai/download")
            return False
    
    def setup_ollama_model(self):
        """Configura el modelo de Ollama por defecto."""
        print("🤖 Configurando modelo de Ollama...")
        
        try:
            # Verificar si el servidor de Ollama está corriendo
            subprocess.run(["ollama", "list"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("🚀 Iniciando servidor de Ollama...")
            try:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time
                time.sleep(3)  # Esperar a que el servidor inicie
            except Exception as e:
                print(f"⚠️ Error iniciando servidor de Ollama: {e}")
        
        # Descargar modelo por defecto
        default_model = "llama3.2:3b"
        print(f"📥 Descargando modelo {default_model}...")
        try:
            subprocess.run(["ollama", "pull", default_model], check=True)
            print(f"✅ Modelo {default_model} descargado")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error descargando modelo: {e}")
        
        print()
    
    def create_default_config(self):
        """Crea la configuración por defecto si no existe."""
        print("⚙️ Configurando sistema...")
        
        config_file = self.project_root / "para_config.json"
        if not config_file.exists():
            default_config = {
                "vault_path": "",
                "chroma_db_path": "./para_chroma_db",
                "ollama_host": "http://localhost:11434",
                "ollama_model": "llama3.2:3b",
                "dashboard_port": 7860,
                "auto_backup": True,
                "backup_path": "./backups",
                "keywords": [],
                "rules": [],
                "profile": "Default"
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print("✅ Archivo de configuración creado")
        else:
            print("✅ Archivo de configuración ya existe")
        
        print()
    
    def create_directories(self):
        """Crea los directorios necesarios."""
        print("📁 Creando directorios del sistema...")
        
        directories = [
            "logs",
            "backups",
            "para_chroma_db",
            "default_learning"
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            print(f"✅ {directory}/")
        
        print()
    
    def make_scripts_executable(self):
        """Hace los scripts ejecutables."""
        print("🔧 Configurando scripts ejecutables...")
        
        scripts = ["para_cli.py", "para.py"]
        
        for script in scripts:
            script_path = self.project_root / script
            if script_path.exists():
                try:
                    os.chmod(script_path, 0o755)
                    print(f"✅ {script} hecho ejecutable")
                except Exception as e:
                    print(f"⚠️ Error haciendo {script} ejecutable: {e}")
        
        print()
    
    def run_tests(self):
        """Ejecuta tests básicos para verificar la instalación."""
        print("🧪 Ejecutando tests de verificación...")
        
        python_exe = self.get_python_executable()
        
        # Test de importación de módulos
        test_script = """
import sys
sys.path.insert(0, '.')

try:
    import rich
    print("✅ rich - OK")
except ImportError as e:
    print(f"❌ rich - Error: {e}")

try:
    import ollama
    print("✅ ollama - OK")
except ImportError as e:
    print(f"❌ ollama - Error: {e}")

try:
    import chromadb
    print("✅ chromadb - OK")
except ImportError as e:
    print(f"❌ chromadb - Error: {e}")

try:
    from paralib.config import load_config
    print("✅ paralib - OK")
except ImportError as e:
    print(f"❌ paralib - Error: {e}")

print("🎉 Tests completados")
"""
        
        try:
            result = subprocess.run([str(python_exe), "-c", test_script], 
                                  capture_output=True, text=True, check=True)
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error en tests: {e}")
            print(e.stderr)
        
        print()
    
    def print_completion_message(self):
        """Imprime el mensaje de finalización."""
        print("=" * 60)
        print("🎉 ¡Instalación completada exitosamente!")
        print("=" * 60)
        print()
        print("📋 Próximos pasos:")
        print("1. Configura tu vault de Obsidian en para_config.json")
        print("2. Ejecuta: ./para_cli.py start")
        print("3. O ejecuta: ./para_cli.py help")
        print()
        print("🚀 Comandos disponibles:")
        print("  ./para_cli.py start     - Migración automática al sistema PARA")
        print("  ./para_cli.py help      - Ver todos los comandos")
        print("  ./para_cli.py dashboard - Abrir dashboard web")
        print("  ./para_cli.py doctor    - Diagnosticar problemas")
        print()
        print("📚 Documentación:")
        print("  - README.md para más información")
        print("  - docs/ para documentación detallada")
        print()
        print("💡 ¿Necesitas ayuda? Ejecuta: ./para_cli.py help")
        print()
    
    def run(self):
        """Ejecuta todo el proceso de instalación."""
        self.print_header()
        
        try:
            self.check_python_version()
            self.create_virtual_environment()
            self.upgrade_pip()
            self.install_python_packages()
            self.check_ollama_installation()
            self.setup_ollama_model()
            self.create_default_config()
            self.create_directories()
            self.make_scripts_executable()
            self.run_tests()
            self.print_completion_message()
            
        except KeyboardInterrupt:
            print("\n❌ Instalación cancelada por el usuario")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error durante la instalación: {e}")
            sys.exit(1)

def main():
    """Función principal."""
    setup = PARASetup()
    setup.run()

if __name__ == "__main__":
    main() 