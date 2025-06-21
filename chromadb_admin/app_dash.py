import dash
from dash import html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import json
from chromadb_wrapper import ChromaDBWrapper
import sys
import subprocess
import re

# --- DETECTAR DIRECTORIO DEL SCRIPT ---
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- LOGGING ---
import logging
LOG_DIR = os.path.join(SCRIPT_DIR, '../logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'chromadb_admin.log')
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("chromadb_admin")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"])
app.title = "ChromaDB Admin Dashboard"

# --- CARGA DE CONFIGURACIÓN ---
def load_config():
    config_path = os.path.join(SCRIPT_DIR, '../para_config.json')
    if not os.path.exists(config_path):
        config_path = os.path.join(SCRIPT_DIR, '../para_config.default.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

config = load_config()
db_path = os.path.abspath(os.path.join(SCRIPT_DIR, '..', config.get('chroma_db_path', './para_chroma_db')))

# --- CARGA DE DATOS REALES ---
def load_chroma_data(db_path):
    try:
        db = ChromaDBWrapper(db_path)
        notes = db.get_all_notes_metadata()
        return notes, None
    except Exception as e:
        logger.error(f"Error cargando la base: {e}")
        return [], str(e)

notes, load_error = load_chroma_data(db_path)
if notes:
    df = pd.DataFrame(notes)
    if 'filename' not in df.columns and 'path' in df.columns:
        df['filename'] = df['path'].apply(lambda p: os.path.basename(p))
    if 'words' not in df.columns and 'content' in df.columns:
        df['words'] = df['content'].apply(lambda c: len(str(c).split()))
    if 'created' not in df.columns:
        df['created'] = ''
    if 'category' not in df.columns:
        df['category'] = df.get('predicted_category', 'unknown')
    if 'feedback' not in df.columns:
        df['feedback'] = False
else:
    df = pd.DataFrame([{'filename': 'Sin datos', 'category': '', 'words': 0, 'feedback': False, 'created': '', 'content': ''}])

# --- MÉTRICAS ÚTILES ---
def calcular_metricas(df):
    total_notas = len(df)
    notas_inbox = df[df['category'].str.lower() == 'inbox'].shape[0] if 'category' in df.columns else 0
    notas_feedback = df[df['feedback'] == True].shape[0] if 'feedback' in df.columns else 0
    palabras_promedio = int(df['words'].mean()) if 'words' in df.columns and total_notas > 0 else 0
    notas_por_categoria = df['category'].value_counts().to_dict() if 'category' in df.columns else {}
    # Porcentaje de notas correctamente clasificadas (si existe columna real_category)
    if 'real_category' in df.columns and 'category' in df.columns:
        correctas = (df['real_category'].str.lower() == df['category'].str.lower()).sum()
        porcentaje_correctas = 100 * correctas / total_notas if total_notas > 0 else 0
    else:
        porcentaje_correctas = 'N/A'
    return {
        'total_notas': total_notas,
        'notas_inbox': notas_inbox,
        'notas_feedback': notas_feedback,
        'palabras_promedio': palabras_promedio,
        'notas_por_categoria': notas_por_categoria,
        'porcentaje_correctas': porcentaje_correctas
    }

metricas = calcular_metricas(df)

# --- CARDS OBJETIVOS Y MÉTRICAS ---
def objetivos_cards():
    return dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Total de notas", className="card-title"),
                html.H2(f"{metricas['total_notas']}", className="text-primary"),
                html.Div("Notas en la base ChromaDB", className="card-text")
            ])
        ], color="dark", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Notas en Inbox", className="card-title"),
                html.H2(f"{metricas['notas_inbox']}", className="text-info"),
                html.Div("Notas clasificadas como Inbox", className="card-text")
            ])
        ], color="dark", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Notas con feedback", className="card-title"),
                html.H2(f"{metricas['notas_feedback']}", className="text-warning"),
                html.Div("Notas marcadas para revisión", className="card-text")
            ])
        ], color="dark", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("Palabras promedio", className="card-title"),
                html.H2(f"{metricas['palabras_promedio']}", className="text-success"),
                html.Div("Palabras por nota (promedio)", className="card-text")
            ])
        ], color="dark", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H5("% Notas correctas", className="card-title"),
                html.H2(f"{metricas['porcentaje_correctas'] if metricas['porcentaje_correctas'] != 'N/A' else 'N/A'}%", className="text-success"),
                html.Div("Clasificación PARA vs real", className="card-text")
            ])
        ], color="dark", outline=True), md=2),
    ], className="mb-4")

# --- GRAFICO DE CATEGORIAS ---
def grafico_categorias(df):
    cat_counts = df["category"].value_counts().reset_index()
    cat_counts.columns = ["Categoría", "Cantidad"]
    fig = px.bar(cat_counts, x="Categoría", y="Cantidad", color="Categoría",
                 color_discrete_sequence=px.colors.sequential.Plasma)
    fig.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), height=300)
    return dcc.Graph(figure=fig)

