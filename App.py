import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

BG_B64 = "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_x40gKvfV4g7pPL576QX/GoRWe+kKWqrxK3SeX/GkmRjtoct3FMh5awVJHVHadhV4kyYVMnxrhlZ7aDmQsnYEjvB2rxkHHOr2Qd8LGSO+kKk786FF895pJf8am2TdCpk+Nc95x20IL57Mmm/eklQSFpJ7gasLKJhn3jO+aSuRkULDx764p499TbK3TS+hA/xh8q50SAf"

# Configurações globais de layout e estilo CSS customizado
st.set_page_config(page_title="Painel de Controle e Monitoramento", layout="wide")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&display=swap');
    
    :root {{
        --bg: #f8fafc;
        --card-bg: #ffffff;
        --txt: #1e293b;
        --txt-sub: #64748b;
        --bdr: #e2e8f0;
        --primary: #2563eb;
        --acc: #3b82f6;
    }}
    
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: var(--bg);
        font-family: 'Sora', sans-serif !important;
        color: var(--txt);
    }}
    
    /* Painel Geral (Cards) */
    .card {{
        background: var(--card-bg);
        border: 1px solid var(--bdr);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }}
    
    .card-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--bdr);
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }}
    
    .card-title {{
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--txt);
    }}
    
    .card-count {{
        font-size: 0.85rem;
        background: #f1f5f9;
        padding: 4px 10px;
        border-radius: 20px;
        color: var(--txt-sub);
        font-weight: 600;
    }}
    
    /* Estilização de KPIs */
    .kpi-mini {{
        background: var(--card-bg);
        border: 1px solid var(--bdr);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }}
    .kpi-mini-label {{
        font-size: 0.8rem;
        color: var(--txt-sub);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }}
    .kpi-mini-value {{
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--txt);
    }}
    .kpi-mini-sub {{
        font-size: 0.75rem;
        color: var(--txt-sub);
        margin-top: 0.25rem;
    }}
    
    /* Customização de Tabelas / Linhas */
    td {{
        font-family: 'Sora', sans-serif !important;
        font-size: 0.8rem !important;
        border-bottom: 1px solid var(--bdr) !important;
        color: var(--txt) !important;
        padding: 9px 12px !important;
        background: transparent !important;
    }}
    
    /* Note card */
    .nota-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid var(--bdr);
    }}
    .nota-row:last-child {{
        border-bottom: none;
    }}
    .placa-chip {{
        background: #eff6ff;
        color: #1e40af;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .al-i {{
        font-style: italic;
        color: var(--txt-sub);
    }}
