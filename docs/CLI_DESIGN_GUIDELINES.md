# 🎨 CLI Design Guidelines - PARA System

## 📋 Documento Maestro de Lineamientos de Diseño CLI

Este documento establece los principios fundamentales, patrones de diseño y estándares de implementación para la CLI del sistema PARA. Es el **lineamiento maestro principal** que debe seguirse en todo el desarrollo.

---

## 🎯 **Principios Fundamentales**

### 1. **Robustez y Seguridad Primero**
- **Nunca perder datos**: Backup automático antes de cualquier operación crítica
- **Fallbacks inteligentes**: Si la IA falla, usar ChromaDB; si algo falla, tener alternativa
- **Confirmaciones críticas**: Para operaciones destructivas, confirmación explícita
- **Rollback automático**: Siempre poder volver al estado anterior

### 2. **UX Intuitiva y Visual**
- **Interfaz rica**: Usar Rich para colores, tablas, paneles y progreso visual
- **Feedback inmediato**: El usuario siempre sabe qué está pasando
- **Progreso visual**: Barras de progreso para operaciones largas
- **Jerarquía visual clara**: Títulos, subtítulos, listas organizadas

### 3. **Automatización Inteligente**
- **Resolución automática**: Detectar y resolver problemas sin intervención
- **Pre-checks**: Verificar todo antes de ejecutar operaciones críticas
- **Notificaciones inteligentes**: Alertar solo cuando es necesario
- **Flujos sin fricción**: Minimizar pasos manuales

---

## 🎨 **Patrones de Interacción y Estética**

### **1. Estilo de Programación "Conversacional"**
```python
# ❌ Estilo tradicional (frío y técnico)
print("Processing files...")
print("Files processed: 150")
print("Operation completed.")

# ✅ Nuestro estilo (conversacional y amigable)
console.print(f"🤖 Consultando IA con análisis completo...")
console.print(f"📄 Analizando notas... ━━━━━━━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  18% 0:12:32")
console.print(f"✅ IA clasificó como: AI-Prompts -> Prompt AI")
console.print(f"🤖 IA: AI-Prompts → Prompt AI")
console.print(f"⚖️ Pesos dinámicos: ChromaDB=0.61, IA=0.39")
console.print(f"🔄 DISCREPANCIA: ChromaDB=Projects vs IA=AI-Prompts")
```

### **2. Feedback Visual Detallado y Contextual**
```python
# ❌ Feedback básico
print("Processing note: file.md")

# ✅ Nuestro feedback rico y contextual
console.print(f"🔍 Análisis completo de nota activado")
console.print(f"📄 Analizando: {note_name}")
console.print(f"📊 Tags: {tags}...")
console.print(f"📅 Última modificación: {last_modified}")
console.print(f"📝 Palabras: {word_count}")
console.print(f"🔍 ChromaDB: {chroma_result} (confianza: {confidence:.3f})")
```

### **3. Progreso Visual Narrativo**
```python
# ❌ Progreso simple
progress.update(task, advance=10)

# ✅ Nuestro progreso narrativo
console.print(f"Analizando notas... ━━━━━━━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  {percentage}% {eta}")
console.print(f"🤖 Consultando IA ({model_name}) para clasificación...")
console.print(f"✅ IA clasificó como: {result}")
console.print(f"⚖️ Pesos dinámicos: ChromaDB={chroma_weight:.2f}, IA={ai_weight:.2f}")
```

### **4. Manejo de Errores con Personalidad**
```python
# ❌ Error frío
print("Error: Model not available")

# ✅ Nuestro error con personalidad y soluciones
console.print(f"⚠️ Usando modelo Ollama más robusto disponible: {fallback_model}")
console.print(f"🤖 Consultando IA ({fallback_model}) para clasificación...")
console.print(f"✅ IA clasificó como: {result}")
```

---

## 🎨 **Estándares Visuales**

### **Paleta de Colores**
```python
# Colores principales
SUCCESS = "green"      # ✅ Operaciones exitosas
ERROR = "red"          # ❌ Errores críticos
WARNING = "yellow"     # ⚠️ Advertencias
INFO = "blue"          # ℹ️ Información
HIGHLIGHT = "cyan"     # 🔍 Elementos importantes
MUTED = "dim"          # 📝 Texto secundario
```

