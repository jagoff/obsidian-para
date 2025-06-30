# 📖 Guía de Usuario - PARA System v2.0

**Guía completa para usar el sistema de organización automática de notas**

## 🎯 Introducción

PARA System v2.0 es una herramienta avanzada que combina la metodología PARA de Tiago Forte con inteligencia artificial para automatizar la organización de tus notas en Obsidian.

### ¿Qué es PARA?

PARA es una metodología de organización digital que divide la información en cuatro categorías:

- **P**rojects - Proyectos activos con fechas límite
- **A**reas - Áreas de responsabilidad a largo plazo
- **R**esources - Referencias y recursos para consulta
- **A**rchive - Información inactiva pero valiosa

## 🚀 Primeros Pasos

### 1. Configuración Inicial

```bash
# Configurar el sistema por primera vez
python para_cli.py setup

# Verificar que todo esté funcionando
python para_cli.py doctor
```

### 2. Configurar tu Vault

```bash
# Analizar tu vault actual
python para_cli.py analyze /ruta/a/tu/vault

# Ver el estado del sistema
python para_cli.py status
```

### 3. Primera Organización

```bash
# Organizar automáticamente tu vault
python para_cli.py organize /ruta/a/tu/vault

# Verificar resultados
python para_cli.py analyze /ruta/a/tu/vault
```

## 📋 Comandos Principales

### 🎯 Comandos de Inicio

#### `start` - Iniciar el Sistema
```bash
python para_cli.py start
```
**Descripción**: Inicia el sistema PARA y verifica que todo esté funcionando correctamente.

**Funcionalidades**:
- Verifica dependencias del sistema
- Inicializa bases de datos
- Muestra estado general
- Proporciona próximos pasos

#### `help` - Ayuda del Sistema
```bash
# Ayuda general
python para_cli.py help

# Ayuda específica de un comando
python para_cli.py help organize
```
**Descripción**: Muestra ayuda detallada del sistema o de comandos específicos.

### 🗂️ Comandos de Organización

#### `organize` - Organización Automática
```bash
# Organizar vault completo
python para_cli.py organize /ruta/a/tu/vault

# Organizar con opciones específicas
python para_cli.py organize /ruta/a/tu/vault --dry-run --verbose
```

**Opciones**:
- `--dry-run`: Simula la organización sin hacer cambios
- `--verbose`: Muestra información detallada
- `--force`: Fuerza la reorganización
- `--exclude`: Excluye carpetas específicas

**Funcionalidades**:
- Clasificación automática con IA
- Aplicación de metodología PARA
- Naming inteligente de carpetas
- Reorganización de estructura

#### `analyze` - Análisis de Estructura
```bash
# Análisis completo
python para_cli.py analyze /ruta/a/tu/vault

# Análisis con exportación
python para_cli.py analyze /ruta/a/tu/vault --export-json
```

**Funcionalidades**:
- Análisis de estructura de carpetas
- Estadísticas de archivos
- Detección de problemas
- Sugerencias de mejora
- Exportación de datos

#### `reclassify-all` - Reclasificación Completa
```bash
# Reclasificar todas las notas
python para_cli.py reclassify-all /ruta/a/tu/vault

# Reclasificar con confirmación
python para_cli.py reclassify-all /ruta/a/tu/vault --confirm
```

**Funcionalidades**:
- Reclasificación masiva de notas
- Aplicación de reglas actualizadas
- Corrección de clasificaciones incorrectas
- Optimización de estructura

### 🧹 Comandos de Limpieza

#### `clean` - Limpieza Automática
```bash
# Limpieza básica
python para_cli.py clean /ruta/a/tu/vault

# Limpieza agresiva
python para_cli.py clean /ruta/a/tu/vault --aggressive
```

**Funcionalidades**:
- Eliminación de archivos duplicados
- Limpieza de carpetas vacías
- Consolidación de fragmentos
- Optimización de nombres

