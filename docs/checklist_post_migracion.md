# checklist post-migración obsidian-para

| paso                                                        | verificación esperada                         | estado |
|-------------------------------------------------------------|-----------------------------------------------|--------|
| 1. Clonar el repositorio                                    | Repo clonado sin errores                      | [ ]    |
| 2. Ejecutar ./install_para_system.sh                        | Instalación y setup completados               | [ ]    |
| 3. Editar para_config.json (vault_path)                     | Ruta correcta al vault de Obsidian            | [ ]    |
| 4. Ejecutar ./launch_para.sh                                | Panel de control se muestra correctamente     | [ ]    |
| 5. Lanzar dashboard desde el panel                          | Dashboard accesible en navegador              | [ ]    |
| 6. Probar comando CLI (ej: classify, analyze, doctor)       | Comandos ejecutan y muestran resultados       | [ ]    |
| 7. Verificar integración IA (Ollama, modelo descargado)     | IA responde, clasifica y sugiere              | [ ]    |
| 8. Revisar métricas y evolución en dashboard                | Gráficas y métricas visibles y actualizadas   | [ ]    |
| 9. Probar backup y rollback                                | Backups creados y restaurados correctamente   | [ ]    |
| 10. Verificar sincronización con Google Drive/Obsidian      | Archivos y seguimiento sincronizados          | [ ]    |
| 11. Revisar logs y alertas del sistema                      | Logs accesibles, sin errores críticos         | [ ]    |
| 12. Consultar el doctor ante cualquier error                | Sugerencias y auto-fix funcionan             | [ ]    |
| 13. Documentar cualquier ajuste necesario                   | README y vault actualizados                   | [ ]    |

---

> Usa este checklist tras cada migración o setup en una nueva Mac para asegurar la portabilidad y robustez del sistema obsidian-para. 