### **Iconos y Símbolos**
```python
# Iconos estándar
ICONS = {
    "success": "✅",
    "error": "❌", 
    "warning": "⚠️",
    "info": "ℹ️",
    "progress": "🔄",
    "complete": "🎯",
    "backup": "🔒",
    "ai": "🤖",
    "database": "🗄️",
    "vault": "��",
    "notes": "📄",
    "search": "🔍",
    "settings": "⚙️",
    "help": "💡",
    "time": "⏱️",
    "stats": "📊",
    "analysis": "🔍",
    "classification": "🏷️",
    "learning": "🧠",
    "sync": "🔄",
    "check": "✔️",
    "cross": "✖️",
    "arrow": "→",
    "discrepancy": "🔄",
    "weights": "⚖️"
}
```

### **Tipografía y Estructura**
```python
# Jerarquía visual
TITLE_STYLE = "bold blue"
SUBTITLE_STYLE = "bold cyan" 
SECTION_STYLE = "bold"
CODE_STYLE = "dim"
HIGHLIGHT_STYLE = "bold yellow"
```

---

## 🏗️ **Patrones de Implementación**

### **1. Estructura de Comandos**
```python
def cmd_example(self, *args):
    """Descripción clara del comando."""
    # 1. Pre-checks y validaciones
    vault = self._require_vault()
    if not vault:
        return
    
    # 2. Pre-classification summary (si aplica)
    self._print_pre_classification_summary(vault)
    
    # 3. Backup automático (si es crítico)
    self._auto_export_knowledge(vault)
    
    # 4. Ejecución principal con progreso visual
    with Progress() as progress:
        task = progress.add_task("Operación...", total=100)
        # ... lógica principal
    
    # 5. Notificaciones post-ejecución
    self._notify_if_unrestored_backup()
```

### **2. Manejo de Errores**
```python
try:
    # Operación principal
    result = perform_operation()
    console.print(f"[green]✅ {success_message}[/green]")
except Exception as e:
    # Logging automático
    logger.error(f"Error en operación: {e}")
    console.print(f"[red]❌ {error_message}[/red]")
    console.print(f"[yellow]💡 {suggestion}[/yellow]")
    return False
```

### **3. Tablas de Información**
```python
table = Table(title="Título Descriptivo")
table.add_column("Columna", style="cyan", no_wrap=True)
table.add_column("Descripción", style="green")
table.add_column("Estado", style="yellow")
table.add_column("Acción", style="blue")

for item in items:
    table.add_row(
        str(item.id),
        item.description,
        item.status,
        item.action
    )
console.print(table)
```

### **4. Paneles de Resumen**
```python
console.print(Panel(
    f"[bold green]✅ {title}[/bold green]\n"
    f"📁 {details}\n"
    f"⏱️ {time_info}\n"
    f"💡 {next_steps}",
    title="[bold blue]Resumen de Operación[/bold blue]"
))
```

---

## 🔄 **Flujos de Usuario**

### **1. Flujo de Clasificación**
```
1. Pre-check visual con checklist
2. Backup automático con progreso
3. Análisis híbrido (ChromaDB + IA)
4. Progreso visual detallado
5. Resumen final con estadísticas
6. Notificaciones de próximos pasos
```

### **2. Flujo de Restauración**
```
1. Lista visual de backups disponibles
2. Confirmación crítica con advertencias
3. Backup de seguridad automático
4. Restauración con progreso visual
5. Verificación post-restauración
6. Instrucciones de próximos pasos
```

### **3. Flujo de Diagnóstico**
```
1. Análisis automático de logs
2. Detección de problemas
3. Auto-resolución cuando es posible
4. Reporte visual de estado
5. Recomendaciones específicas
```

---

## 📊 **Estándares de Logging**

### **Niveles de Log**
```python
# Estructura estándar de logs
logger.info(f"[MODULE] Mensaje informativo")
logger.warning(f"[MODULE] Advertencia: {details}")
logger.error(f"[MODULE] Error crítico: {error}")
logger.debug(f"[MODULE] Debug: {debug_info}")
```

### **Métricas y Monitoreo**
```python
# Métricas estándar a recolectar
metrics = {
    'total_operations': 0,
    'successful_operations': 0,
    'failed_operations': 0,
    'auto_resolved_issues': 0,
    'manual_interventions': 0,
    'avg_operation_time': 0,
    'backup_count': 0,
    'ai_fallback_count': 0
}
```

---

## 🎯 **Patrones de UX**

### **1. Confirmaciones Críticas**
```python
if not Confirm.ask("[bold red]¿Estás seguro?", default=False):
    console.print("[yellow]❌ Operación cancelada por el usuario.[/yellow]")
    return False
```

