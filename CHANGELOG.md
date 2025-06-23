# CHANGELOG

## [2.1.0] - 2024-06-21
### Mejoras
- Detección robusta de vaults en Google Drive, iCloud y otras nubes (búsqueda profunda y timeouts inteligentes).
- Uso de caché para vaults detectados y opción de forzar detección o especificar manualmente.
- Mejoras en la CLI: mensajes más claros, manejo de errores y auto-recuperación.
- Nueva sección de troubleshooting y FAQ en la documentación.
- Mejoras en la edición de pesos y robustez ante archivos faltantes.

## [2.0.0] - 2024-06-20
### Added
- Refactor total de la CLI y lógica de negocio.
- Features estructurados y matriz de pesos editable.
- Feedback/corrección interactiva y logging exhaustivo.
- Sugerencia y automatización de reglas simples.
- Procesamiento incremental y selectivo (por carpeta, nota, o solo cambios).
- Caché de features para máxima performance.
- Exportación de dataset y fine-tuning del modelo (dummy y extensible).
- Validación y comparación de modelos.
- Visualización profesional y explicable en CLI y dashboard web.
- Gestión y versionado de configuración.
- Backup y restauración automáticos.
- Ejemplos de uso y documentación extendida.

### Changed
- Unificación de lógica de negocio en `paralib/`.
- CLI y dashboard dependen solo de `paralib/`.
- Configuración y caché centralizados.

### Fixed
- Corrección de bugs en clasificación, feedback y reglas.
- Mejor manejo de errores y logs.

## [1.x.x] - 2024-05-XX
### Added
- Primeras versiones, clasificación básica, reglas manuales. 