# 🚀 Guía de Instalación - Sistema PARA v3.0

## 📋 **Guía Completa de Instalación**

Esta guía te llevará desde la instalación inicial hasta tener un sistema PARA v3.0 completamente funcional organizando tu vault de Obsidian automáticamente.

---

## ⚡ **Instalación Rápida (Recomendada)**

### **🎯 Un Solo Comando - Todo Automático**

```bash
# 1. Clonar y entrar al directorio
git clone https://github.com/tu-usuario/obsidian-para.git
cd obsidian-para

# 2. Instalación automática completa
./install.sh

# 3. ¡Listo! Iniciar el sistema
./para_cli.py start
```

**✅ El script automático instala TODO**:
- Python 3.8+ (si no está instalado)
- Ollama y modelo de IA llama3.2:3b
- Entorno virtual Python
- Todas las dependencias Python
- Configuración inicial del sistema
- Tests de verificación completos

---

## 🔧 **Requisitos del Sistema**

### **💻 Requisitos Mínimos**
- **Sistema Operativo**: macOS, Linux, Windows
- **Python**: 3.8 o superior
- **Memoria RAM**: 4GB (recomendado 8GB+)
- **Espacio en Disco**: 3GB libres
- **Conexión**: Internet (solo para instalación inicial)

### **🔍 Verificar Requisitos Previos**

```bash
# Verificar Python
python3 --version
# Debe mostrar Python 3.8.x o superior

# Verificar espacio en disco
df -h
# Verificar que hay al menos 3GB libres

# Verificar conexión (opcional)
ping -c 1 google.com
```

---

## 📦 **Instalación Manual (Avanzada)**

Si prefieres instalar paso a paso o el script automático falla:

### **1. Preparar el Entorno**

```bash
# Verificar Python
python3 --version

# Clonar repositorio
git clone https://github.com/tu-usuario/obsidian-para.git
cd obsidian-para

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### **2. Instalar Dependencias Python**

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias principales
pip install -r requirements.txt

# Verificar instalación
python -c "import streamlit, chromadb; print('✅ Dependencias instaladas')"
```

### **3. Instalar y Configurar Ollama**

#### **En macOS:**
```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# O con Homebrew
brew install ollama
```

#### **En Linux:**
```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar servicio
sudo systemctl start ollama
sudo systemctl enable ollama
```

#### **En Windows:**
```bash
# Descargar desde https://ollama.ai/download
# Ejecutar el instalador
# Ollama se instala como servicio automáticamente
```

### **4. Descargar Modelo de IA**

```bash
# Descargar modelo principal
ollama pull llama3.2:3b

# Verificar modelo descargado
ollama list
# Debe mostrar llama3.2:3b

# Probar modelo (opcional)
ollama run llama3.2:3b "Hello, test"
```

### **5. Configuración Inicial**

```bash
# Hacer scripts ejecutables (macOS/Linux)
chmod +x para_cli.py install.sh

# Copiar configuración por defecto (opcional)
cp para_config.default.json para_config.json

# Crear directorios necesarios
mkdir -p logs backups
```

---

## ✅ **Verificación de Instalación**

### **🏥 Test Automático Completo**

```bash
# Ejecutar diagnóstico completo
./para_cli.py doctor

# Debe mostrar:
# ✅ Ollama: Funcionando
# ✅ Modelo llama3.2:3b: Disponible
# ✅ ChromaDB: Inicializado
# ✅ Dependencias: Completas
# ✅ Permisos: Correctos
# Health Score: 95-100
```

### **🧪 Tests Manuales**

```bash
# Test 1: CLI funciona
./para_cli.py --help
# Debe mostrar ayuda completa

# Test 2: IA responde
./para_cli.py "hola sistema"
# Debe interpretar como comando

# Test 3: Dashboard web
./para_cli.py dashboard
# Debe abrir navegador con dashboard

# Test 4: QA automático
./para_cli.py qa
# Debe ejecutar tests completos
```

---

## 🔧 **Solución de Problemas de Instalación**

### **❌ Problema: Python no encontrado**

```bash
# Instalar Python 3.8+ en Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Instalar Python 3.8+ en CentOS/RHEL
sudo yum install python3 python3-pip

# En macOS con Homebrew
brew install python@3.11

# En Windows
# Descargar desde https://python.org/downloads/
```

### **❌ Problema: Ollama no instala**

```bash
# Verificar conexión
curl -I https://ollama.ai

# Instalación manual en macOS
curl -L https://ollama.ai/download/ollama-darwin.zip -o ollama.zip
unzip ollama.zip
sudo mv ollama /usr/local/bin/

# Instalación manual en Linux
curl -L https://ollama.ai/download/ollama-linux-amd64 -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/
```

### **❌ Problema: Modelo no descarga**

```bash
# Verificar servicio Ollama
ollama serve
# Debe ejecutarse sin errores

# En otra terminal
ollama pull llama3.2:3b

# Si falla, probar modelo más pequeño
ollama pull llama3.2:1b

# Configurar modelo en para_config.json
{
    "ollama_model": "llama3.2:1b"
}
```

### **❌ Problema: Permisos en macOS**

