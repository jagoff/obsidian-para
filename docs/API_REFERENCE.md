# 🔧 Referencia Completa de la API - Sistema PARA

## 📋 Documentación Técnica de Funciones y Métodos

Este documento proporciona una referencia completa de todas las funciones, métodos y clases del sistema PARA, con ejemplos de uso, parámetros y casos de aplicación.

---

## 🚀 **API Principal (`para_cli.py`)**

### **Clase Principal: `PARACLI`**

#### **Métodos de Inicialización**
```python
def __init__(self)
```
**Propósito**: Inicializa la CLI principal del sistema PARA
**Responsabilidades**:
- Configuración de Rich para interfaz visual
- Inicialización del sistema de plugins
- Configuración de logging
- Carga de configuración

#### **Métodos de Comandos Principales**

##### **`start_command()`**
```python
def start_command(self, vault: str = None, force: bool = False)
```
**Propósito**: Comando de migración completa automatizada
**Parámetros**:
- `vault`: Ruta al vault (opcional, auto-detecta si no se especifica)
- `force`: Forzar migración sin confirmación

**Flujo**:
1. Detección automática de vault
2. Pre-checks de seguridad
3. Backup automático
4. Análisis completo del vault
5. Clasificación inicial
6. Configuración de sistema de aprendizaje

##### **`classify_command()`**
```python
def classify_command(self, vault: str = None, prompt: str = None, force: bool = False)
```
**Propósito**: Clasificación de notas nuevas o modificadas
**Parámetros**:
- `vault`: Ruta al vault
- `prompt`: Instrucciones personalizadas para la IA
- `force`: Forzar clasificación sin confirmación

**Flujo**:
1. Pre-checks de seguridad
2. Backup automático
3. Análisis de notas nuevas
4. Clasificación híbrida (ChromaDB + IA)
5. Aplicación de cambios
6. Actualización del sistema de aprendizaje

##### **`reclassify_all_command()`**
```python
def reclassify_all_command(self, vault: str = None, execute: bool = False)
```
**Propósito**: Reclasificación completa de todas las notas
**Parámetros**:
- `vault`: Ruta al vault
- `execute`: Ejecutar cambios (sin esto solo muestra el plan)

**Flujo**:
1. Análisis completo del vault
2. Generación de plan de reclasificación
3. Backup automático (si execute=True)
4. Reclasificación de todas las notas
5. Archivo automático de notas diarias vacías

##### **`doctor_command()`**
```python
def doctor_command(self, vault: str = None, auto_fix: bool = False)
```
**Propósito**: Diagnóstico y auto-reparación del sistema
**Parámetros**:
- `vault`: Ruta al vault
- `auto_fix`: Aplicar fixes automáticamente

**Flujo**:
1. Análisis de logs del sistema
2. Detección de problemas
3. Generación de reporte de diagnóstico
4. Auto-fix (si auto_fix=True)
5. Resumen de acciones realizadas

##### **`dashboard_command()`**
```python
def dashboard_command(self, port: int = 8501, host: str = "localhost")
```
**Propósito**: Lanzar dashboard web interactivo
**Parámetros**:
- `port`: Puerto del dashboard
- `host`: Host del dashboard

**Flujo**:
1. Verificación de dependencias
2. Inicialización del dashboard
3. Lanzamiento del servidor web
4. Apertura automática del navegador

##### **`backups_command()`**
```python
def backups_command(self, action: str = "list", vault: str = None)
```
**Propósito**: Gestión de backups del sistema
**Parámetros**:
- `action`: Acción a realizar (list, create, restore, clean)
- `vault`: Ruta al vault

**Acciones disponibles**:
- `list`: Listar backups disponibles
- `create`: Crear backup manual
- `restore`: Restaurar backup específico
- `clean`: Limpiar backups antiguos

##### **`restore_backup_command()`**
```python
def restore_backup_command(self, backup_name: str, vault: str = None, force: bool = False)
```
**Propósito**: Restauración completa de un backup
**Parámetros**:
- `backup_name`: Nombre del backup a restaurar
- `vault`: Ruta al vault
- `force`: Forzar restauración sin confirmación