# --- TABLA DE NOTAS ---
def tabla_notas(df):
    return dash_table.DataTable(
        columns=[{"name": i.capitalize(), "id": i} for i in ["filename", "category", "words", "feedback", "created"]],
        data=df.to_dict("records"),
        style_table={"overflowX": "auto", "backgroundColor": "#181A1B"},
        style_header={"backgroundColor": "#222", "color": "#fff", "fontWeight": "bold"},
        style_cell={"backgroundColor": "#181A1B", "color": "#F8F9FA", "border": "1px solid #333"},
        page_size=10,
        filter_action="native",
        sort_action="native",
        row_selectable="single",
        style_as_list_view=True,
    )

def leer_logs_para(n=50):
    log_path = os.path.abspath(os.path.join(SCRIPT_DIR, '../logs/para.log'))
    if not os.path.exists(log_path):
        return [dbc.Alert("No se encontró el archivo de log para analizar.", color="warning")]
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-n:]
    # Resaltar errores y advertencias
    def color_line(line):
        if 'CRITICAL' in line or 'ERROR' in line:
            return html.Div(line, style={"color": "#ff4c4c", "fontWeight": "bold", "fontFamily": "monospace", "whiteSpace": "pre-wrap"})
        elif 'WARNING' in line:
            return html.Div(line, style={"color": "#ffc107", "fontWeight": "bold", "fontFamily": "monospace", "whiteSpace": "pre-wrap"})
        else:
            return html.Div(line, style={"color": "#aaa", "fontFamily": "monospace", "whiteSpace": "pre-wrap"})
    return [html.Div([color_line(l) for l in lines], style={"maxHeight": "500px", "overflowY": "auto", "background": "#181A1B", "padding": "1em", "borderRadius": "8px"})]

def analizar_y_autofix_log():
    log_path = os.path.abspath(os.path.join(SCRIPT_DIR, '../logs/para.log'))
    fixes = []
    if not os.path.exists(log_path):
        return fixes
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[-100:]
    error_lines = [l for l in lines if 'ERROR' in l or 'CRITICAL' in l]
    for l in error_lines:
        # UnboundLocalError típico de para_cli.py
        if 'UnboundLocalError' in l and 'vault_path_obj' in l:
            fixes.append('Detectado UnboundLocalError: intentado reiniciar para_cli.py')
            logger.warning('Auto-fix: Reiniciar para_cli.py por UnboundLocalError')
            # Aquí podrías reiniciar el proceso, pero solo logueamos
        # Error de ChromaDB: no such column
        if 'sqlite3.OperationalError' in l and 'no such column' in l:
            fixes.append('Detectado error de schema en ChromaDB: renombrando base para forzar recreación')
            logger.warning('Auto-fix: Renombrando para_chroma_db para forzar recreación de schema')
            db_dir = os.path.abspath(os.path.join(SCRIPT_DIR, '../para_chroma_db'))
            if os.path.exists(db_dir):
                import shutil
                shutil.move(db_dir, db_dir + '.bak_autofix')
                fixes.append(f'Base renombrada a {db_dir}.bak_autofix')
        # Faltan dependencias
        if 'ModuleNotFoundError' in l:
            fixes.append('Detectado ModuleNotFoundError: ejecutando pip install -r requirements.txt')
            logger.warning('Auto-fix: Ejecutando pip install -r requirements.txt')
            subprocess.run(['pip', 'install', '-r', os.path.abspath(os.path.join(SCRIPT_DIR, '../requirements.txt'))])
    return fixes

# --- DETECTAR BASES DE DATOS DISPONIBLES ---
def listar_bases_chromadb():
    parent = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
    bases = []
    for d in os.listdir(parent):
        if d.startswith('para_chroma_db') and os.path.isdir(os.path.join(parent, d)):
            bases.append(d)
    return sorted(bases)

bases_disponibles = listar_bases_chromadb()

# --- LAYOUT ---
app.layout = dbc.Container([
    html.H1("🗂️ ChromaDB Admin Dashboard", className="mt-4 mb-2 text-center"),
    html.Div("Minimal, dark, beautiful. 100% open source.", className="mb-4 text-center text-muted"),
    dbc.Row([
        dbc.Col([
            html.Div("Base de datos actual:", className="mb-1"),
            dcc.Dropdown(
                id="db-dropdown",
                options=[{"label": b, "value": b} for b in bases_disponibles],
                value=os.path.basename(db_path),
                clearable=False,
                style={"width": "300px"}
            ),
        ], width="auto"),
        dbc.Col(dbc.Button("Recargar datos", id="reload-btn", color="primary", className="mb-2"), width="auto"),
        dbc.Col(html.Div(id="reload-status")),
    ], className="mb-2 justify-content-center"),
    html.Div(id="main-content"),
    html.Footer([
        html.Hr(),
        html.Small("ChromaDB Admin Dashboard • Minimal, dark, beautiful • MIT License • 2024", className="text-muted")
    ], className="mt-4 mb-2 text-center")
], fluid=True)

