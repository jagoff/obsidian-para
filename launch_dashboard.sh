#!/bin/bash

# Script de lanzamiento para el PARA Backend Dashboard
# Uso: ./launch_dashboard.sh [puerto] [host]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración por defecto
DEFAULT_PORT=8501
DEFAULT_HOST="localhost"

# Obtener parámetros
PORT=${1:-$DEFAULT_PORT}
HOST=${2:-$DEFAULT_HOST}

echo -e "${BLUE}🚀 PARA Backend Dashboard Launcher${NC}"
echo -e "${YELLOW}Puerto: ${PORT}${NC}"
echo -e "${YELLOW}Host: ${HOST}${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "para_backend_dashboard.py" ]; then
    echo -e "${RED}❌ Error: No se encontró para_backend_dashboard.py${NC}"
    echo -e "${YELLOW}💡 Asegúrate de ejecutar este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar que Python esté instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python3 no está instalado${NC}"
    exit 1
fi

# Verificar que streamlit esté instalado
if ! python3 -c "import streamlit" &> /dev/null; then
    echo -e "${RED}❌ Error: Streamlit no está instalado${NC}"
    echo -e "${YELLOW}💡 Instala con: pip install streamlit plotly${NC}"
    exit 1
fi

# Verificar que plotly esté instalado
if ! python3 -c "import plotly" &> /dev/null; then
    echo -e "${RED}❌ Error: Plotly no está instalado${NC}"
    echo -e "${YELLOW}💡 Instala con: pip install plotly${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencias verificadas${NC}"

# Crear directorio de logs si no existe
mkdir -p logs

# Función para limpiar al salir
cleanup() {
    echo -e "\n${YELLOW}👋 Cerrando dashboard...${NC}"
    exit 0
}

# Capturar Ctrl+C
trap cleanup SIGINT

echo -e "${BLUE}🌐 Iniciando dashboard en http://${HOST}:${PORT}${NC}"
echo -e "${YELLOW}💡 Presiona Ctrl+C para cerrar${NC}"
echo ""

# Lanzar el dashboard de backend (puerto por defecto: 8501)
streamlit run para_backend_dashboard.py --server.headless true --server.runOnSave true &
echo "[INFO] Dashboard lanzado en http://localhost:8501"

# Script para actualizar automáticamente el seguimiento y template del proyecto Obsidian-PARA cada 30 minutos

while true; do
  cp "$(dirname "$0")/01-Projects/Obsidian-PARA/notas.md" \
    "/Users/fernandoferrari/Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian/01-Projects/Obsidian-PARA/notas.md"
  cp "$(dirname "$0")/99 Templates/FEATURES_STATUS_TEMPLATE.md" \
    "/Users/fernandoferrari/Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian/01-Projects/Obsidian-PARA/FEATURES_STATUS_TEMPLATE.md"
  cp "$(dirname "$0")/99 Templates/FEATURES_STATUS_TEMPLATE.md" \
    "/Users/fernandoferrari/Library/CloudStorage/GoogleDrive-fernandoferrari@gmail.com/Mi unidad/Obsidian/04-Archive/Obsidian-System/99 Templates/FEATURES_STATUS_TEMPLATE.md"
  echo "[OK] Seguimiento y template actualizados: $(date)"
  sleep 1800 # 30 minutos
done 