#### `consolidate` - Consolidación
```bash
# Consolidar carpetas fragmentadas
python para_cli.py consolidate /ruta/a/tu/vault

# Consolidar con preview
python para_cli.py consolidate /ruta/a/tu/vault --preview
```

**Funcionalidades**:
- Unificación de carpetas similares
- Eliminación de fragmentación
- Optimización de estructura
- Mejora de navegación

### 💾 Comandos de Backup

#### `backup` - Gestión de Backups
```bash
# Crear backup
python para_cli.py backup create

# Listar backups
python para_cli.py backup list

# Restaurar backup
python para_cli.py backup restore backup_20250629_120000.zip
```

**Funcionalidades**:
- Creación automática de backups
- Compresión y encriptación
- Gestión de versiones
- Restauración selectiva

### 🧠 Comandos de IA

#### `learn` - Sistema de Aprendizaje
```bash
# Entrenar con nuevas notas
python para_cli.py learn /ruta/a/tu/vault

# Ver estado del aprendizaje
python para_cli.py learn status
```

**Funcionalidades**:
- Aprendizaje automático
- Mejora de clasificación
- Adaptación a patrones
- Optimización continua

#### `finetune` - Fine-tuning de IA
```bash
# Fine-tuning básico
python para_cli.py finetune

# Fine-tuning avanzado
python para_cli.py finetune --epochs 10 --batch-size 32
```

**Funcionalidades**:
- Entrenamiento personalizado
- Optimización de modelos
- Mejora de precisión
- Adaptación específica

### 📊 Comandos de Monitoreo

#### `status` - Estado del Sistema
```bash
# Estado general
python para_cli.py status

# Estado detallado
python para_cli.py status --verbose
```

**Información mostrada**:
- Estado de componentes
- Estadísticas del sistema
- Últimas actividades
- Próximas tareas

#### `health` - Verificación de Salud
```bash
# Verificación básica
python para_cli.py health

# Verificación completa
python para_cli.py health --full
```

**Verificaciones**:
- Integridad de archivos
- Estado de bases de datos
- Funcionamiento de IA
- Conectividad de servicios

#### `doctor` - Diagnóstico y Reparación
```bash
# Diagnóstico
python para_cli.py doctor

# Diagnóstico con auto-reparación
python para_cli.py doctor --fix

# Diagnóstico completo
python para_cli.py doctor --fix --verbose
```

**Funcionalidades**:
- Detección de problemas
- Auto-reparación
- Limpieza automática
- Optimización del sistema

### 🌐 Dashboard Web

#### `dashboard` - Dashboard Web
```bash
# Iniciar dashboard
python para_cli.py dashboard

# Dashboard en puerto específico
python para_cli.py dashboard --port 3001
```

**Características**:
- Interfaz web moderna
- Métricas en tiempo real
- Gestión visual
- Monitoreo avanzado

## 🔧 Configuración Avanzada

### Archivo de Configuración

El sistema usa `para_config.json` para configuración personalizada:

```json
{
  "vault_path": "/ruta/a/tu/vault",
  "ai_model": "gpt-4",
  "backup_enabled": true,
  "auto_organize": true,
  "log_level": "INFO",
  "exclusions": ["sensitive_folder"],
  "backup_retention_days": 30,
  "auto_cleanup": true,
  "learning_enabled": true
}
```

### Variables de Entorno

```bash
# Configuración de IA
export PARA_AI_API_KEY="tu-api-key"
export PARA_AI_MODEL="gpt-4"

# Configuración de logging
export PARA_LOG_LEVEL="DEBUG"
export PARA_LOG_FILE="para_system.log"

# Configuración de backup
export PARA_BACKUP_RETENTION=30
export PARA_BACKUP_PATH="/ruta/backups"

# Configuración del dashboard
export PARA_DASHBOARD_PORT=3000
export PARA_DASHBOARD_HOST="localhost"
```

### Exclusiones

Protege carpetas sensibles de la organización automática:

