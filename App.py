<think>
O usuário está dizendo que houve um erro de sintaxe no código que eu forneci. Parece que o código foi truncado ou algo deu errado na transmissão. O erro indica que a string multilinha (triple-quoted string) não foi terminada corretamente.

Eu preciso fornecer o código completo e corrigido. Vou criar uma versão mais robusta que não tenha esse problema - talvez dividindo em partes menores ou garantindo que todas as strings estejam properly fechado.

Vou reescrever o código de forma mais cuidadosa, quebrando em partes menores para evitar o problema de strings não terminadas.
</think>

Sim! O código ficou incompleto na transmissão. Deixa eu corrigir isso e te passar o código completo e funcional:

```python
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
# ESTILO CORPORATIVO - PARTE 1
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
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
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg_principal) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--texto_principal) !important;
    }
    
    .block-container {
        padding: 0 !important;
        padding-top: 0 !important;
    }
    
    /* HEADER */
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
    
    /* MAIN */
    .main-container {
        padding: 1.5rem;
        background-color: var(--bg_principal);
        min-height: calc(100vh - 70px);
    }
    
    /* FILTROS */
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
    
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    @media (max-width: 1200px) {
        .kpi-grid { grid-template-columns: repeat(3, 1fr); }
    }
    
    @media (max-width: 768px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
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
    
    /* TABELA */
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
    
    .tabela-filtros {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid var(--borda);
        flex-wrap: wrap;
    }
    
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# STYLE ADDITIONAL - PARTE 2
# ============================================================
st.markdown("""
<style>
    /* Input styles */
    .filtros-container input[type="text"],
    .filtros-container input[type="date"] {
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
    
    /* DataFrame */
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
    
    /* Status tags */
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
    
    /* Button */
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEETS - CONFIG
# ============================================================
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = st.secrets["gspread_creds"]
credentials = Credentials.from_service_account_info(CREDS_DICT, scopes=SCOPE)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = st.secrets["spreadsheet_id"]

def get_sheet_data(sheet_name):
    """Retorna os dados brutos de uma aba como DataFrame"""
    try:
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao conectar à aba {sheet_name}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_transferencias():
    return get_sheet_data("transferencias")

@st.cache_data(ttl=60)
def load_road():
    return get_sheet_data("road")

def dedup_columns(df):
    """Garante que colunas duplicadas não causem conflito"""
    return df.loc[:, ~df.columns.duplicated()]

def br(val):
    """Formatação de moeda BRL"""
    try:
        return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def peso_format(val):
    """Formatação de peso em KG"""
    try:
        return f"{float(val):,.2f} kg".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00 kg"

# ============================================================
# SIDEBAR - MENU
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="logo-container">
        <p class="logo-titulo">🚛 Sistema de Transferências</p>
        <p class="logo-subtitulo">Logística e Gestão</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu itens
    menu_opcoes = [
        ("📊", "Dashboard", True),
        ("📋", "Registro", False),
        ("🗺️", "Roteirização", False),
        ("📜", "Histórico", False),
    ]
    
    for icon, titulo, ativo in menu_opcoes:
        classe = "menu-item active" if ativo else "menu-item"
        st.markdown(f"""
        <div class="{classe}">
            <span class="menu-icon">{icon}</span>
            <span>{titulo}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color: #32363e; margin: 1.5rem 0;'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="padding: 0.5rem 1rem; color: #6b7280; font-size: 0.75rem;">
        © 2024 - Sistema de Transferências<br>
        Versão 1.0.0
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
data_atual = date.today().strftime("%d/%m/%Y")
st.markdown(f"""
<div class="header-container">
    <div class="header-info">
        <h1 class="header-titulo">Sistema de Transferências</h1>
        <p class="header-subtitulo">Logística e Gestão de Transferências</p>
    </div>
    <div class="header-user">
        <span class="header-data">{data_atual}</span>
        <div class="header-user-info">
            <div class="user-avatar">OP</div>
            <span class="user-name">Operador</span>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            Online
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# MAIN CONTENT
# ============================================================
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# FILTROS
fc1, fc2, fc3, fc4 = st.columns([2, 2, 1, 1])
with fc1:
    data_filtro = st.date_input("Data", date.today())
with fc2:
    ver_todas = st.checkbox("Todas as Datas", value=False)
with fc3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Atualizar", key="refresh_btn"):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()
with fc4:
    pass

st.markdown("</div>", unsafe_allow_html=True)

# CARREGA DADOS
data_str = data_filtro.isoformat()
data_display = data_filtro.strftime("%d/%m/%Y")

df_all = load_transferencias()
df_road = load_road()

if df_all.empty:
    st.warning("Nenhum dado encontrado na aba 'transferências'.")
    st.stop()

# PROCESSA DADOS
if not ver_todas:
    if "dt_transferencia" in df_all.columns:
        df_all["dt_transferencia"] = df_all["dt_transferencia"].astype(str).str.strip()
        df_h = df_all[df_all["dt_transferencia"] == data_str].copy()
    else:
        df_h = df_all.copy()
else:
    df_h = df_all.copy()

# KPIs
n_total = len(df_h)
n_pend = len(df_h[df_h["status"] != "roteirizado"]) if "status" in df_h.columns else 0
n_rot = len(df_h[df_h["status"] == "roteirizado"]) if "status" in df_h.columns else 0

# Calcula valor total e peso total
valor_total = df_h["vltotal"].sum() if "vltotal" in df_h.columns else 0
peso_total = df_h["peso"].sum() if "peso" in df_h.columns else 0

# Renderiza KPIs
st.markdown("""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Total de Notas</div>
        <div class="kpi-valor azul">{n_total}</div>
        <div class="kpi-sub">registradas na data</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Pendentes</div>
        <div class="kpi-valor amarelo">{n_pend}</div>
        <div class="kpi-sub">aguardando roteirização</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Roteirizadas</div>
        <div class="kpi-valor verde">{n_rot}</div>
        <div class="kpi-sub">com placa definida</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label
