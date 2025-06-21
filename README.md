# PARA: Organización Inteligente de Vaults Obsidian

PARA es un sistema avanzado para organizar, clasificar y mantener tu vault de Obsidian usando IA, reglas, feedback y automatización, con soporte para fine-tuning y aprendizaje continuo.

## Principales funcionalidades
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

## Instalación
1. Clona el repositorio y entra en la carpeta.
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura tu vault y modelo en `para_config.json`.

## Comandos principales (CLI)
- `classify` — Clasifica notas nuevas o modificadas.
- `weights`, `set-weight`, `simulate-weight` — Ajusta y simula la matriz de pesos.
- `suggest-rules` — Sugiere reglas automáticas simples.
- `export-finetune-dataset`, `finetune`, `validate-finetune` — Exporta, entrena y valida modelos.
- `feedback-log` — Muestra el historial de feedback/correcciones.
- `reset` — Limpia caché y restaura configuración.
- `export-config`, `import-config` — Exporta/importa configuración.
- `dashboard` — Lanza el dashboard web Gradio.
- `help-examples` — Muestra ejemplos reales de uso.

## Ejemplos de uso
```bash
# Clasificar todas las notas nuevas o modificadas
python para_cli.py classify --incremental

# Ajustar el peso de un factor
python para_cli.py set-weight content 10

# Sugerir reglas automáticas
python para_cli.py suggest-rules --incremental

# Exportar dataset para fine-tuning
python para_cli.py export-finetune-dataset --output my_dataset.jsonl

# Lanzar dashboard web
def para_cli.py dashboard
```

## Changelog resumido
- **v2.0** (2024-06-20)
  - Refactor total de la CLI y lógica de negocio.
  - Features estructurados y matriz de pesos editable.
  - Feedback/corrección interactiva.
  - Sugerencia y automatización de reglas.
  - Procesamiento incremental y caché de features.
  - Exportación, fine-tuning y validación de modelos.
  - Visualización profesional y explicable.
  - Gestión de configuración y backup.
  - Ejemplos de uso y documentación extendida.
- **v1.x**
  - Primeras versiones, clasificación básica, reglas manuales.

## Arquitectura
- Toda la lógica de negocio está en `paralib/` (features, reglas, scoring, embeddings, etc.).
- CLI y dashboard solo orquestan funciones de `paralib/`.
- Configuración y caché centralizados.
- Feedback y logs exhaustivos y auditables.

## Recomendaciones futuras
- Suite de tests automatizados.
- Mejorar la modularidad de `paralib/` y la documentación interna.
- Soporte multiusuario y colaboración.
- Integración con otros sistemas (Notion, Google Drive, etc.).
- Mejorar la experiencia de onboarding y la documentación para usuarios nuevos.
- Automatización de backups y restauración desde la CLI.
- Mejorar la gestión de perfiles/configuración avanzada.

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
