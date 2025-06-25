#!/bin/bash

# install.sh - Script de instalación principal del sistema PARA
# Este script automatiza la instalación completa del sistema

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_header() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "🚀 PARA System - Instalación y Configuración Automática"
    echo "============================================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}💡 $1${NC}"
}

# Verificar sistema operativo
check_os() {
    print_step "🔍 Verificando sistema operativo..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "macOS detectado"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "Linux detectado"
    else
        print_error "Sistema operativo no soportado: $OSTYPE"
        exit 1
    fi
}

# Verificar Python
check_python() {
    print_step "🐍 Verificando Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        print_success "Python $PYTHON_VERSION encontrado"
    else
        print_error "Python 3 no encontrado"
        print_info "Instala Python 3 desde: https://python.org"
        exit 1
    fi
}

# Instalar dependencias del sistema
install_system_dependencies() {
    print_step "📦 Instalando dependencias del sistema..."
    
    if [[ "$OS" == "macos" ]]; then
        # Verificar si Homebrew está instalado
        if ! command -v brew &> /dev/null; then
            print_info "Instalando Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        # Instalar dependencias con Homebrew
        brew install curl git
        print_success "Dependencias de macOS instaladas"
        
    elif [[ "$OS" == "linux" ]]; then
        # Detectar gestor de paquetes
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y curl git python3-venv
        elif command -v yum &> /dev/null; then
            sudo yum install -y curl git python3-venv
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y curl git python3-venv
        else
            print_error "Gestor de paquetes no soportado"
            exit 1
        fi
        print_success "Dependencias de Linux instaladas"
    fi
}

# Instalar Ollama
install_ollama() {
    print_step "🤖 Instalando Ollama..."
    
    if command -v ollama &> /dev/null; then
        print_success "Ollama ya está instalado"
    else
        print_info "Descargando e instalando Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        
        # Agregar Ollama al PATH si es necesario
        if [[ "$OS" == "macos" ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
            source ~/.zshrc
        fi
        
        print_success "Ollama instalado exitosamente"
    fi
}

# Crear entorno virtual
create_virtual_environment() {
    print_step "🔧 Creando entorno virtual..."
    
    if [ -d "venv" ]; then
        print_success "Entorno virtual ya existe"
    else
        python3 -m venv venv
        print_success "Entorno virtual creado"
    fi
}

# Activar entorno virtual e instalar dependencias
install_python_dependencies() {
    print_step "📦 Instalando dependencias de Python..."
    
    # Activar entorno virtual
    source venv/bin/activate
    
    # Actualizar pip
    pip install --upgrade pip
    
    # Instalar dependencias desde requirements.txt
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencias de requirements.txt instaladas"
    fi
    
    # Instalar dependencias adicionales si es necesario
    pip install rich ollama chromadb streamlit pandas numpy requests
    print_success "Dependencias de Python instaladas"
}

# Configurar el sistema
setup_system() {
    print_step "⚙️ Configurando sistema..."
    
    # Crear directorios necesarios
    mkdir -p logs backups para_chroma_db default_learning
    
    # Crear configuración por defecto si no existe
    if [ ! -f "para_config.json" ]; then
        cat > para_config.json << EOF
{
  "vault_path": "",
  "chroma_db_path": "./para_chroma_db",
  "ollama_host": "http://localhost:11434",
  "ollama_model": "llama3.2:3b",
  "dashboard_port": 7860,
  "auto_backup": true,
  "backup_path": "./backups",
  "keywords": [],
  "rules": [],
  "profile": "Default"
}
EOF
        print_success "Archivo de configuración creado"
    fi
    
    # Hacer scripts ejecutables
    chmod +x para_cli.py para.py setup.py
    print_success "Scripts hechos ejecutables"
}

# Descargar modelo de Ollama
setup_ollama_model() {
    print_step "🤖 Configurando modelo de Ollama..."
    
    # Iniciar servidor de Ollama en background
    ollama serve &
    OLLAMA_PID=$!
    
    # Esperar a que el servidor inicie
    sleep 5
    
    # Descargar modelo por defecto
    ollama pull llama3.2:3b
    
    # Detener servidor
    kill $OLLAMA_PID 2>/dev/null || true
    
    print_success "Modelo de Ollama configurado"
}

# Ejecutar tests de verificación
run_tests() {
    print_step "🧪 Ejecutando tests de verificación..."
    
    source venv/bin/activate
    
    # Test básico de importación
    python3 -c "
import sys
sys.path.insert(0, '.')

try:
    import rich
    print('✅ rich - OK')
except ImportError as e:
    print(f'❌ rich - Error: {e}')

try:
    import ollama
    print('✅ ollama - OK')
except ImportError as e:
    print(f'❌ ollama - Error: {e}')

try:
    import chromadb
    print('✅ chromadb - OK')
except ImportError as e:
    print(f'❌ chromadb - Error: {e}')

print('🎉 Tests completados')
"
    
    print_success "Tests de verificación completados"
}

# Mostrar mensaje de finalización
show_completion() {
    echo -e "${GREEN}"
    echo "============================================================"
    echo "🎉 ¡Instalación completada exitosamente!"
    echo "============================================================"
    echo -e "${NC}"
    echo
    echo "📋 Próximos pasos:"
    echo "1. Configura tu vault de Obsidian en para_config.json"
    echo "2. Ejecuta: ./para_cli.py start"
    echo "3. O ejecuta: ./para_cli.py help"
    echo
    echo "🚀 Comandos disponibles:"
    echo "  ./para_cli.py start     - Migración automática al sistema PARA"
    echo "  ./para_cli.py help      - Ver todos los comandos"
    echo "  ./para_cli.py dashboard - Abrir dashboard web"
    echo "  ./para_cli.py doctor    - Diagnosticar problemas"
    echo
    echo "📚 Documentación:"
    echo "  - README.md para más información"
    echo "  - docs/ para documentación detallada"
    echo
    echo "💡 ¿Necesitas ayuda? Ejecuta: ./para_cli.py help"
    echo
}

# Ejecutar setup de Python si está disponible
if command -v python3 >/dev/null 2>&1; then
    print_step "🔧 Ejecutando setup de Python..."
    if [ -f "paralib/setup.py" ]; then
        python3 paralib/setup.py
        if [ $? -eq 0 ]; then
            print_success "Setup de Python completado"
        else
            print_error "Error en setup de Python"
        fi
    else
        print_info "Setup de Python no encontrado, continuando con instalación manual"
    fi
fi

# Función principal
main() {
    print_header
    
    check_os
    check_python
    install_system_dependencies
    install_ollama
    create_virtual_environment
    install_python_dependencies
    setup_system
    setup_ollama_model
    run_tests
    show_completion
}

# Manejar interrupciones
trap 'print_error "Instalación cancelada por el usuario"; exit 1' INT

# Ejecutar instalación
main "$@" 