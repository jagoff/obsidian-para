# 🏗️ Arquitectura del Sistema PARA - Documentación Completa

## 📋 Documentación Maestra de Arquitectura

Este documento proporciona una descripción completa de cada archivo, módulo y componente del sistema PARA, explicando su función exacta, responsabilidades y cómo se integra en la arquitectura general.

---

## 🎯 **Estructura General del Proyecto**

```
obsidian-para/
├── para_cli.py              # 🚀 Punto de entrada principal de la CLI
├── qa_auto.py               # 🧪 Sistema de QA automático
├── requirements.txt         # 📦 Dependencias del proyecto
├── para_config.json         # ⚙️ Configuración del usuario
├── para_config.default.json # ⚙️ Configuración por defecto
├── README.md                # 📖 Documentación principal
├── CHANGELOG.md             # 📝 Historial de cambios
├── LICENSE                  # 📄 Licencia del proyecto
├── install.sh               # 🔧 Script de instalación
├── paralib/                 # 📚 Biblioteca principal
├── plugins/                 # 🔌 Sistema de plugins
├── docs/                    # 📋 Documentación técnica
├── logs/                    # 📊 Logs del sistema
├── backups/                 # 💾 Backups automáticos
├── test/                    # 🧪 Tests del sistema
└── venv/                    # 🐍 Entorno virtual Python
```

---

## 🚀 **Archivos Principales (Root)**

### **1. `para_cli.py` - Punto de Entrada Principal**
**Función**: CLI principal que orquesta todo el sistema PARA
**Responsabilidades**:
- Interfaz de usuario principal con Rich
- Gestión de comandos core y plugins
- Integración de todos los módulos
- Manejo de argumentos y flujos de usuario
- Sistema de prompts en lenguaje natural
- Pre-checks de seguridad y backup automático

**Comandos principales**:
- `start` - Migración completa automatizada
- `classify` - Clasificación de notas
- `reclassify-all` - Reclasificación completa
- `doctor` - Diagnóstico y auto-reparación
- `dashboard` - Dashboard web interactivo
- `backups` - Gestión de backups
- `restore-backup` - Restauración completa
- `logs` - Gestión de logs
- `qa` - QA automático

**Integración**: Importa y coordina todos los módulos de `paralib/`

### **2. `qa_auto.py` - Sistema de QA Automático**
**Función**: Ejecuta pruebas automáticas completas del sistema
**Responsabilidades**:
- Prueba todos los comandos principales
- Verifica prompts de IA
- Analiza logs para detectar errores
- Valida integridad del sistema
- Genera reportes de QA

**Integración**: Se ejecuta independientemente o desde `para qa`

### **3. `requirements.txt` - Dependencias**
**Función**: Lista todas las dependencias Python necesarias
**Contenido principal**:
- `rich` - Interfaz visual rica
- `chromadb` - Base de datos vectorial
- `ollama` - Cliente para modelos de IA
- `typer` - Framework CLI
- `streamlit` - Dashboard web

### **4. `para_config.json` - Configuración del Usuario**
**Función**: Configuración personalizada del usuario
**Campos principales**:
- `vault_path` - Ruta al vault de Obsidian
- `ollama_model` - Modelo de IA preferido
- `auto_backup` - Backup automático activado
- `dashboard_port` - Puerto del dashboard

### **5. `install.sh` - Script de Instalación**
**Función**: Instalación automatizada del sistema
**Responsabilidades**:
- Instala dependencias Python
- Configura entorno virtual
- Ejecuta QA inicial
- Configuración inicial

---

## 📚 **Biblioteca Principal (`paralib/`)**

### **1. `__init__.py` - Inicialización del Módulo**
**Función**: Define la API pública de la biblioteca
**Responsabilidades**:
- Exporta funciones y clases principales
- Configuración de logging
- Inicialización de componentes

### **2. `ai_engine.py` - Motor de Inteligencia Artificial**
**Función**: Gestión y comunicación con modelos de IA
**Responsabilidades**:
- Comunicación con Ollama
- Gestión de modelos de IA
- Fallback automático entre modelos
- Procesamiento de prompts
- Validación de respuestas JSON
- Sistema de intents para comandos naturales

**Clases principales**:
- `AIEngine` - Motor principal de IA
- `IntentExample` - Ejemplos de intents