**Flujo**:
1. Validación del backup
2. Backup de seguridad del estado actual
3. Restauración de archivos y carpetas
4. Restauración de base de datos ChromaDB
5. Restauración de conocimiento de aprendizaje
6. Verificación de integridad

##### **`logs_command()`**
```python
def logs_command(self, action: str = "show", level: str = "INFO", lines: int = 50)
```
**Propósito**: Gestión y análisis de logs
**Parámetros**:
- `action`: Acción (show, analyze, clean)
- `level`: Nivel de log (DEBUG, INFO, WARNING, ERROR)
- `lines`: Número de líneas a mostrar

##### **`qa_command()`**
```python
def qa_command(self, vault: str = None, full: bool = False)
```
**Propósito**: Ejecutar QA automático del sistema
**Parámetros**:
- `vault`: Ruta al vault
- `full`: Ejecutar QA completo (más lento pero más exhaustivo)

---

## 🧠 **Motor de IA (`paralib/ai_engine.py`)**

### **Clase Principal: `AIEngine`**

#### **Métodos de Inicialización**
```python
def __init__(self, model_name: str = "llama3.2:3b", fallback_models: List[str] = None)
```
**Propósito**: Inicializa el motor de IA con modelo principal y fallbacks
**Parámetros**:
- `model_name`: Modelo principal de IA
- `fallback_models`: Lista de modelos de respaldo

#### **Métodos Principales**

##### **`classify_note()`**
```python
def classify_note(self, content: str, metadata: dict, prompt: str = None) -> dict
```
**Propósito**: Clasifica una nota usando IA
**Parámetros**:
- `content`: Contenido de la nota
- `metadata`: Metadatos de la nota
- `prompt`: Instrucciones personalizadas

**Retorna**: Diccionario con clasificación y confianza

##### **`process_intent()`**
```python
def process_intent(self, user_input: str) -> dict
```
**Propósito**: Procesa intents de lenguaje natural
**Parámetros**:
- `user_input`: Entrada del usuario en lenguaje natural

**Retorna**: Diccionario con intent detectado y parámetros

##### **`validate_json_response()`**
```python
def validate_json_response(self, response: str) -> dict
```
**Propósito**: Valida y parsea respuestas JSON de la IA
**Parámetros**:
- `response`: Respuesta de la IA

**Retorna**: Diccionario parseado o None si inválido

##### **`get_available_models()`**
```python
def get_available_models(self) -> List[str]
```
**Propósito**: Obtiene lista de modelos disponibles
**Retorna**: Lista de nombres de modelos

---

## 📊 **Organizador Principal (`paralib/organizer.py`)**

### **Clase Principal: `PARAOrganizer`**

#### **Métodos de Inicialización**
```python
def __init__(self, vault_path: str, ai_engine: AIEngine = None)
```
**Propósito**: Inicializa el organizador principal
**Parámetros**:
- `vault_path`: Ruta al vault
- `ai_engine`: Instancia del motor de IA

#### **Métodos Principales**

##### **`classify_notes()`**
```python
def classify_notes(self, notes: List[str], prompt: str = None) -> dict
```
**Propósito**: Clasifica múltiples notas
**Parámetros**:
- `notes`: Lista de rutas de notas
- `prompt`: Instrucciones personalizadas

**Retorna**: Plan de clasificación

##### **`execute_classification_plan()`**
```python
def execute_classification_plan(self, plan: dict, dry_run: bool = False) -> dict
```
**Propósito**: Ejecuta un plan de clasificación
**Parámetros**:
- `plan`: Plan de clasificación
- `dry_run`: Solo simular sin aplicar cambios

**Retorna**: Resultado de la ejecución

##### **`reclassify_all_notes()`**
```python
def reclassify_all_notes(self, prompt: str = None) -> dict
```
**Propósito**: Reclasifica todas las notas del vault
**Parámetros**:
- `prompt`: Instrucciones personalizadas

**Retorna**: Plan de reclasificación completo

##### **`get_classification_stats()`**
```python
def get_classification_stats(self) -> dict
```
**Propósito**: Obtiene estadísticas de clasificación
**Retorna**: Estadísticas detalladas

---

## 🗄️ **Base de Datos (`paralib/db.py`)**

### **Clase Principal: `ChromaPARADatabase`**