</style>
""", unsafe_allow_html=True)

# Definição de escopos e credenciais do Google Sheets
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDS_DICT = st.secrets["gspread_creds"]
credentials = Credentials.from_service_account_info(CREDS_DICT, scopes=SCOPE)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = st.secrets["spreadsheet_id"]
HIST_COLS = ["id", "dt_saida", "placa_veiculo", "status", "praca", "vltotal"]

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
    df = get_sheet_data("transferencias")
    if not df.empty and "dt_saida" in df.columns:
        df["dt_saida"] = pd.to_datetime(df["dt_saida"], errors="coerce").dt.date
    return df

@st.cache_data(ttl=60)
def load_road():
    return get_sheet_data("road")

def dedup_columns(df):
    """Garante que colunas duplicadas não causem conflito de índices"""
    df = df.loc[:, ~df.columns.duplicated()]
    return df

def br(val):
    """Formatação de moeda BRL simples"""
    try:
        return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ─── Estrutura Principal da Interface (Filtros superiores) ───────────────────
st.markdown("<h3>🚚 Gestão de Roteirização e Entregas</h3>", unsafe_allow_html=True)

fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 4])
with fc1:
    data_filtro = st.date_input("Filtrar por data de saída:", date.today())
with fc2:
    ver_todas = st.checkbox("Visualizar todas as datas", value=False)
with fc3:
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Atualizar", key="refresh_btn"):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()
with fc4:
    pass

st.markdown("</div>", unsafe_allow_html=True)

# ─── Carrega e Processa Dados ──────────────────────────────────────────────────
data_str = data_filtro.isoformat()
data_display = data_filtro.strftime("%d/%m/%Y")

df_all = load_transferencias()
df_road = load_road()

if df_all.empty:
    st.warning("Nenhum dado encontrado na aba 'transferencias'.")
else:
    # Filtra dados principais com base na data escolhida
    if ver_todas:
        df_h = df_all.copy()
    else:
        df_h = df_all[df_all["dt_saida"] == data_filtro].copy()

    # Base complementar para sincronizar registros vindos da aba de roteirização externa
    rote_base = df_all[df_all["status"] == "roteirizado"].copy() if not df_all.empty else pd.DataFrame()
    
    if ver_todas or rote_base.empty:
        rote = rote_base
    else:
        rote = rote_base[rote_base["dt_saida"] == data_filtro].copy()

    # Processamento cruzado com os dados do 'road'
    if not df_road.empty and not rote.empty:
        try:
            df_road_clean = df_road.dropna(subset=["id"]).copy()
            df_road_clean["id"] = df_road_clean["id"].astype(str).str.strip()
            rote["id"] = rote["id"].astype(str).str.strip()
            
            # Mapeamento dinâmico para evitar problemas de colunas duplicadas ou fora de ordem
            placa_v_idx = "placa_veiculo" if "placa_veiculo" in df_road_clean.columns else None
            placa_r_idx = "placa_road" if "placa_road" in df_road_clean.columns else None
            
            if placa_v_idx and placa_r_idx:
                map_placa_v = dict(zip(df_road_clean["id"], df_road_clean[placa_v_idx]))
                map_placa_r = dict(zip(df_road_clean["id"], df_road_clean[placa_r_idx]))
                map_dt_rot = dict(zip(df_road_clean["id"], df_road_clean.get("dt_roteirizacao", df_road_clean.index)))
                
                # Atualização segura via dicionários mapeados
                for idx, row in df_all.iterrows():
                    r_id = str(row["id"]).strip()
                    if r_id in map_placa_v:
                        df_all.at[idx, "placa_veiculo"] = map_placa_v[r_id]
                        df_all.at[idx, "status"] = "roteirizado"
                        row.setdefault("placa_road", map_placa_r[r_id])
                        row.setdefault("dt_roteirizacao", map_dt_rot[r_id])
        except Exception as ex:
            st.warning(f"Erro ao processar integração com a aba road: {ex}")

    # Cálculos dos blocos de KPIs superiores
    n_total = len(df_h)
    n_pend = len(df_h[df_h["status"].get("status", df_h["status"]) != "roteirizado"])
    n_rot = len(df_h[df_h["status"].get("status", df_h["status"]) == "roteirizado"])

    # Renderização da linha de métricas estruturadas
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Total de Notas</div>
          <div class="kpi-mini-value" style="color:#2563eb">{n_total}</div>
          <div class="kpi-mini-sub">registradas na data</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Pendentes</div>
          <div class="kpi-mini-value" style="color:#f59e0b">{n_pend}</div>
          <div class="kpi-mini-sub">aguardando roteirização</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Roteirizadas</div>
          <div class="kpi-mini-value" style="color:#10b981">{n_rot}</div>
          <div class="kpi-mini-sub">com placa definida</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Bloco Inferior: Lista detalhada de registos
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title">📋 Registros</span>
      <span class="card-count">{len(df_h)} resultados</span>
    </div>
    """, unsafe_allow_html=True)

    if df_h.empty:
        st.markdown(f'<div style="padding:1.5rem"><div class="al-i">Nenhum registro encontrado para os filtros selecionados.</div></div>', unsafe_allow_html=True)
    else:
        df_hd = dedup_columns(df_h[HIST_COLS].copy())
        
        # Limpeza estética e substituição de vazios para exibição limpa na tabela
        for _c2 in ["placa_veiculo", "dt_saida"]:
            if _c2 in df_hd.columns:
                df_hd[_c2] = df_hd[_c2].fillna("—").astype(str).replace("", "—")
        
        # Loop de renderização visual dos cartões em HTML para cada linha de registo
        for _, row_r in df_hd.iterrows():
            pr = str(row_r.get("placa_veiculo", "—")).strip()
            if pr == "" or pr == "nan":
                pr = "—"
                
            st.markdown(f"""
            <div class="nota-row">
                <div style="display:flex; flex-direction:column; gap:4px;">
                    <div style="font-weight:600;font-size:0.9rem;">ID Transf: {row_r.get("id","—")}</div>
                    <div style="color:var(--txt-sub);font-size:0.75rem;">📅 Saída: {row_r.get("dt_saida","—")} | 🏙️ {row_r.get("praca","—")}</div>
                </div>
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style="font-weight:700;color:var(--acc);font-size:.85rem;min-width:90px">{br(row_r["vltotal"])}</div>
                    {"<span class=\"placa-chip\">🚛 Veículo: " + pr + "</span>" if pr != "—" else "<span class=\"placa-chip\" style=\"background:#fffbeb;color:#b45309;\">⏳ Pendente</span>"}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True)
