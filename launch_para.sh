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