#### **Métodos de Inicialización**
```python
def __init__(self, db_path: str = None)
```
**Propósito**: Inicializa la base de datos ChromaDB
**Parámetros**:
- `db_path`: Ruta a la base de datos

#### **Métodos Principales**

##### **`add_note()`**
```python
def add_note(self, note_path: str, content: str, metadata: dict) -> bool
```
**Propósito**: Agrega una nota a la base de datos
**Parámetros**:
- `note_path`: Ruta de la nota
- `content`: Contenido de la nota
- `metadata`: Metadatos de la nota

**Retorna**: True si se agregó exitosamente

##### **`search_similar()`**
```python
def search_similar(self, query: str, n_results: int = 5) -> List[dict]
```
**Propósito**: Busca notas similares
**Parámetros**:
- `query`: Consulta de búsqueda
- `n_results`: Número de resultados

**Retorna**: Lista de notas similares

##### **`get_note_metadata()`**
```python
def get_note_metadata(self, note_path: str) -> dict
```
**Propósito**: Obtiene metadatos de una nota
**Parámetros**:
- `note_path`: Ruta de la nota

**Retorna**: Metadatos de la nota

##### **`update_note()`**
```python
def update_note(self, note_path: str, content: str, metadata: dict) -> bool
```
**Propósito**: Actualiza una nota existente
**Parámetros**:
- `note_path`: Ruta de la nota
- `content`: Nuevo contenido
- `metadata`: Nuevos metadatos

**Retorna**: True si se actualizó exitosamente

##### **`delete_note()`**
```python
def delete_note(self, note_path: str) -> bool
```
**Propósito**: Elimina una nota de la base de datos
**Parámetros**:
- `note_path`: Ruta de la nota

**Retorna**: True si se eliminó exitosamente

##### **`get_stats()`**
```python
def get_stats(self) -> dict
```
**Propósito**: Obtiene estadísticas de la base de datos
**Retorna**: Estadísticas detalladas

##### **`backup_database()`**
```python
def backup_database(self, backup_path: str) -> bool
```
**Propósito**: Crea backup de la base de datos
**Parámetros**:
- `backup_path`: Ruta del backup

**Retorna**: True si el backup fue exitoso

##### **`restore_database()`**
```python
def restore_database(self, backup_path: str) -> bool
```
**Propósito**: Restaura la base de datos desde un backup
**Parámetros**:
- `backup_path`: Ruta del backup

**Retorna**: True si la restauración fue exitosa

---

## 🧠 **Sistema de Aprendizaje (`paralib/learning_system.py`)**

### **Clase Principal: `PARA_Learning_System`**

#### **Métodos de Inicialización**
```python
def __init__(self, vault_path: str)
```
**Propósito**: Inicializa el sistema de aprendizaje
**Parámetros**:
- `vault_path`: Ruta al vault

#### **Métodos Principales**

##### **`learn_from_classification()`**
```python
def learn_from_classification(self, note_path: str, classification: dict, user_feedback: dict = None)
```
**Propósito**: Aprende de una clasificación realizada
**Parámetros**:
- `note_path`: Ruta de la nota
- `classification`: Clasificación realizada
- `user_feedback`: Feedback del usuario (opcional)

##### **`get_learning_stats()`**
```python
def get_learning_stats(self) -> dict
```
**Propósito**: Obtiene estadísticas de aprendizaje
**Retorna**: Estadísticas detalladas del aprendizaje

##### **`export_knowledge()`**
```python
def export_knowledge(self, export_path: str) -> bool
```
**Propósito**: Exporta el conocimiento aprendido
**Parámetros**:
- `export_path`: Ruta de exportación

**Retorna**: True si la exportación fue exitosa

##### **`import_knowledge()`**
```python
def import_knowledge(self, import_path: str) -> bool
```
**Propósito**: Importa conocimiento desde un archivo
**Parámetros**:
- `import_path`: Ruta del archivo a importar

**Retorna**: True si la importación fue exitosa

##### **`get_improvement_suggestions()`**
```python
def get_improvement_suggestions(self) -> List[str]
```
**Propósito**: Obtiene sugerencias de mejora
**Retorna**: Lista de sugerencias

---

## 📈 **Gestor de Análisis (`paralib/analyze_manager.py`)**

### **Clase Principal: `AnalyzeManager`**

