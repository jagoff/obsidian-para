import streamlit as st
import plotly.express as px
import os
import json
from pathlib import Path
from chromadb_wrapper import ChromaDBWrapper
import pandas as pd

# --- CONFIGURACIÓN DE TEMA ---
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

THEME = st.session_state["theme"]

# Bootstrap palette
BOOTSTRAP_COLORS = {
    "dark": {
        "bg": "#181A1B",
        "fg": "#F8F9FA",
        "primary": "#0d6efd",
        "secondary": "#6c757d",
        "success": "#198754",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "info": "#0dcaf0",
        "light": "#f8f9fa",
        "muted": "#6c757d"
    },
    "light": {
        "bg": "#f8f9fa",
        "fg": "#181A1B",
        "primary": "#0d6efd",
        "secondary": "#6c757d",
        "success": "#198754",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "info": "#0dcaf0",
        "light": "#f8f9fa",
        "muted": "#6c757d"
    }
}

st.set_page_config(
    page_title="ChromaDB Admin Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- HEADER Y TEMA ---
st.markdown(f"""
    <style>
    body {{
        background-color: {BOOTSTRAP_COLORS[THEME]['bg']};
        color: {BOOTSTRAP_COLORS[THEME]['fg']};
    }}
    .stApp {{
        background-color: {BOOTSTRAP_COLORS[THEME]['bg']};
    }}
    .stButton>button {{
        background-color: {BOOTSTRAP_COLORS[THEME]['primary']};
        color: white;
        border-radius: 4px;
        border: none;
        padding: 0.5em 1.2em;
        font-weight: 600;
    }}
    .stButton>button:hover {{
        background-color: {BOOTSTRAP_COLORS[THEME]['info']};
        color: {BOOTSTRAP_COLORS[THEME]['bg']};
    }}
    .stDataFrame {{
        background-color: {BOOTSTRAP_COLORS[THEME]['bg']};
        color: {BOOTSTRAP_COLORS[THEME]['fg']};
    }}
    </style>
""", unsafe_allow_html=True)

st.title("🗂️ ChromaDB Admin Dashboard")
st.caption("Visualiza, explora y audita cualquier base de datos ChromaDB. Inspirado en Bootstrap. ")

# --- TEMA SWITCHER ---
col1, col2 = st.columns([1, 8])
with col1:
    if st.button("🌙" if THEME == "dark" else "☀️", help="Cambiar tema"):
        st.session_state["theme"] = "light" if THEME == "dark" else "dark"
        st.experimental_rerun()

# --- SELECCIÓN DE BASE DE DATOS ---
st.sidebar.header("Configuración")
db_path = st.sidebar.text_input("Ruta a la base ChromaDB", value="./para_chroma_db")

# --- CARGA DE DATOS REALES ---
@st.cache_data(show_spinner=True)
def load_chroma_data(db_path):
    try:
        db = ChromaDBWrapper(db_path)
        notes = db.get_all_notes_metadata()
        feedback = db.get_feedback_notes()
        return notes, feedback
    except Exception as e:
        st.error(f"Error cargando la base: {e}")
        return [], []

data, feedback = load_chroma_data(db_path)

# --- PROCESAMIENTO Y MÉTRICAS DE EFICIENCIA PARA ---
def para_metrics(notes):
    if not notes:
        return {}, pd.DataFrame()
    df = pd.DataFrame(notes)
    # Carpeta real: inferida del path
    df["real_folder"] = df["path"].apply(lambda p: Path(p).parent.name if "path" in df.columns else "")
    # Predicción: usar predicted_category o category
    df["predicted"] = df.get("predicted_category", df.get("category", "")).str.lower()
    # Mapeo de carpetas a categorías
    folder_map = {
        "01-projects": "projects",
        "02-areas": "areas",
        "03-resources": "resources",
        "04-archive": "archive",
        "00-inbox": "inbox"
    }
    df["real_category"] = df["real_folder"].map(folder_map).fillna(df["real_folder"])
    # Correcta si coincide
    df["correct"] = df["real_category"] == df["predicted"]
    # Métricas
    total = len(df)
    correct = df["correct"].sum()
    percent = 100 * correct / total if total else 0
    by_cat = df.groupby("real_category")["correct"].mean().to_dict()
    # Notas desordenadas
    wrong_notes = df[~df["correct"]]
    # Feedback
    feedback_count = df.get("feedback", pd.Series([False]*total)).sum()
    # Objetivos/pilares
    pillars = {
        "Inbox vacío": 100 * (1 - (df["real_category"] == "inbox").mean()),
        "Proyectos bien clasificados": 100 * df[df["real_category"] == "projects"]["correct"].mean() if (df["real_category"] == "projects").any() else 100,
        "Correcciones mínimas": 100 * (1 - feedback_count / total) if total else 100,
    }
    return {
        "total": total,
        "correct": correct,
        "percent": percent,
        "by_cat": by_cat,
        "wrong_notes": wrong_notes,
        "feedback_count": feedback_count,
        "pillars": pillars,
        "df": df
    }, df

metrics, df = para_metrics(data)

# --- TABS PRINCIPALES ---
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Objetivos & Acciones", "📋 Notas", "📊 Estadísticas", "📝 Feedback", "🔍 Vecinos"
])