### **2. Progreso Visual**
```python
with Progress() as progress:
    task = progress.add_task("Operación...", total=100)
    for step in steps:
        progress.update(task, advance=step_progress)
        # ... lógica de paso
```

### **3. Resúmenes Post-Operación**
```python
console.print(f"\n[bold green]✅ OPERACIÓN COMPLETADA[/bold green]")
console.print(f"📁 Resultado: {result}")
console.print(f"⏱️ Tiempo: {duration}")
console.print(f"💡 Próximos pasos: {next_steps}")
```

### **4. Notificaciones Inteligentes**
```python
if condition_needs_attention:
    console.print(f"[yellow]⚠️ {warning_message}[/yellow]")
    console.print(f"[yellow]💡 {suggestion}[/yellow]")
```

---

## 🔧 **Estándares Técnicos**

### **1. Imports y Dependencias**
```python
# Imports estándar para CLI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Confirm, IntPrompt
from rich.markdown import Markdown
from datetime import datetime
from pathlib import Path
```

### **2. Configuración de Consola**
```python
console = Console()
console.print(f"[bold blue]Título Principal[/bold blue]")
console.print(f"{'='*80}")
```

### **3. Manejo de Archivos**
```python
# Patrones estándar para archivos
backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```

---

## 📋 **Checklist de Implementación**

### **Antes de Implementar un Comando:**
- [ ] ¿Tiene pre-checks de seguridad?
- [ ] ¿Incluye backup automático si es crítico?
- [ ] ¿Usa progreso visual para operaciones largas?
- [ ] ¿Tiene confirmaciones para operaciones destructivas?
- [ ] ¿Incluye logging automático de errores?
- [ ] ¿Proporciona feedback visual claro?
- [ ] ¿Tiene resumen post-ejecución?
- [ ] ¿Incluye sugerencias de próximos pasos?

### **Antes de Deploy:**
- [ ] ¿Sigue la paleta de colores estándar?
- [ ] ¿Usa los iconos correctos?
- [ ] ¿Tiene manejo de errores robusto?
- [ ] ¿Incluye fallbacks automáticos?
- [ ] ¿Está documentado correctamente?
- [ ] ¿Ha sido probado con casos edge?

---

## 🎨 **Ejemplos de Implementación**

### **Comando de Clasificación (Ejemplo Completo)**
```python
def cmd_classify(self, *args):
    """Clasifica notas usando el sistema híbrido PARA."""
    
    # 1. Pre-checks
    vault = self._require_vault()
    if not vault:
        return
    
    # 2. Pre-classification summary
    self._print_pre_classification_summary(vault)
    
    # 3. Backup automático
    self._auto_export_knowledge(vault)
    
    # 4. Ejecución con progreso
    with Progress() as progress:
        task = progress.add_task("Clasificando notas...", total=100)
        
        try:
            # Lógica de clasificación
            result = self._perform_classification(vault)
            progress.update(task, advance=100)
            
            # 5. Resumen final
            console.print(f"\n[bold green]✅ CLASIFICACIÓN COMPLETADA[/bold green]")
            console.print(f"📄 Notas procesadas: {result['total']}")
            console.print(f"⏱️ Tiempo: {result['duration']}")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            return False
    
    # 6. Notificaciones
    self._notify_if_unrestored_backup()
```

---

## 📚 **Referencias y Recursos**

### **Documentación Rich:**
- [Rich Console](https://rich.readthedocs.io/en/stable/console.html)
- [Rich Tables](https://rich.readthedocs.io/en/stable/tables.html)
- [Rich Progress](https://rich.readthedocs.io/en/stable/progress.html)
- [Rich Panels](https://rich.readthedocs.io/en/stable/panel.html)

### **Patrones de CLI:**
- [CLI Design Patterns](https://clig.dev/)
- [UX Guidelines for CLI](https://ux.stackexchange.com/questions/tagged/command-line)

---

## 🎯 **Objetivo Final**

Este documento debe garantizar que **todos los comandos de la CLI PARA**:
- Sean visualmente atractivos y funcionales
- Proporcionen feedback claro y inmediato
- Manejen errores de forma robusta
- Sigan patrones consistentes
- Ofrezcan una experiencia de usuario excepcional

**Este es el lineamiento maestro principal que debe seguirse en todo el desarrollo de la CLI PARA.**

---

*Última actualización: 2025-06-26*
*Versión: 1.0*
*Mantenido por: Sistema PARA* 