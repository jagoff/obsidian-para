#!/bin/zsh
# Completion script for PARA CLI
# Para instalar: source para_zsh_completion.sh

# Colores para el output
autoload -U colors && colors

# Función principal de completion
_para_cli() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    # Obtener el comando actual
    local cmd="${words[1]}"
    local subcmd="${words[2]}"
    local current_word="${words[CURRENT]}"

    # Si es la primera palabra, mostrar todos los comandos disponibles
    if [[ $CURRENT -eq 1 ]]; then
        # Comandos core
        local core_commands=(
            'classify:Clasificar notas usando PARA'
            'analyze:Analizar contenido de notas'
            'clean:Limpiar y organizar vault'
            'learn:Sistema de aprendizaje automático'
            'logs:Gestión de logs del sistema'
            'dashboard:Dashboard web del sistema'
            'doctor:Diagnóstico y reparación del sistema'
            'plugins:Gestión de plugins'
            'reclassify-all:Reclasificar todas las notas'
            'help:Mostrar ayuda'
            'version:Mostrar versión'
        )

        # Comandos de plugins (Obsidian)
        local plugin_commands=(
            'obsidian-vault:Gestionar vault de Obsidian'
            'obsidian-sync:Sincronizar con Obsidian'
            'obsidian-backup:Crear backup del vault de Obsidian'
            'obsidian-plugins:Gestionar plugins de Obsidian'
            'obsidian-notes:Gestionar notas de Obsidian'
            'obsidian-search:Búsqueda avanzada en Obsidian'
            'obsidian-graph:Análisis del grafo de Obsidian'
            'obsidian-watch:Monitorear cambios en tiempo real'
        )

        # Aliases cortos
        local short_commands=(
            're:reclassify-all'
            'cl:classify'
            'an:analyze'
            'cl:clean'
            'le:learn'
            'lo:logs'
            'da:dashboard'
            'do:doctor'
            'pl:plugins'
            'he:help'
            've:version'
            'ov:obsidian-vault'
            'os:obsidian-sync'
            'ob:obsidian-backup'
            'op:obsidian-plugins'
            'on:obsidian-notes'
            'osearch:obsidian-search'
            'ograph:obsidian-graph'
            'owatch:obsidian-watch'
        )

        # Ejemplos de prompts AI
        local ai_prompts=(
            're clasifica todas mis notas'
            'muéstrame las notas recientes'
            'crea un backup'
            'limpiar vault'
            'aprende de mis clasificaciones'
            'muéstrame los logs'
            'abre el dashboard'
            'diagnostica el sistema'
            'muéstrame los plugins'
        )

        # Combinar todos los comandos
        local all_commands=($core_commands $plugin_commands)
        
        # Si el usuario está escribiendo algo que parece un prompt AI, sugerir prompts
        if [[ "$current_word" =~ ^[a-záéíóúñ]+ ]]; then
            _describe -t ai-prompts "AI Prompts" ai_prompts
        fi
        
        # Mostrar comandos normales
        _describe -t commands "PARA Commands" all_commands
        
        # Mostrar aliases cortos
        _describe -t aliases "Short Aliases" short_commands
        
        return 0
    fi

    # Completion específica para cada comando
    case "$cmd" in
        classify|cl)
            _para_classify
            ;;
        analyze|an)
            _para_analyze
            ;;
        clean)
            _para_clean
            ;;
        learn|le)
            _para_learn
            ;;
        logs|lo)
            _para_logs
            ;;
        plugins|pl)
            _para_plugins
            ;;
        obsidian-vault|ov)
            _para_obsidian_vault
            ;;
        obsidian-sync|os)
            _para_obsidian_sync
            ;;
        obsidian-backup|ob)
            _para_obsidian_backup
            ;;
        obsidian-plugins|op)
            _para_obsidian_plugins
            ;;
        obsidian-notes|on)
            _para_obsidian_notes
            ;;
        obsidian-search|osearch)
            _para_obsidian_search
            ;;
        obsidian-graph|ograph)
            _para_obsidian_graph
            ;;
        obsidian-watch|owatch)
            _para_obsidian_watch
            ;;
        reclassify-all|re)
            _para_reclassify_all
            ;;
        dashboard|da)
            _para_dashboard
            ;;
        doctor|do)
            _para_doctor
            ;;
        *)
            # Para prompts AI o comandos no reconocidos, sugerir archivos markdown
            _files -g "*.md"
            ;;
    esac
}

