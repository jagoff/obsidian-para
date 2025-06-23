#!/usr/bin/env zsh

# PARA Setup for ZSH - Optimized for macOS
# Leverages ZSH native features and arrays

setopt extended_glob null_glob

# Colors for ZSH
autoload -U colors && colors
GREEN="%{$fg[green]%}"
BLUE="%{$fg[blue]%}" 
RED="%{$fg[red]%}"
YELLOW="%{$fg[yellow]%}"
BOLD="%{$terminfo[bold]%}"
RESET="%{$reset_color%}"

print_header() {
    clear
    print -P "${BOLD}${BLUE}"
    print "╔════════════════════════════════════════════════════════════╗"
    print "║               🚀 PARA ZSH SETUP 🚀                        ║"
    print "║                                                            ║"
    print "║  ⚡ Optimized for macOS + ZSH                             ║"
    print "║  🧠 Smart PARA organization                                ║"
    print "║  📁 Based on Tiago Forte's examples                       ║"
    print "║  ⏱️  Complete setup in under 2 minutes                    ║"
    print "╚════════════════════════════════════════════════════════════╝"
    print -P "${RESET}\n"
}

print_status() { print -P "${BLUE}[INFO]${RESET} $1" }
print_success() { print -P "${GREEN}[✓]${RESET} $1" }
print_error() { print -P "${RED}[✗]${RESET} $1" }

