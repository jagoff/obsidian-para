#!/bin/bash

# PARA System Installation Script
# Installs and configures the complete PARA organization system

set -e

echo "🚀 Installing PARA System with ChromaDB and Dashboard..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
print_status "Checking system requirements..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed."
    exit 1
fi

print_success "System requirements met"

# Create virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install chromadb gradio sentence-transformers ollama rich numpy plotly

print_success "Python dependencies installed"

# Check/Install Ollama
if ! command -v ollama &> /dev/null; then
    print_warning "Ollama not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
        print_success "Ollama installed"
    else
        print_error "Please install Ollama manually from https://ollama.ai"
        exit 1
    fi
else
    print_success "Ollama found: $(ollama --version)"
fi

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_status "Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Download Ollama model
print_status "Downloading Ollama model (llama3.2:3b)..."
ollama pull llama3.2:3b
print_success "Ollama model downloaded"

# Create directories
mkdir -p backups logs
print_success "Directories created"

# Create configuration
cat > para_config.json << 'EOF'
{
    "vault_path": "",
    "chroma_db_path": "./para_chroma_db",
    "ollama_host": "http://localhost:11434",
    "ollama_model": "llama3.2:3b",
    "dashboard_port": 7860,
    "auto_backup": true,
    "backup_path": "./backups"
}
EOF

print_success "Configuration created"

# Create launcher script
cat > launch_para.sh << 'EOF'
#!/bin/bash

# PARA System Launcher
echo "🚀 Launching PARA System..."

# Activate virtual environment
source venv/bin/activate

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "⚠️  Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Launch dashboard
python para_dashboard.py
EOF

chmod +x launch_para.sh
print_success "Launcher script created"

# Create requirements file
cat > requirements.txt << 'EOF'
chromadb>=0.4.0
gradio>=4.0.0
sentence-transformers>=2.2.0
ollama>=0.1.0
rich>=13.0.0
numpy>=1.24.0
plotly>=5.0.0
EOF

print_success "Requirements file created"

# Create README
cat > README.md << 'EOF'
# 🗂️ PARA System with ChromaDB

Sistema completo para organizar automáticamente tu vault de Obsidian usando la metodología PARA con IA local y base de datos vectorial.

## 🚀 Instalación

```bash
./install_para_system.sh
```

## 🎯 Uso

### Lanzar el Dashboard
```bash
./launch_para.sh
```

### Organización Manual
```bash
source venv/bin/activate
python para_organizer.py
```

## 🗂️ Estructura PARA

- **00-inbox**: Elementos sin procesar
- **01-projects**: Proyectos activos
- **02-areas**: Responsabilidades continuas
- **03-resources**: Materiales de referencia
- **04-archive**: Proyectos completados

## 🔍 Características

- IA Local con Ollama
- Base de datos vectorial ChromaDB
- Dashboard web en tiempo real
- Búsqueda semántica
- Backup automático
- Monitoreo de progreso

## 🌐 Dashboard

Abre http://localhost:7860 en tu navegador

## 🛡️ Seguridad

- Backup automático
- Modo dry-run por defecto
- Validación de IA
- Manejo de errores robusto

---

**¡Organiza tu conocimiento con IA! 🧠✨**
EOF

print_success "README created"

echo ""
print_success "🎉 PARA System installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit para_config.json to set your vault path"
echo "2. Run: ./launch_para.sh"
echo "3. Open: http://localhost:7860"
echo ""
print_success "Happy organizing! 🗂️✨" 