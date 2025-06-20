# 🗂️ PARA System with ChromaDB

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-jagoff/obsidian--para-blue.svg)](https://github.com/jagoff/obsidian-para)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2:3b-orange.svg)](https://ollama.ai)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-purple.svg)](https://chromadb.com)

Sistema completo para organizar automáticamente tu vault de Obsidian usando la metodología PARA con IA local y base de datos vectorial.

## 🚀 Características

- **🤖 IA Local**: Clasificación automática usando Ollama (llama3.2:3b)
- **🗄️ Base de Datos Vectorial**: ChromaDB para búsqueda semántica y almacenamiento
- **📊 Dashboard en Tiempo Real**: Interfaz web con Gradio para monitoreo
- **🔍 Búsqueda Semántica**: Búsqueda vectorial avanzada de notas
- **📈 Monitoreo Avanzado**: Estadísticas detalladas y gráficos interactivos
- **🛡️ Seguridad**: Backup automático y modo dry-run
- **⚡ Detección Automática**: Encuentra automáticamente tu vault de Obsidian

## 📦 Instalación

### Requisitos Previos

- Python 3.8+
- pip3
- Ollama (se instala automáticamente en macOS)

### Instalación Automática

```bash
# Clonar el repositorio
git clone https://github.com/jagoff/obsidian-para.git
cd obsidian-para

# Ejecutar instalación automática
./install_para_system.sh
```

### Instalación Manual

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install chromadb gradio sentence-transformers ollama rich numpy plotly

# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo
ollama pull llama3.2:3b
```

## 🎯 Uso

### 1. Lanzar el Dashboard Web

```bash
./launch_para.sh
# O
python para_dashboard.py
```

Abre http://localhost:7860 en tu navegador

### 2. Monitorear en Terminal

```bash
python para_monitor.py
```

### 3. Organización Manual

```bash
python para_organizer.py
```

## 🗂️ Estructura PARA

El sistema organiza tus notas en la siguiente estructura:

- **00-inbox**: Elementos sin procesar que necesitan revisión
- **01-projects**: Proyectos activos con fechas límite y resultados específicos
- **02-areas**: Responsabilidades continuas y áreas de vida
- **03-resources**: Materiales de referencia, conocimiento y herramientas
- **04-archive**: Proyectos completados e items inactivos

## 🔍 Búsqueda Semántica

El sistema incluye búsqueda semántica usando embeddings vectoriales:

```python
# Buscar notas similares
results = db.search_similar_notes("proyecto de desarrollo", n_results=5)

# Búsqueda con filtro por categoría
results = db.search_similar_notes("marketing", category_filter="projects")
```

## 📊 Dashboard Web

### Funcionalidades

- **📊 Control de Organización**: Start/Stop con opciones de dry-run y backup
- **📈 Estadísticas en Tiempo Real**: Progreso, velocidad, tiempo estimado
- **🔍 Búsqueda Avanzada**: Búsqueda vectorial con filtros por categoría
- **📊 Gráficos Interactivos**: Distribución PARA con Plotly
- **📝 Notas Recientes**: Actividad reciente del sistema
- **🔄 Auto-refresh**: Actualización automática cada 3-5 segundos

### Interfaz

- **Organización Control**: Iniciar/detener organización, configurar opciones
- **Real-time Statistics**: Estadísticas en tiempo real con gráficos
- **Advanced Search**: Búsqueda semántica con filtros
- **Recent Activity**: Actividad reciente y notas procesadas

## 📈 Monitoreo de Terminal

El monitor en terminal muestra:

- **📊 Estadísticas de Base de Datos**: Tamaño, número de notas, palabras
- **🗂️ Distribución por Categorías**: Conteos y porcentajes
- **📝 Actividad Reciente**: Notas procesadas en las últimas 24h
- **⚡ Métricas de Rendimiento**: Velocidad de procesamiento, tiempo estimado

## 🛡️ Seguridad

- **🔄 Backup Automático**: Respaldo automático antes de cada operación
- **👀 Modo Dry-Run**: Vista previa sin mover archivos (por defecto)
- **✅ Validación de IA**: Verificación de respuestas de clasificación
- **🛠️ Manejo de Errores**: Recuperación robusta de fallos
- **💾 Configuración Persistente**: Ajustes guardados automáticamente

## 🔧 Configuración

Edita `para_config.json` para personalizar:

```json
{
    "vault_path": "/path/to/your/vault",
    "chroma_db_path": "./para_chroma_db",
    "ollama_host": "http://localhost:11434",
    "ollama_model": "llama3.2:3b",
    "dashboard_port": 7860,
    "auto_backup": true,
    "backup_path": "./backups",
    "dry_run_default": true
}
```

## 📁 Estructura del Proyecto

```
obsidian-para/
├── para_dashboard.py          # Dashboard web principal
├── para_monitor.py           # Monitor de terminal
├── para_organizer.py         # Organizador principal
├── install_para_system.sh    # Script de instalación
├── launch_para.sh           # Lanzador del sistema
├── para_config.json         # Configuración
├── requirements.txt         # Dependencias Python
├── README.md               # Este archivo
├── backups/                # Backups automáticos
├── logs/                   # Logs del sistema
└── para_chroma_db/         # Base de datos vectorial
```

## 🔄 Actualización

Para actualizar el sistema:

```bash
# Actualizar dependencias
source venv/bin/activate
pip install --upgrade chromadb gradio sentence-transformers ollama rich plotly

# Actualizar modelo de IA
ollama pull llama3.2:3b
```

## 🐛 Solución de Problemas

### Ollama no está ejecutándose
```bash
ollama serve
```

### Error de dependencias
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Vault no detectado
Edita `para_config.json` y especifica manualmente la ruta del vault.

### Error de permisos
```bash
chmod +x *.sh
```

## 📝 Logs

Los logs se guardan en `./logs/` para debugging y monitoreo.

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [Ollama](https://ollama.ai) - IA local
- [ChromaDB](https://chromadb.com) - Base de datos vectorial
- [Gradio](https://gradio.app) - Interfaz web
- [Rich](https://rich.readthedocs.io) - Terminal UI
- [Sentence Transformers](https://sentence-transformers.readthedocs.io) - Embeddings

## 📞 Soporte

Si tienes problemas o preguntas:

1. Revisa la sección de [Solución de Problemas](#-solución-de-problemas)
2. Abre un [Issue](https://github.com/jagoff/obsidian-para/issues)
3. Consulta la [documentación](https://github.com/jagoff/obsidian-para/wiki)

---

**¡Disfruta organizando tu conocimiento con IA! 🧠✨**

---

*Desarrollado con ❤️ para la comunidad de Obsidian*