find_obsidian_vault() {
    print -P "${BOLD}🔍 Finding your Obsidian vault...${RESET}"
    
    # ZSH array of search paths (more efficient)
    local search_paths=(
        "$HOME/Documents"
        "$HOME/Desktop"
        "$HOME/Obsidian"
        "$HOME/iCloud Drive (Archive)/Documents"
        "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
        "/Users/Shared"
    )
    
    # ZSH associative array for found vaults
    typeset -A found_vaults
    local vault_count=0
    
    # Use ZSH globbing to find vaults efficiently
    for search_path in $search_paths; do
        if [[ -d "$search_path" ]]; then
            # ZSH glob pattern to find .obsidian directories
            for obsidian_dir in "$search_path"/**/.obsidian(N/); do
                local vault_dir="${obsidian_dir:h}"
                local md_files=("$vault_dir"/**/*.md(N))
                local md_count=${#md_files}
                
                if (( md_count > 0 )); then
                    vault_count=$((vault_count + 1))
                    found_vaults[$vault_count]="$vault_dir|$md_count"
                fi
            done
        fi
    done
    
    if (( ${#found_vaults} == 0 )); then
        print_error "No Obsidian vaults found automatically"
        print "Please enter your vault path:"
        read "user_vault?Vault path: "
        
        if [[ -d "$user_vault" && -d "$user_vault/.obsidian" ]]; then
            VAULT_PATH="$user_vault"
            print_success "Using vault: ${VAULT_PATH:t}"
        else
            print_error "Invalid vault path"
            exit 1
        fi
    else
        print_success "Found ${#found_vaults} vault(s):"
        
        # Display found vaults
        for i in {1..${#found_vaults}}; do
            local vault_info=(${(s:|:)found_vaults[$i]})
            local vault_path="$vault_info[1]"
            local file_count="$vault_info[2]"
            print "  $i. ${vault_path:t} ($file_count files)"
            print "     Path: $vault_path"
        done
        
        # Auto-select vault with most files
        local max_files=0
        local best_vault=""
        
        for i in {1..${#found_vaults}}; do
            local vault_info=(${(s:|:)found_vaults[$i]})
            local vault_path="$vault_info[1]"
            local file_count="$vault_info[2]"
            
            if (( file_count > max_files )); then
                max_files=$file_count
                best_vault="$vault_path"
            fi
        done
        
        VAULT_PATH="$best_vault"
        print -P "\n${BOLD}🎯 Selected: ${VAULT_PATH:t} ($max_files files)${RESET}"
    fi
}

create_para_structure() {
    print -P "\n${BOLD}📁 Creating PARA structure...${RESET}"
    
    cd "$VAULT_PATH" || exit 1
    
    # PARA structure based on Tiago Forte's examples
    # Using ZSH parameter expansion for clean code
    local para_structure=(
        "00-inbox"
        "01-projects/aws-cloud"
        "01-projects/client-work" 
        "01-projects/internal"
        "01-projects/personal"
        "02-areas/team-leadership"
        "02-areas/cost-management"
        "02-areas/security-compliance"
        "02-areas/performance-optimization"
        "02-areas/professional-development"
        "03-resources/aws-architecture"
        "03-resources/best-practices"
        "03-resources/troubleshooting"
        "03-resources/industry-trends"
        "03-resources/tools-and-techniques"
        "04-archives/completed-2024"
        "04-archives/completed-2023"
        "04-archives/reference-materials"
        "templates"
    )
    
    # Create all directories efficiently
    for dir in $para_structure; do
        mkdir -p "$dir"
    done
    
    print_success "PARA structure created (${#para_structure} folders)"
}

classify_content() {
    local content="$1"
    local filename="$2"
    
    # Convert to lowercase for analysis
    local lower_content="${content:l}"
    local lower_filename="${filename:l}"
    
    # Project indicators (following Tiago's methodology)
    if [[ "$lower_content" =~ (deadline|project|task|todo|deliverable|sprint|milestone|goal) ]] ||
       [[ "$lower_content" =~ (\-\ \[\ \]|\-\ \[x\]|due\ date) ]] ||
       [[ "$lower_content" =~ [0-9]{4}-[0-9]{2}-[0-9]{2} ]] ||
       [[ "$lower_filename" =~ (project|task|sprint) ]]; then
        
        # Subcategorize projects
        if [[ "$lower_content" =~ (aws|ec2|rds|s3|lambda|cloud|terraform|kubernetes) ]]; then
            print "01-projects/aws-cloud"
        elif [[ "$lower_content" =~ (client|customer|external) ]]; then
            print "01-projects/client-work"
        elif [[ "$lower_content" =~ (internal|company|team) ]]; then
            print "01-projects/internal"
        else
            print "01-projects/personal"
        fi
        return
    fi
    
    # Area indicators (ongoing responsibilities)
    if [[ "$lower_content" =~ (area|responsibility|team|management|ongoing|process|kpi|metric|standard) ]] ||
       [[ "$lower_filename" =~ (area|management|team|process) ]]; then
        
        # Subcategorize areas
        if [[ "$lower_content" =~ (cost|budget|financial|expense) ]]; then
            print "02-areas/cost-management"
        elif [[ "$lower_content" =~ (security|compliance|audit|policy) ]]; then
            print "02-areas/security-compliance"
        elif [[ "$lower_content" =~ (team|people|leadership|hiring|1on1) ]]; then
            print "02-areas/team-leadership"
        elif [[ "$lower_content" =~ (performance|optimization|monitoring|metrics) ]]; then
            print "02-areas/performance-optimization"
        elif [[ "$lower_content" =~ (learning|development|skill|training|certification) ]]; then
            print "02-areas/professional-development"
        else
            print "02-areas/team-leadership"
        fi
        return
    fi
    
    # Resource indicators (reference materials)
    if [[ "$lower_content" =~ (guide|reference|documentation|tutorial|pattern|template|example|how.to|best.practice) ]] ||
       [[ "$lower_filename" =~ (guide|reference|template|pattern|example) ]]; then
        
        # Subcategorize resources
        if [[ "$lower_content" =~ (aws|cloud|architecture|infrastructure) ]]; then
            print "03-resources/aws-architecture"
        elif [[ "$lower_content" =~ (troubleshoot|debug|error|fix|solution|problem) ]]; then
            print "03-resources/troubleshooting"
        elif [[ "$lower_content" =~ (tool|software|app|utility) ]]; then
            print "03-resources/tools-and-techniques"
        elif [[ "$lower_content" =~ (trend|industry|future|market) ]]; then
            print "03-resources/industry-trends"
        else
            print "03-resources/best-practices"
        fi
        return
    fi
    
    # Default to archives
    print "04-archives/reference-materials"
}

organize_files() {
    print -P "\n${BOLD}🧠 Organizing files with intelligent classification...${RESET}"
    
    # Create backup with timestamp
    local backup_dir="_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    print_status "Backup directory: $backup_dir"
    
    # Find markdown files to organize (excluding PARA structure)
    local exclude_patterns=(
        "00-inbox/*"
        "01-projects/*" 
        "02-areas/*"
        "03-resources/*"
        "04-archives/*"
        "templates/*"
        "$backup_dir/*"
    )
    
    # ZSH glob to find files (excluding our new structure)
    local md_files=()
    for file in **/*.md(N); do
        local skip=false
        for pattern in $exclude_patterns; do
            if [[ "$file" == $pattern ]]; then
                skip=true
                break
            fi
        done
        
        if [[ "$skip" == false ]]; then
            md_files+=("$file")
        fi
    done
    
    print_status "Found ${#md_files} files to organize"
    
    # Initialize counters using ZSH associative array
    typeset -A category_counts
    category_counts=(
        "01-projects" 0
        "02-areas" 0  
        "03-resources" 0
        "04-archives" 0
    )
    
    # Process each file
    local processed=0
    for file in $md_files; do
        if [[ ! -f "$file" ]]; then continue; fi
        
        local filename="${file:t}"
        processed=$((processed + 1))
        
        # Show progress
        print -n "[$processed/${#md_files}] Processing $filename... "
        
        # Create backup
        local backup_path="$backup_dir/$file"
        mkdir -p "${backup_path:h}"
        cp "$file" "$backup_path" 2>/dev/null
        
        # Read file content (first 800 chars for better analysis)
        local content=""
        if [[ -r "$file" ]]; then
            content="$(head -c 800 "$file" 2>/dev/null)"
        fi
        
        # Classify content
        local target_dir="$(classify_content "$content" "$filename")"
        
        # Extract main category for counting
        local main_category="${target_dir%%/*}"
        category_counts[$main_category]=$((category_counts[$main_category] + 1))
        
        # Move file with conflict resolution
        local target_file="$target_dir/$filename"
        local counter=1
        
        while [[ -f "$target_file" ]]; do
            local name_base="${filename%.*}"
            local extension="${filename##*.}"
            
            if [[ "$name_base" == "$extension" ]]; then
                # No extension
                target_file="$target_dir/${filename}_${counter}"
            else
                target_file="$target_dir/${name_base}_${counter}.${extension}"
            fi
            counter=$((counter + 1))
        done
        
        # Ensure target directory exists and move file
        mkdir -p "$target_dir"
        mv "$file" "$target_file" 2>/dev/null || cp "$file" "$target_file"
        
        # Show category assignment
        print "→ ${target_dir##*/}"
    done
    
    print ""
    print_success "Organization complete:"
    print "   📋 Projects: ${category_counts[01-projects]} files"
    print "   🎯 Areas: ${category_counts[02-areas]} files"
    print "   📚 Resources: ${category_counts[03-resources]} files" 
    print "   🗂️ Archives: ${category_counts[04-archives]} files"
    print "   💾 Backup: $backup_dir"
}

create_dashboard_and_templates() {
    print -P "\n${BOLD}📊 Creating dashboard and templates...${RESET}"
    
    # Count files in each category
    typeset -A file_counts
    file_counts=(
        "inbox" "$(print 00-inbox/**/*.md(N) | wc -w)"
        "projects" "$(print 01-projects/**/*.md(N) | wc -w)"
        "areas" "$(print 02-areas/**/*.md(N) | wc -w)"
        "resources" "$(print 03-resources/**/*.md(N) | wc -w)"
        "archives" "$(print 04-archives/**/*.md(N) | wc -w)"
        "templates" "$(print templates/**/*.md(N) | wc -w)"
    )
    
    # Create main dashboard
    cat > "_para_dashboard.md" << EOF
---
tags: ["para", "dashboard", "tiago-forte"]
created: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

# 🎛️ PARA Dashboard

> **Auto-organized on $(date '+%Y-%m-%d %H:%M:%S')** using Tiago Forte's PARA Method

## 🚀 Quick Navigation
- [[00-inbox/]] - 📥 Quick capture (${file_counts[inbox]} files)
- [[01-projects/]] - 📋 Active projects (${file_counts[projects]} files)
- [[02-areas/]] - 🎯 Areas of responsibility (${file_counts[areas]} files)
- [[03-resources/]] - 📚 Knowledge resources (${file_counts[resources]} files)
- [[04-archives/]] - 🗂️ Completed items (${file_counts[archives]} files)
- [[templates/]] - 📝 Templates (${file_counts[templates]} files)

## 📊 Vault Overview
\`\`\`
📁 $(basename "$VAULT_PATH")
├── 📥 00-inbox/        ${file_counts[inbox]} files
├── 📋 01-projects/     ${file_counts[projects]} files
│   ├── aws-cloud/
│   ├── client-work/
│   ├── internal/
│   └── personal/
├── 🎯 02-areas/        ${file_counts[areas]} files
│   ├── team-leadership/
│   ├── cost-management/
│   ├── security-compliance/
│   ├── performance-optimization/
│   └── professional-development/
├── 📚 03-resources/    ${file_counts[resources]} files
│   ├── aws-architecture/
│   ├── best-practices/
│   ├── troubleshooting/
│   ├── industry-trends/
│   └── tools-and-techniques/
├── 🗂️ 04-archives/     ${file_counts[archives]} files
└── 📝 templates/       ${file_counts[templates]} files
\`\`\`

## 🎯 Today's Focus
- [ ] Review active projects in [[01-projects/]]
- [ ] Check area KPIs in [[02-areas/]]  
- [ ] Process new items in [[00-inbox/]]
- [ ] Update project progress and next actions

## 🚀 Quick Actions

### 📋 For Projects
- **New project:** Use [[templates/project_template.md]]
- **AWS projects:** [[01-projects/aws-cloud/]]
- **Client work:** [[01-projects/client-work/]]
- **Internal projects:** [[01-projects/internal/]]

### 🎯 For Areas
- **Team leadership:** [[02-areas/team-leadership/]]
- **Cost management:** [[02-areas/cost-management/]]
- **Security:** [[02-areas/security-compliance/]]
- **Performance:** [[02-areas/performance-optimization/]]
- **Development:** [[02-areas/professional-development/]]

### 📚 For Resources
- **AWS architecture:** [[03-resources/aws-architecture/]]
- **Best practices:** [[03-resources/best-practices/]]
- **Troubleshooting:** [[03-resources/troubleshooting/]]
- **Tools:** [[03-resources/tools-and-techniques/]]
- **Trends:** [[03-resources/industry-trends/]]

## 📝 Quick Capture Workflow
1. **Immediate capture** → [[00-inbox/]]
2. **Weekly review** → Organize into proper PARA categories  
3. **Monthly cleanup** → Move completed projects to [[04-archives/]]

## 🎊 PARA Method Principles (Tiago Forte)
1. **Projects** = Specific outcomes with deadlines
2. **Areas** = Standards to maintain over time
3. **Resources** = Future reference topics
4. **Archives** = Inactive items from other categories

## 🔗 Learn More
- [Building a Second Brain](https://www.buildingasecondbrain.com)
- [PARA Method Examples](https://www.buildingasecondbrain.com/para/examples)

---
**Last updated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)  
**System:** PARA Method by Tiago Forte  
**Setup:** ZSH Automated Organization
EOF

    # Create project template based on Tiago's methodology
    cat > "templates/project_template.md" << EOF
---
status: "planning"
priority: "medium"
deadline: ""
outcome: ""
team: []
budget: ""
tags: ["project", "para"]
created: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

# 🚀 [Project Name]

## 📋 Project Overview
**Specific Outcome:** [What exactly will be accomplished?]
**Deadline:** [When must this be completed?]
**Why This Matters:** [Context and importance]
**Success Criteria:** [How will we know it's done?]

## 🎯 Project Details
- **Status:** Planning
- **Priority:** Medium  
- **Deadline:** [YYYY-MM-DD]
- **Budget:** [Amount if applicable]
- **Team Members:** [Who's involved?]
- **Project Owner:** [Who's accountable?]

## 📅 Project Phases
| Phase | Key Deliverable | Target Date | Status | Notes |
|-------|----------------|-------------|---------|-------|
| 1. Planning | Project plan & requirements | | 🔄 Planning | |
| 2. Design | Architecture & specifications | | ⏳ Pending | |
| 3. Implementation | Working solution | | ⏳ Pending | |
| 4. Testing | Validated deliverable | | ⏳ Pending | |
| 5. Launch | Live/deployed outcome | | ⏳ Pending | |

## ✅ Next Actions
- [ ] Define specific success criteria
- [ ] Create detailed project timeline
- [ ] Identify required resources
- [ ] Assign team responsibilities
- [ ] Set up progress tracking

## 🚨 Risks & Mitigations
| Risk | Impact | Probability | Mitigation Strategy | Owner |
|------|--------|-------------|-------------------|-------|
| | High/Med/Low | High/Med/Low | | |

## 📝 Project Log
### $(date '+%Y-%m-%d')
- Project initiated
- Initial planning started

### Key Decisions
- 

### Lessons Learned
- 

## 🔗 Related PARA Items
- **Related Areas:** [[02-areas/]]
- **Useful Resources:** [[03-resources/]]
- **Reference Projects:** [[04-archives/]]

## 📎 Supporting Materials
- Documents:
- Links:
- Files:

---
**Project Template based on PARA Method**  
**Last updated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

    # Create area template
    cat > "templates/area_template.md" << EOF
---
type: "area"
standard: ""
review_frequency: "monthly"
kpi: ""
tags: ["area", "para", "responsibility"]
created: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

# 🎯 [Area Name]

## 📋 Area Definition
**Standard to Maintain:** [What standard needs to be upheld?]
**Why It Matters:** [Context and importance]
**Success Metrics:** [How do we measure success?]

## 🎯 Current Status
- **Overall Health:** [Red/Yellow/Green]
- **Key Metric:** [Current performance]
- **Last Review:** [Date]
- **Next Review:** [Date]

## 📊 Key Performance Indicators
| KPI | Target | Current | Trend | Notes |
|-----|--------|---------|--------|-------|
| | | | ↗️↘️➡️ | |

## 🔄 Recurring Activities
### Daily
- [ ] 

### Weekly  
- [ ] 

### Monthly
- [ ] Review area performance
- [ ] Update KPIs and metrics

### Quarterly
- [ ] Strategic review
- [ ] Process improvements

## 📝 Area Log
### $(date '+%Y-%m-%d')
- Area established
- Initial baseline set

## 🔗 Related PARA Items
- **Active Projects:** [[01-projects/]]
- **Supporting Resources:** [[03-resources/]]
- **Historical Data:** [[04-archives/]]

---
**Area Template based on PARA Method**  
**Last updated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

    # Create resource template
    cat > "templates/resource_template.md" << EOF
---
type: "resource"
topic: ""
relevance: "high"
tags: ["resource", "para", "reference"]
created: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

# 📚 [Resource Title]

## 📋 Resource Overview
**Topic:** [What is this about?]
**Why Saved:** [Why is this useful for future reference?]
**Potential Applications:** [How might this be used?]

## 🔑 Key Information
- **Source:** [Where did this come from?]
- **Date:** [When was this created/found?]
- **Relevance:** High/Medium/Low
- **Last Updated:** $(date '+%Y-%m-%d')

## 📝 Summary
[Brief summary of key points]

## 💡 Key Insights
- 
- 
- 

## 🔗 Related Links
- 
- 

## 🏷️ Tags for Future Discovery
[Add relevant tags to make this findable later]

## 🔗 Related PARA Items
- **Could Support Projects:** [[01-projects/]]
- **Relevant to Areas:** [[02-areas/]]
- **Related Resources:** [[03-resources/]]

---
**Resource Template based on PARA Method**  
**Last updated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

    print_success "Dashboard and templates created"
}

create_zsh_scripts() {
    print -P "\n${BOLD}⚙️ Creating ZSH automation scripts...${RESET}"
    
    # Advanced inbox organizer using ZSH features
    cat > "organize_inbox.zsh" << 'EOF'
#!/usr/bin/env zsh

# ZSH Inbox Organizer with advanced features
setopt extended_glob null_glob

autoload -U colors && colors
GREEN="%{$fg[green]%}"
BLUE="%{$fg[blue]%}"
RESET="%{$reset_color%}"

print -P "${BLUE}🔄 Organizing 00-inbox files...${RESET}"

# Find all markdown files in inbox using ZSH glob
local inbox_files=(00-inbox/**/*.md(N))

if (( ${#inbox_files} == 0 )); then
    print -P "${GREEN}📭 00-inbox is empty${RESET}"
    exit 0
fi

typeset -A category_counts
category_counts=("projects" 0 "areas" 0 "resources" 0 "archives" 0)

for file in $inbox_files; do
    if [[ ! -f "$file" ]]; then continue; fi
    
    local filename="${file:t}"
    print -n "📄 $filename → "
    
    # Read content for classification
    local content="$(head -c 500 "$file" 2>/dev/null)"
    local lower_content="${content:l}"
    
    # ZSH pattern matching for classification
    if [[ "$lower_content" =~ (deadline|task|project|todo|deliverable) ]] ||
       [[ "$lower_content" =~ (\-\ \[\ \]|\-\ \[x\]) ]]; then
        mv "$file" "01-projects/personal/"
        print "projects"
        category_counts[projects]=$((category_counts[projects] + 1))
    elif [[ "$lower_content" =~ (area|responsibility|ongoing|team|management) ]]; then
        mv "$file" "02-areas/team-leadership/"
        print "areas"
        category_counts[areas]=$((category_counts[areas] + 1))
    elif [[ "$lower_content" =~ (guide|reference|tutorial|pattern|resource) ]]; then
        mv "$file" "03-resources/best-practices/"
        print "resources"
        category_counts[resources]=$((category_counts[resources] + 1))
    else
        mv "$file" "04-archives/reference-materials/"
        print "archives"
        category_counts[archives]=$((category_counts[archives] + 1))
    fi
done

print -P "\n${GREEN}✅ Organized ${#inbox_files} files:${RESET}"
print "   📋 Projects: ${category_counts[projects]}"
print "   🎯 Areas: ${category_counts[areas]}"
print "   📚 Resources: ${category_counts[resources]}"
print "   🗂️ Archives: ${category_counts[archives]}"
EOF

    chmod +x "organize_inbox.zsh"
    
    # Enhanced status script with ZSH features
    cat > "para_status.zsh" << 'EOF'
#!/usr/bin/env zsh

# ZSH PARA Status with detailed breakdown
setopt extended_glob null_glob

autoload -U colors && colors
GREEN="%{$fg[green]%}"
BLUE="%{$fg[blue]%}"
YELLOW="%{$fg[yellow]%}"
CYAN="%{$fg[cyan]%}"
RESET="%{$reset_color%}"

print -P "${BLUE}📊 PARA Vault Status${RESET}"
print -P "${BLUE}=====================${RESET}"
print ""

# ZSH associative array for folder info
typeset -A folders
folders=(
    "00-inbox" "📥"
    "01-projects" "📋" 
    "02-areas" "🎯"
    "03-resources" "📚"
    "04-archives" "🗂️"
)

# Calculate totals
local total_files=0

for folder icon in ${(kv)folders}; do
    local files=($folder/**/*.md(N))
    local count=${#files}
    total_files=$((total_files + count))
    
    printf "%-15s %s %3d files\n" "$folder" "$icon" "$count"
    
    # Show subfolders for main categories
    if [[ "$folder" != "00-inbox" ]]; then
        for subfolder in $folder/*(N/); do
            local subfiles=($subfolder/**/*.md(N))
            local subcount=${#subfiles}
            if (( subcount > 0 )); then
                printf "  ├── %-20s %2d files\n" "${subfolder:t}" "$subcount"
            fi
        done
    fi
done

print ""
print -P "${CYAN}📈 Summary: $total_files total files organized${RESET}"
print ""
print -P "${YELLOW}🎯 Quick Actions:${RESET}"
print "  ./organize_inbox.zsh    - Organize 00-inbox files"
print "  ./para_status.zsh       - Show this status"
print "  ./para_maintenance.zsh  - Run weekly maintenance"
print ""
print -P "${GREEN}📊 Open _para_dashboard.md in Obsidian to start!${RESET}"
EOF

    chmod +x "para_status.zsh"
    
    # Create maintenance script
    cat > "para_maintenance.zsh" << 'EOF'
#!/usr/bin/env zsh

# Weekly PARA maintenance using ZSH
setopt extended_glob null_glob

autoload -U colors && colors
GREEN="%{$fg[green]%}"
BLUE="%{$fg[blue]%}"
YELLOW="%{$fg[yellow]%}"
RESET="%{$reset_color%}"

print -P "${BLUE}🔧 PARA Weekly Maintenance${RESET}"
print -P "${BLUE}===========================${RESET}"
print ""

# 1. Organize inbox
print -P "${YELLOW}1. Organizing inbox...${RESET}"
if [[ -x "./organize_inbox.zsh" ]]; then
    ./organize_inbox.zsh
else
    print "   organize_inbox.zsh not found"
fi

print ""

# 2. Check for completed projects
print -P "${YELLOW}2. Checking for completed projects...${RESET}"
local completed_projects=()

for project in 01-projects/**/*.md(N); do
    if grep -q -i "status.*completed\|completed.*true\|✅.*completed" "$project" 2>/dev/null; then
        completed_projects+=("$project")
    fi
done

if (( ${#completed_projects} > 0 )); then
    print "   Found ${#completed_projects} completed projects:"
    for project in $completed_projects; do
        print "   📋 ${project:t}"
        
        # Ask if user wants to archive
        print -n "   Archive this project? (y/n): "
        read -k1 response
        print ""
        
        if [[ "$response" == "y" || "$response" == "Y" ]]; then
            local archive_path="04-archives/completed-2024/${project:t}"
            mv "$project" "$archive_path"
            print -P "   ${GREEN}✅ Archived to $archive_path${RESET}"
        fi
    done
else
    print "   No completed projects found"
fi

print ""

# 3. Clean up empty folders
print -P "${YELLOW}3. Cleaning up empty folders...${RESET}"
local empty_dirs=()

for dir in **/*(N/); do
    if [[ -d "$dir" && -z "$(ls -A "$dir" 2>/dev/null)" ]]; then
        empty_dirs+=("$dir")
    fi
done

if (( ${#empty_dirs} > 0 )); then
    print "   Found ${#empty_dirs} empty directories:"
    for dir in $empty_dirs; do
        print "   📁 $dir"
        rmdir "$dir" 2>/dev/null && print -P "   ${GREEN}✅ Removed${RESET}"
    done
else
    print "   No empty directories found"
fi

print ""

# 4. Update dashboard with current counts
print -P "${YELLOW}4. Updating dashboard...${RESET}"

# Count files using ZSH
typeset -A file_counts
file_counts=(
    "inbox" "$(print 00-inbox/**/*.md(N) | wc -w)"
    "projects" "$(print 01-projects/**/*.md(N) | wc -w)"
    "areas" "$(print 02-areas/**/*.md(N) | wc -w)"
    "resources" "$(print 03-resources/**/*.md(N) | wc -w)"
    "archives" "$(print 04-archives/**/*.md(N) | wc -w)"
)

# Update last updated time in dashboard
if [[ -f "_para_dashboard.md" ]]; then
    sed -i.bak "s/Last updated:.*/Last updated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)/" "_para_dashboard.md"
    rm "_para_dashboard.md.bak" 2>/dev/null
    print -P "   ${GREEN}✅ Dashboard updated${RESET}"
fi

print ""
print -P "${GREEN}🎉 Weekly maintenance complete!${RESET}"
print ""
print -P "${BLUE}📊 Current Status:${RESET}"
print "   📥 Inbox: ${file_counts[inbox]} files"
print "   📋 Projects: ${file_counts[projects]} files"
print "   🎯 Areas: ${file_counts[areas]} files"
print "   📚 Resources: ${file_counts[resources]} files"
print "   🗂️ Archives: ${file_counts[archives]} files"
EOF

    chmod +x "para_maintenance.zsh"

    print_success "ZSH automation scripts created"
}

display_completion() {
    print -P "\n${BOLD}${GREEN}"
    print "╔════════════════════════════════════════════════════════════╗"
    print "║                  🎉 ZSH SETUP COMPLETE! 🎉                ║"
    print "╚════════════════════════════════════════════════════════════╝"
    print -P "${RESET}"
    
    print -P "${BOLD}🎯 YOUR VAULT IS NOW ORGANIZED WITH PARA:${RESET}"
    
    cd "$VAULT_PATH" || exit 1
    
    # Use ZSH to count files efficiently
    typeset -A final_counts
    final_counts=(
        "00-inbox" "$(print 00-inbox/**/*.md(N) | wc -w)"
        "01-projects" "$(print 01-projects/**/*.md(N) | wc -w)"
        "02-areas" "$(print 02-areas/**/*.md(N) | wc -w)"
        "03-resources" "$(print 03-resources/**/*.md(N) | wc -w)"
        "04-archives" "$(print 04-archives/**/*.md(N) | wc -w)"
    )
    
    for folder in "00-inbox" "01-projects" "02-areas" "03-resources" "04-archives"; do
        local count=${final_counts[$folder]}
        case $folder in
            "00-inbox") print "  📥 inbox: $count files" ;;
            "01-projects") print "  📋 projects: $count files" ;;
            "02-areas") print "  🎯 areas: $count files" ;;
            "03-resources") print "  📚 resources: $count files" ;;
            "04-archives") print "  🗂️ archives: $count files" ;;
        esac
    done
    
    print ""
    print -P "${BOLD}🚀 NEXT STEPS:${RESET}"
    print "  1. Open Obsidian"
    print "  2. Navigate to: ${VAULT_PATH:t}"
    print "  3. Start with: _para_dashboard.md" 
    print "  4. Explore templates/ for new content"
    print ""
    
    print -P "${BOLD}📱 ZSH-POWERED WORKFLOW:${RESET}"
    print "  • Quick capture → 00-inbox/"
    print "  • Weekly organize → ./organize_inbox.zsh"
    print "  • Check status → ./para_status.zsh"
    print "  • Weekly maintenance → ./para_maintenance.zsh"
    print ""
    
    print -P "${BOLD}🎊 PARA METHOD RESOURCES:${RESET}"
    print "  • 📺 Video: https://www.youtube.com/watch?v=445yxZbj4H4"
    print "  • 📚 Examples: https://www.buildingasecondbrain.com/para/examples"
    print "  • 🏠 Official site: https://www.buildingasecondbrain.com"
    print ""
    
    print -P "${BOLD}✨ ENJOY YOUR ZSH-OPTIMIZED PRODUCTIVITY SYSTEM!${RESET}"
    
    # Show final status using our new ZSH script
    print ""
    if [[ -x "./para_status.zsh" ]]; then
        ./para_status.zsh
    fi
}

# Main execution function
main() {
    print_header
    
    print -P "${BOLD}🚀 Starting ZSH-optimized PARA setup...${RESET}\n"
    
    find_obsidian_vault
    create_para_structure  
    organize_files
    create_dashboard_and_templates
    create_zsh_scripts
    display_completion
}

# ZSH-specific error handling
zshexit() {
    print -P "\n${YELLOW}⚠️  Setup interrupted. Your files are safely backed up.${RESET}"
    exit 130
}

# Ensure we're running in ZSH
if [[ -z "$ZSH_VERSION" ]]; then
    print "This script requires ZSH. Please run: zsh para_zsh_setup.zsh"
    exit 1
fi

# Run main function
main "$@"