# --- TAB 0: OBJETIVOS & ACCIONES ---
with tab0:
    st.subheader("Grandes objetivos y salud del sistema PARA")
    if metrics:
        st.metric("% Notas correctamente clasificadas", f"{metrics['percent']:.1f}%")
        st.markdown("### Pilares/Objetivos")
        for k, v in metrics["pillars"].items():
            st.progress(v/100, text=f"{k}: {v:.1f}%")
        st.markdown("---")
        st.markdown("### Acciones sugeridas")
        if metrics["pillars"]["Inbox vacío"] < 100:
            st.warning("Mover notas fuera de Inbox para vaciarlo.")
        if metrics["pillars"]["Correcciones mínimas"] < 100:
            st.info(f"Revisar feedback/correcciones pendientes: {metrics['feedback_count']}")
        if len(metrics["wrong_notes"]):
            st.error(f"Hay {len(metrics['wrong_notes'])} notas desordenadas. ¡Revisa y corrige!")
    else:
        st.info("No hay datos para calcular métricas.")

# --- TAB 1: NOTAS ---
with tab1:
    st.subheader("Notas en la base ChromaDB")
    if not df.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            cat = st.selectbox("Categoría", ["Todas"] + sorted(df["real_category"].unique().tolist()))
        with col2:
            fb = st.selectbox("Feedback", ["Todos", "Con feedback", "Sin feedback"])
        with col3:
            search = st.text_input("Buscar por nombre")
        filtered = df.copy()
        if cat != "Todas":
            filtered = filtered[filtered["real_category"] == cat]
        if fb == "Con feedback":
            filtered = filtered[filtered.get("feedback", False) == True]
        elif fb == "Sin feedback":
            filtered = filtered[filtered.get("feedback", False) == False]
        if search:
            filtered = filtered[filtered["filename"].str.contains(search, case=False)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        # Panel de detalles
        st.markdown("---")
        st.subheader("Detalle de nota")
        if not filtered.empty:
            selected = st.selectbox("Selecciona una nota", filtered["filename"].tolist())
            note = filtered[filtered["filename"] == selected].iloc[0]
            st.markdown(f"**Archivo:** {note['filename']}")
            st.markdown(f"**Categoría real:** `{note['real_category']}`")
            st.markdown(f"**Predicción:** `{note['predicted']}`")
            st.markdown(f"**Palabras:** {note.get('word_count', note.get('words', 'N/A'))}")
            st.markdown(f"**Feedback:** {'✅' if note.get('feedback', False) else '—'}")
            st.markdown(f"**Creada:** {note.get('created', note.get('last_updated_utc', 'N/A'))}")
            st.code(note.get('content', ''), language="markdown")
            # Explicación, confianza, vecinos
            if 'explanation' in note:
                st.markdown(f"**Explicación:** {note['explanation']}")
            if 'confidence' in note:
                st.markdown(f"**Confianza:** {note['confidence']:.2f}")
            if 'neighbors' in note:
                st.markdown(f"**Vecinos:** {note['neighbors']}")
    else:
        st.info("No se encontraron notas en la base de datos.")

# --- TAB 2: ESTADÍSTICAS ---
with tab2:
    st.subheader("Distribución de categorías")
    if not df.empty:
        cat_counts = df["real_category"].value_counts().reset_index()
        cat_counts.columns = ["Categoría", "Cantidad"]
        fig = px.bar(cat_counts, x="Categoría", y="Cantidad", color="Categoría",
                     color_discrete_sequence=[BOOTSTRAP_COLORS[THEME]["primary"], BOOTSTRAP_COLORS[THEME]["info"], BOOTSTRAP_COLORS[THEME]["success"], BOOTSTRAP_COLORS[THEME]["danger"], BOOTSTRAP_COLORS[THEME]["warning"]])
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        st.subheader("Histograma de longitud de notas")
        if "word_count" in df.columns:
            fig2 = px.histogram(df, x="word_count", nbins=10, title="Distribución de palabras por nota", color_discrete_sequence=[BOOTSTRAP_COLORS[THEME]["primary"]])
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No hay datos para mostrar estadísticas.")

# --- TAB 3: FEEDBACK ---
with tab3:
    st.subheader("Notas con feedback/corrección")
    if not df.empty:
        fb_notes = df[df.get("feedback", False) == True]
        st.dataframe(fb_notes, use_container_width=True, hide_index=True)
        st.markdown(f"Total: **{len(fb_notes)}** notas con feedback.")
    else:
        st.info("No hay notas con feedback registradas.")

# --- TAB 4: VECINOS ---
with tab4:
    st.subheader("Navegador de vecinos semánticos")
    if not df.empty:
        selected = st.selectbox("Selecciona una nota para ver vecinos", df["filename"].tolist())
        note = df[df["filename"] == selected].iloc[0]
        db = ChromaDBWrapper(db_path)
        neighbors = db.search_similar_notes(note.get("content", ""), n_results=5)
        st.markdown("**Vecinos más cercanos:**")
        for meta, dist in neighbors:
            st.markdown(f"- {meta.get('filename', 'N/A')} | Categoría: {meta.get('category', 'N/A')} | Distancia: {dist:.3f}")
    else:
        st.info("No hay notas para mostrar vecinos.")

st.markdown("<hr style='margin-top:2em;margin-bottom:1em;border:1px solid #333;'>", unsafe_allow_html=True)
st.caption("ChromaDB Admin Dashboard • Visual Bootstrap • MIT License • 2024") 