# Completion para classify
_para_classify() {
    local state
    _arguments \
        '1: :->path' \
        '--plan[Generar plan de clasificación]' \
        '--confirm[Confirmar plan automáticamente]' \
        '--backup[Crear backup antes de clasificar]'
    
    case $state in
        path)
            _files -g "*.md"
            ;;
    esac
}

# Completion para analyze
_para_analyze() {
    local state
    _arguments \
        '1: :->path' \
        '--detailed[Análisis detallado]' \
        '--export: :->export_file'
    
    case $state in
        path)
            _files -g "*.md"
            ;;
        export_file)
            _files
            ;;
    esac
}

# Completion para clean
_para_clean() {
    _arguments \
        '--dry-run[Simular limpieza sin ejecutar]' \
        '--backup[Crear backup antes de limpiar]'
}

# Completion para learn
_para_learn() {
    _arguments \
        '1: :->action' \
        '--days[Días a analizar]: :->days'
    
    case $state in
        action)
            local actions=(
                'review:Revisar clasificaciones'
                'analyze:Analizar rendimiento'
                'improve:Mejorar modelos'
                'report:Generar reporte'
            )
            _describe -t actions "Learn Actions" actions
            ;;
        days)
            local days=(7 30 90 365)
            _describe -t days "Days" days
            ;;
    esac
}

# Completion para logs
_para_logs() {
    _arguments \
        '1: :->action' \
        '--days[Días a analizar]: :->days'
    
    case $state in
        action)
            local actions=(
                'analyze:Analizar logs'
                'resolve:Resolver problemas'
                'metrics:Mostrar métricas'
            )
            _describe -t actions "Log Actions" actions
            ;;
        days)
            local days=(1 7 30 90)
            _describe -t days "Days" days
            ;;
    esac
}

# Completion para plugins
_para_plugins() {
    _arguments \
        '1: :->action'
    
    case $state in
        action)
            local actions=(
                'enable:Habilitar plugin'
                'disable:Deshabilitar plugin'
                'reload:Recargar plugins'
                'commands:Listar comandos'
                'ai-stats:Estadísticas AI'
            )
            _describe -t actions "Plugin Actions" actions
            ;;
    esac
}

# Completion para obsidian-vault
_para_obsidian_vault() {
    _arguments \
        '1: :->action' \
        '2: :->vault_path'
    
    case $state in
        action)
            local actions=(
                'info:Mostrar información del vault'
                'set:Configurar vault'
                'list:Listar vaults disponibles'
            )
            _describe -t actions "Vault Actions" actions
            ;;
        vault_path)
            _files -/
            ;;
    esac
}

# Completion para obsidian-sync
_para_obsidian_sync() {
    _arguments \
        '1: :->action'
    
    case $state in
        action)
            local actions=(
                'status:Estado de sincronización'
                'sync:Sincronizar ahora'
                'conflicts:Resolver conflictos'
            )
            _describe -t actions "Sync Actions" actions
            ;;
    esac
}

# Completion para obsidian-backup
_para_obsidian_backup() {
    _arguments \
        '1: :->backup_dir'
    
    case $state in
        backup_dir)
            _files -/
            ;;
    esac
}

# Completion para obsidian-plugins
_para_obsidian_plugins() {
    _arguments \
        '1: :->action'
    
    case $state in
        action)
            local actions=(
                'list:Listar plugins'
                'enable:Habilitar plugin'
                'disable:Deshabilitar plugin'
                'update:Actualizar plugins'
            )
            _describe -t actions "Plugin Actions" actions
            ;;
    esac
}

# Completion para obsidian-notes
_para_obsidian_notes() {
    _arguments \
        '1: :->action'
    
    case $state in
        action)
            local actions=(
                'stats:Estadísticas de notas'
                'recent:Notas recientes'
                'orphaned:Notas huérfanas'
                'duplicates:Notas duplicadas'
            )
            _describe -t actions "Note Actions" actions
            ;;
    esac
}