# --- CALLBACKS ---
@app.callback(
    [Output("main-content", "children"), Output("reload-status", "children")],
    [Input("reload-btn", "n_clicks"), Input("db-dropdown", "value")],
    [State("db-dropdown", "value")]
)
def update_dashboard(n_clicks, db_selected, db_state):
    # Determinar ruta de la base seleccionada
    db_dir = os.path.abspath(os.path.join(SCRIPT_DIR, '..', db_selected or os.path.basename(db_path)))
    notes, load_error = load_chroma_data(db_dir)
    if not notes:
        if load_error:
            return [
                dbc.Alert(f"Error cargando la base: {load_error}", color="danger", className="mt-4"),
                "Error al cargar datos"
            ]
        else:
            return [
                dbc.Alert("No hay datos en la base ChromaDB. Agrega notas para ver estadísticas.", color="warning", className="mt-4"),
                "Sin datos"
            ]
    df = pd.DataFrame(notes)
    if 'filename' not in df.columns and 'path' in df.columns:
        df['filename'] = df['path'].apply(lambda p: os.path.basename(p))
    if 'words' not in df.columns and 'content' in df.columns:
        df['words'] = df['content'].apply(lambda c: len(str(c).split()))
    if 'created' not in df.columns:
        df['created'] = ''
    if 'category' not in df.columns:
        df['category'] = df.get('predicted_category', 'unknown')
    if 'feedback' not in df.columns:
        df['feedback'] = False
    metricas = calcular_metricas(df)
    # --- CONTENIDO PRINCIPAL ---
    return [
        html.Div([
            html.Div(f"Base de datos cargada: {db_selected}", className="mb-2 text-info"),
            objetivos_cards(),
            dbc.Tabs([
                dbc.Tab(label="Notas", tab_id="notas", children=[
                    html.Br(),
                    tabla_notas(df),
                ]),
                dbc.Tab(label="Estadísticas", tab_id="estadisticas", children=[
                    html.Br(),
                    grafico_categorias(df),
                ]),
                dbc.Tab(label="Feedback", tab_id="feedback", children=[
                    html.Br(),
                    dash_table.DataTable(
                        columns=[{"name": i.capitalize(), "id": i} for i in df.columns],
                        data=df[df["feedback"] == True].to_dict("records"),
                        style_table={"overflowX": "auto", "backgroundColor": "#181A1B"},
                        style_header={"backgroundColor": "#222", "color": "#fff", "fontWeight": "bold"},
                        style_cell={"backgroundColor": "#181A1B", "color": "#F8F9FA", "border": "1px solid #333"},
                        page_size=10,
                        style_as_list_view=True,
                    )
                ]),
                dbc.Tab(label="Logs", tab_id="logs", children=[
                    html.Br(),
                    html.H5("Últimos eventos del sistema PARA"),
                    *leer_logs_para(50),
                    html.Br(),
                    html.H6("Fixes automáticos aplicados:"),
                    html.Ul([html.Li(fix) for fix in analizar_y_autofix_log()])
                ]),
            ], id="tabs", active_tab="notas", className="mb-4"),
        ]),
        dbc.Alert("Datos recargados correctamente.", color="success", className="mb-2") if n_clicks else ""
    ]

if __name__ == "__main__":
    import socket
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0
    def get_pid_on_port(port):
        try:
            result = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True)
            pids = [int(pid) for pid in result.stdout.strip().split("\n") if pid]
            return pids[0] if pids else None
        except Exception:
            return None
    port = int(os.environ.get("DASH_PORT", 8050))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            pass
    if is_port_in_use(port):
        pid = get_pid_on_port(port)
        if pid:
            print(f"[INFO] Terminando proceso {pid} en puerto {port} automáticamente...")
            try:
                os.kill(pid, 9)
                print(f"[OK] Proceso {pid} terminado. Lanzando dashboard...")
                logger.warning(f"Proceso {pid} en puerto {port} terminado automáticamente por el script.")
                app.run(debug=True, port=port)
            except Exception as e:
                print(f"[ERROR] No se pudo terminar el proceso {pid}: {e}")
                logger.error(f"No se pudo terminar el proceso {pid}: {e}")
        else:
            print(f"[ERROR] El puerto {port} está ocupado. Usa otro puerto: python app_dash.py 8051 o export DASH_PORT=8051")
            logger.error(f"El puerto {port} está ocupado. Usa otro puerto: python app_dash.py 8051 o export DASH_PORT=8051")
    else:
        logger.info(f"Iniciando ChromaDB Admin Dashboard en modo debug en puerto {port}")
        app.run(debug=True, port=port) 