**Integración**: Usado por `organizer.py`, `analyze_manager.py`, `feedback_manager.py`

### **3. `organizer.py` - Organizador Principal**
**Función**: Lógica central de clasificación y organización
**Responsabilidades**:
- Clasificación híbrida (ChromaDB + IA)
- Gestión de planes de clasificación
- Ejecución de reclasificación completa
- Sistema de pesos dinámicos
- Manejo de discrepancias entre sistemas
- Progreso visual detallado

**Clases principales**:
- `PARAOrganizer` - Organizador principal
- Funciones de planificación y ejecución

**Integración**: Usado por `para_cli.py` para clasificación

### **4. `db.py` - Base de Datos ChromaDB**
**Función**: Gestión de la base de datos vectorial
**Responsabilidades**:
- Operaciones CRUD en ChromaDB
- Gestión de embeddings
- Búsqueda semántica
- Estadísticas de base de datos
- Migración y compatibilidad
- Backup y restauración de datos

**Clases principales**:
- `ChromaPARADatabase` - Clase principal de base de datos

**Integración**: Usado por todos los módulos que necesitan persistencia

### **5. `learning_system.py` - Sistema de Aprendizaje**
**Función**: Aprendizaje autónomo y mejora continua
**Responsabilidades**:
- Aprendizaje de clasificaciones del usuario
- Exportación/importación de conocimiento
- Gestión de feedback
- Mejora de precisión
- Historial de aprendizaje
- Métricas de aprendizaje

**Clases principales**:
- `PARA_Learning_System` - Sistema principal de aprendizaje

**Integración**: Usado por `organizer.py`, `feedback_manager.py`

### **6. `analyze_manager.py` - Gestor de Análisis**
**Función**: Análisis profundo de notas y vault
**Responsabilidades**:
- Análisis completo de notas
- Extracción de metadatos
- Análisis de contenido
- Generación de snapshots
- Estadísticas detalladas
- Detección de patrones

**Clases principales**:
- `AnalyzeManager` - Gestor principal de análisis

**Integración**: Usado por `organizer.py`, `dashboard.py`

### **7. `vault.py` - Gestor de Vault**
**Función**: Detección y gestión de vaults de Obsidian
**Responsabilidades**:
- Detección automática de vaults
- Búsqueda en Google Drive, iCloud
- Validación de vaults
- Caché de rutas
- Gestión de múltiples vaults

**Funciones principales**:
- `find_vault()` - Detección automática
- `validate_vault()` - Validación

**Integración**: Usado por todos los módulos que necesitan acceso al vault

### **8. `vault_selector.py` - Selector de Vault**
**Función**: Selección interactiva de vaults
**Responsabilidades**:
- Interfaz de selección de vault
- Gestión de múltiples vaults
- Caché inteligente
- Validación de rutas

**Integración**: Usado por `para_cli.py`

### **9. `vault_cli.py` - CLI de Vault**
**Función**: Comandos específicos para gestión de vault
**Responsabilidades**:
- Comandos de gestión de vault
- Validación de rutas
- Configuración de vault
- Información de vault

**Integración**: Plugin del sistema principal

### **10. `dashboard.py` - Dashboard Web**
**Función**: Dashboard web interactivo con Streamlit
**Responsabilidades**:
- Interfaz web del sistema
- Visualización de datos
- Estadísticas en tiempo real
- Gestión de configuración
- Monitoreo de estado

**Clases principales**:
- `PARABackendDashboard` - Dashboard principal

**Integración**: Se ejecuta independientemente o desde `para dashboard`

### **11. `log_manager.py` - Gestor de Logs**
**Función**: Sistema inteligente de gestión de logs
**Responsabilidades**:
- Análisis automático de logs
- Auto-resolución de problemas
- Métricas de logs
- Detección de patrones
- Notificaciones inteligentes

**Clases principales**:
- `PARALogManager` - Gestor principal de logs
- `LogEntry` - Entrada de log

**Integración**: Usado por todos los módulos para logging

### **12. `logger.py` - Logger Básico**
**Función**: Configuración básica de logging
**Responsabilidades**:
- Configuración de logging
- Formato de logs
- Niveles de log

**Integración**: Usado por todos los módulos

