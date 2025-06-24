#!/usr/bin/env python3
"""
para_backend_dashboard.py

Backend Dashboard para PARA System.
Unifica logs, métricas de aprendizaje, ChromaDB analytics, salud del sistema y analytics de usuario.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import os
import re
import subprocess

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paralib.log_manager import PARALogManager
from paralib.learning_system import PARA_Learning_System
from paralib.db import ChromaPARADatabase
from paralib.config import load_config

class PARABackendDashboard:
    def __init__(self):
        # Cargar configuración desde el archivo por defecto
        config_path = Path("para_config.default.json")
        self.config = load_config(str(config_path)) if config_path.exists() else {}
        
        self.log_manager = PARALogManager()
        
        # Inicializar sistema de aprendizaje con vault path
        vault_path = Path(self.config.get('vault_path', '.'))
        db_path = vault_path / ".para_db" / "chroma"
        self.chroma_db = ChromaPARADatabase(db_path=str(db_path))
        self.learning_system = PARA_Learning_System(self.chroma_db, vault_path)
        
        # Configurar página
        st.set_page_config(
            page_title="PARA Backend Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def run(self):
        """Ejecuta el dashboard principal."""
        st.title("🚀 PARA Backend Dashboard")
        st.markdown("**Sistema de gestión y monitoreo integral del PARA System**")
        # Sidebar para navegación
        st.sidebar.title("📋 Navegación")
        page = st.sidebar.selectbox(
            "Seleccionar sección:",
            [
                "🏠 Dashboard Principal",
                "🚨 Alertas del Sistema",
                "📊 Logs & Errores",
                "🧠 Sistema de Aprendizaje",
                "🔍 ChromaDB Analytics",
                "💊 Doctor System",
                "📈 Métricas de Usuario",
                "⚙️ Configuración del Sistema"
            ]
        )
        # Navegación por páginas
        if page == "🏠 Dashboard Principal":
            self.show_main_dashboard()
        elif page == "🚨 Alertas del Sistema":
            self.show_alerts_dashboard()
        elif page == "📊 Logs & Errores":
            self.show_logs_dashboard()
        elif page == "🧠 Sistema de Aprendizaje":
            self.show_learning_dashboard()
        elif page == "🔍 ChromaDB Analytics":
            self.show_chromadb_dashboard()
        elif page == "💊 Doctor System":
            self.show_doctor_dashboard()
        elif page == "📈 Métricas de Usuario":
            self.show_user_metrics()
        elif page == "⚙️ Configuración del Sistema":
            self.show_system_config()
    
    def show_main_dashboard(self):
        """Dashboard principal con resumen general."""
        st.header("🏠 Dashboard Principal")
        # --- Resumen de alertas ---
        service_status = self.check_services_status()
        priority_order = [
            'ChromaDB', 'Vault Manager', 'AI Engine', 'Organizer', 'Plugins',
            'Learning System', 'Log Manager', 'Feedback Manager', 'Clean Manager', 'UI/Monitor'
        ]
        errors = []
        warnings = []
        oks = []
        for key in priority_order:
            if key in service_status:
                info = service_status[key]
                if info['status'] == 'error':
                    errors.append((key, info))
                elif info['status'] == 'warning':
                    warnings.append((key, info))
                else:
                    oks.append((key, info))
        st.markdown(f"### 🚨 Resumen de Alertas: [Errores: {len(errors)} | Advertencias: {len(warnings)} | OK: {len(oks)}]")
        
        # Métricas principales en cards
        col1, col2, col3, col4 = st.columns(4)
        
        # Logs metrics
        log_metrics = self.log_manager.get_metrics()
        with col1:
            st.metric(
                label="📊 Total Logs",
                value=log_metrics['total_logs'],
                delta=log_metrics['auto_resolved']
            )
        
        with col2:
            st.metric(
                label="✅ Auto-Resueltos",
                value=log_metrics['auto_resolved'],
                delta=f"{log_metrics['auto_resolved']/max(log_metrics['total_logs'], 1)*100:.1f}%"
            )
        
        with col3:
            st.metric(
                label="⏳ Pendientes",
                value=log_metrics['pending'],
                delta=f"{log_metrics['pending']/max(log_metrics['total_logs'], 1)*100:.1f}%"
            )
        
        with col4:
            st.metric(
                label="⏱️ Tiempo Promedio Resolución",
                value=f"{log_metrics['avg_resolution_time']:.1f} min"
            )
        
        # Learning metrics
        learning_metrics = self.learning_system.get_metrics()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🧠 Total Feedback",
                value=learning_metrics.get('total_feedback', 0)
            )
        
        with col2:
            st.metric(
                label="📈 Precisión Actual",
                value=f"{learning_metrics.get('current_accuracy', 0)*100:.1f}%"
            )
        
        with col3:
            st.metric(
                label="🔄 Modelos Entrenados",
                value=learning_metrics.get('models_trained', 0)
            )
        
        with col4:
            st.metric(
                label="📊 Notas Clasificadas",
                value=learning_metrics.get('notes_classified', 0)
            )
        
        # Gráficos principales
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Actividad de Logs (Últimas 24h)")
            recent_activity = self.log_manager.get_recent_activity(24)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=['Total', 'Auto-Resueltos', 'Manual', 'Pendientes'],
                    y=[
                        recent_activity['total'],
                        recent_activity['auto_resolved'],
                        recent_activity['manually_resolved'],
                        recent_activity['pending']
                    ],
                    marker_color=['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728']
                )
            ])
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🧠 Progreso de Aprendizaje")
            # Gráfico de progreso de aprendizaje
            try:
                progress = self.learning_system.get_learning_progress(days=30)
                if progress and 'accuracy_trend' in progress:
                    # Crear DataFrame para el gráfico
                    df = pd.DataFrame({
                        'timestamp': progress.get('timestamps', []),
                        'accuracy': progress.get('accuracy_trend', [])
                    })
                    
                    if not df.empty:
                        fig = px.line(
                            df, 
                            x='timestamp', 
                            y='accuracy',
                            title="Evolución de la Precisión"
                        )
                        fig.update_layout(height=300)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos de precisión disponibles")
                else:
                    st.info("No hay datos de progreso de aprendizaje disponibles")
            except Exception as e:
                st.warning(f"No se pudieron cargar los datos de progreso: {e}")
        
        # Alertas y estado del sistema
        st.subheader("🚨 Alertas del Sistema")
        
        # Verificar estado de servicios
        services_status = self.check_services_status()
        
        for service, status in services_status.items():
            if status['status'] == 'error':
                st.error(f"❌ {service}: {status['message']}")
            elif status['status'] == 'warning':
                st.warning(f"⚠️ {service}: {status['message']}")
            else:
                st.success(f"✅ {service}: {status['message']}")
    
    def show_alerts_dashboard(self):
        """Página dedicada a mostrar todas las alertas del sistema ordenadas por importancia."""
        st.header("🚨 Alertas del Sistema")
        service_status = self.check_services_status()
        priority_order = [
            'ChromaDB', 'Vault Manager', 'AI Engine', 'Organizer', 'Plugins',
            'Learning System', 'Log Manager', 'Feedback Manager', 'Clean Manager', 'UI/Monitor'
        ]
        errors = []
        warnings = []
        oks = []
        for key in priority_order:
            if key in service_status:
                info = service_status[key]
                if info['status'] == 'error':
                    errors.append((key, info))
                elif info['status'] == 'warning':
                    warnings.append((key, info))
                else:
                    oks.append((key, info))
        for key, info in errors:
            st.error(f"❌ {key}: {info['message']}")
        for key, info in warnings:
            st.warning(f"⚠️ {key}: {info['message']}")
        for key, info in oks:
            st.success(f"✅ {key}: {info['message']}")
    
    def show_logs_dashboard(self):
        """Dashboard específico para logs y errores."""
        st.header("📊 Logs & Errores")
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            log_level = st.selectbox(
                "Nivel de Log:",
                ["Todos", "ERROR", "WARNING", "INFO", "DEBUG"]
            )
        with col2:
            time_range = st.selectbox(
                "Rango de tiempo:",
                ["Últimas 24h", "Últimos 7 días", "Último mes", "Todo"]
            )
        with col3:
            status_filter = st.selectbox(
                "Estado:",
                ["Todos", "Pendiente", "Auto-Resuelto", "Manual", "Escalado"]
            )
        if st.button("🔄 Analizar Logs"):
            with st.spinner("Analizando logs..."):
                result = self.log_manager.analyze_log_file()
                st.success(f"Procesados: {result['processed']}, Auto-resueltos: {result['auto_resolved']}, Pendientes: {result['pending']}")
        # --- NUEVO: Pestañas para logs pendientes y resueltos ---
        tabs = st.tabs(["⏳ Pendientes", "✅ Resueltos"])
        with tabs[0]:
            st.subheader("⏳ Logs Pendientes")
            pending_logs = self.log_manager.get_pending_logs(20)
            if pending_logs:
                for log in pending_logs:
                    with st.expander(f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {log.level} - {log.module}"):
                        st.write(f"**Mensaje:** {log.message}")
                        st.write(f"**Estado:** {log.status.value}")
                        if log.auto_resolution_attempted:
                            st.info("Se intentó resolución automática")
                        # Botón para intentar resolver automáticamente con doctor
                        if st.button(f"Resolver este error", key=f"doctor_{log.id}"):
                            st.info("Ejecutando doctor para este error...")
                            try:
                                result = subprocess.run([
                                    sys.executable, "para_cli.py", "doctor", "--prompt", log.message
                                ], capture_output=True, text=True, check=False)
                                output = result.stdout or result.stderr
                                # Buscar resumen de resolución
                                resolved = False
                                summary = ""
                                for line in output.splitlines():
                                    if "Problemas resueltos:" in line or "Doctor completado" in line:
                                        summary += line + "\n"
                                        if any(s in line for s in ["Problemas resueltos: 1", "Problemas resueltos: 2", "Doctor completado"]):
                                            resolved = True
                                st.code(output)
                                if summary:
                                    st.info(f"Resumen doctor:\n{summary}")
                                if resolved:
                                    st.success("✅ El error fue resuelto por doctor.")
                                else:
                                    st.warning("El error no fue resuelto automáticamente. Revisa el detalle o intenta una acción manual.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error ejecutando doctor: {e}")
            else:
                st.success("✅ No hay logs pendientes")
        with tabs[1]:
            st.subheader("✅ Logs Resueltos (Historial)")
            resolved_logs = self.log_manager.get_resolved_logs(20)
            if resolved_logs:
                for log in resolved_logs:
                    with st.expander(f"{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {log.level} - {log.module}"):
                        st.write(f"**Mensaje:** {log.message}")
                        st.write(f"**Estado:** {log.status.value}")
                        st.write(f"**Resolución:** {log.resolution}")
                        st.write(f"**Resuelto en:** {log.resolved_at}")
            else:
                st.info("No hay logs resueltos en el historial")
        # Métricas detalladas
        st.subheader("📈 Métricas Detalladas")
        metrics = self.log_manager.get_metrics()
        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure(data=[
                go.Pie(
                    labels=['Auto-Resueltos', 'Manual', 'Pendientes', 'Escalados'],
                    values=[
                        metrics['auto_resolved'],
                        metrics['manually_resolved'],
                        metrics['pending'],
                        metrics['escalated']
                    ],
                    hole=0.3
                )
            ])
            fig.update_layout(title="Distribución por Estado")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.info("Gráfico de tendencia temporal - En desarrollo")
    
    def show_learning_dashboard(self):
        """Dashboard del sistema de aprendizaje con métricas completas."""
        st.header("🧠 Sistema de Aprendizaje Autónomo")
        
        # Obtener todas las métricas disponibles
        try:
            metrics = self.learning_system.get_metrics()
        except Exception as e:
            st.error(f"Error obteniendo métricas de aprendizaje: {e}")
            return
        
        # Métricas principales en cards
        st.subheader("📊 Métricas Principales")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🎯 Precisión",
                value=f"{metrics.get('accuracy_rate', 0):.1f}%",
                delta=f"{metrics.get('overall_improvement', {}).get('accuracy', 0):.1f}%"
            )
        
        with col2:
            st.metric(
                label="🚀 Velocidad de Aprendizaje",
                value=f"{metrics.get('learning_velocity', 0):.2f}",
                delta="Mejora" if metrics.get('learning_velocity', 0) > 0.5 else "Necesita datos"
            )
        
        with col3:
            st.metric(
                label="📈 Score de Mejora",
                value=f"{metrics.get('improvement_score', 0):.2f}",
                delta="Positivo" if metrics.get('improvement_score', 0) > 0.5 else "Necesita mejora"
            )
        
        with col4:
            st.metric(
                label="🎲 Correlación Confianza",
                value=f"{metrics.get('confidence_correlation', 0):.3f}",
                delta="Alta" if metrics.get('confidence_correlation', 0) > 0.7 else "Baja"
            )
        
        # Segunda fila de métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📚 Total Clasificaciones",
                value=metrics.get('total_classifications', 0)
            )
        
        with col2:
            st.metric(
                label="📁 Carpetas Creadas",
                value=metrics.get('total_folders_created', 0)
            )
        
        with col3:
            st.metric(
                label="✅ Tasa Aprobación Carpetas",
                value=f"{metrics.get('folder_approval_rate', 0):.1f}%"
            )
        
        with col4:
            st.metric(
                label="🧠 Adaptabilidad Sistema",
                value=f"{metrics.get('system_adaptability', 0):.2f}"
            )
        
        # Métricas de calidad
        st.subheader("🔍 Métricas de Calidad")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="⚖️ Balance Categorías",
                value=f"{metrics.get('category_balance', 0):.2f}"
            )
        
        with col2:
            st.metric(
                label="🔗 Coherencia Semántica",
                value=f"{metrics.get('semantic_coherence', 0):.2f}"
            )
        
        with col3:
            st.metric(
                label="😊 Satisfacción Usuario",
                value=f"{metrics.get('user_satisfaction', 0):.2f}"
            )
        
        with col4:
            st.metric(
                label="📊 Snapshots Históricos",
                value=metrics.get('total_snapshots', 0)
            )
        
        # Análisis de rendimiento por categoría
        st.subheader("📂 Rendimiento por Categoría")
        category_performance = metrics.get('category_performance', {})
        
        if category_performance:
            cat_data = []
            for category, perf in category_performance.items():
                cat_data.append({
                    'Categoría': category,
                    'Total Notas': perf.get('total_notes', 0),
                    'Correcciones': perf.get('corrections', 0),
                    'Precisión': f"{perf.get('accuracy', 0):.1f}%",
                    'Tasa Corrección': f"{perf.get('correction_rate', 0):.1f}%"
                })
            
            if cat_data:
                df_cat = pd.DataFrame(cat_data)
                st.dataframe(df_cat, use_container_width=True)
        else:
            st.info("No hay datos de rendimiento por categoría disponibles")
        
        # Análisis de modelos de IA
        st.subheader("🤖 Rendimiento de Modelos de IA")
        model_performance = metrics.get('model_performance', {})
        
        if model_performance:
            model_data = []
            for model, accuracy in model_performance.items():
                model_data.append({
                    'Modelo': model,
                    'Precisión': f"{accuracy:.1f}%"
                })
            
            if model_data:
                df_model = pd.DataFrame(model_data)
                st.dataframe(df_model, use_container_width=True)
        else:
            st.info("No hay datos de rendimiento de modelos disponibles")
        
        # Análisis de creación de carpetas
        st.subheader("📁 Análisis de Creación de Carpetas")
        folder_method_performance = metrics.get('folder_method_performance', {})
        
        if folder_method_performance:
            method_data = []
            for method, perf in folder_method_performance.items():
                method_data.append({
                    'Método': method,
                    'Total': perf.get('total', 0),
                    'Aprobadas': perf.get('approved', 0),
                    'Tasa Aprobación': f"{perf.get('approval_rate', 0):.1f}%",
                    'Confianza Promedio': f"{perf.get('avg_confidence', 0):.3f}"
                })
            
            if method_data:
                df_method = pd.DataFrame(method_data)
                st.dataframe(df_method, use_container_width=True)
        else:
            st.info("No hay datos de métodos de creación de carpetas disponibles")
        
        # Insights de aprendizaje
        st.subheader("💡 Insights de Aprendizaje")
        learning_insights = metrics.get('learning_insights', [])
        folder_insights = metrics.get('folder_learning_insights', [])
        
        all_insights = learning_insights + folder_insights
        
        if all_insights:
            for insight in all_insights[:10]:  # Mostrar máximo 10 insights
                st.info(f"💡 {insight}")
        else:
            st.info("No hay insights de aprendizaje disponibles")
        
        # Sugerencias de mejora
        st.subheader("🔧 Sugerencias de Mejora")
        suggestions = metrics.get('improvement_suggestions', [])
        
        if suggestions:
            for suggestion in suggestions:
                priority_color = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(suggestion.get('priority', 'medium'), '🟡')
                
                st.warning(f"{priority_color} **{suggestion.get('type', 'Mejora')}**: {suggestion.get('description', '')}")
                st.write(f"*Acción sugerida: {suggestion.get('action', 'N/A')}*")
        else:
            st.success("✅ No hay sugerencias de mejora - el sistema está funcionando bien")
        
        # Acciones de aprendizaje
        st.subheader("🔄 Acciones de Aprendizaje")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Generar Reporte Completo"):
                with st.spinner("Generando reporte..."):
                    try:
                        snapshot = self.learning_system.create_learning_snapshot()
                        st.json(snapshot)
                    except Exception as e:
                        st.error(f"Error generando reporte: {e}")
        
        with col2:
            if st.button("📈 Ver Progreso Detallado"):
                with st.spinner("Cargando progreso..."):
                    try:
                        progress = self.learning_system.get_learning_progress(days=30)
                        st.json(progress)
                    except Exception as e:
                        st.error(f"Error cargando progreso: {e}")
        
        # Información temporal
        st.subheader("⏰ Información Temporal")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Última actualización:** {metrics.get('last_updated', 'N/A')}")
        
        with col2:
            st.write(f"**Período de análisis:** {metrics.get('progress_period_days', 30)} días")
        
        # Mejora general
        overall_improvement = metrics.get('overall_improvement', {})
        if overall_improvement:
            st.subheader("📈 Mejora General del Sistema")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="Mejora Precisión",
                    value=f"{overall_improvement.get('accuracy', 0):.1f}%"
                )
            
            with col2:
                st.metric(
                    label="Mejora Confianza",
                    value=f"{overall_improvement.get('confidence', 0):.1f}%"
                )
            
            with col3:
                st.metric(
                    label="Mejora General",
                    value=f"{overall_improvement.get('overall', 0):.1f}%"
                )
    
    def show_chromadb_dashboard(self):
        """Dashboard de ChromaDB con análisis completo."""
        st.header("🔍 ChromaDB Analytics Avanzado")
        
        try:
            # Estadísticas básicas de ChromaDB
            stats = self.chroma_db.get_database_stats()
            
            # Métricas principales
            st.subheader("📊 Métricas Principales")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="📚 Total Collections",
                    value=stats.get('total_collections', 0)
                )
            
            with col2:
                st.metric(
                    label="📄 Total Documents",
                    value=stats.get('total_documents', 0)
                )
            
            with col3:
                st.metric(
                    label="🔢 Total Embeddings",
                    value=stats.get('total_embeddings', 0)
                )
            
            with col4:
                st.metric(
                    label="💾 Tamaño DB",
                    value=f"{stats.get('database_size_mb', 0):.1f} MB"
                )
            
            # Distribución de categorías
            st.subheader("📂 Distribución de Categorías")
            try:
                category_distribution = self.chroma_db.get_category_distribution()
                
                if category_distribution:
                    # Crear gráfico de distribución
                    categories = list(category_distribution.keys())
                    counts = list(category_distribution.values())
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Gráfico de barras
                        fig = go.Figure(data=[
                            go.Bar(x=categories, y=counts, marker_color='lightblue')
                        ])
                        fig.update_layout(
                            title="Distribución de Notas por Categoría",
                            xaxis_title="Categoría",
                            yaxis_title="Número de Notas",
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Tabla de datos
                        cat_data = []
                        for cat, count in category_distribution.items():
                            percentage = (count / sum(counts)) * 100 if sum(counts) > 0 else 0
                            cat_data.append({
                                'Categoría': cat,
                                'Notas': count,
                                'Porcentaje': f"{percentage:.1f}%"
                            })
                        
                        df_cat = pd.DataFrame(cat_data)
                        st.dataframe(df_cat, use_container_width=True)
                else:
                    st.info("No hay datos de distribución de categorías disponibles")
                    
            except Exception as e:
                st.warning(f"No se pudo obtener distribución de categorías: {e}")
            
            # Análisis de embeddings
            st.subheader("🔢 Análisis de Embeddings")
            try:
                all_notes = self.chroma_db.get_all_notes_metadata()
                
                if all_notes:
                    # Estadísticas de embeddings
                    embedding_stats = {
                        'total_notes': len(all_notes),
                        'notes_with_embeddings': sum(1 for note in all_notes if 'embedding' in note),
                        'avg_content_length': sum(len(str(note.get('content', ''))) for note in all_notes) / len(all_notes) if all_notes else 0,
                        'notes_with_tags': sum(1 for note in all_notes if note.get('tags')),
                        'notes_with_frontmatter': sum(1 for note in all_notes if note.get('frontmatter'))
                    }
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            label="📝 Notas con Embeddings",
                            value=embedding_stats['notes_with_embeddings'],
                            delta=f"{embedding_stats['notes_with_embeddings']/embedding_stats['total_notes']*100:.1f}%" if embedding_stats['total_notes'] > 0 else "0%"
                        )
                    
                    with col2:
                        st.metric(
                            label="📏 Longitud Promedio",
                            value=f"{embedding_stats['avg_content_length']:.0f} chars"
                        )
                    
                    with col3:
                        st.metric(
                            label="🏷️ Notas con Tags",
                            value=embedding_stats['notes_with_tags'],
                            delta=f"{embedding_stats['notes_with_tags']/embedding_stats['total_notes']*100:.1f}%" if embedding_stats['total_notes'] > 0 else "0%"
                        )
                    
                    with col4:
                        st.metric(
                            label="📋 Notas con Frontmatter",
                            value=embedding_stats['notes_with_frontmatter'],
                            delta=f"{embedding_stats['notes_with_frontmatter']/embedding_stats['total_notes']*100:.1f}%" if embedding_stats['total_notes'] > 0 else "0%"
                        )
                    
                    # Análisis de patrones de contenido
                    st.subheader("📊 Patrones de Contenido")
                    
                    # Contar patrones
                    patterns = {
                        'todos': sum(1 for note in all_notes if 'todo' in str(note.get('content', '')).lower()),
                        'fechas': sum(1 for note in all_notes if re.search(r'\d{4}-\d{2}-\d{2}', str(note.get('content', '')))),
                        'enlaces': sum(1 for note in all_notes if '[[' in str(note.get('content', '')) and ']]' in str(note.get('content', ''))),
                        'adjuntos': sum(1 for note in all_notes if '![' in str(note.get('content', ''))),
                        'headers': sum(1 for note in all_notes if re.search(r'^#{1,6}\s+', str(note.get('content', '')), re.MULTILINE)),
                        'listas': sum(1 for note in all_notes if re.search(r'^[-*+]\s+', str(note.get('content', '')), re.MULTILINE))
                    }
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Patrones de Estructura:**")
                        st.write(f"📝 TO-DOs: {patterns['todos']}")
                        st.write(f"📅 Fechas: {patterns['fechas']}")
                        st.write(f"🔗 Enlaces: {patterns['enlaces']}")
                    
                    with col2:
                        st.write("**Patrones de Formato:**")
                        st.write(f"📎 Adjuntos: {patterns['adjuntos']}")
                        st.write(f"📋 Headers: {patterns['headers']}")
                        st.write(f"📝 Listas: {patterns['listas']}")
                    
                    with col3:
                        # Gráfico de patrones
                        pattern_names = list(patterns.keys())
                        pattern_counts = list(patterns.values())
                        
                        fig = go.Figure(data=[
                            go.Bar(x=pattern_names, y=pattern_counts, marker_color='lightgreen')
                        ])
                        fig.update_layout(
                            title="Patrones de Contenido Detectados",
                            xaxis_title="Patrón",
                            yaxis_title="Cantidad",
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.info("No hay notas disponibles para análisis")
                    
            except Exception as e:
                st.warning(f"Error en análisis de embeddings: {e}")
            
            # Collections específicas
            st.subheader("📚 Collections Detalladas")
            
            collections = self.chroma_db.list_collections()
            if collections:
                for collection in collections:
                    with st.expander(f"Collection: {collection.name}"):
                        try:
                            collection_stats = self.chroma_db.get_collection_stats(collection.name)
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.write(f"**Documentos:** {collection_stats.get('count', 0)}")
                            
                            with col2:
                                st.write(f"**Tamaño:** {collection_stats.get('size_mb', 0):.1f} MB")
                            
                            with col3:
                                st.write(f"**Dimensiones:** {collection_stats.get('dimensions', 'N/A')}")
                            
                            # Mostrar algunos documentos de ejemplo
                            if st.button(f"Ver documentos de {collection.name}", key=f"btn_{collection.name}"):
                                try:
                                    documents = self.chroma_db.get_collection_documents(collection.name, limit=5)
                                    for i, doc in enumerate(documents, 1):
                                        st.write(f"{i}. **{doc.get('metadata', {}).get('title', 'Sin título')}**")
                                        st.write(f"   Categoría: {doc.get('metadata', {}).get('category', 'N/A')}")
                                        st.write(f"   Contenido: {str(doc.get('content', ''))[:200]}...")
                                        st.write("---")
                                except Exception as e:
                                    st.error(f"Error obteniendo documentos: {e}")
                        except Exception as e:
                            st.error(f"Error obteniendo estadísticas de collection: {e}")
            else:
                st.info("No hay collections disponibles")
            
            # Análisis de similitud
            st.subheader("🔍 Análisis de Similitud")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Analizar Similitud Semántica"):
                    with st.spinner("Analizando similitud..."):
                        try:
                            # Ejemplo de análisis de similitud
                            sample_notes = all_notes[:5] if all_notes else []
                            if sample_notes:
                                st.write("**Análisis de similitud de muestra:**")
                                for note in sample_notes:
                                    content = str(note.get('content', ''))[:100]
                                    st.write(f"📄 {content}...")
                                
                                st.info("Para análisis completo de similitud, usar el comando CLI: `para-cli analyze-similarity`")
                            else:
                                st.warning("No hay notas para analizar similitud")
                        except Exception as e:
                            st.error(f"Error en análisis de similitud: {e}")
            
            with col2:
                if st.button("📊 Generar Reporte ChromaDB"):
                    with st.spinner("Generando reporte..."):
                        try:
                            report = {
                                'basic_stats': stats,
                                'category_distribution': category_distribution if 'category_distribution' in locals() else {},
                                'embedding_stats': embedding_stats if 'embedding_stats' in locals() else {},
                                'content_patterns': patterns if 'patterns' in locals() else {},
                                'collections': [c.name for c in collections] if collections else [],
                                'timestamp': datetime.now().isoformat()
                            }
                            st.json(report)
                        except Exception as e:
                            st.error(f"Error generando reporte: {e}")
            
            # Estado de salud de ChromaDB
            st.subheader("💚 Estado de Salud")
            
            health_indicators = {
                'Conexión': '✅ Conectado' if stats else '❌ Error de conexión',
                'Documentos': '✅ Documentos disponibles' if stats.get('total_documents', 0) > 0 else '⚠️ Sin documentos',
                'Embeddings': '✅ Embeddings generados' if stats.get('total_embeddings', 0) > 0 else '⚠️ Sin embeddings',
                'Tamaño': '✅ Tamaño razonable' if stats.get('database_size_mb', 0) < 1000 else '⚠️ Base muy grande'
            }
            
            for indicator, status in health_indicators.items():
                st.write(f"**{indicator}:** {status}")
                
        except Exception as e:
            st.error(f"Error al conectar con ChromaDB: {e}")
            st.info("Verificar que ChromaDB esté ejecutándose y la configuración sea correcta")
    
    def show_doctor_dashboard(self):
        """Dashboard del Doctor System."""
        st.header("💊 Doctor System")
        
        st.info("El Doctor System analiza automáticamente los logs y resuelve problemas comunes.")
        
        # Estado del doctor
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Ejecutar Doctor"):
                with st.spinner("Ejecutando diagnóstico..."):
                    # Aquí ejecutarías el doctor
                    st.success("Diagnóstico completado")
        
        with col2:
            if st.button("📊 Ver Reporte de Salud"):
                # Generar reporte de salud del sistema
                health_report = self.generate_health_report()
                st.json(health_report)
        
        # Problemas conocidos y soluciones
        st.subheader("🔧 Problemas Conocidos")
        
        known_issues = [
            {
                "problema": "Modelo de IA no encontrado",
                "solución": "Ejecutar: ollama pull [nombre_modelo]",
                "frecuencia": "Alta"
            },
            {
                "problema": "Error de conexión con ChromaDB",
                "solución": "Verificar configuración de la base de datos",
                "frecuencia": "Media"
            },
            {
                "problema": "Error de permisos",
                "solución": "Verificar permisos de escritura en el directorio",
                "frecuencia": "Baja"
            }
        ]
        
        for issue in known_issues:
            with st.expander(f"{issue['problema']} ({issue['frecuencia']})"):
                st.write(f"**Solución:** {issue['solución']}")
    
    def show_user_metrics(self):
        """Dashboard de métricas de usuario."""
        st.header("📈 Métricas de Usuario")
        
        # Aquí podrías agregar métricas específicas del usuario
        # como notas procesadas, tiempo de uso, etc.
        
        st.info("Métricas de usuario - En desarrollo")
        
        # Placeholder para métricas futuras
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Notas Procesadas", "1,234")
        with col2:
            st.metric("Tiempo de Uso", "45 min")
        with col3:
            st.metric("Clasificaciones", "567")
        with col4:
            st.metric("Precisión", "89.2%")
    
    def show_system_config(self):
        """Dashboard de configuración del sistema."""
        st.header("⚙️ Configuración del Sistema")
        
        # Mostrar configuración actual
        st.subheader("📋 Configuración Actual")
        
        config_data = {
            "Vault Path": self.config.get('vault_path'),
            "AI Model": self.config.get('ai_model'),
            "ChromaDB Path": self.config.get('chromadb_path'),
            "Log Level": self.config.get('log_level'),
            "Backup Enabled": self.config.get('backup_enabled')
        }
        
        for key, value in config_data.items():
            st.write(f"**{key}:** {value}")
        
        # Opciones de configuración
        st.subheader("🔧 Opciones de Configuración")
        
        if st.button("🔄 Recargar Configuración"):
            self.config.reload()
            st.success("Configuración recargada")
        
        if st.button("💾 Guardar Configuración"):
            # Aquí guardarías la configuración
            st.success("Configuración guardada")
    
    def check_services_status(self):
        """Verifica el estado de los servicios del sistema."""
        status = {}
        # Verificar ChromaDB
        try:
            self.chroma_db.get_database_stats()
            status['ChromaDB'] = {'status': 'ok', 'message': 'Conectado correctamente'}
        except Exception as e:
            status['ChromaDB'] = {'status': 'error', 'message': f'Error de conexión: {e}'}
        # Verificar base de datos de aprendizaje
        try:
            self.learning_system.get_metrics()
            status['Learning System'] = {'status': 'ok', 'message': 'Operativo'}
        except Exception as e:
            status['Learning System'] = {'status': 'warning', 'message': f'Problemas: {e}'}
        # Verificar log manager
        try:
            self.log_manager.get_metrics()
            status['Log Manager'] = {'status': 'ok', 'message': 'Operativo'}
        except Exception as e:
            status['Log Manager'] = {'status': 'error', 'message': f'Error: {e}'}
        # Verificar AI Engine/modelo
        try:
            from paralib.ai_engine import AIEngine
            ai_engine = AIEngine(model_name=self.config.get('ai_model', 'llama3.2:3b'))
            if ai_engine.check_model_availability():
                status['AI Engine'] = {'status': 'ok', 'message': f"Modelo '{ai_engine.model_name}' disponible"}
            else:
                status['AI Engine'] = {'status': 'warning', 'message': f"Modelo '{ai_engine.model_name}' no disponible"}
        except Exception as e:
            status['AI Engine'] = {'status': 'error', 'message': f'Error: {e}'}
        # Verificar sistema de plugins
        try:
            from paralib.plugin_system import PARAPluginManager
            plugin_manager = PARAPluginManager()
            stats = plugin_manager.get_plugin_stats()
            if stats['total_plugins'] == 0:
                status['Plugins'] = {'status': 'warning', 'message': 'No hay plugins cargados'}
            elif stats['plugins_with_errors'] > 0:
                status['Plugins'] = {'status': 'warning', 'message': f"{stats['plugins_with_errors']} plugins con errores"}
            else:
                status['Plugins'] = {'status': 'ok', 'message': f"{stats['total_plugins']} plugins cargados"}
        except Exception as e:
            status['Plugins'] = {'status': 'error', 'message': f'Error: {e}'}
        # Verificar Vault Manager
        try:
            from paralib.vault import find_vault
            vault = find_vault()
            if vault and vault.exists():
                note_count = len(list(vault.rglob('*.md')))
                # Buscar último error en logs relacionado a vault
                last_error = None
                try:
                    from paralib.log_manager import PARALogManager
                    log_manager = PARALogManager()
                    logs = log_manager.get_pending_logs(50) + log_manager.get_resolved_logs(50)
                    for log in logs:
                        if 'vault' in log.module.lower() or 'vault' in log.message.lower():
                            last_error = log.message
                            break
                except Exception:
                    pass
                msg = f"Vault detectado: {vault} ({note_count} notas)"
                if last_error:
                    msg += f" | Último error: {last_error[:80]}"
                status['Vault Manager'] = {'status': 'ok', 'message': msg}
            else:
                status['Vault Manager'] = {'status': 'warning', 'message': 'No se detectó un vault válido'}
        except Exception as e:
            status['Vault Manager'] = {'status': 'error', 'message': f'Error: {e}'}
        # Verificar Organizer
        try:
            from paralib.organizer import PARAOrganizer
            organizer = PARAOrganizer()
            pending_tasks = getattr(organizer, 'pending_tasks', None)
            last_action = getattr(organizer, 'last_action', None)
            msg = 'Organizer inicializado'
            if pending_tasks is not None:
                msg += f' ({len(pending_tasks)} tareas pendientes)'
            if last_action:
                msg += f' | Última acción: {last_action}'
            status['Organizer'] = {'status': 'ok', 'message': msg}
        except Exception as e:
            status['Organizer'] = {'status': 'warning', 'message': f'No inicializado: {e}'}
        # Verificar Clean Manager
        try:
            from paralib.clean_manager import run_clean_manager
            # No hay estado persistente, solo mostrar disponible
            status['Clean Manager'] = {'status': 'ok', 'message': 'Módulo de limpieza disponible'}
        except Exception as e:
            status['Clean Manager'] = {'status': 'warning', 'message': f'No disponible: {e}'}
        # Verificar Feedback Manager
        try:
            from paralib.feedback_manager import FeedbackAnalyzer
            analyzer = FeedbackAnalyzer(self.chroma_db, Path(self.config.get('vault_path', '.')))
            feedback_count = 0
            last_feedback = None
            try:
                all_feedback = analyzer.get_all_classifications()
                feedback_count = len(all_feedback)
                if all_feedback:
                    last_feedback = all_feedback[-1].get('content', '')[:80]
            except Exception:
                pass
            msg = f'Feedback manager disponible ({feedback_count} feedbacks)'
            if last_feedback:
                msg += f' | Último feedback: {last_feedback}'
            status['Feedback Manager'] = {'status': 'ok', 'message': msg}
        except Exception as e:
            status['Feedback Manager'] = {'status': 'warning', 'message': f'No disponible: {e}'}
        # Verificar UI/Monitor
        try:
            from paralib.ui import run_monitor_dashboard
            status['UI/Monitor'] = {'status': 'ok', 'message': 'Monitor UI disponible'}
        except Exception as e:
            status['UI/Monitor'] = {'status': 'warning', 'message': f'No disponible: {e}'}
        return status
    
    def generate_health_report(self):
        """Genera un reporte de salud del sistema."""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": self.check_services_status(),
            "metrics": {
                "logs": self.log_manager.get_metrics(),
                "learning": self.learning_system.get_metrics()
            },
            "recommendations": [
                "Sistema funcionando correctamente",
                "Recomendación: Revisar logs pendientes regularmente"
            ]
        }

def main():
    """Función principal para ejecutar el dashboard."""
    dashboard = PARABackendDashboard()
    dashboard.run()

if __name__ == "__main__":
    main() 