"""
paralib/learning_dashboard.py

Dashboard de Aprendizaje Autónomo - Visualización gráfica del progreso y mejora del sistema.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

from paralib.learning_system import PARA_Learning_System
from paralib.db import ChromaPARADatabase
from paralib.classification_log import get_feedback_notes

def create_learning_dashboard(vault_path: str):
    """Crea el dashboard de aprendizaje principal."""
    st.set_page_config(
        page_title="PARA Learning Dashboard",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("🧠 Sistema de Aprendizaje Autónomo PARA")
    st.markdown("### Dashboard de Progreso y Mejora Continua")
    
    # Inicializar sistema de aprendizaje
    db_path = f"{vault_path}/.para_db/chroma"
    db = ChromaPARADatabase(db_path=db_path)
    learning_system = PARA_Learning_System(db, vault_path)
    
    # Sidebar para controles
    st.sidebar.header("🎛️ Controles")
    
    # Selector de período
    period_options = {
        "Últimos 7 días": 7,
        "Últimos 30 días": 30,
        "Últimos 90 días": 90,
        "Todo el historial": 365
    }
    
    selected_period = st.sidebar.selectbox(
        "Período de análisis:",
        list(period_options.keys()),
        index=1
    )
    
    days = period_options[selected_period]
    
    # Obtener datos de progreso
    progress_data = learning_system.get_learning_progress(days)
    
    if 'error' in progress_data:
        st.error(progress_data['error'])
        return
    
    # Crear snapshot actual
    current_snapshot = learning_system.create_learning_snapshot()
    
    # Layout principal
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_accuracy_card(current_snapshot['metrics'])
    
    with col2:
        display_learning_velocity_card(current_snapshot['metrics'])
    
    with col3:
        display_confidence_card(current_snapshot['metrics'])
    
    with col4:
        display_improvement_card(current_snapshot['metrics'])
    
    # Gráficos principales
    st.markdown("---")
    st.subheader("📈 Tendencias de Aprendizaje")
    
    col1, col2 = st.columns(2)
    
    with col1:
        create_accuracy_trend_chart(progress_data)
    
    with col2:
        create_confidence_trend_chart(progress_data)
    
    # Gráficos adicionales
    col1, col2 = st.columns(2)
    
    with col1:
        create_learning_velocity_chart(progress_data)
    
    with col2:
        create_improvement_trend_chart(progress_data)
    
    # Análisis detallado
    st.markdown("---")
    st.subheader("🔍 Análisis Detallado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        display_category_performance(current_snapshot['category_performance'])
    
    with col2:
        display_model_performance(current_snapshot['model_performance'])
    
    # Insights y sugerencias
    st.markdown("---")
    st.subheader("💡 Insights de Aprendizaje")
    
    col1, col2 = st.columns(2)
    
    with col1:
        display_learning_insights(current_snapshot['learning_insights'])
    
    with col2:
        display_improvement_suggestions(current_snapshot['improvement_suggestions'])
    
    # Métricas avanzadas
    st.markdown("---")
    st.subheader("📊 Métricas Avanzadas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_semantic_coherence_card(current_snapshot['metrics'])
    
    with col2:
        display_category_balance_card(current_snapshot['metrics'])
    
    with col3:
        display_user_satisfaction_card(current_snapshot['metrics'])
    
    # Resumen de progreso
    st.markdown("---")
    st.subheader("🎯 Resumen de Progreso")
    
    display_progress_summary(progress_data)

def display_accuracy_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de precisión."""
    accuracy = metrics['accuracy_rate']
    
    # Determinar color basado en precisión
    if accuracy >= 90:
        color = "green"
        status = "Excelente"
    elif accuracy >= 80:
        color = "orange"
        status = "Buena"
    else:
        color = "red"
        status = "Necesita mejora"
    
    st.metric(
        label="🎯 Precisión",
        value=f"{accuracy:.1f}%",
        delta=f"{status}",
        delta_color="normal" if color != "red" else "inverse"
    )

def display_learning_velocity_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de velocidad de aprendizaje."""
    velocity = metrics['learning_velocity']
    
    if velocity >= 0.7:
        status = "Rápido"
        color = "normal"
    elif velocity >= 0.4:
        status = "Moderado"
        color = "normal"
    else:
        status = "Lento"
        color = "inverse"
    
    st.metric(
        label="🚀 Velocidad de Aprendizaje",
        value=f"{velocity:.2f}",
        delta=f"{status}",
        delta_color=color
    )

def display_confidence_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de correlación de confianza."""
    confidence = metrics['confidence_correlation']
    
    if confidence >= 0.8:
        status = "Alta"
        color = "normal"
    elif confidence >= 0.5:
        status = "Media"
        color = "normal"
    else:
        status = "Baja"
        color = "inverse"
    
    st.metric(
        label="🎲 Correlación Confianza",
        value=f"{confidence:.3f}",
        delta=f"{status}",
        delta_color=color
    )

