# PARA System v2.0

Sistema de organización de Obsidian usando IA y metodología PARA (Projects, Areas, Resources, Archive).

## 🚀 Características

- **Clasificación Automática**: IA que clasifica notas en la estructura PARA
- **Balance Automático**: Distribuye notas equitativamente entre categorías
- **Fine-tuning**: Entrena modelos personalizados con tus datos
- **Dashboard Web**: Interfaz web moderna para monitoreo
- **Sistema de Logs**: Logging robusto y auto-fix de errores
- **Backup Automático**: Sistema de respaldo inteligente

## 📁 Estructura del Proyecto

```
obsidian-para/
├── src/                    # Código fuente principal
│   ├── paralib/           # Biblioteca principal
│   │   ├── cli/           # Comandos CLI modulares
│   │   ├── ai_engine.py   # Motor de IA
│   │   ├── organizer.py   # Organizador principal
│   │   └── ...
│   └── para_cli.py        # CLI principal
├── docs/                  # Documentación
├── examples/              # Ejemplos de uso
├── para_config.json       # Configuración del sistema
└── requirements.txt       # Dependencias
```

## 🛠️ Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/obsidian-para.git
   cd obsidian-para
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar**:
   ```bash
   python para_cli.py start
   ```

## 🎯 Uso Básico

### Comandos Principales

```bash
# Iniciar sistema
python para_cli.py start

# Clasificar notas
python para_cli.py classify

# Analizar vault
python para_cli.py analyze

# Dashboard web
python para_cli.py dashboard

# Diagnóstico del sistema
python para_cli.py doctor

# Balance automático
python para_cli.py balance --execute
```

### Comandos de IA

```bash
# Preguntas y respuestas
python para_cli.py qa "¿Cómo organizar mis proyectos?"

# Fine-tuning
python para_cli.py finetune auto

# Auto-fix de errores
python para_cli.py logs-auto-fix
```

## 🔧 Configuración

Edita `para_config.json` para personalizar:

- **AI Engine**: Cambiar modelo de IA
- **Vault**: Configurar ruta del vault
- **Clasificación**: Ajustar umbrales de confianza
- **Backup**: Configurar respaldos automáticos

## 📊 Dashboard Web

Ejecuta `python para_cli.py dashboard` para acceder al dashboard web en `http://localhost:3000`.

## 🤖 IA y Fine-tuning

El sistema incluye:

- **Clasificación Inteligente**: Clasifica notas usando IA
- **Fine-tuning Automático**: Entrena modelos con tus datos
- **Auto-fix**: Corrige errores automáticamente
- **QA System**: Responde preguntas sobre tu vault

## 📝 Logs y Monitoreo

- **Logs Detallados**: Sistema de logging robusto
- **Auto-fix**: Corrección automática de errores
- **Métricas**: Estadísticas de rendimiento
- **Health Check**: Diagnóstico del sistema

## 🔄 Backup y Restauración

```bash
# Crear backup
python para_cli.py backup

# Restaurar backup
python para_cli.py restore <backup_id>

# Listar backups
python para_cli.py backup list
```

## 🐛 Solución de Problemas

### Diagnóstico
```bash
python para_cli.py doctor
```

### Auto-fix
```bash
python para_cli.py logs-auto-fix
```

### Limpieza
```bash
python para_cli.py clean
```

## 📚 Documentación

- [Guía de Usuario](docs/USER_GUIDE.md)
- [Referencia de API](docs/API_REFERENCE.md)
- [Arquitectura](docs/ARCHITECTURE_DOCUMENTATION.md)
- [Guía de Instalación](docs/INSTALLATION_GUIDE.md)

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/obsidian-para/issues)
- **Documentación**: [docs/](docs/)
- **Comandos de ayuda**: `python para_cli.py help`

---

**PARA System v2.0** - Organiza tu vida digital con IA 🚀 