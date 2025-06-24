#!/bin/bash
# Este script prepara el proyecto para publicación en GitHub, asegurando limpieza, estructura profesional y documentación en docs/.

echo "🚀 Preparando PARA System para GitHub..."

# Verificar que todos los archivos necesarios estén presentes
required_files=(
    "README.md"
    "LICENSE"
    ".gitignore"
    "requirements.txt"
    "para_dashboard.py"
    "para_monitor.py"
    "para_organizer.py"
    "install_para_system.sh"
)

echo "📋 Verificando archivos necesarios..."

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - FALTANTE"
        exit 1
    fi
done

# Verificar permisos de ejecución
echo ""
echo "🔧 Verificando permisos de ejecución..."

chmod +x install_para_system.sh
chmod +x para_monitor.py
chmod +x para_organizer.py

echo "✅ Permisos actualizados"

# Crear directorios necesarios si no existen
echo ""
echo "📁 Creando directorios necesarios..."

mkdir -p backups
mkdir -p logs

echo "✅ Directorios creados"

# Verificar que no haya archivos temporales o de desarrollo
echo ""
echo "🧹 Verificando limpieza del proyecto..."

# Listar archivos que podrían ser innecesarios
unwanted_patterns=(
    "*.pyc"
    "*.pyo"
    "__pycache__"
    "*.log"
    "*.tmp"
    "*.bak"
)

for pattern in "${unwanted_patterns[@]}"; do
    if ls $pattern 2>/dev/null; then
        echo "⚠️  Encontrados archivos con patrón: $pattern"
        echo "   Considera limpiarlos antes de subir a GitHub"
    fi
done

# Mostrar estadísticas del proyecto
echo ""
echo "📊 Estadísticas del proyecto:"

total_lines=$(find . -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.txt" -o -name "*.json" | xargs wc -l | tail -1 | awk '{print $1}')
echo "📝 Total de líneas de código: $total_lines"

total_files=$(find . -type f -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.txt" -o -name "*.json" | wc -l)
echo "📁 Total de archivos: $total_files"

echo ""
echo "🎉 ¡Proyecto listo para GitHub!"
echo ""
echo "📋 Próximos pasos:"
echo "1. git init"
echo "2. git add ."
echo "3. git commit -m 'Initial commit: PARA System with ChromaDB'"
echo "4. git remote add origin https://github.com/tu-usuario/obsidian-para.git"
echo "5. git push -u origin main"
echo ""
echo "🔗 Recuerda actualizar la URL del repositorio en README.md"
echo "📝 Considera agregar badges de estado en README.md"
echo "🎯 ¡Listo para compartir con la comunidad!" 