#### **Métodos de Inicialización**
```python
def __init__(self, vault_path: str)
```
**Propósito**: Inicializa el gestor de análisis
**Parámetros**:
- `vault_path`: Ruta al vault

#### **Métodos Principales**

##### **`analyze_vault()`**
```python
def analyze_vault(self) -> dict
```
**Propósito**: Analiza todo el vault
**Retorna**: Análisis completo del vault

##### **`analyze_note()`**
```python
def analyze_note(self, note_path: str) -> dict
```
**Propósito**: Analiza una nota específica
**Parámetros**:
- `note_path`: Ruta de la nota

**Retorna**: Análisis detallado de la nota

##### **`get_vault_stats()`**
```python
def get_vault_stats(self) -> dict
```
**Propósito**: Obtiene estadísticas del vault
**Retorna**: Estadísticas completas

##### **`detect_patterns()`**
```python
def detect_patterns(self) -> List[dict]
```
**Propósito**: Detecta patrones en el vault
**Retorna**: Lista de patrones detectados

##### **`generate_snapshot()`**
```python
def generate_snapshot(self, snapshot_path: str) -> bool
```
**Propósito**: Genera un snapshot del vault
**Parámetros**:
- `snapshot_path`: Ruta del snapshot

**Retorna**: True si el snapshot fue exitoso

---

## 📝 **Gestor de Logs (`paralib/log_manager.py`)**

### **Clase Principal: `PARALogManager`**

#### **Métodos de Inicialización**
```python
def __init__(self, log_path: str = None)
```
**Propósito**: Inicializa el gestor de logs
**Parámetros**:
- `log_path`: Ruta del archivo de log

#### **Métodos Principales**

##### **`add_log_entry()`**
```python
def add_log_entry(self, level: str, message: str, context: dict = None)
```
**Propósito**: Agrega una entrada de log
**Parámetros**:
- `level`: Nivel del log (DEBUG, INFO, WARNING, ERROR)
- `message`: Mensaje del log
- `context`: Contexto adicional (opcional)

##### **`analyze_logs()`**
```python
def analyze_logs(self, time_range: str = "24h") -> dict
```
**Propósito**: Analiza logs del sistema
**Parámetros**:
- `time_range`: Rango de tiempo para analizar

**Retorna**: Análisis de logs

##### **`get_log_stats()`**
```python
def get_log_stats(self) -> dict
```
**Propósito**: Obtiene estadísticas de logs
**Retorna**: Estadísticas de logs

##### **`auto_fix_issues()`**
```python
def auto_fix_issues(self) -> List[str]
```
**Propósito**: Intenta arreglar problemas automáticamente
**Retorna**: Lista de problemas arreglados

##### **`clean_old_logs()`**
```python
def clean_old_logs(self, days: int = 30) -> int
```
**Propósito**: Limpia logs antiguos
**Parámetros**:
- `days`: Número de días a mantener

**Retorna**: Número de logs eliminados

---

## 🔌 **Sistema de Plugins (`paralib/plugin_system.py`)**

### **Clase Principal: `PARAPluginManager`**

#### **Métodos de Inicialización**
```python
def __init__(self, plugins_dir: str = "plugins")
```
**Propósito**: Inicializa el gestor de plugins
**Parámetros**:
- `plugins_dir`: Directorio de plugins

#### **Métodos Principales**

##### **`load_plugins()`**
```python
def load_plugins(self) -> List[str]
```
**Propósito**: Carga todos los plugins disponibles
**Retorna**: Lista de plugins cargados

##### **`get_plugin_commands()`**
```python
def get_plugin_commands(self) -> List[dict]
```
**Propósito**: Obtiene comandos de todos los plugins
**Retorna**: Lista de comandos disponibles

##### **`execute_plugin_command()`**
```python
def execute_plugin_command(self, command: str, args: dict) -> dict
```
**Propósito**: Ejecuta un comando de plugin
**Parámetros**:
- `command`: Comando a ejecutar
- `args`: Argumentos del comando

**Retorna**: Resultado de la ejecución

---

## 🧹 **Gestor de Limpieza (`paralib/clean_manager.py`)**

### **Clase Principal: `CleanManager`**

