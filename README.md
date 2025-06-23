# PARA: Organización Inteligente de Vaults Obsidian

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