```bash
# Dar permisos completos
chmod +x para_cli.py install.sh

# Si macOS bloquea ejecución
sudo xattr -r -d com.apple.quarantine .

# Verificar permisos de escritura
touch test_file && rm test_file
```

### **❌ Problema: Dependencias Python fallan**

```bash
# Actualizar herramientas
pip install --upgrade pip setuptools wheel

# Instalar dependencias una por una
pip install rich
pip install typer
pip install chromadb
pip install streamlit
pip install plotly

# Si ChromaDB falla en M1 Mac
pip install --no-deps chromadb
```

---

## 🎯 **Configuración Personalizada**

### **📝 Archivo de Configuración**

Edita `para_config.json` para personalizar:

```json
{
    "vault_path": "/ruta/a/tu/vault",
    "ollama_model": "llama3.2:3b",
    "dashboard_port": 8501,
    "auto_backup": true,
    "learning_enabled": true,
    "log_level": "INFO",
    "theme": "dark"
}
```

### **🎨 Configuración de Dashboard**

```bash
# Puerto personalizado
./para_cli.py dashboard --port 8502

# Host personalizado (acceso remoto)
./para_cli.py dashboard --host 0.0.0.0

# Tipo de dashboard específico
./para_cli.py dashboard --type supremo
```

---

## 🚀 **Primer Uso - Setup Inicial**

### **🎯 Migración Automática (Recomendada)**

```bash
# Comando mágico que hace todo
./para_cli.py start
```

**El comando `start` hace automáticamente**:
1. 🔍 Detecta tu vault de Obsidian
2. 🌳 Abre GUI para seleccionar exclusiones
3. 💾 Crea backup automático
4. 🧠 Analiza todas tus notas
5. 📂 Organiza en estructura PARA
6. 📊 Configura aprendizaje autónomo

### **🔧 Setup Manual Paso a Paso**

Si prefieres control total:

```bash
# 1. Configurar vault
./para_cli.py config --vault /ruta/a/tu/vault

# 2. Análisis inicial
./para_cli.py analyze --detailed

# 3. Configurar exclusiones
./para_cli.py exclude custom

# 4. Crear backup manual
./para_cli.py backups create

# 5. Clasificación inicial
./para_cli.py classify

# 6. Setup aprendizaje
./para_cli.py learn --setup
```

---

## 📊 **Verificación Post-Instalación**

### **✅ Checklist de Verificación**

```bash
# ✅ 1. Sistema funciona
./para_cli.py doctor
# Health Score debe ser >90

# ✅ 2. IA clasifica correctamente
./para_cli.py classify --test

# ✅ 3. Dashboard carga
./para_cli.py dashboard &
curl http://localhost:8501
# Debe retornar HTML

# ✅ 4. Backup funciona
./para_cli.py backups create
ls backups/
# Debe mostrar archivo de backup

# ✅ 5. Aprendizaje activo
./para_cli.py learning-metrics
# Debe mostrar métricas iniciales
```

### **📈 Métricas de Instalación Exitosa**

```bash
./para_cli.py metrics --installation
```

**Debe mostrar**:
- ✅ Health Score: >90
- ✅ IA Response Time: <5s
- ✅ Dashboard Load Time: <3s
- ✅ ChromaDB: Inicializada
- ✅ Learning System: Activo

---

## 🆘 **Soporte y Ayuda**

### **🔍 Auto-diagnóstico**

```bash
# Diagnóstico completo con auto-fix
./para_cli.py doctor --auto-fix

# Análisis de logs si hay problemas
./para_cli.py logs --analyze

# QA automático completo
./para_cli.py qa --full
```

### **📞 Obtener Ayuda**

1. **Documentación**: [docs/](../docs/)
2. **Issues GitHub**: Para reportar bugs
3. **Logs del sistema**: `./para_cli.py logs --export`
4. **Health check**: `./para_cli.py doctor --report`

### **🐛 Reportar Problemas**

Si encuentras problemas:

```bash
# 1. Ejecutar diagnóstico
./para_cli.py doctor --report > diagnostico.txt

# 2. Exportar logs
./para_cli.py logs --export > logs.txt

# 3. Crear issue con ambos archivos
```

---

## 🎉 **¡Instalación Completa!**

Si llegaste hasta aquí, tu sistema PARA v3.0 está **completamente instalado y funcionando**.

### **🚀 Próximos Pasos**

1. **Organiza tu vault**: `./para_cli.py start`
2. **Explora el dashboard**: `./para_cli.py dashboard`
3. **Revisa métricas**: `./para_cli.py learning-metrics`
4. **Lee la documentación**: [docs/PARA_SYSTEM_STANDARD_V3.md](PARA_SYSTEM_STANDARD_V3.md)

### **💡 Tips Importantes**

- 🔄 El sistema **mejora automáticamente** con el uso
- 💾 **Backup automático** antes de cualquier cambio
- 🏥 Ejecuta `doctor` si algo no funciona
- 📊 El **dashboard** muestra todo en tiempo real

---

**¡Disfruta organizando tu conocimiento con IA! 🤖✨**

*Guía de instalación del Sistema PARA v3.0 - Actualizada Diciembre 2024* 