#### **Métodos de Inicialización**
```python
def __init__(self, vault_path: str)
```
**Propósito**: Inicializa el gestor de limpieza
**Parámetros**:
- `vault_path`: Ruta al vault

#### **Métodos Principales**

##### **`clean_vault()`**
```python
def clean_vault(self, dry_run: bool = False) -> dict
```
**Propósito**: Limpia el vault completo
**Parámetros**:
- `dry_run`: Solo simular sin aplicar cambios

**Retorna**: Plan de limpieza

##### **`find_duplicates()`**
```python
def find_duplicates(self) -> List[dict]
```
**Propósito**: Encuentra archivos duplicados
**Retorna**: Lista de duplicados encontrados

##### **`find_empty_files()`**
```python
def find_empty_files(self) -> List[str]
```
**Propósito**: Encuentra archivos vacíos
**Retorna**: Lista de archivos vacíos

##### **`organize_non_markdown()`**
```python
def organize_non_markdown(self) -> dict
```
**Propósito**: Organiza archivos no-Markdown
**Retorna**: Plan de organización

---

## 🎨 **Interfaz de Usuario (`paralib/ui.py`)**

### **Funciones Principales**

##### **`create_progress_bar()`**
```python
def create_progress_bar(total: int, description: str = "Procesando") -> Progress
```
**Propósito**: Crea una barra de progreso
**Parámetros**:
- `total`: Total de elementos
- `description`: Descripción del progreso

**Retorna**: Objeto Progress de Rich

##### **`display_table()`**
```python
def display_table(data: List[dict], title: str = "Datos")
```
**Propósito**: Muestra una tabla de datos
**Parámetros**:
- `data`: Datos a mostrar
- `title`: Título de la tabla

##### **`show_status()`**
```python
def show_status(status: str, style: str = "info")
```
**Propósito**: Muestra un mensaje de estado
**Parámetros**:
- `status`: Mensaje de estado
- `style`: Estilo del mensaje

##### **`confirm_action()`**
```python
def confirm_action(message: str) -> bool
```
**Propósito**: Solicita confirmación del usuario
**Parámetros**:
- `message`: Mensaje de confirmación

**Retorna**: True si el usuario confirma

---

## 🔧 **Utilidades (`paralib/utils.py`)**

### **Funciones Principales**

##### **`auto_backup_if_needed()`**
```python
def auto_backup_if_needed(vault_path: str, operation: str) -> bool
```
**Propósito**: Crea backup automático si es necesario
**Parámetros**:
- `vault_path`: Ruta al vault
- `operation`: Operación que se va a realizar

**Retorna**: True si el backup fue exitoso

##### **`validate_vault_path()`**
```python
def validate_vault_path(vault_path: str) -> bool
```
**Propósito**: Valida que la ruta del vault sea correcta
**Parámetros**:
- `vault_path`: Ruta a validar

**Retorna**: True si la ruta es válida

##### **`get_file_hash()`**
```python
def get_file_hash(file_path: str) -> str
```
**Propósito**: Calcula el hash de un archivo
**Parámetros**:
- `file_path`: Ruta del archivo

**Retorna**: Hash del archivo

##### **`safe_file_operation()`**
```python
def safe_file_operation(operation: callable, *args, **kwargs) -> bool
```
**Propósito**: Ejecuta una operación de archivo de forma segura
**Parámetros**:
- `operation`: Función a ejecutar
- `*args, **kwargs`: Argumentos de la función

**Retorna**: True si la operación fue exitosa

---

## ⚙️ **Configuración (`paralib/config.py`)**

### **Funciones Principales**

##### **`load_config()`**
```python
def load_config(config_path: str = "para_config.json") -> dict
```
**Propósito**: Carga la configuración del sistema
**Parámetros**:
- `config_path`: Ruta al archivo de configuración

**Retorna**: Configuración cargada

##### **`save_config()`**
```python
def save_config(config: dict, config_path: str = "para_config.json") -> bool
```
**Propósito**: Guarda la configuración del sistema
**Parámetros**:
- `config`: Configuración a guardar
- `config_path`: Ruta del archivo de configuración

**Retorna**: True si se guardó exitosamente

##### **`validate_config()`**
```python
def validate_config(config: dict) -> List[str]
```
**Propósito**: Valida la configuración
**Parámetros**:
- `config`: Configuración a validar