### **13. `log_analyzer.py` - Analizador de Logs**
**Función**: Análisis avanzado de logs
**Responsabilidades**:
- Análisis de patrones en logs
- Detección de errores
- Auto-fix de problemas
- Reportes de análisis

**Integración**: Usado por `log_manager.py`

### **14. `classification_log.py` - Log de Clasificación**
**Función**: Logging específico de clasificación
**Responsabilidades**:
- Registro de clasificaciones
- Historial de decisiones
- Métricas de precisión
- Análisis de tendencias

**Integración**: Usado por `organizer.py`

### **15. `feedback_manager.py` - Gestor de Feedback**
**Función**: Sistema de feedback y mejora
**Responsabilidades**:
- Recolección de feedback
- Análisis de calidad
- Mejora de clasificación
- Estadísticas de feedback

**Clases principales**:
- `FeedbackAnalyzer` - Analizador de feedback

**Integración**: Usado por `learning_system.py`

### **16. `clean_manager.py` - Gestor de Limpieza**
**Función**: Limpieza automática del vault
**Responsabilidades**:
- Detección de archivos duplicados
- Limpieza de archivos vacíos
- Organización de archivos no-Markdown
- Detección de archivos corruptos

**Clases principales**:
- `CleanManager` - Gestor principal de limpieza

**Integración**: Usado por `para_cli.py`

### **17. `plugin_system.py` - Sistema de Plugins**
**Función**: Sistema modular de plugins
**Responsabilidades**:
- Carga dinámica de plugins
- Gestión de comandos de plugins
- Sistema de hooks
- Registro de plugins

**Clases principales**:
- `PARAPluginManager` - Gestor de plugins
- `PARAPlugin` - Clase base de plugins

**Integración**: Usado por `para_cli.py`

### **18. `ui.py` - Interfaz de Usuario**
**Función**: Componentes de UI reutilizables
**Responsabilidades**:
- Componentes de interfaz
- Monitoreo en tiempo real
- Interfaz de terminal
- Componentes visuales

**Integración**: Usado por varios módulos

### **19. `utils.py` - Utilidades**
**Función**: Funciones utilitarias del sistema
**Responsabilidades**:
- Backup automático
- Pre-checks de comandos
- Funciones auxiliares
- Validaciones comunes

**Integración**: Usado por múltiples módulos

### **20. `config.py` - Configuración**
**Función**: Gestión de configuración
**Responsabilidades**:
- Carga de configuración
- Validación de config
- Configuración por defecto
- Gestión de perfiles

**Integración**: Usado por todos los módulos

### **21. `setup.py` - Configuración Inicial**
**Función**: Configuración inicial del sistema
**Responsabilidades**:
- Configuración inicial
- Creación de directorios
- Configuración por defecto
- Validación de entorno

**Clases principales**:
- `PARASetup` - Configuración inicial

**Integración**: Usado durante la instalación

### **22. `auto_fix.py` - Auto-Reparación**
**Función**: Reparación automática de errores
**Responsabilidades**:
- Detección de errores
- Auto-fix con IA
- Backup antes de cambios
- Registro de fixes

**Clases principales**:
- `AutoFixEngine` - Motor de auto-fix

**Integración**: Usado por `log_manager.py`

### **23. `similarity.py` - Cálculo de Similitud**
**Función**: Cálculo de similitud entre documentos
**Responsabilidades**:
- Cálculo de similitud
- Algoritmos de comparación
- Optimización de búsqueda
- Métricas de similitud

**Integración**: Usado por `organizer.py`, `analyze_manager.py`

### **24. `finetune_manager.py` - Gestor de Fine-tuning**
**Función**: Fine-tuning de modelos de IA
**Responsabilidades**:
- Preparación de datos
- Fine-tuning de modelos
- Evaluación de modelos
- Gestión de versiones

**Integración**: Usado por `learning_system.py`

---

## 🔌 **Sistema de Plugins (`plugins/`)**

### **1. `__init__.py` - Inicialización de Plugins**
**Función**: Configuración del sistema de plugins

### **2. `obsidian_integration.py` - Integración con Obsidian**
**Función**: Integración específica con Obsidian
**Responsabilidades**:
- Comandos específicos de Obsidian
- Gestión de vault de Obsidian
- Sincronización con Obsidian
- Backup de Obsidian
- Gestión de plugins de Obsidian
- Búsqueda en Obsidian
- Análisis del grafo de Obsidian
- Monitoreo en tiempo real

