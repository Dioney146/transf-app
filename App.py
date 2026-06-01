import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Sistema de Transferências",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# ESTILO CORPORATIVO - TEMA ESCURO
# ============================================================
st.markdown("""
<style>
    /* IMPORTAÇÕES E FONTES */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* VARIÁVEIS DE COR */
    :root {
        --bg_principal: #121417;
        --bg_secundario: #1a1d21;
        --bg_card: #212529;
        --bg_hover: #2a2f35;
        --borda: #32363e;
        --borda_clara: #3d4248;
        --texto_principal: #e8eaed;
        --texto_secundario: #9aa0a6;
        --texto_muted: #6b7280;
        --azul_institucional: #3b82f6;
        --azul_escuro: #1d4ed8;
        --verde_sucesso: #10b981;
        --amarelo_alerta: #f59e0b;
        --vermelho_erro: #ef4444;
        --branco: #ffffff;
    }
    
    /* RESET GERAL */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg_principal) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--texto_principal) !important;
    }
    
    /* REMOVER ESPAÇAMENTOS PADRÃO */
    .block-container {
        padding: 0 !important;
        padding-top: 0 !important;
    }
    
    /* ============================================================ */
    /* SIDEBAR - MENU LATERAL */
    /* ============================================================ */
    section[data-testid="stSidebar"] {
        background-color: var(--bg_secundario !important;
        border-right: 1px solid var(--borda) !important;
    }
    
    /* Logo no Sidebar */
    .logo-container {
        padding: 1.25rem 1rem;
        border-bottom: 1px solid var(--borda);
        margin-bottom: 0.5rem;
    }
    
    .logo-titulo {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--branco);
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .logo-subtitulo {
        font-size: 0.75rem;
        color: var(--texto_muted);
        margin: 0.25rem 0 0 0;
    }
    
    /* Itens do Menu */
    .menu-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        margin: 0.125rem 0.5rem;
        border-radius: 6px;
        color: var(--texto_secundario);
        cursor: pointer;
        transition: all 0.15s ease;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .menu-item:hover {
        background-color: var(--bg_hover);
        color: var(--texto_principal);
    }
    
    .menu-item.active {
        background-color: rgba(59, 130, 246, 0.15);
        color: var(--azul_institucional);
        border-left: 3px solid var(--azul_institucional);
    }
    
    .menu-icon {
        font-size: 1.1rem;
        width: 20px;
        text-align: center;
    }
    
    /* ============================================================ */
    /* HEADER - TOPO DA PÁGINA */
    /* ============================================================ */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.5rem;
        background-color: var(--bg_secundario);
        border-bottom: 1px solid var(--borda);
        position: sticky;
        top: 0;
        z-index: 100;
    }
    
    .header-info {
        display: flex;
        flex-direction: column;
    }
    
    .header-titulo {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--branco);
        margin: 0;
    }
    
    .header-subtitulo {
        font-size: 0.8rem;
        color: var(--texto_secundario);
        margin: 0.125rem 0 0 0;
    }
    
    .header-user {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .header-data {
        font-size: 0.875rem;
        color: var(--texto_secundario);
    }
    
    .header-user-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .user-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--azul_institucional), var(--azul_escuro));
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.875rem;
        font-weight: 600;
        color: white;
    }
    
    .user-name {
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.25rem 0.625rem;
        background-color: rgba(16, 185, 129, 0.15);
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--verde_sucesso);
    }
    
    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: var(--verde_sucesso);
    }
    
    /* ============================================================ */
    /* ÁREA PRINCIPAL */
    /* ============================================================ */
    .main-container {
        padding: 1.5rem;
        background-color: var(--bg_principal);
        min-height: calc(100vh - 70px);
    }
    
    /* BARRA DE FILTROS */
    .filtros-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background-color: var(--bg_card);
        border-radius: 8px;
        border: 1px solid var(--borda);
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
    }
    
    .filtro-grupo {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .filtro-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--texto_secundario);
        white-space: nowrap;
    }
    
    /* Inputs estilizados */
    .filtros-container input[type="text"],
    .filtros-container input[type="date"],
    .filtros-container input[type="datetime-local"] {
        background-color: var(--bg_secundario) !important;
        border: 1px solid var(--borda_clara) !important;
        border-radius: 6px !important;
        color: var(--texto_principal) !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.875rem !important;
    }
    
    .filtros-container input:focus {
        border-color: var(--azul_institucional) !important;
        outline: none !important;
    }
    
    /* Checkbox estilizado */
    .filtros-container .stCheckbox {
        margin-top: 0;
    }
    
    .filtros-container .stCheckbox > label {
        color: var(--texto_secundario) !important;
        font-size: 0.875rem !important;
    }
    
    /* Botão Atualizar */
    .btn-atualizar {
        background-color: var(--azul_institucional);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.15s ease;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .btn-atualizar:hover {
        background-color: var(--azul_escuro);
    }
    
    /* ============================================================ */
    /* INDICADORES (KPIs) */
    /* ============================================================ */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    @media (max-width: 1200px) {
        .kpi-grid {
            grid-template-columns: repeat(3, 1fr);
        }
    }
    
    @media (max-width: 768px) {
        .kpi-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    
    .kpi-card {
        background-color: var(--bg_card);
        border: 1px solid var(--borda);
        border-radius: 8px;
        padding: 1.25rem;
    }
    
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--texto_secundario);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    
    .kpi-valor {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--branco);
        line-height: 1.2;
    }
    
    .kpi-valor.azul { color: var(--azul_institucional); }
    .kpi-valor.amarelo { color: var(--amarelo_alerta); }
    .kpi-valor.verde { color: var(--verde_sucesso); }
    
    .kpi-sub {
        font-size: 0.75rem;
        color: var(--texto_muted);
        margin-top: 0.25rem;
    }
    
    /* ============================================================ */
    /* TABELA PRINCIPAL */
    /* ============================================================ */
    .tabela-container {
        background-color: var(--bg_card);
        border: 1px solid var(--borda);
        border-radius: 8px;
        overflow: hidden;
    }
    
    .tabela-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--borda);
        background-color: var(--bg_secundario);
    }
    
    .tabela-titulo {
        font-size: 1rem;
        font-weight: 600;
        color: var(--branco);
    }
    
    .tabela-quantidade {
        font-size: 0.875rem;
        color: var(--texto_secundario);
    }
    
    /* Filtros da Tabela */
    .tabela-filtros {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--borda);
        flex-wrap: wrap;
    }
    
    .filtro-pesquisa {
        flex: 1;
        min-width: 250px;
    }
    
    .filtro-pesquisa input {
        width: 100%;
        background-color: var(--bg_principal);
        border: 1px solid var(--borda_clara);
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
        color: var(--texto_principal);
        font-size: 0.875rem;
    }
    
    .filtro-pesquisa input::placeholder {
        color: var(--texto_muted);
    }
    
    .filtro-select {
        min-width: 150px;
    }
    
    /* DataFrame estilizado */
    .tabela-wrapper {
        padding: 0;
    }
    
    /* Estilização das células da tabela */
    .dataframe {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.875rem !important;
    }
    
    .dataframe th {
        background-color: var(--bg_secundario) !important;
        color: var(--texto_secundario) !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.875rem 1rem !important;
        border-bottom: 1px solid var(--borda) !important;
    }
    
    .dataframe td {
        background-color: transparent !important;
        color: var(--texto_principal) !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid var(--borda) !important;
    }
    
    .dataframe tr:hover td {
        background-color: var(--bg_hover) !important;
    }
    
    /* Status na tabela */
    .status-tag {
        display: inline-block;
        padding: 0.25rem 0.625rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-tag.pendente {
        background-color: rgba(245, 158, 11, 0.15);
        color: var(--amarelo_alerta);
    }
    
    .status-tag.roteirizado {
        background-color: rgba(16, 185, 129, 0.15);
        color: var(--verde_sucesso);
    }
    
    .status-tag.concluido {
        background-color: rgba(59, 130, 246, 0.15);
        color: var(--azul_institucional);
    }
    
    /* ============================================================ */
    /* BOTÕES E INTERAÇÕES */
    /* ============================================================ */
    .stButton > button {
        background-color: var(--bg_card);
        color: var(--texto_principal);
        border: 1px solid var(--borda);
        border-radius: 6px;
    }
    
    .stButton > button:hover {
        background-color: var(--bg_hover);
        border-color: var(--borda_clara);
    }
    
    /* ============================================================ */
    /* SCROLLBAR PERSONALIZADA */
    /* ============================================================ */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg_secundario);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--borda_clara);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--texto_muted);
    }
    
    /* ============================================================ */
    /* MENSAGENS E ALERTAS */
    /* ============================================================ */
    .stWarning {
        background-color: rgba(245, 158, 11, 0.1);
        border: 1px solid var(--amarelo_alerta);
        color: var(--amarelo_alerta);
    }
    
    .stSuccess {
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid var(--verde_sucesso);
        color: var(--verde_sucesso);
    }
