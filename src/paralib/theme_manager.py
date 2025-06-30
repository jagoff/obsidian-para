#!/usr/bin/env python3
"""
paralib/theme_manager.py

Sistema de gestión de temas para el dashboard de PARA System.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import streamlit as st

@dataclass
class ThemeColors:
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str
    text_secondary: str
    success: str
    warning: str
    error: str
    info: str

@dataclass
class Theme:
    name: str
    description: str
    colors: ThemeColors

class ThemeManager:
    def __init__(self, themes_dir: str = "themes"):
        self.themes_dir = Path(themes_dir)
        self.themes_dir.mkdir(exist_ok=True)
        self.current_theme = "default"
        self.themes = self._load_builtin_themes()
    
    def _load_builtin_themes(self) -> Dict[str, Theme]:
        themes = {}
        
        # Tema Default - Azul Material Design
        themes["default"] = Theme(
            name="Default",
            description="Tema moderno con Material Design",
            colors=ThemeColors(
                primary="#1976d2",
                secondary="#424242",
                accent="#ff4081",
                background="#ffffff",
                surface="#f5f5f5",
                text="#212121",
                text_secondary="#757575",
                success="#4caf50",
                warning="#ff9800",
                error="#f44336",
                info="#2196f3"
            )
        )
        
        # Tema Dark - Oscuro con alto contraste
        themes["dark"] = Theme(
            name="Dark",
            description="Tema oscuro con alto contraste",
            colors=ThemeColors(
                primary="#90caf9",
                secondary="#81c784",
                accent="#ffab91",
                background="#0d1117",
                surface="#161b22",
                text="#f0f6fc",
                text_secondary="#8b949e",
                success="#238636",
                warning="#d29922",
                error="#da3633",
                info="#58a6ff"
            )
        )
        
        # Tema Professional - Corporativo minimalista
        themes["professional"] = Theme(
            name="Professional",
            description="Tema corporativo minimalista",
            colors=ThemeColors(
                primary="#2563eb",
                secondary="#64748b",
                accent="#0891b2",
                background="#fefefe",
                surface="#f8fafc",
                text="#0f172a",
                text_secondary="#64748b",
                success="#059669",
                warning="#d97706",
                error="#dc2626",
                info="#0284c7"
            )
        )
        
        # Tema Ocean - Verde azulado
        themes["ocean"] = Theme(
            name="Ocean",
            description="Tema inspirado en el océano",
            colors=ThemeColors(
                primary="#006a6b",
                secondary="#40a9a4",
                accent="#7fb069",
                background="#f0f8ff",
                surface="#e6f3ff",
                text="#1a4a4a",
                text_secondary="#4a7a7a",
                success="#7fb069",
                warning="#ffb347",
                error="#ff6b6b",
                info="#40a9a4"
            )
        )
        
        # Tema Sunset - Colores cálidos
        themes["sunset"] = Theme(
            name="Sunset",
            description="Tema con colores cálidos del atardecer",
            colors=ThemeColors(
                primary="#ff6b35",
                secondary="#f7931e",
                accent="#ffd23f",
                background="#fff8f0",
                surface="#ffe6d9",
                text="#2d1b14",
                text_secondary="#8b4513",
                success="#7fb069",
                warning="#f7931e",
                error="#dc143c",
                info="#ff6b35"
            )
        )
        
        return themes
    
    def get_theme(self, theme_name: str) -> Optional[Theme]:
        return self.themes.get(theme_name.lower())
    
    def get_available_themes(self) -> Dict[str, str]:
        return {name: theme.description for name, theme in self.themes.items()}
    
    def set_current_theme(self, theme_name: str):
        if theme_name.lower() in self.themes:
            self.current_theme = theme_name.lower()
            return True
        return False
    
    def get_current_theme(self) -> Theme:
        return self.themes[self.current_theme]
    
    def apply_theme_to_streamlit(self, theme: Theme):
        """Aplica el tema completo a Streamlit con CSS avanzado."""
        css = f"""
        <style>
        /* Variables CSS del tema */
        :root {{
            --primary-color: {theme.colors.primary};
            --secondary-color: {theme.colors.secondary};
            --accent-color: {theme.colors.accent};
            --background-color: {theme.colors.background};
            --surface-color: {theme.colors.surface};
            --text-color: {theme.colors.text};
            --text-secondary-color: {theme.colors.text_secondary};
            --success-color: {theme.colors.success};
            --warning-color: {theme.colors.warning};
            --error-color: {theme.colors.error};
            --info-color: {theme.colors.info};
        }}
        
        /* Fondo principal */
        .stApp {{
            background-color: var(--background-color);
            color: var(--text-color);
        }}
        
        /* Sidebar */
        .css-1d391kg {{
            background-color: var(--surface-color);
        }}
        
        /* Botones */
        .stButton > button {{
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            background-color: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        /* Métricas */
        .metric-container {{
            background-color: var(--surface-color);
            border-radius: 12px;
            padding: 1.5rem;
            border-left: 4px solid var(--primary-color);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 0.5rem 0;
        }}
        
        /* Tarjetas */
        .card {{
            background-color: var(--surface-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,0,0,0.05);
            margin: 1rem 0;
        }}
        
        /* Headers */
        h1, h2, h3 {{
            color: var(--primary-color);
            font-weight: bold;
        }}
        
        /* Alertas */
        .alert-success {{
            background-color: var(--success-color);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }}
        
        .alert-warning {{
            background-color: var(--warning-color);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }}
        
        .alert-error {{
            background-color: var(--error-color);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }}
        
        .alert-info {{
            background-color: var(--info-color);
            color: white;
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }}
        
        /* Selectbox y inputs */
        .stSelectbox > div > div {{
            background-color: var(--surface-color);
            border: 1px solid var(--primary-color);
        }}
        
        /* Progreso */
        .stProgress > div > div > div {{
            background-color: var(--primary-color);
        }}
        
        /* Tablas */
        .stDataFrame {{
            background-color: var(--surface-color);
        }}
        
        /* Texto secundario */
        .secondary-text {{
            color: var(--text-secondary-color);
            font-size: 0.9rem;
        }}
        
        /* Status badges */
        .status-healthy {{
            background-color: var(--success-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .status-warning {{
            background-color: var(--warning-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .status-critical {{
            background-color: var(--error-color);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        /* Animaciones */
        .fade-in {{
            animation: fadeIn 0.5s ease-in;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        /* Gráficos */
        .plotly-graph-div {{
            background-color: var(--surface-color) !important;
            border-radius: 12px;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

theme_manager = ThemeManager()

def get_theme_manager() -> ThemeManager:
    return theme_manager 