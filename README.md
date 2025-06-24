# PARA System with ChromaDB

## 🚀 Portabilidad y Setup en nueva Mac

1. **Clona el repositorio:**
   ```bash
   git clone <URL_DEL_REPO>
   cd obsidian-para
   ```
2. **Instala el sistema:**
   ```bash
   ./install_para_system.sh
   ```
3. **Configura el vault:**
   - Edita `para_config.json` y pon la ruta de tu vault de Obsidian en `vault_path`.
4. **Lanza el sistema:**
   ```bash
   ./launch_para.sh
   ```
5. **(Opcional) Lanza el dashboard backend/seguimiento:**
   ```bash
   ./launch_dashboard.sh
   ```
6. **Abre el dashboard en tu navegador:**
   - http://localhost:7860 (o el puerto configurado)

---

# 📦 PARA System with ChromaDB

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

## 📦 Estructura PARA

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

## Sobre PARA (Método de Tiago Forte)

PARA es un sistema de organización de información personal creado por Tiago Forte, parte del método Building a Second Brain. Su objetivo es ayudarte a clasificar y encontrar cualquier nota o archivo en segundos, usando solo cuatro categorías universales:

- **Projects (Proyectos):** Resultados con una fecha límite o un objetivo claro. Ejemplo: "Lanzar nueva web", "Preparar presentación".
- **Areas (Áreas):** Responsabilidades continuas y de largo plazo. Ejemplo: "Salud", "Finanzas", "Clientes".
- **Resources (Recursos):** Referencias útiles, plantillas, manuales, ideas, materiales de consulta. Ejemplo: "Plantillas de IA", "Recetas", "Guías".
- **Archive (Archivo):** Todo lo inactivo, terminado o que no necesitas revisar regularmente.

"El método PARA es la forma más simple y universal de organizar cualquier tipo de información digital." — Tiago Forte

