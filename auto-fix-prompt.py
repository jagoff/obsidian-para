import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

LOG_PATH = Path('logs/para.log')

# 1. Leer el log unificado
if not LOG_PATH.exists():
    print('No se encontró el log unificado (logs/para.log).')
    exit(1)

with open(LOG_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 2. Detectar errores y contarlos por comando y módulo
error_pattern = re.compile(r'ERROR \[para:([\w_]+):(\d+)\].*')
cmd_pattern = re.compile(r'Comando (\w+)')

module_counter = Counter()
cmd_counter = Counter()
error_lines = []

for line in lines:
    m = error_pattern.search(line)
    if m:
        module = m.group(1)
        module_counter[module] += 1
        error_lines.append(line)
        # Buscar comando si está en la línea
        cmd_m = cmd_pattern.search(line)
        if cmd_m:
            cmd_counter[cmd_m.group(1)] += 1

# 3. Ranking de módulos y comandos más problemáticos
print('--- Ranking de módulos con más errores ---')
for mod, count in module_counter.most_common(10):
    print(f'{mod}: {count} errores')
print('\n--- Ranking de comandos con más errores ---')
for cmd, count in cmd_counter.most_common(10):
    print(f'{cmd}: {count} errores')

# 4. Sugerir y ejecutar fixes automáticos
fixes = []

# a) Si hay muchos errores de import/module, intentar reinstalar dependencias
if any('ModuleNotFoundError' in l or 'ImportError' in l for l in error_lines):
    print('🔧 Fix: Reinstalando dependencias con pip...')
    try:
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        fixes.append('Reinstalación de dependencias ejecutada')
    except Exception as e:
        print(f'❌ Error reinstalando dependencias: {e}')

# b) Si hay errores de ChromaDB, sugerir reinicio o verificación de servicio
if any('chromadb' in l.lower() or 'Connection refused' in l for l in error_lines):
    print('🔧 Fix: Sugerido reiniciar ChromaDB o verificar configuración.')
    fixes.append('Sugerido reinicio/verificación de ChromaDB')

# c) Si hay errores de vault/configuración
if any('No vault found' in l or 'vault' in l.lower() for l in error_lines):
    print('🔧 Fix: Sugerido configurar vault con para obsidian-vault')
    fixes.append('Sugerido configurar vault')

# d) Si hay errores de permisos
if any('Permission denied' in l for l in error_lines):
    print('🔧 Fix: Sugerido verificar permisos de escritura en el directorio')
    fixes.append('Sugerido verificar permisos de escritura')

# e) Si hay errores de modelo/ollama
if any('ollama' in l.lower() or 'model' in l.lower() for l in error_lines):
    print('🔧 Fix: Sugerido verificar modelos de IA instalados')
    fixes.append('Sugerido verificar modelos de IA')

# f) Si hay errores de backup
if any('backup' in l.lower() for l in error_lines):
    print('🔧 Fix: Sugerido verificar espacio en disco y permisos para backups')
    fixes.append('Sugerido verificar backups')

# 5. Resumen final
print('\n--- Resumen de fixes automáticos ---')
if fixes:
    for fix in fixes:
        print(f'✅ {fix}')
else:
    print('No se detectaron fixes automáticos necesarios.')

print('\n--- QA COMPLETO FINALIZADO ---') 