```bash
# Mostrar exclusiones actuales
python para_cli.py exclude show

# Agregar exclusión
python para_cli.py exclude add "carpeta_sensible"

# Remover exclusión
python para_cli.py exclude remove "carpeta_sensible"

# Limpiar todas las exclusiones
python para_cli.py exclude clear
```

## 📈 Flujos de Trabajo

### 🆕 Configuración Inicial

1. **Instalación**: `./install.sh`
2. **Configuración**: `python para_cli.py setup`
3. **Verificación**: `python para_cli.py doctor`
4. **Análisis**: `python para_cli.py analyze /ruta/vault`
5. **Organización**: `python para_cli.py organize /ruta/vault`

### 🔄 Mantenimiento Diario

1. **Estado**: `python para_cli.py status`
2. **Salud**: `python para_cli.py health`
3. **Organización**: `python para_cli.py organize /ruta/vault`
4. **Backup**: `python para_cli.py backup create`

### 🧹 Mantenimiento Semanal

1. **Diagnóstico**: `python para_cli.py doctor --fix`
2. **Limpieza**: `python para_cli.py clean /ruta/vault`
3. **Consolidación**: `python para_cli.py consolidate /ruta/vault`
4. **Aprendizaje**: `python para_cli.py learn /ruta/vault`

### 📊 Revisión Mensual

1. **Análisis completo**: `python para_cli.py analyze /ruta/vault --full`
2. **Fine-tuning**: `python para_cli.py finetune`
3. **Optimización**: `python para_cli.py optimize`
4. **Backup completo**: `python para_cli.py backup create --full`

## 🎨 Personalización

### Reglas de Clasificación

Puedes personalizar las reglas de clasificación editando el archivo de configuración:

```json
{
  "classification_rules": {
    "projects": {
      "keywords": ["proyecto", "deadline", "fecha límite"],
      "patterns": ["**/proyectos/**", "**/trabajo/**"]
    },
    "areas": {
      "keywords": ["responsabilidad", "área", "rol"],
      "patterns": ["**/areas/**", "**/responsabilidades/**"]
    },
    "resources": {
      "keywords": ["recurso", "referencia", "documentación"],
      "patterns": ["**/recursos/**", "**/docs/**"]
    },
    "archive": {
      "keywords": ["completado", "archivado", "antiguo"],
      "patterns": ["**/archivo/**", "**/completados/**"]
    }
  }
}
```

### Templates Personalizados

Crea templates para diferentes tipos de notas:

```bash
# Crear template de proyecto
python para_cli.py template create project

# Crear template de área
python para_cli.py template create area

# Listar templates
python para_cli.py template list
```

## 🚨 Solución de Problemas

### Problemas Comunes

#### Error de API Key
```bash
# Verificar configuración
python para_cli.py config show

# Configurar API key
python para_cli.py config set ai_api_key "tu-api-key"
```

#### Error de Permisos
```bash
# Verificar permisos
python para_cli.py doctor

# Corregir permisos
python para_cli.py doctor --fix
```

#### Error de Base de Datos
```bash
# Verificar base de datos
python para_cli.py health

# Reparar base de datos
python para_cli.py doctor --fix
```

### Logs y Debugging

```bash
# Ver logs en tiempo real
python para_cli.py logs --follow

# Ver logs de error
python para_cli.py logs --level ERROR

# Exportar logs
python para_cli.py logs --export logs.txt
```

## 📚 Recursos Adicionales

### Documentación Técnica
- [Arquitectura del Sistema](ARCHITECTURE_DOCUMENTATION.md)
- [API Reference](API_REFERENCE.md)
- [CLI Design Guidelines](CLI_DESIGN_GUIDELINES.md)

### Metodología PARA
- [Estándar PARA v3](PARA_SYSTEM_STANDARD_V3.md)
- [Mejores Prácticas](PARA_BEST_PRACTICES.md)
- [Casos de Uso](PARA_USE_CASES.md)

### Soporte
- [FAQ](FAQ.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Contacto](CONTACT.md)

---

**¿Necesitas ayuda?** Consulta la documentación técnica o contacta al equipo de soporte. 