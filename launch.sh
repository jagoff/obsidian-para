#!/usr/bin/env zsh
# set -e
#
# launch.sh
#
# Script de lanzamiento para la aplicación PARA CLI.
# Se asegura de que la aplicación se ejecute dentro de su entorno virtual
# y de que las dependencias estén correctamente instaladas.
#
# MIT License
#
# Copyright (c) 2024 Fernando Ferrari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# Obtenemos el directorio donde se encuentra el script
SCRIPT_DIR="$( cd "$( dirname "${0}" )" &> /dev/null && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
DEPS_MARKER="$VENV_DIR/.deps_installed"

# 1. Verificar si el entorno virtual existe, si no, crearlo.
if [[ ! -d "$VENV_DIR" ]]; then
    echo "🐍 Creando entorno virtual en '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
    if [[ $? -ne 0 ]]; then
        echo "❌ Error: No se pudo crear el entorno virtual."
        exit 1
    fi
fi

# 2. Activar el entorno virtual
source "$VENV_DIR/bin/activate"

# 3. Instalar/actualizar dependencias si es la primera vez o si requirements.txt cambió.
if [[ ! -f "$DEPS_MARKER" || "$SCRIPT_DIR/requirements.txt" -nt "$DEPS_MARKER" ]]; then
    echo "📦 Actualizando dependencias (esto podría tardar un momento)..."
    pip install --upgrade pip &> /dev/null
    pip install --no-cache-dir -r "$SCRIPT_DIR/requirements.txt" > /dev/null
    if [[ $? -ne 0 ]]; then
        echo "❌ Error: No se pudieron instalar las dependencias."
        deactivate
        exit 1
    fi
    # Crear/actualizar el archivo marcador para no reinstalar la próxima vez
    touch "$DEPS_MARKER"
    echo "✅ Dependencias listas."
fi

# 4. Ejecutar la aplicación principal
echo "🚀 Lanzando PARA CLI..."
python3 "$SCRIPT_DIR/para_cli.py" "$@"

# Opcional: Desactivar el entorno al salir (el script de arriba toma el control,
# pero si el script de python falla, esto se ejecutará)
deactivate 