**Retorna**: Lista de errores encontrados

##### **`get_default_config()`**
```python
def get_default_config() -> dict
```
**Propósito**: Obtiene la configuración por defecto
**Retorna**: Configuración por defecto

---

## 🔄 **Flujos de Integración Típicos**

### **1. Clasificación de Notas**
```python
# 1. Inicializar componentes
ai_engine = AIEngine("llama3.2:3b")
organizer = PARAOrganizer(vault_path, ai_engine)
db = ChromaPARADatabase()

# 2. Analizar notas nuevas
analyzer = AnalyzeManager(vault_path)
new_notes = analyzer.get_new_notes()

# 3. Clasificar
plan = organizer.classify_notes(new_notes, prompt="Instrucciones personalizadas")

# 4. Ejecutar clasificación
result = organizer.execute_classification_plan(plan)

# 5. Aprender de la clasificación
learning_system = PARA_Learning_System(vault_path)
for note_path, classification in result['classifications'].items():
    learning_system.learn_from_classification(note_path, classification)
```

### **2. Análisis Completo**
```python
# 1. Inicializar analizador
analyzer = AnalyzeManager(vault_path)

# 2. Analizar vault completo
analysis = analyzer.analyze_vault()

# 3. Detectar patrones
patterns = analyzer.detect_patterns()

# 4. Generar snapshot
analyzer.generate_snapshot("snapshot_20250626.json")

# 5. Obtener estadísticas
stats = analyzer.get_vault_stats()
```

### **3. Gestión de Logs**
```python
# 1. Inicializar gestor de logs
log_manager = PARALogManager()

# 2. Agregar entrada de log
log_manager.add_log_entry("INFO", "Operación completada", {"operation": "classify"})

# 3. Analizar logs
analysis = log_manager.analyze_logs("24h")

# 4. Auto-fix de problemas
fixed_issues = log_manager.auto_fix_issues()

# 5. Limpiar logs antiguos
cleaned_count = log_manager.clean_old_logs(30)
```

### **4. Sistema de Plugins**
```python
# 1. Inicializar gestor de plugins
plugin_manager = PARAPluginManager("plugins")

# 2. Cargar plugins
loaded_plugins = plugin_manager.load_plugins()

# 3. Obtener comandos disponibles
commands = plugin_manager.get_plugin_commands()

# 4. Ejecutar comando de plugin
result = plugin_manager.execute_plugin_command("obsidian-vault", {"action": "info"})
```

---

## 📊 **Estructuras de Datos Comunes**

### **Clasificación de Nota**
```python
{
    "category": "Projects",  # Projects, Areas, Resources, Archive
    "confidence": 0.85,      # Confianza de la clasificación (0-1)
    "reasoning": "Contiene deadline y OKRs",  # Razón de la clasificación
    "features": {            # Features extraídos
        "has_deadline": True,
        "has_okrs": True,
        "has_tasks": False,
        "word_count": 150
    },
    "ai_prediction": "Projects",  # Predicción de la IA
    "chroma_similarity": 0.92     # Similitud con ChromaDB
}
```

### **Plan de Clasificación**
```python
{
    "total_notes": 150,
    "classifications": {
        "/path/to/note1.md": {
            "current_category": "Inbox",
            "new_category": "Projects",
            "confidence": 0.85,
            "reasoning": "Contiene deadline y OKRs"
        }
    },
    "summary": {
        "Projects": 45,
        "Areas": 30,
        "Resources": 50,
        "Archive": 25
    },
    "estimated_time": "5 minutes"
}
```

### **Análisis de Vault**
```python
{
    "total_notes": 1500,
    "total_words": 45000,
    "categories": {
        "Projects": 400,
        "Areas": 300,
        "Resources": 500,
        "Archive": 300
    },
    "patterns": [
        {
            "type": "daily_notes",
            "count": 200,
            "pattern": "YYYY-MM-DD"
        }
    ],
    "issues": [
        {
            "type": "empty_files",
            "count": 5,
            "files": ["/path/to/empty1.md"]
        }
    ]
}
```

---

*Última actualización: 2025-06-26*
*Versión: 1.0*
*Mantenido por: Sistema PARA*
