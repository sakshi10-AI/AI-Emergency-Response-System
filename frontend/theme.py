"""
Streamlit Emergency Operations Center Dark Theme & Styling Engine

Provides custom CSS injection for futuristic command center styling:
- Dark slate/obsidian palette
- Neon glowing metric cards
- Status badges and hazard indicators
- Command header banner
"""

import streamlit as st


def inject_custom_theme():
    """Injects custom CSS styles into the Streamlit app."""
    css = """
    <style>
    /* Dark Theme Core Reset */
    .stApp {
        background-color: #0e1117;
        color: #e5e7eb;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 98%;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #58a6ff !important;
    }

    /* Command Banner Header */
    .command-header {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    .command-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f9fafb;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .command-subtitle {
        font-size: 0.875rem;
        color: #9ca3af;
        margin-top: 0.25rem;
    }
    .status-badge-online {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: transform 0.2s, border-color 0.2s;
    }
    .metric-card:hover {
        border-color: #60a5fa;
        transform: translateY(-2px);
    }
    .metric-card-red { border-left: 4px solid #ef4444; }
    .metric-card-amber { border-left: 4px solid #f59e0b; }
    .metric-card-cyan { border-left: 4px solid #06b6d4; }
    .metric-card-emerald { border-left: 4px solid #10b981; }

    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f9fafb;
        margin-top: 0.25rem;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }

    /* Status Pills */
    .badge-critical { background-color: #ef4444; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
    .badge-urgent { background-color: #f59e0b; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
    .badge-active { background-color: #06b6d4; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
    .badge-normal { background-color: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }

    /* Custom Buttons */
    div.stButton > button {
        background-color: #1f2937;
        color: #e5e7eb;
        border: 1px solid #4b5563;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #374151;
        border-color: #3b82f6;
        color: #ffffff;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_command_header(title: str, subtitle: str):
    """Renders sleek top command header bar."""
    html = f"""
    <div class="command-header">
        <div>
            <h1 class="command-title">🚨 EOC COMMAND CENTER | {title.upper()}</h1>
            <div class="command-subtitle">{subtitle}</div>
        </div>
        <div>
            <span class="status-badge-online">● SYSTEM ONLINE | LIVE DATA STREAM</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(title: str, value: str, subtext: str = "", color: str = "cyan"):
    """Renders glowing metric card widget."""
    html = f"""
    <div class="metric-card metric-card-{color}">
        <div class="metric-label">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtext}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