def display_improvement_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de score de mejora."""
    improvement = metrics['improvement_score']
    
    if improvement >= 0.7:
        status = "Excelente"
        color = "normal"
    elif improvement >= 0.5:
        status = "Buena"
        color = "normal"
    else:
        status = "Necesita mejora"
        color = "inverse"
    
    st.metric(
        label="📈 Score de Mejora",
        value=f"{improvement:.2f}",
        delta=f"{status}",
        delta_color=color
    )

def create_accuracy_trend_chart(progress_data: Dict[str, Any]):
    """Crea gráfico de tendencia de precisión."""
    if not progress_data['accuracy_trend']:
        st.warning("No hay datos de precisión disponibles")
        return
    
    df = pd.DataFrame({
        'Fecha': progress_data['timestamps'],
        'Precisión (%)': progress_data['accuracy_trend']
    })
    
    fig = px.line(
        df, 
        x='Fecha', 
        y='Precisión (%)',
        title="📈 Tendencias de Precisión",
        line_shape="linear",
        render_mode="svg"
    )
    
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Precisión (%)",
        height=400,
        showlegend=False
    )
    
    # Agregar línea de objetivo
    fig.add_hline(y=85, line_dash="dash", line_color="red", 
                  annotation_text="Objetivo: 85%")
    
    st.plotly_chart(fig, use_container_width=True)

def create_confidence_trend_chart(progress_data: Dict[str, Any]):
    """Crea gráfico de tendencia de confianza."""
    if not progress_data['confidence_trend']:
        st.warning("No hay datos de confianza disponibles")
        return
    
    df = pd.DataFrame({
        'Fecha': progress_data['timestamps'],
        'Correlación': progress_data['confidence_trend']
    })
    
    fig = px.line(
        df, 
        x='Fecha', 
        y='Correlación',
        title="🎲 Tendencias de Confianza",
        line_shape="linear",
        render_mode="svg"
    )
    
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Correlación Confianza-Precisión",
        height=400,
        showlegend=False
    )
    
    # Agregar línea de objetivo
    fig.add_hline(y=0.8, line_dash="dash", line_color="red", 
                  annotation_text="Objetivo: 0.8")
    
    st.plotly_chart(fig, use_container_width=True)

def create_learning_velocity_chart(progress_data: Dict[str, Any]):
    """Crea gráfico de velocidad de aprendizaje."""
    if not progress_data['learning_velocity_trend']:
        st.warning("No hay datos de velocidad de aprendizaje disponibles")
        return
    
    df = pd.DataFrame({
        'Fecha': progress_data['timestamps'],
        'Velocidad': progress_data['learning_velocity_trend']
    })
    
    fig = px.bar(
        df, 
        x='Fecha', 
        y='Velocidad',
        title="🚀 Velocidad de Aprendizaje",
        color='Velocidad',
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Velocidad de Aprendizaje",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_improvement_trend_chart(progress_data: Dict[str, Any]):
    """Crea gráfico de tendencia de mejora."""
    if not progress_data['improvement_trend']:
        st.warning("No hay datos de mejora disponibles")
        return
    
    df = pd.DataFrame({
        'Fecha': progress_data['timestamps'],
        'Score de Mejora': progress_data['improvement_trend']
    })
    
    fig = px.area(
        df, 
        x='Fecha', 
        y='Score de Mejora',
        title="📈 Score de Mejora Continua",
        fill='tonexty'
    )
    
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Score de Mejora",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_category_performance(category_performance: Dict[str, Dict[str, float]]):
    """Muestra rendimiento por categoría."""
    st.subheader("📂 Rendimiento por Categoría")
    
    if not category_performance:
        st.warning("No hay datos de rendimiento por categoría")
        return
    
    # Crear DataFrame
    data = []
    for category, perf in category_performance.items():
        data.append({
            'Categoría': category,
            'Total Notas': perf['total_notes'],
            'Correcciones': perf['corrections'],
            'Precisión (%)': perf['accuracy'],
            'Tasa Corrección (%)': perf['correction_rate']
        })
    
    df = pd.DataFrame(data)
    
    # Gráfico de barras
    fig = px.bar(
        df,
        x='Categoría',
        y='Precisión (%)',
        color='Tasa Corrección (%)',
        title="Precisión por Categoría",
        color_continuous_scale='RdYlGn_r'
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de datos
    st.dataframe(df, use_container_width=True)

def display_model_performance(model_performance: Dict[str, float]):
    """Muestra rendimiento por modelo."""
    st.subheader("🤖 Rendimiento por Modelo")
    
    if not model_performance:
        st.warning("No hay datos de rendimiento por modelo")
        return
    
    # Crear DataFrame
    data = []
    for model, accuracy in model_performance.items():
        data.append({
            'Modelo': model,
            'Precisión (%)': accuracy
        })
    
    df = pd.DataFrame(data)
    
    # Gráfico de barras
    fig = px.bar(
        df,
        x='Modelo',
        y='Precisión (%)',
        title="Precisión por Modelo de IA",
        color='Precisión (%)',
        color_continuous_scale='RdYlGn'
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de datos
    st.dataframe(df, use_container_width=True)

def display_learning_insights(insights: List[str]):
    """Muestra insights de aprendizaje."""
    st.subheader("💡 Insights de Aprendizaje")
    
    if not insights:
        st.info("No hay insights disponibles en este momento")
        return
    
    for insight in insights:
        st.info(f"• {insight}")

def display_improvement_suggestions(suggestions: List[Dict[str, Any]]):
    """Muestra sugerencias de mejora."""
    st.subheader("🔧 Sugerencias de Mejora")
    
    if not suggestions:
        st.success("¡Excelente! No se detectaron mejoras necesarias")
        return
    
    for suggestion in suggestions:
        priority_color = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(suggestion['priority'], '⚪')
        
        st.markdown(f"**{priority_color} {suggestion['type'].replace('_', ' ').title()}**")
        st.markdown(f"*{suggestion['description']}*")
        st.markdown(f"**Acción:** {suggestion['action']}")
        st.markdown("---")

def display_semantic_coherence_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de coherencia semántica."""
    coherence = metrics['semantic_coherence']
    
    st.metric(
        label="🔗 Coherencia Semántica",
        value=f"{coherence:.2f}",
        delta="Buena" if coherence >= 0.7 else "Mejorable"
    )