# Completion para obsidian-search
_para_obsidian_search() {
    _arguments \
        '1: :->query' \
        '--folder[Carpeta específica]: :->folder'
    
    case $state in
        query)
            # Sugerir términos de búsqueda comunes
            local search_terms=(
                'tag:'
                'path:'
                'content:'
                'modified:'
            )
            _describe -t search "Search Terms" search_terms
            ;;
        folder)
            _files -/
            ;;
    esac
}

# Completion para obsidian-graph
_para_obsidian_graph() {
    _arguments \
        '1: :->action'
    
    case $state in
        action)
            local actions=(
                'analyze:Analizar grafo'
                'export:Exportar grafo'
                'stats:Estadísticas del grafo'
            )
            _describe -t actions "Graph Actions" actions
            ;;
    esac
}

# Completion para obsidian-watch
_para_obsidian_watch() {
    _arguments \
        '1: :->watch_time'
    
    case $state in
        watch_time)
            local times=(30 60 300 600)
            _describe -t times "Watch Time (seconds)" times
            ;;
    esac
}

# Completion para reclassify-all
_para_reclassify_all() {
    _arguments \
        '--backup[Crear backup antes de reclasificar]' \
        '--confirm[Confirmar automáticamente]'
}

# Completion para dashboard
_para_dashboard() {
    _arguments \
        '--port[Puerto del dashboard]: :->port'
    
    case $state in
        port)
            local ports=(8501 8502 8503 8504)
            _describe -t ports "Port" ports
            ;;
    esac
}

# Completion para doctor
_para_doctor() {
    _arguments \
        '--advanced[Modo avanzado]' \
        '--fix[Reparar automáticamente]'
}

# Función para instalar el completion
install_para_completion() {
    echo "${fg[green]}Instalando completion para PARA CLI...${reset_color}"
    
    # Crear directorio de completion si no existe
    local completion_dir="$HOME/.zsh/completions"
    mkdir -p "$completion_dir"
    
    # Copiar el script de completion
    cp "$0" "$completion_dir/_para_cli"
    chmod +x "$completion_dir/_para_cli"
    
    # Agregar al .zshrc si no está ya
    if ! grep -q "fpath.*completions" "$HOME/.zshrc"; then
        echo "" >> "$HOME/.zshrc"
        echo "# PARA CLI Completion" >> "$HOME/.zshrc"
        echo "fpath=(~/.zsh/completions \$fpath)" >> "$HOME/.zshrc"
        echo "autoload -U compinit && compinit" >> "$HOME/.zshrc"
    fi
    
    echo "${fg[green]}✅ Completion instalado exitosamente!${reset_color}"
    echo "${fg[yellow]}🔄 Recarga tu terminal o ejecuta: source ~/.zshrc${reset_color}"
}

# Función para mostrar ayuda
show_completion_help() {
    echo "${fg[blue]}PARA CLI Zsh Completion${reset_color}"
    echo ""
    echo "${fg[green]}Uso:${reset_color}"
    echo "  ./para_cli.py <TAB>          # Mostrar todos los comandos"
    echo "  ./para_cli.py re<TAB>        # Completar 're' → 'reclassify-all'"
    echo "  ./para_cli.py classify<TAB>  # Mostrar opciones de classify"
    echo ""
    echo "${fg[green]}Comandos cortos:${reset_color}"
    echo "  re  → reclassify-all"
    echo "  cl  → classify"
    echo "  an  → analyze"
    echo "  pl  → plugins"
    echo "  ov  → obsidian-vault"
    echo ""
    echo "${fg[green]}Prompts AI:${reset_color}"
    echo "  ./para_cli.py 're clasifica todas mis notas'"
    echo "  ./para_cli.py 'muéstrame los plugins'"
    echo ""
    echo "${fg[green]}Instalación:${reset_color}"
    echo "  ./para_zsh_completion.sh install"
}

# Manejar argumentos del script
case "$1" in
    install)
        install_para_completion
        ;;
    help|--help|-h)
        show_completion_help
        ;;
    *)
        # Registrar la función de completion
        compdef _para_cli para_cli.py
        compdef _para_cli ./para_cli.py
        ;;
esac 