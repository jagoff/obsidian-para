si # PARA System — Descripción de Archivos y Carpetas

Este documento describe exhaustivamente la utilidad de cada archivo y carpeta del proyecto PARA, para referencia de desarrolladores y usuarios avanzados.

---

## Estructura General del Proyecto

```
obsidian-para/
│
├── para_cli.py
├── qa_auto.py
├── analysis_output.json
├── para_learning_knowledge_restored.json
├── para_learning_knowledge_20250625_025651.json
├── para_config.default.json
├── para_config.json
├── requirements.txt
├── CHANGELOG.md
├── LICENSE
├── README.md
├── install.sh
│
├── paralib/
├── plugins/
├── docs/
├── scripts/
├── logs/
├── backups/
├── test/
├── default_learning/
├── .para_db/
├── venv/
└── __pycache__/
```

---

## Archivos y Carpetas Principales

### Archivos raíz

- **para_cli.py**  
  CLI principal del sistema PARA. Orquesta todos los comandos de organización, migración, backup, restauración, análisis, dashboard, auto-fix, etc.

- **qa_auto.py**  
  Script de automatización para pruebas rápidas de calidad y regresión.

- **analysis_output.json**  
  Salida de análisis de vaults, usada para debugging o reportes.

- **para_learning_knowledge_restored.json / para_learning_knowledge_*.json**  
  Backups y snapshots del conocimiento aprendido por el sistema (ChromaDB, IA).

- **para_config.default.json / para_config.json**  
  Configuración por defecto y personalizada del sistema PARA.

- **requirements.txt**  
  Dependencias Python necesarias para el entorno.

- **CHANGELOG.md**  
  Historial de cambios y versiones del sistema.

- **LICENSE**  
  Licencia del proyecto.

- **README.md**  
  Documentación principal, guía de uso, instalación y ejemplos.

- **install.sh**  
  Script de instalación y setup inicial (puede estar en desuso si todo es Python).

---

### Carpetas clave

#### paralib/
Módulos principales de lógica, IA, organización, auto-fix, logging, plugins, etc.

- **ai_engine.py**  
  Motor de IA para clasificación, prompts, integración con LLMs.
- **organizer.py**  
  Lógica central de organización y migración de notas según PARA.
- **analyze_manager.py**  
  Análisis de vaults, generación de snapshots, métricas.
- **learning_system.py**  
  Sistema de aprendizaje continuo, feedback y ajuste de parámetros.
- **db.py**  
  Acceso y gestión de la base de datos ChromaDB y otras.
- **log_manager.py**  
  Gestión avanzada de logs, auto-fix, resolución automática, métricas.
- **auto_fix.py**  
  Motor de auto-fix de errores de código y sistema usando IA.
- **log_analyzer.py**  
  Análisis de logs para sugerir y aplicar fixes automáticos.
- **clean_manager.py**  
  Limpieza automática de vaults: duplicados, vacíos, corruptos.
- **feedback_manager.py**  
  Gestión y análisis de feedback de usuario y sistema.
- **finetune_manager.py**  
  Lógica para fine-tuning de modelos de IA.
- **dashboard.py**  
  Backend del dashboard visual (Streamlit).
- **ui.py**  
  Utilidades de interfaz de usuario para CLI y dashboard.
- **utils.py**  
  Utilidades generales, helpers, backups automáticos.
- **vault.py / vault_cli.py / vault_selector.py**  
  Gestión de vaults, selección, CLI específica de vaults.
- **plugin_system.py**  
  Sistema de plugins y hooks para extensibilidad.
- **classification_log.py**  
  Registro de clasificaciones y resultados de IA.
- **similarity.py**  
  Utilidades de similitud semántica y búsqueda.
- **logger.py**  
  Logger centralizado para todo el sistema.
- **config.py**  
  Utilidades de configuración.
- **setup.py**  
  Setup y utilidades de inicialización.
- **tests/**  
  Pruebas unitarias y de integración (ej: test_features.py).
- **exclusion_manager.py**  
  Módulo centralizado para gestionar exclusiones de carpetas en todo el sistema PARA.

#### plugins/
Plugins oficiales y de integración.

- **obsidian_integration.py**  
  Plugin para integración avanzada con Obsidian (sincronización, comandos, hooks).
- **plugins_config.json**  
  Configuración de plugins activos.
- **__init__.py**  
  Inicialización del paquete de plugins.

#### docs/
Documentación avanzada y de referencia.

- **API_REFERENCE.md**  
  Referencia completa de la API interna y pública.
- **ARCHITECTURE_DOCUMENTATION.md**  
  Documentación de arquitectura y diseño del sistema.
- **CLI_DESIGN_GUIDELINES.md**  
  Guía de diseño y buenas prácticas para la CLI.
- **checklist_post_migracion.md**  
  Checklist para migraciones y validaciones post-migración.
- **FEATURES_STATUS.md**  
  Estado de desarrollo y cobertura de features.

#### scripts/
Scripts utilitarios y de mantenimiento.

- **force_log_autofix.py**  
  Script para forzar auto-fix y limpieza manual de logs pendientes.

#### logs/
Logs de ejecución, errores, auditoría y debugging.

#### backups/
Backups automáticos y manuales de vaults y bases de datos.

- **vault_backup_*.zip**  
  Backups completos de vaults.
- **chromadb_backup_*.zip**  
  Backups de la base de datos de conocimiento.

#### default_learning/
Datos y bases de conocimiento por defecto para aprendizaje inicial.

#### test/
Carpeta para pruebas, puede contener bases de datos o fixtures de test.

#### .para_db/
Bases de datos internas del sistema PARA.

#### venv/
Entorno virtual Python (no versionar).

#### __pycache__/
Archivos de caché de Python (no versionar).

---

## Resumen

- Cada archivo y módulo tiene una función clara: desde la organización y migración de notas, hasta el auto-fix, logging inteligente, integración con Obsidian, y aprendizaje automático.
- El sistema es extensible mediante plugins y scripts de mantenimiento.
- La documentación y los scripts de mantenimiento permiten mantener el sistema limpio, auditable y fácil de evolucionar.

## Módulos Core (paralib/)

### paralib/exclusion_manager.py
**Propósito:** Módulo centralizado para gestionar exclusiones de carpetas en todo el sistema PARA.
**Funcionalidades:**
- Gestión unificada de exclusiones globales de carpetas
- GUI interactiva para seleccionar carpetas a excluir
- Filtrado automático de notas basado en exclusiones
- Estadísticas de exclusión por vault
- Interfaz consistente para todos los scripts y módulos
**Uso:** Importado automáticamente por todos los comandos que procesan notas
**Dependencias:** paralib/config.py, paralib/ui.py

### paralib/config.py 