**Recursos oficiales y ejemplos:**
- [Artículo original de PARA](https://fortelabs.com/blog/para/)
- [Ejemplos de organización PARA](https://www.buildingasecondbrain.com/para/examples)
- [Video explicativo de Tiago Forte](https://www.youtube.com/watch?v=-bdE_54UUA4)

---

## Importancia de la IA en PARA

La IA es el núcleo del sistema PARA:
- Permite clasificar notas según contexto, reglas, historial y features estructurados, no solo por palabras clave.
- Aprende de tu feedback y de los patrones de tu vault, mejorando con el tiempo.
- Ofrece explicaciones transparentes de cada decisión, permitiendo auditar y ajustar el sistema.
- Facilita la automatización de reglas y la sugerencia de agrupaciones inteligentes (por ejemplo, agrupar recursos de IA, prompts, etc.).

**¡IMPORTANTE!**
Antes de ejecutar cualquier acción de clasificación, refactorización o automatización con IA, el sistema PARA realiza (o recomienda realizar) un **backup automático** de tu vault. Esto garantiza que siempre puedas restaurar tu información en caso de un error, cambio no deseado o para auditar el impacto de la IA en tu organización.

**IMPORTANTE:** El backup automático es **obligatorio** y se ejecuta **siempre** antes de cualquier acción que modifique tu vault (classify, refactor, clean, reset, etc.). Si el backup falla, la acción se aborta para proteger tus datos.

**Flujo recomendado:**
1. Backup automático/manual (antes de cualquier cambio masivo)
2. Clasificación y organización con IA
3. Revisión y feedback (opcional)
4. Ajuste de reglas, pesos o prompts según resultados

### 3. Revisión y feedback (opcional)
   - Revisa las clasificaciones sugeridas
   - Proporciona feedback para mejorar el sistema
   - El sistema aprende de tus correcciones

## 📊 Sistema de Feedback y Mejora Continua

El sistema incluye un **sistema avanzado de feedback** que permite mejorar continuamente la calidad de clasificación:

### Comandos de Feedback

```bash
# Análisis de calidad del sistema
python para_cli.py feedback-quality --detailed

# Revisión interactiva de feedback
python para_cli.py review-feedback

# Mejora automática de parámetros
python para_cli.py improve-classification --auto-adjust

# Crear feedback de muestra para pruebas
python para_cli.py sample-feedback

# Exportar reporte completo de calidad
python para_cli.py export-report
```

### Características del Sistema de Feedback

- **Análisis de Calidad**: Score de calidad (0-100) basado en múltiples métricas
- **Análisis de Patrones**: Detecta transiciones comunes y razones de corrección
- **Ajuste Automático**: Optimiza parámetros basado en feedback acumulado
- **Reportes Detallados**: Exporta análisis completos en JSON
- **Revisión Interactiva**: Interfaz para revisar y gestionar feedback
- **Métricas Avanzadas**: Análisis de confianza, distribución por categorías, patrones temporales

### Métricas de Calidad

- **Tasa de Feedback**: Porcentaje de notas con correcciones
- **Score de Calidad**: Puntuación general del sistema (0-100)
- **Distribución por Categorías**: Análisis de precisión por tipo
- **Análisis de Confianza**: Relación entre confianza y precisión
- **Patrones de Corrección**: Transiciones más comunes
- **Análisis Temporal**: Tendencias y sesiones de feedback

## 🧠 Sistema de Aprendizaje Autónomo

El **Sistema de Aprendizaje Autónomo** es la evolución del feedback, proporcionando aprendizaje automático con métricas cuantificables y visualización gráfica:

### Comandos de Aprendizaje

```bash
# Dashboard interactivo de aprendizaje
python para_cli.py learn --dashboard

# Crear snapshot de aprendizaje
python para_cli.py learn --snapshot

# Análisis de progreso (30 días)
python para_cli.py learn --progress 30

# Aprender de una clasificación específica
python para_cli.py learn-from-classification "nota.md" --actual "Projects"

# Métricas detalladas de aprendizaje
python para_cli.py learning-metrics --detailed --export
```

### Características del Sistema de Aprendizaje

- **Aprendizaje Automático**: Aprende de cada clasificación individual
- **Métricas Cuantificables**: Score de calidad (0-100) con múltiples factores
- **Velocidad de Aprendizaje**: Mide qué tan rápido mejora el sistema
- **Correlación Confianza-Precisión**: Calibración automática del sistema
- **Dashboard Visual**: Gráficos interactivos con Plotly y Streamlit
- **Insights Automáticos**: Sugerencias de mejora basadas en datos
- **Análisis Histórico**: Tendencias y progreso a lo largo del tiempo

### Métricas de Aprendizaje

- **Score de Calidad** (0-100): Basado en 4 factores principales
- **Velocidad de Aprendizaje**: Tendencia de mejora en precisión
- **Correlación Confianza**: Qué tan bien calibrado está el sistema
- **Score de Mejora**: Progreso general del sistema
- **Coherencia Semántica**: Calidad de embeddings
- **Balance de Categorías**: Distribución equilibrada
- **Satisfacción Usuario**: Basada en feedback rate
- **Adaptabilidad Sistema**: Capacidad de ajuste automático

---

## 📁 Sistema de Feedback de Carpetas

El **Sistema de Feedback de Carpetas** es una funcionalidad avanzada que permite evaluar la calidad de las carpetas creadas automáticamente, especialmente las carpetas de proyectos. Este sistema aprende de las decisiones del usuario para mejorar continuamente la clasificación.

### ¿Por qué es Importante?

La creación de carpetas de proyectos es fundamental para la organización efectiva:
- ✅ **"aws-tagging"** - Tiene sentido como proyecto real
- ❌ **"lalala-land"** - No debería crearse como proyecto

El sistema necesita aprender estas preferencias específicas del usuario.

### Comandos de Feedback de Carpetas

```bash
# Estadísticas de feedback de carpetas
python para_cli.py folder-feedback --stats

# Modo interactivo para revisar carpetas creadas
python para_cli.py folder-feedback --interactive

# Sugerencias de mejora basadas en feedback
python para_cli.py folder-feedback --suggest

# Análisis personalizado (60 días)
python para_cli.py folder-feedback --stats --days 60
```

### Características del Sistema de Feedback de Carpetas

- **Registro Automático**: Cada carpeta creada se registra automáticamente con información completa
- **Feedback Interactivo**: Permite revisar carpetas recientes y dar feedback detallado
- **Análisis Estadístico**: Tasa de aprobación por categoría, método y confianza
- **Patrones de Nombres**: Identifica patrones exitosos en nombres de carpetas
- **Sugerencias Inteligentes**: Propone mejoras basadas en el análisis de feedback
- **Integración Completa**: Se integra con el sistema de aprendizaje autónomo

### Métricas de Carpetas

- **Tasa de Aprobación**: Porcentaje de carpetas que el usuario considera apropiadas
- **Rendimiento por Método**: Efectividad de ChromaDB vs IA vs Consenso
- **Correlación de Confianza**: Relación entre confianza del sistema y aprobación del usuario
- **Patrones Exitosos**: Nombres y patrones de carpetas más aprobados
- **Análisis por Categoría**: Precisión específica para Projects, Areas, Resources

### Flujo de Trabajo Recomendado

1. **Clasificación**: `python para_cli.py classify --execute`
2. **Revisión Semanal**: `python para_cli.py folder-feedback --interactive`
3. **Análisis Mensual**: `python para_cli.py folder-feedback --stats`
4. **Optimización**: `python para_cli.py folder-feedback --suggest`

---

## 📊 Log Manager Inteligente

El **Log Manager Inteligente** es un sistema avanzado que analiza automáticamente los logs del sistema, resuelve problemas comunes y mantiene métricas de resolución. Proporciona una gestión proactiva de errores y eventos del sistema.

### Características del Log Manager

- **Análisis Automático**: Parsea y analiza logs automáticamente
- **Auto-Resolución**: Resuelve problemas comunes sin intervención manual
- **Métricas de Resolución**: Tiempo promedio, tasas de éxito, problemas pendientes
- **Escalación Inteligente**: Identifica problemas complejos que requieren atención manual
- **Base de Datos de Logs**: Almacena logs procesados con estado y resolución
- **Patrones de Problemas**: Detecta patrones recurrentes y aplica soluciones

### Comandos del Log Manager

```bash
# Analizar logs automáticamente
python para_cli.py logs --analyze

# Mostrar logs pendientes
python para_cli.py logs --pending

# Ver métricas de logs
python para_cli.py logs --metrics

# Marcar log como resuelto
python para_cli.py logs --resolve 123 --resolution "Problema solucionado"

# Actividad reciente (24h por defecto)
python para_cli.py logs --recent 48
```

### Problemas Auto-Resueltos

El Log Manager puede resolver automáticamente:

- **Modelos de IA no encontrados**: Sugiere comandos para descargar modelos
- **Errores de conexión Ollama**: Indica cómo iniciar el servicio
- **Problemas de ChromaDB**: Verifica configuración de base de datos
- **Errores de permisos**: Sugiere verificar permisos de escritura
- **Problemas de backup**: Verifica espacio en disco y permisos
- **Errores de clasificación**: Sugiere verificar contenido y modelo
- **Problemas de JSON**: Indica problemas de formato en respuestas de IA

### Métricas del Log Manager

- **Total de Logs**: Número total de entradas procesadas
- **Auto-Resueltos**: Problemas resueltos automáticamente
- **Manual**: Problemas resueltos manualmente
- **Pendientes**: Problemas que requieren atención
- **Escalados**: Problemas complejos que requieren intervención
- **Tiempo Promedio**: Tiempo promedio de resolución en minutos

---

## 🚀 Backend Dashboard Unificado

El **Backend Dashboard Unificado** es una interfaz web completa que unifica toda la información del sistema PARA en una sola vista. Proporciona métricas en tiempo real, análisis avanzados y gestión integral del sistema.

### Características del Dashboard

- **Dashboard Principal**: Vista general con métricas clave y alertas
- **Logs & Errores**: Gestión visual de logs con filtros y resolución
- **Sistema de Aprendizaje**: Métricas de aprendizaje y progreso
- **ChromaDB Analytics**: Análisis detallado de la base de datos semántica
- **Doctor System**: Diagnóstico y salud del sistema
- **Métricas de Usuario**: Analytics de uso y rendimiento
- **Configuración**: Gestión visual de configuración del sistema

### Lanzamiento del Dashboard

```bash
# Lanzamiento básico (puerto 8501)
python para_cli.py dashboard

# Puerto personalizado
python para_cli.py dashboard --port 8502

# Host personalizado
python para_cli.py dashboard --host 0.0.0.0

# Sin abrir navegador automáticamente
python para_cli.py dashboard --open false

# Script de lanzamiento directo
./launch_dashboard.sh
```

### Secciones del Dashboard

#### 🏠 Dashboard Principal
- Métricas de logs en tiempo real
- Progreso del sistema de aprendizaje
- Estado de servicios del sistema
- Alertas y recomendaciones

#### 📊 Logs & Errores
- Filtros por nivel, tiempo y estado
- Análisis automático de logs
- Gestión de logs pendientes
- Métricas detalladas de resolución

#### 🧠 Sistema de Aprendizaje
- Métricas de precisión y progreso
- Historial de feedback
- Acciones de aprendizaje
- Reportes de mejora

#### 🔍 ChromaDB Analytics
- Estadísticas de la base de datos
- Análisis de collections
- Documentos y embeddings
- Patrones semánticos

#### 💊 Doctor System
- Diagnóstico automático del sistema
- Verificación de servicios
- Problemas conocidos y soluciones
- Reportes de salud

#### 📈 Métricas de Usuario
- Notas procesadas
- Tiempo de uso
- Clasificaciones realizadas
- Precisión del sistema

#### ⚙️ Configuración del Sistema
- Configuración actual
- Opciones de gestión
- Recarga de configuración
- Guardado de cambios

### Requisitos del Dashboard

```bash
# Instalar dependencias
pip install streamlit plotly

# Verificar instalación
python -c "import streamlit, plotly; print('✅ Dependencias instaladas')"
```

---

## 💊 Doctor System Avanzado

El **Doctor System Avanzado** es una evolución del doctor original que incluye análisis automático de logs y reparación inteligente. Proporciona diagnóstico completo y proactivo del sistema.

### Comandos del Doctor Avanzado

```bash
# Diagnóstico completo con análisis de logs
python para_cli.py doctor-advanced

# Solo análisis de logs
python para_cli.py doctor-advanced --log-analysis --health false

# Solo verificación de salud
python para_cli.py doctor-advanced --log-analysis false --health

# Con auto-reparación
python para_cli.py doctor-advanced --auto-fix

# Generar reporte de salud
python para_cli.py doctor-advanced --report
```

### Servicios Verificados

- **ChromaDB**: Conexión y operaciones de base de datos
- **Learning System**: Sistema de aprendizaje y métricas
- **Log Manager**: Gestión de logs y análisis
- **Database**: Base de datos principal del sistema

### Reportes de Salud

El doctor genera reportes completos que incluyen:

- Estado de todos los servicios
- Métricas de logs y actividad reciente
- Recomendaciones de mejora
- Timestamp de verificación
- Análisis de tendencias

---

## Personalización de la IA: Instrucciones al Prompt

Puedes darle instrucciones personalizadas a la IA usando el parámetro `--prompt` en la CLI. Ejemplo:

```bash
python para_cli.py classify --prompt "Las notas taggeadas con prompt se agrupan en un recurso AI - Prompt. No es un proyecto, es un recurso."
```

Esto permite reglas contextuales, agrupaciones especiales o cualquier directiva que desees. Ejemplo avanzado:
- "Las notas con tag prompt son recursos. Las que mencionan OKR y deadline son proyectos activos."

La IA tendrá en cuenta tu instrucción al clasificar las notas, combinando tu prompt con las reglas y features estructurados del sistema.

---

## 🚀 Características Principales

- **Clasificación Inteligente**: Usa IA para clasificar automáticamente notas en Projects, Areas, Resources o Archive.
- **Análisis Semántico Avanzado**: Integración profunda con ChromaDB para búsqueda semántica y análisis de patrones.
- **Sistema Híbrido**: Combina análisis semántico y clasificación por IA para máxima precisión.
- **🧠 Sistema de Aprendizaje Autónomo**: Aprende, mejora y se optimiza automáticamente con métricas cuantificables y dashboard visual.
- **Feedback y Mejora Continua**: Sistema completo de feedback con análisis de calidad y ajuste automático de parámetros.
- **Planificación Inteligente**: Genera planes detallados antes de aplicar cambios con confirmación del usuario.
- **Backup Automático**: Crea respaldos antes de cada operación con capacidad de rollback.
- **Interfaz Web**: Dashboard completo para visualizar y gestionar tu vault.
- **CLI Potente**: Comandos intuitivos para todas las operaciones.
- **Aprende de tu feedback y de los patrones de tu vault, mejorando con el tiempo.**

## Principales funcionalidades
- Detección automática y robusta de vaults, incluyendo rutas en Google Drive, iCloud y otras nubes.
- Clasificación automática de notas en Projects, Areas, Resources, Archive, Inbox.
- Features estructurados: OKRs, KPIs, deadlines, status, tareas, backlinks, embeddings, historial, etc.
- Matriz de pesos editable para ajustar la importancia de cada factor.
- Feedback/corrección interactiva y logging exhaustivo.
- Sugerencia y automatización de reglas basada en patrones reales.
- Procesamiento incremental y selectivo (por carpeta, nota, o solo cambios).
- Caché de features para máxima performance.
- Exportación de dataset y fine-tuning del modelo.
- Validación y comparación de modelos.
- Visualización profesional en CLI y dashboard web.
- Gestión y versionado de configuración.
- Backup y restauración automáticos.
- Auto-recuperación y robustez ante errores o archivos faltantes.

## Instalación
1. Clona el repositorio y entra en la carpeta.
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. (Opcional) Configura tu vault y modelo en `para_config.json`.

## Detección de Vaults
- El sistema detecta automáticamente vaults en rutas locales y en la nube (Google Drive, iCloud, etc.).
- Si tienes tu vault en Google Drive, asegúrate de que la carpeta `.obsidian` esté presente en la ruta.
- El sistema prioriza rutas locales, pero buscará en la nube con mayor profundidad y timeout.
- La ubicación del vault se guarda en caché para futuras ejecuciones rápidas.
- Puedes forzar la detección o especificar el vault manualmente con `--vault`.

## Comandos principales (CLI)
- `classify` — Clasifica notas nuevas o modificadas.
- `refactor` — Re-evalúa notas archivadas para reactivarlas si corresponde.
- `search` — Búsqueda semántica en tu vault.
- `monitor` — Dashboard interactivo en terminal.
- `weights`, `set-weight` — Ajusta la matriz de pesos (usa notación `Categoria.subfactor`).
- `reset` — Limpia caché y restaura configuración.
- `doctor`, `autoheal`, `clean` — Diagnóstico, auto-recuperación y limpieza.
- `logs` — Muestra logs del sistema.
- `backup_manager.py` — Backup y restauración manual o automática.

**Todos los comandos que modifican el vault ejecutan SIEMPRE un backup automático antes de realizar cualquier cambio. Si el backup falla, la acción se cancela automáticamente.**

## Ejemplos de uso
```bash
# Clasificar todas las notas nuevas o modificadas
./para_cli.py classify

# Forzar detección de vault o especificar manualmente
./para_cli.py classify --vault "/ruta/a/tu/vault"

# Ajustar el peso de un subfactor
./para_cli.py set-weight Projects.llm_prediction 12

# Refactorizar el archivo
./para_cli.py refactor

# Buscar por significado
./para_cli.py search "palabra clave"

# Ver el dashboard en terminal
./para_cli.py monitor

# Backup manual
./backup_manager.py --action backup --vault-path "/ruta/a/tu/vault"
```

## Troubleshooting y Preguntas Frecuentes (FAQ)
- **No encuentra mi vault en Google Drive:**
  - Asegúrate de que la carpeta `.obsidian` esté presente.
  - El sistema busca hasta 5 niveles de profundidad en Google Drive.
  - Usa `--vault "/ruta/completa/a/Mi unidad/Obsidian"` si es necesario.
- **Timeouts o lentitud en la nube:**
  - El sistema limita la profundidad y el tiempo de búsqueda en rutas de nube para evitar bloqueos.
  - Si tienes muchos vaults, especifica el tuyo manualmente.
- **No hay notas en '00-Inbox':**
  - El sistema solo procesa notas nuevas en esa carpeta. Mueve o crea notas ahí para clasificarlas.
- **¿Cómo edito los pesos de clasificación?**
  - Usa `set-weight Categoria.subfactor valor` (ej: `Projects.llm_prediction 12`).
- **¿Cómo hago backup o restauro?**
  - Usa el script `backup_manager.py` o los comandos automáticos de la CLI.
- **¿Qué hago si hay un error inesperado?**
  - Ejecuta `python para_cli.py doctor` o `autoheal` para limpiar y auto-recuperar el sistema.
- **¿Qué pasa si el backup automático falla?**
  - La acción se aborta automáticamente y no se realizan cambios en tu vault. Revisa permisos, espacio en disco o rutas y vuelve a intentarlo.

## Arquitectura
- Toda la lógica de negocio está en `paralib/` (features, reglas, scoring, embeddings, etc.).
- CLI y dashboard solo orquestan funciones de `paralib/`.
- Configuración y caché centralizados.
- Feedback y logs exhaustivos y auditables.

## Créditos
Desarrollado por Fernando Ferrari y colaboradores. MIT License.

## ChromaDB Admin Dashboard (Experimental)

Incluye un dashboard visual moderno (Streamlit) para explorar, auditar y analizar cualquier base de datos ChromaDB, con tema oscuro por defecto y opción clara. 

- Navegador de notas, filtros, feedback, vecinos semánticos, estadísticas y exportación.
- Inspirado en Bootstrap, visualmente limpio y flexible.
- Puede usarse fuera de PARA: solo requiere la ruta de la base ChromaDB.

**Lanzamiento:**

```bash
cd chromadb_admin
streamlit run app.py
```

---

## Estructura del Proyecto

- `para_cli.py`: CLI principal del sistema PARA.
- `paralib/`: Lógica central, algoritmos, integración con ChromaDB, aprendizaje y feedback.
- `chromadb_admin/`: Utilidades avanzadas y administración de ChromaDB (para usuarios avanzados/desarrolladores).
- `backups/`: Backups automáticos y manuales del vault antes de cada acción importante.
- `docs/`: Documentación avanzada, sistemas, arquitectura y ejemplos.
- `logs/`: Logs de operación y auditoría.
- `requirements.txt`: Dependencias del sistema.
- `launch.sh`/`launch.py`: Scripts legacy, usar la CLI principal.

### Flujo de Backups

Antes de cualquier acción que modifique el vault (clasificación, refactorización, limpieza, etc.), el sistema crea un backup automático en la carpeta `backups/`. Puedes restaurar cualquier backup manualmente descomprimiendo el archivo correspondiente.

---

## Documentación avanzada

Toda la documentación técnica, arquitectónica y de sistemas avanzados se encuentra en la carpeta `docs/`:

- `SISTEMA_FEEDBACK_CARPETAS.md`: Feedback de carpetas y aprendizaje.
- `SISTEMA_APRENDIZAJE_AUTONOMO.md`: Sistema de aprendizaje autónomo.
- `SISTEMA_FEEDBACK_MEJORADO.md`: Feedback mejorado y análisis de calidad.
- `SISTEMA_PLANIFICACION_COMPLETO.md`: Planificación y confirmación de acciones.
- `SISTEMA_HIBRIDO_AVANZADO.md`: Sistema híbrido de clasificación.
- `CHROMADB_POTENCIADO.md`: Integración avanzada con ChromaDB.
- `ANALISIS_COMPLETO_OBSIDIAN.md`: Análisis completo de notas y vault.

Consulta estos archivos en `docs/` para detalles, ejemplos y arquitectura.

---

## Comando principal: Reclasificación total

### `reclassify-all`

Reclasifica todas las notas del vault usando el sistema híbrido (ChromaDB + IA + aprendizaje automático). Las notas diarias vacías o genéricas se archivan automáticamente. Al finalizar, puedes ver la evolución y mejora en el panel de aprendizaje.

**Uso:**

```bash
python para_cli.py reclassify-all --vault /ruta/al/vault --execute
```

- Reclasifica todas las notas del vault, sin importar en qué carpeta estén.
- Aprovecha el sistema de aprendizaje para mejorar la precisión respecto a la clasificación inicial.
- Archiva automáticamente las notas diarias vacías o con contenido genérico.
- Realiza backup automático antes de ejecutar.
- Al finalizar, puedes abrir el panel de aprendizaje:

```bash
python para_cli.py learn --dashboard
```

---