**Clases principales**:
- `ObsidianIntegrationPlugin` - Plugin principal

**Comandos**:
- `obsidian-vault` - Gestión de vault
- `obsidian-sync` - Sincronización
- `obsidian-backup` - Backup
- `obsidian-plugins` - Gestión de plugins
- `obsidian-notes` - Gestión de notas
- `obsidian-search` - Búsqueda
- `obsidian-graph` - Análisis de grafo
- `obsidian-watch` - Monitoreo

### **3. `plugins_config.json` - Configuración de Plugins**
**Función**: Configuración del sistema de plugins

---

## 📋 **Documentación (`docs/`)**

### **1. `CLI_DESIGN_GUIDELINES.md`**
**Función**: Lineamientos maestros de diseño CLI
**Contenido**:
- Principios fundamentales
- Estándares visuales
- Patrones de implementación
- Flujos de usuario
- Estándares de logging
- Patrones de UX

### **2. `FEATURES_STATUS.md`**
**Función**: Estado actual de todas las funcionalidades
**Contenido**:
- Estado de implementación
- Funcionalidades completadas
- Funcionalidades en desarrollo
- Roadmap

### **3. `checklist_post_migracion.md`**
**Función**: Checklist post-migración
**Contenido**:
- Verificaciones post-migración
- Configuraciones necesarias
- Pruebas recomendadas

---

## 📊 **Directorios de Datos**

### **1. `logs/` - Logs del Sistema**
**Función**: Almacenamiento de logs
**Contenido**:
- `para.log` - Log principal del sistema
- `log_manager.db` - Base de datos de logs
- Logs de diferentes módulos

### **2. `backups/` - Backups Automáticos**
**Función**: Almacenamiento de backups
**Contenido**:
- Backups de vault (`vault_backup_*.zip`)
- Backups de conocimiento (`para_learning_knowledge_backup_*.json`)
- Backups de ChromaDB (`chromadb_backup_*.zip`)

### **3. `test/` - Tests del Sistema**
**Función**: Tests automatizados
**Contenido**:
- Tests unitarios
- Tests de integración
- Tests de QA

### **4. `venv/` - Entorno Virtual**
**Función**: Entorno virtual Python
**Contenido**:
- Dependencias instaladas
- Configuración de Python

---

## 🔄 **Flujos de Integración Principales**

### **1. Flujo de Clasificación**
```
para_cli.py → organizer.py → ai_engine.py + db.py → learning_system.py
```

### **2. Flujo de Análisis**
```
para_cli.py → analyze_manager.py → db.py → similarity.py
```

### **3. Flujo de Logging**
```
Todos los módulos → logger.py → log_manager.py → log_analyzer.py
```

### **4. Flujo de Backup**
```
para_cli.py → utils.py → auto_backup_if_needed() → backups/
```

### **5. Flujo de Plugins**
```
para_cli.py → plugin_system.py → plugins/ → comandos específicos
```

---

## 🎯 **Principios de Arquitectura**

### **1. Modularidad**
- Cada módulo tiene responsabilidades específicas
- Interfaces claras entre módulos
- Bajo acoplamiento, alta cohesión

### **2. Robustez**
- Fallbacks automáticos en cada nivel
- Backup automático antes de operaciones críticas
- Manejo de errores en cascada

### **3. Extensibilidad**
- Sistema de plugins modular
- APIs claras para extensión
- Configuración flexible

### **4. Observabilidad**
- Logging detallado en todos los niveles
- Métricas y monitoreo
- Dashboard en tiempo real

---

## 📚 **Dependencias Principales**

### **Core Dependencies**
- `rich` - Interfaz visual rica
- `chromadb` - Base de datos vectorial
- `ollama` - Cliente para modelos de IA
- `typer` - Framework CLI
- `streamlit` - Dashboard web

### **AI/ML Dependencies**
- `sentence-transformers` - Embeddings
- `numpy` - Computación numérica
- `pandas` - Manipulación de datos

### **Utility Dependencies**
- `pathlib` - Manejo de rutas
- `datetime` - Manejo de fechas
- `json` - Serialización
- `sqlite3` - Base de datos local

---

*Última actualización: 2025-06-26*
*Versión: 1.0*
*Mantenido por: Sistema PARA* 