def display_category_balance_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de balance de categorías."""
    balance = metrics['category_balance']
    
    st.metric(
        label="⚖️ Balance de Categorías",
        value=f"{balance:.2f}",
        delta="Balanceado" if balance >= 0.7 else "Desbalanceado"
    )

def display_user_satisfaction_card(metrics: Dict[str, Any]):
    """Muestra tarjeta de satisfacción del usuario."""
    satisfaction = metrics['user_satisfaction']
    
    st.metric(
        label="😊 Satisfacción Usuario",
        value=f"{satisfaction:.2f}",
        delta="Alta" if satisfaction >= 0.7 else "Mejorable"
    )

def display_progress_summary(progress_data: Dict[str, Any]):
    """Muestra resumen de progreso."""
    improvement = progress_data['overall_improvement']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="📈 Mejora en Precisión",
            value=f"{improvement['accuracy']:+.1f}%",
            delta="Mejorando" if improvement['accuracy'] > 0 else "Estable"
        )
    
    with col2:
        st.metric(
            label="🎲 Mejora en Confianza",
            value=f"{improvement['confidence']:+.3f}",
            delta="Mejorando" if improvement['confidence'] > 0 else "Estable"
        )
    
    with col3:
        st.metric(
            label="🚀 Mejora General",
            value=f"{improvement['overall']:+.2f}",
            delta="Excelente progreso" if improvement['overall'] > 0.1 else "Progreso estable"
        )
    
    # Gráfico de radar con métricas principales
    if progress_data['accuracy_trend'] and progress_data['confidence_trend']:
        create_radar_chart(progress_data)

def create_radar_chart(progress_data: Dict[str, Any]):
    """Crea gráfico de radar con métricas principales."""
    # Obtener valores más recientes
    recent_accuracy = progress_data['accuracy_trend'][-1] if progress_data['accuracy_trend'] else 0
    recent_confidence = progress_data['confidence_trend'][-1] if progress_data['confidence_trend'] else 0
    recent_velocity = progress_data['learning_velocity_trend'][-1] if progress_data['learning_velocity_trend'] else 0
    recent_improvement = progress_data['improvement_trend'][-1] if progress_data['improvement_trend'] else 0
    
    # Normalizar valores para el radar (0-100)
    normalized_accuracy = recent_accuracy
    normalized_confidence = recent_confidence * 100
    normalized_velocity = recent_velocity * 100
    normalized_improvement = recent_improvement * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=[normalized_accuracy, normalized_confidence, normalized_velocity, normalized_improvement],
        theta=['Precisión', 'Confianza', 'Velocidad', 'Mejora'],
        fill='toself',
        name='Estado Actual',
        line_color='blue'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=True,
        title="🎯 Estado General del Sistema de Aprendizaje"
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    # Para ejecutar directamente
    import sys
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
        create_learning_dashboard(vault_path)
    else:
        st.error("Debe proporcionar la ruta del vault como argumento") 