import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io, base64, pathlib

st.set_page_config(
    page_title="Delly's — Sistema de Transferências",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Logo Delly's (base64 embutido) ─────────────────────────────────────────
LOGO_B64 = "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"
LOGO_MIME = "image/webp"

BG_IMAGE = "/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAJAAwADASIAAhEBAxEB/8QAHAAAAgMBAQEBAAAAAAAAAAAABQYEBwMCCAH/xABaEAABAwMCAgYFBQkOBAUFAQECAwQFEQASBiExEyJBUWFxBzJCgZEUI1JiobEVFiQzNENTcnOCkqKywdHhFyU1RFRjdIOTswgmNmSU8CZFVWWj0vH/xAAcAQACAwEBAQAAAAAAAAAAAAADBAECBQYHCP/EAD8RAAIBAgQDBgQDCAIBBQEBAAECAAMRIQQSMUFRBRMiYXGBkaEGMrHB0fAUFSNC4TNSYvFDU3KCoiQ0gv/aAAwDAQACEQMRAD8A..."

SCOPES = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]

@st.cache_resource(show_spinner=False)
def get_client():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    return get_client().open_by_key(st.secrets["spreadsheet_id"])

def get_sheet(name):
    ss = get_spreadsheet()
    try: return ss.worksheet(name)
    except gspread.WorksheetNotFound: return ss.add_worksheet(title=name, rows=5000, cols=20)

# ─── Colunas internas da aba "transferencias" ────────────────────────────────
# Mapeamento direto das colunas da planilha ROAD:
# PEDIDO → numped | NOTA FISCAL → numnota | CLIENTE → nomecliente
# DATA LIBERADO → dt_liberado | VENDEDOR → nomevend | SUPERVISOR → nomesup
# PESO → pesobrutotot | VALOR → vltotal | PRAÇA → praca
# CARREGAMENTO → numcarregamento | DESTINO → destino | PLACA ANTIGA → placa_road
TCOLS = [
    "id",
    "dt_transferencia",   # Data em que foi registrada a transferência
    "numped",             # PEDIDO
    "numnota",            # NOTA FISCAL
    "nomecliente",        # CLIENTE
    "dt_liberado",        # DATA LIBERADO
    "nomevend",           # VENDEDOR
    "nomesup",            # SUPERVISOR
    "pesobrutotot",       # PESO
    "vltotal",            # VALOR
    "praca",              # PRAÇA
    "numcarregamento",    # CARREGAMENTO
    "destino",            # DESTINO
    "placa_road",         # PLACA ANTIGA
    # Campos preenchidos pela Roteirização:
    "placa_veiculo",      # Nova placa informada na roteirização
    "dt_saida",           # Data de saída informada na roteirização
    "dt_roteirizacao",    # Data em que foi roteirizado
    "status",             # pendente / roteirizado
    "criado_em",
]

def ensure_header():
    ws = get_sheet("transferencias")
    if not ws.row_values(1):
        ws.update("A1", [TCOLS])
    else:
        hdr = ws.row_values(1)
        for col in TCOLS:
            if col not in hdr:
                ws.update_cell(1, len(hdr)+1, col)
                hdr = hdr + [col]
    return ws

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias():
    ws = ensure_header()
    try:
        data = ws.get_all_records(expected_headers=[])
    except Exception:
        vals = ws.get_all_values()
        if not vals or len(vals) < 2:
            return pd.DataFrame(columns=TCOLS)
        hdr = vals[0]
        data = [dict(zip(hdr, row)) for row in vals[1:]]
    if not data:
        return pd.DataFrame(columns=TCOLS)
    df = pd.DataFrame(data)
    for c in ["pesobrutotot","vltotal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in TCOLS:
        if c not in df.columns:
            df[c] = ""
    return df

def next_id(df):
    if df.empty: return 1
    v = pd.to_numeric(df["id"], errors="coerce").dropna()
    return int(v.max()+1) if len(v) else 1

def append_transf(row):
    ws = ensure_header()
    df = load_transferencias()
    row["id"] = next_id(df)
    row["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    row.setdefault("status", "pendente")
    row.setdefault("placa_veiculo", "")
    row.setdefault("placa_road", "")
    row.setdefault("dt_roteirizacao", "")
    row.setdefault("dt_saida", "")
    ws.append_row([str(row.get(c,"")) for c in TCOLS], value_input_option="USER_ENTERED")
    load_transferencias.clear()

def update_transf(tid, updates):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    hdr = data[0]
    for col in updates:
        if col not in hdr:
            ws.update_cell(1, len(hdr)+1, col)
            hdr = hdr + [col]
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(hdr,row)).get("id","") == str(tid):
            for col,val in updates.items():
                if col in hdr:
                    ws.update_cell(i, hdr.index(col)+1, str(val))
            break
    load_transferencias.clear()

def delete_transf(tid):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    hdr = data[0]
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(hdr,row)).get("id","") == str(tid):
            ws.delete_rows(i)
            break
    load_transferencias.clear()

def check_dup(numnota, dt):
    df = load_transferencias()
    if df.empty: return False
    return bool(((df["numnota"].astype(str)==str(numnota))&(df["dt_transferencia"].astype(str)==str(dt))).any())

@st.cache_data(ttl=60, show_spinner=False)
def load_road():
    """
    Carrega a planilha ROAD e normaliza os nomes das colunas.
    Colunas esperadas (conforme imagem da planilha):
    PEDIDO | NOTA FISCAL | FILIAL | CLIENTE | POSICAO | DATA LIBERADO |
    HORA | MINUTO | DATA DE ENTREGA | VENDEDOR | SUPERVISOR | PESO |
    VALOR | CIDADE | PRAÇA | CARREGAMENTO | DESTINO | PLACA ANTIGA |
    LONGITUDE | LATITUDE
    """
    try:
        ws = get_sheet("ROAD")
        try:
            data = ws.get_all_records(expected_headers=[])
        except Exception:
            vals = ws.get_all_values()
            if not vals or len(vals) < 2:
                return pd.DataFrame()
            hdr = vals[0]
            data = [dict(zip(hdr, row)) for row in vals[1:]]
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        # Normaliza: maiúsculas + strip
        df.columns = [str(c).upper().strip() for c in df.columns]
        # Garante que NOTA FISCAL e PEDIDO sejam string sem decimais
        for c in ["NOTA FISCAL", "PEDIDO"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.split(".").str[0].str.strip()
        return df
    except:
        return pd.DataFrame()

def buscar_nota(numnota):
    """
    Busca a nota na planilha ROAD e retorna um dict com os campos mapeados.
    """
    df = load_road()
    if df.empty: return None
    row = df[df["NOTA FISCAL"].astype(str) == numnota.strip()]
    if row.empty: return None
    r = row.iloc[0]

    def safe(col):
        v = r.get(col, "")
        if str(v) in ("nan", "None", "", None): return ""
        v = str(v)
        return v[:-2] if v.endswith(".0") else v

    # Peso: coluna "PESO"
    try:
        peso = float(str(r.get("PESO", "0")).replace(",", ".").strip())
    except:
        peso = 0.0

    # Valor: coluna "VALOR"
    try:
        vl_raw = str(r.get("VALOR", "0")).replace("R$", "").replace(".", "").replace(",", ".").strip()
        vl = float(vl_raw)
    except:
        vl = 0.0

    # Praça: coluna "PRAÇA" (pode aparecer com encoding variado)
    praca = ""
    for col_name in ["PRAÇA", "PRACA", "PRAA", "PRAçA", "PRAÃ‡A"]:
        praca = safe(col_name)
        if praca: break

    return {
        "numped":          safe("PEDIDO"),
        "numnota":         safe("NOTA FISCAL"),
        "nomecliente":     safe("CLIENTE"),
        "dt_liberado":     safe("DATA LIBERADO"),
        "nomevend":        safe("VENDEDOR"),
        "nomesup":         safe("SUPERVISOR"),
        "pesobrutotot":    peso,
        "vltotal":         vl,
        "praca":           praca,
        "numcarregamento": safe("CARREGAMENTO"),
        "destino":         safe("DESTINO"),
        "placa_road":      safe("PLACA ANTIGA"),
    }

# ─── Utilitários de formatação ───────────────────────────────────────────────
def br(v):
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("","nan","None","—"): return "—"
    s = str(s).strip()
    if len(s)==10 and s[2]=="/" and s[5]=="/": return s
    if len(s)>=10 and s[4]=="-" and s[7]=="-":
        parts = s[:10].split("-")
        if len(parts)==3: return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s

def fmt_col(df, col="dt_transferencia"):
    df = df.copy()
    if col in df.columns: df[col] = df[col].apply(fmt_date)
    return df

def to_iso(dt_str):
    if not dt_str or dt_str=="—": return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str)==10 and dt_str[2]=="/" and dt_str[5]=="/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

# ─── Session state ────────────────────────────────────────────────────────────
if "nav_date" not in st.session_state:
    st.session_state.nav_date = date.today()
if "ver_todas" not in st.session_state:
    st.session_state.ver_todas = False

today_str = date.today().strftime("%d/%m/%Y")

# ─── Logo HTML ────────────────────────────────────────────────────────────────
_logo_html = (
    f'''<img src="data:{LOGO_MIME};base64,{LOGO_B64}"
         style="width:44px;height:44px;border-radius:50%;
                object-fit:cover;object-position:center;
                box-shadow:0 0 0 2px rgba(249,115,22,.5),
                           0 4px 16px rgba(0,0,0,.5);"
         alt="Delly's Food Service" />'''
    if LOGO_B64 else
    '<div class="topnav-logo">🚛</div>'
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
  --bg: #0b0f1a;
  --sur: #111827;
  --sur2: #1a2235;
  --sur3: #1f2d42;
  --bdr: rgba(255,255,255,0.07);
  --bdr2: rgba(255,255,255,0.12);
  --acc: #f97316;
  --acc2: #fb923c;
  --acc3: #fed7aa;
  --grn: #10b981;
  --grn2: #34d399;
  --blu: #3b82f6;
  --blu2: #60a5fa;
  --txt: #f0f4ff;
  --txt2: #8899aa;
  --mut: #4a5568;
  --red: #ef4444;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body, [class*="css"], .stApp {{
  font-family: 'Outfit', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--txt) !important;
}}

.stApp {{
  position: relative;
  isolation: isolate;
}}

.stApp::before {{
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: url("data:image/jpeg;base64,{BG_IMAGE}");
  background-size: cover;
  background-position: center center;
  background-attachment: fixed;
  filter: blur(6px) brightness(0.18) saturate(0.7);
  transform: scale(1.05);
}}

.stApp::after {{
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: linear-gradient(180deg,
    rgba(11,15,26,0.72) 0%,
    rgba(11,15,26,0.55) 50%,
    rgba(11,15,26,0.75) 100%);
}}

.stApp > * {{ position: relative; z-index: 1; }}
section[data-testid="stVerticalBlock"] {{ position: relative; z-index: 1; }}

::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(249,115,22,0.3); border-radius: 99px; }}

#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
section[data-testid="stSidebar"] {{ display: none !important; }}

.main .block-container {{
  padding: 0 !important;
  max-width: 100% !important;
  position: relative;
  z-index: 1;
}}

.topnav {{
  position: sticky; top: 0; z-index: 999;
  background: rgba(11, 15, 26, 0.92);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--bdr2);
  padding: 0 2rem;
  display: flex; align-items: center; justify-content: space-between;
  height: 64px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}}

.topnav-logo {{
  width: 44px; height: 44px;
  background: linear-gradient(135deg, #f97316, #ea580c);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem;
  box-shadow: 0 4px 16px rgba(249,115,22,0.4);
  flex-shrink: 0;
}}

.topnav-name {{
  font-family: 'Outfit', sans-serif;
  font-size: 1.25rem; font-weight: 800; letter-spacing: -0.03em;
  background: linear-gradient(135deg, #f97316, #fb923c);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}

.topnav-sub {{
  font-size: 0.65rem; color: var(--mut);
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase; letter-spacing: 0.08em; line-height: 1; margin-top: 1px;
}}

.topnav-right {{ display: flex; align-items: center; gap: 16px; }}

.nav-status {{
  width: 8px; height: 8px; background: var(--grn); border-radius: 50%;
  box-shadow: 0 0 8px var(--grn); animation: pulse 2s infinite;
}}

@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}

.page-header {{
  margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--bdr);
  display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
}}

.page-eyebrow {{
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--acc2); margin-bottom: 0.4rem;
  display: flex; align-items: center; gap: 6px;
}}
.page-eyebrow::before {{ content: ''; display: inline-block; width: 20px; height: 2px; background: var(--acc); border-radius: 99px; }}

.page-title {{ font-family: 'Outfit', sans-serif; font-size: 2.4rem; font-weight: 900; letter-spacing: -0.04em; color: var(--txt); line-height: 1; }}

.period-pill {{
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2);
  border-radius: 99px; padding: 3px 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700; color: var(--blu2);
}}

.kpi-card {{
  background: var(--sur); border: 1px solid var(--bdr); border-radius: 16px;
  padding: 1.4rem 1.6rem 1.2rem; position: relative; overflow: hidden;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}}
.kpi-card:hover {{ transform: translateY(-3px); border-color: var(--bdr2); box-shadow: 0 12px 32px rgba(0,0,0,0.3); }}
.kpi-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: 16px 16px 0 0; }}
.kpi-card.orange::before {{ background: linear-gradient(90deg, #f97316, #fb923c); }}
.kpi-card.blue::before   {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
.kpi-card.purple::before {{ background: linear-gradient(90deg, #8b5cf6, #a78bfa); }}
.kpi-card.green::before  {{ background: linear-gradient(90deg, #10b981, #34d399); }}
.kpi-card-bg {{ position: absolute; bottom: -20px; right: -20px; font-size: 5rem; opacity: 0.04; pointer-events: none; filter: blur(1px); }}
.kpi-label {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--mut); margin-bottom: 0.75rem; }}
.kpi-value {{ font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 800; letter-spacing: -0.03em; color: var(--txt); line-height: 1; margin-bottom: 0.35rem; }}
.kpi-value.sm {{ font-size: 1.4rem; }}
.kpi-sub {{ font-size: 0.72rem; color: var(--txt2); }}
.kpi-icon {{ position: absolute; top: 1.2rem; right: 1.2rem; width: 36px; height: 36px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 1rem; }}
.kpi-icon.orange {{ background: rgba(249,115,22,0.12); }}
.kpi-icon.blue   {{ background: rgba(59,130,246,0.12); }}
.kpi-icon.purple {{ background: rgba(139,92,246,0.12); }}
.kpi-icon.green  {{ background: rgba(16,185,129,0.12); }}

.chart-card {{ background: var(--sur); border: 1px solid var(--bdr); border-radius: 16px; padding: 1.4rem 1.6rem; margin-bottom: 1rem; }}
.chart-title {{ font-family: 'Outfit', sans-serif; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--txt2); margin-bottom: 1rem; display: flex; align-items: center; gap: 6px; }}
.chart-title::before {{ content: ''; display: inline-block; width: 3px; height: 14px; background: var(--acc); border-radius: 99px; }}

.table-wrap {{ background: var(--sur); border: 1px solid var(--bdr); border-radius: 16px; overflow: hidden; margin-bottom: 1.5rem; }}
.table-header {{ padding: 1rem 1.5rem; border-bottom: 1px solid var(--bdr); display: flex; align-items: center; justify-content: space-between; background: linear-gradient(90deg, var(--sur) 0%, var(--sur2) 100%); }}
.table-title {{ font-family: 'Outfit', sans-serif; font-size: 0.88rem; font-weight: 700; color: var(--txt); display: flex; align-items: center; gap: 8px; }}
.table-count {{ font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--mut); background: var(--sur3); border: 1px solid var(--bdr2); border-radius: 99px; padding: 3px 12px; }}

.sdiv {{ display: flex; align-items: center; gap: 12px; margin: 1.75rem 0 1.25rem; }}
.sdiv-line {{ flex: 1; height: 1px; background: var(--bdr); }}
.sdiv-txt {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.14em; color: var(--mut); white-space: nowrap; display: flex; align-items: center; gap: 5px; }}

.al-s {{ background: rgba(16,185,129,.08); border: 1px solid rgba(16,185,129,.2); color: var(--grn2); border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }}
.al-e {{ background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); color: #fca5a5; border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }}
.al-i {{ background: rgba(59,130,246,.08); border: 1px solid rgba(59,130,246,.2); color: var(--blu2); border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }}
.al-w {{ background: rgba(245,158,11,.08); border: 1px solid rgba(245,158,11,.2); color: #fcd34d; border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }}

.road-box {{ background: linear-gradient(135deg, var(--sur2) 0%, rgba(26,18,5,0.8) 100%); border: 1px solid rgba(249,115,22,0.2); border-left: 3px solid var(--acc); border-radius: 12px; padding: 1rem 1.25rem; margin: .75rem 0; }}
.road-title {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--acc2); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 6px; }}

.nota-card {{ background: var(--sur2); border: 1px solid var(--bdr); border-radius: 10px; padding: .75rem 1rem; margin-bottom: 0.4rem; transition: border-color 0.15s, transform 0.15s; }}
.nota-card:hover {{ border-color: var(--bdr2); transform: translateX(2px); }}
.placa-chip {{ display: inline-flex; align-items: center; gap: 4px; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.25); border-radius: 7px; padding: 2px 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; font-weight: 700; color: #fcd34d; letter-spacing: 0.04em; }}

.stTextInput > div > div > input, .stDateInput > div > div > input {{
  background-color: var(--sur2) !important; color: var(--txt) !important;
  border: 1px solid var(--bdr2) !important; border-radius: 10px !important;
  font-family: 'Outfit', sans-serif !important; font-size: 0.88rem !important; padding: 0.55rem 0.9rem !important;
}}
.stTextInput > div > div > input:focus {{ border-color: var(--acc) !important; box-shadow: 0 0 0 3px rgba(249,115,22,0.1) !important; }}
.stSelectbox > div > div {{ background-color: var(--sur2) !important; border: 1px solid var(--bdr2) !important; border-radius: 10px !important; color: var(--txt) !important; }}
.stTextArea textarea {{ background-color: var(--sur2) !important; color: var(--txt) !important; border: 1px solid var(--bdr2) !important; border-radius: 10px !important; font-family: 'Outfit', sans-serif !important; }}
.stTextInput label, .stDateInput label, .stSelectbox label, .stTextArea label, .stNumberInput label {{ color: var(--txt2) !important; font-size: 0.7rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; font-family: 'Outfit', sans-serif !important; }}

.stButton > button {{ background: linear-gradient(135deg, var(--acc), #ea580c) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; font-family: 'Outfit', sans-serif !important; font-size: 0.84rem !important; transition: all 0.2s !important; box-shadow: 0 4px 16px rgba(249,115,22,0.25) !important; letter-spacing: 0.02em !important; }}
.stButton > button:hover {{ transform: translateY(-1px) !important; box-shadow: 0 6px 24px rgba(249,115,22,0.4) !important; }}
.stDownloadButton > button {{ background: var(--sur2) !important; color: var(--txt2) !important; border: 1px solid var(--bdr2) !important; border-radius: 10px !important; font-weight: 600 !important; box-shadow: none !important; font-family: 'Outfit', sans-serif !important; }}
.stDownloadButton > button:hover {{ color: var(--txt) !important; border-color: var(--bdr2) !important; transform: none !important; }}

.stDataFrame {{ border-radius: 0 0 16px 16px !important; overflow: hidden !important; }}
.stDataFrame thead tr th {{ background: var(--sur2) !important; color: var(--txt2) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.62rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; border-bottom: 1px solid var(--bdr2) !important; padding: 10px 12px !important; }}
.stDataFrame tbody tr:nth-child(even) td {{ background: rgba(255,255,255,0.015) !important; }}
.stDataFrame tbody tr:hover td {{ background: rgba(249,115,22,0.04) !important; }}
.stDataFrame tbody td {{ font-family: 'Outfit', sans-serif !important; font-size: 0.82rem !important; border-bottom: 1px solid rgba(255,255,255,0.03) !important; color: var(--txt) !important; padding: 9px 12px !important; }}

.stCheckbox label, .stRadio label span {{ color: var(--txt2) !important; font-family: 'Outfit', sans-serif !important; font-size: 0.84rem !important; }}
.stCaption {{ color: var(--mut) !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.65rem !important; }}
[data-testid="metric-container"] {{ background: var(--sur) !important; border: 1px solid var(--bdr) !important; border-radius: 12px !important; padding: 1rem !important; }}
input[type="date"] {{ color-scheme: dark !important; }}

.nav-radio div[data-testid="stRadio"] > label {{ display: none; }}
.nav-radio div[data-testid="stRadio"] > div {{
  display: flex !important; flex-direction: row !important; gap: 4px !important;
  padding: 10px 2.5rem !important; background: rgba(11,15,26,0.85) !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important; backdrop-filter: blur(12px) !important;
}}
.nav-radio div[data-testid="stRadio"] > div > label {{
  display: flex !important; align-items: center !important; gap: 8px !important;
  padding: 8px 18px !important; border-radius: 10px !important; font-size: 0.8rem !important;
  font-weight: 600 !important; cursor: pointer !important; border: 1px solid transparent !important;
  color: #8899aa !important; font-family: 'Outfit', sans-serif !important;
  text-transform: uppercase !important; letter-spacing: 0.04em !important; transition: all 0.2s !important;
}}
.nav-radio div[data-testid="stRadio"] > div > label:hover {{ color: #f0f4ff !important; background: rgba(255,255,255,0.05) !important; border-color: rgba(255,255,255,0.1) !important; }}
.nav-radio div[data-testid="stRadio"] > div > label[data-selected="true"] {{ color: #fb923c !important; background: rgba(249,115,22,0.1) !important; border-color: rgba(249,115,22,0.25) !important; }}
.nav-radio div[data-testid="stRadio"] > div > label > div:first-child {{ display: none !important; }}

.info-panel {{ background: var(--sur2); border: 1px solid var(--bdr); border-radius: 12px; padding: 1.1rem 1.3rem; margin-top: 1rem; }}
.info-panel-title {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--mut); margin-bottom: 0.7rem; }}
.info-step {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0.55rem; font-size: 0.8rem; color: var(--txt2); line-height: 1.5; }}
.info-step-num {{ min-width: 20px; height: 20px; background: rgba(249,115,22,0.12); border: 1px solid rgba(249,115,22,0.25); border-radius: 50%; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 700; color: var(--acc2); display: flex; align-items: center; justify-content: center; margin-top: 1px; flex-shrink: 0; }}
</style>
""", unsafe_allow_html=True)

# ─── Top Nav ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="topnav">
  <div style="display:flex;align-items:center;gap:12px">
    {_logo_html}
    <div>
      <div class="topnav-name">Delly's Food Service</div>
      <div class="topnav-sub">Sistema de Transferências</div>
    </div>
  </div>
  <div class="topnav-right">
    <div class="nav-status"></div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('''
<style>
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container { padding: 0 !important; }
</style>
''', unsafe_allow_html=True)

# ─── Navigation ───────────────────────────────────────────────────────────────
st.markdown('<div class="nav-radio">', unsafe_allow_html=True)
pagina = st.radio(
    "nav",
    ["📊  Dashboard", "➕  Nova Transferência", "📋  Histórico", "🗺️  Roteirização"],
    horizontal=True, label_visibility="collapsed", key="nav_main"
)
st.markdown('</div>', unsafe_allow_html=True)

# ─── Barra de filtros global ──────────────────────────────────────────────────
st.markdown('<div style="padding: 0.6rem 2.5rem; background: rgba(11,15,26,0.7); border-bottom: 1px solid rgba(255,255,255,0.05); display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap;">', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns([2,2,4])
with fc1:
    data_filtro = st.date_input("📅 Data", value=st.session_state.nav_date,
                                 key="data_global", format="DD/MM/YYYY")
    st.session_state.nav_date = data_filtro
with fc2:
    ver_todas = st.checkbox("📋 Ver todas as datas", value=st.session_state.ver_todas, key="ver_todas_cb")
    st.session_state.ver_todas = ver_todas
with fc3:
    if st.button("🔄 Atualizar Dados", key="refresh_btn"):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

data_str = data_filtro.isoformat()
data_display = data_filtro.strftime("%d/%m/%Y")

df_all = load_transferencias()
df = df_all.copy() if ver_todas else (
    df_all[df_all["dt_transferencia"]==data_str].copy()
    if not df_all.empty else pd.DataFrame(columns=TCOLS)
)
periodo_txt = "Todas as datas" if ver_todas else data_display

st.markdown('<div style="padding: 1.5rem 2.5rem; max-width: 1600px; margin: 0 auto;">', unsafe_allow_html=True)

# ─── Colunas padronizadas para exibição ───────────────────────────────────────
# Estas são as colunas que aparecem nas tabelas de Histórico e Roteirização
STD_COLS_BASE = [
    "numped",          # Pedido
    "numnota",         # Nota Fiscal
    "nomecliente",     # Cliente
    "dt_liberado",     # Data Liberado
    "nomevend",        # Vendedor
    "pesobrutotot",    # Peso
    "vltotal",         # Valor
    "praca",           # Praça
    "numcarregamento", # Carregamento
    "destino",         # Destino
    "placa_road",      # Placa Antiga
]

STD_CONFIG_BASE = {
    "numped":          st.column_config.TextColumn("📋 Pedido",          width=110),
    "numnota":         st.column_config.TextColumn("🧾 Nota Fiscal",      width=105),
    "nomecliente":     st.column_config.TextColumn("👤 Cliente",          width=200),
    "dt_liberado":     st.column_config.TextColumn("📅 Dt. Liberado",     width=110),
    "nomevend":        st.column_config.TextColumn("🧑‍💼 Vendedor",        width=170),
    "pesobrutotot":    st.column_config.NumberColumn("⚖️ Peso (kg)",       format="%.3f", width=100),
    "vltotal":         st.column_config.NumberColumn("💰 Valor (R$)",      format="R$ %.2f", width=130),
    "praca":           st.column_config.TextColumn("🏙️ Praça",            width=140),
    "numcarregamento": st.column_config.TextColumn("📦 Carregamento",     width=120),
    "destino":         st.column_config.TextColumn("📍 Destino",          width=170),
    "placa_road":      st.column_config.TextColumn("🚛 Placa Antiga",     width=120),
}

# ═══ DASHBOARD ════════════════════════════════════════════════════════════════
if pagina == "📊  Dashboard":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Visão Geral</div>
        <div class="page-title">Dashboard</div>
        <div style="font-size:0.82rem;color:var(--txt2);margin-top:0.4rem">Período: <span class="period-pill">📅 {periodo_txt}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    n  = len(df)
    vt = df["vltotal"].sum() if not df.empty else 0
    pt = df["pesobrutotot"].sum() if not df.empty else 0
    nd = df["nomecliente"].nunique() if not df.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    for col, klass, icon, label, value, sub in [
        (k1,"orange","📦","Notas",str(n),"transferências no período"),
        (k2,"blue","💰","Valor Total",br(vt),"valor acumulado"),
        (k3,"purple","⚖️","Peso Bruto",f"{pt:,.0f} kg","total em kg"),
        (k4,"green","🏪","Clientes",str(nd),"clientes distintos"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-card {klass}">
              <div class="kpi-card-bg">{icon}</div>
              <div class="kpi-icon {klass}">{icon}</div>
              <div class="kpi-label">{label}</div>
              <div class="kpi-value {'sm' if len(value)>8 else ''}">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df.empty:
        try:
            import plotly.graph_objects as go
            T = dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#8899aa",family="Outfit"),margin=dict(l=10,r=10,t=32,b=10))
            GC = "rgba(255,255,255,0.05)"

            r1a, r1b = st.columns([3,2])
            with r1a:
                st.markdown('<div class="chart-card"><div class="chart-title">Valor por Data de Transferência</div>', unsafe_allow_html=True)
                if ver_todas and not df.empty:
                    pd_ = df.groupby("dt_transferencia").agg(valor=("vltotal","sum")).reset_index().sort_values("dt_transferencia").tail(30)
                    pd_["dt_f"] = pd_["dt_transferencia"].apply(fmt_date)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=pd_["dt_f"],y=pd_["valor"],marker=dict(color=pd_["valor"],colorscale=[[0,"#7c2d12"],[0.5,"#f97316"],[1,"#fed7aa"]],showscale=False),hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>"))
                    fig.add_trace(go.Scatter(x=pd_["dt_f"],y=pd_["valor"],mode="lines",line=dict(color="#fb923c",width=2,dash="dot"),showlegend=False))
                    fig.update_layout(**T,height=260,xaxis=dict(gridcolor=GC,tickfont=dict(size=10)),yaxis=dict(gridcolor=GC,tickformat=",.0f",tickfont=dict(size=10)))
                    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
                else:
                    st.markdown(f'<div class="al-i">📅 Data selecionada: <strong>{data_display}</strong> — {n} nota(s) — {br(vt)}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with r1b:
                st.markdown('<div class="chart-card"><div class="chart-title">Status das Notas</div>', unsafe_allow_html=True)
                np_ = int((df["status"]=="pendente").sum()) if not df.empty else 0
                nr_ = int((df["status"]=="roteirizado").sum()) if not df.empty else 0
                if n>0:
                    fig2 = go.Figure(go.Pie(labels=["⏳ Pendentes","✅ Roteirizadas"],values=[np_,nr_],hole=0.62,marker=dict(colors=["#ef4444","#10b981"],line=dict(color="#0b0f1a",width=3)),textinfo="percent+value",hovertemplate="<b>%{label}</b><br>%{value} notas<extra></extra>"))
                    fig2.update_layout(**T,height=260,legend=dict(orientation="h",yanchor="bottom",y=-0.2,xanchor="center",x=0.5,font=dict(size=11)))
                    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
                else:
                    st.markdown('<div class="al-i">Sem dados para o período.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            r2a, r2b = st.columns(2)
            with r2a:
                st.markdown('<div class="chart-card"><div class="chart-title">Top Clientes por Valor</div>', unsafe_allow_html=True)
                cli = df.groupby("nomecliente")["vltotal"].sum().sort_values(ascending=True).tail(8).reset_index()
                if not cli.empty:
                    fig3 = go.Figure(go.Bar(x=cli["vltotal"],y=cli["nomecliente"],orientation="h",marker=dict(color=cli["vltotal"],colorscale=[[0,"#1e3a5f"],[0.5,"#3b82f6"],[1,"#bfdbfe"]],showscale=False),hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"))
                    fig3.update_layout(**T,height=260,xaxis=dict(gridcolor=GC,tickformat=",.0f"),yaxis=dict(gridcolor="rgba(0,0,0,0)",tickfont=dict(size=10)))
                    st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            with r2b:
                st.markdown('<div class="chart-card"><div class="chart-title">Valor por Supervisor</div>', unsafe_allow_html=True)
                sup = df.groupby("nomesup")["vltotal"].sum().sort_values(ascending=False).reset_index()
                if not sup.empty:
                    COLS_P = ["#8b5cf6","#a78bfa","#c4b5fd","#7c3aed","#6d28d9","#5b21b6"]
                    fig4 = go.Figure(go.Pie(labels=sup["nomesup"],values=sup["vltotal"],hole=0.5,marker=dict(colors=COLS_P[:len(sup)],line=dict(color="#0b0f1a",width=2)),hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"))
                    fig4.update_layout(**T,height=260,legend=dict(orientation="h",yanchor="bottom",y=-0.25,xanchor="center",x=0.5,font=dict(size=10)))
                    st.plotly_chart(fig4,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

        except ImportError:
            st.info("Adicione `plotly` ao requirements.txt para ativar os gráficos.")

    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📋 Registro de Transferências</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

    cf1, cf2 = st.columns([3,1])
    with cf1:
        busca = st.text_input("Buscar", key="db", label_visibility="collapsed", placeholder="🔍  Nota, cliente, destino, placa...")
    with cf2:
        fst = st.selectbox("Status", ["Todos","pendente","roteirizado"], key="dst", label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst!="Todos": df_s = df_s[df_s["status"]==fst]
        if busca:
            m = df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_s = df_s[m]

    if not df_s.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w: df_s.to_excel(w,index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel", out, file_name=f"transf_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Dashboard usa colunas base + status
    DASH_COLS = [c for c in STD_COLS_BASE + ["status"] if c in df_s.columns]
    DASH_CONFIG = {**STD_CONFIG_BASE, "status": st.column_config.TextColumn("📌 Status", width=100)}

    st.markdown(f"""
    <div class="table-wrap">
      <div class="table-header">
        <span class="table-title">📋 Transferências</span>
        <span class="table-count">{len(df_s)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_s[DASH_COLS] if not df_s.empty else df_s,
        use_container_width=True, hide_index=True,
        column_config=DASH_CONFIG
    )

    if not df.empty:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🗑️ Excluir Registro</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        ids = df["id"].astype(str).tolist()
        cd1, cd2 = st.columns([3,1])
        with cd1:
            del_id = st.selectbox("Selecionar ID", ["—"]+ids, label_visibility="collapsed")
        with cd2:
            if del_id!="—" and st.button("🗑️ Excluir",type="secondary"):
                delete_transf(int(del_id))
                st.success("✅ Registro excluído!")
                st.rerun()

# ═══ NOVA TRANSFERÊNCIA ═══════════════════════════════════════════════════════
elif pagina == "➕  Nova Transferência":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Faturamento</div>
        <div class="page-title">Nova Transferência</div>
        <div style="font-size:0.82rem;color:var(--txt2);margin-top:0.4rem">Data selecionada: <span class="period-pill">📅 {data_display}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_f, col_s = st.columns([1.4,0.6])

    with col_f:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🧾 Buscar Nota Fiscal</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        cd, cn, cb = st.columns([1.2,2,1])
        with cd:
            dt_t = st.date_input("Data da Transferência", value=data_filtro, label_visibility="visible", format="DD/MM/YYYY")
        with cn:
            nota_inp = st.text_input("Número da Nota Fiscal", placeholder="Ex: 398234", key="nn")
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar_btn = st.button("🔍 Buscar", use_container_width=True)

        if "cur" not in st.session_state: st.session_state.cur = None

        if buscar_btn and nota_inp.strip():
            with st.spinner("Consultando base ROAD..."):
                r = buscar_nota(nota_inp.strip())
            if r:
                st.session_state.cur = r
                st.markdown('<div class="al-s">✅ Nota encontrada! Dados preenchidos automaticamente.</div>', unsafe_allow_html=True)
            else:
                st.session_state.cur = None
                st.markdown(f'<div class="al-e">❌ Nota "{nota_inp.strip()}" não encontrada na base ROAD.</div>', unsafe_allow_html=True)

        cur = st.session_state.cur
        if cur:
            st.markdown('<div class="road-box"><div class="road-title">✅ Dados encontrados na base ROAD</div></div>', unsafe_allow_html=True)

            # Linha 1: Pedido | Nota Fiscal | Carregamento
            a, b, c_ = st.columns(3)
            with a: st.text_input("📋 Pedido",          value=cur["numped"]          or "—", disabled=True)
            with b: st.text_input("🧾 Nota Fiscal",      value=cur["numnota"],                disabled=True)
            with c_: st.text_input("📦 Carregamento",    value=cur["numcarregamento"] or "—", disabled=True)

            # Linha 2: Cliente | Data Liberado | Vendedor
            a2, b2, c2 = st.columns(3)
            with a2: st.text_input("👤 Cliente",         value=cur["nomecliente"],             disabled=True)
            with b2: st.text_input("📅 Data Liberado",   value=cur["dt_liberado"]    or "—", disabled=True)
            with c2: st.text_input("🧑‍💼 Vendedor",      value=cur["nomevend"]        or "—", disabled=True)

            # Linha 3: Supervisor | Praça | Destino
            a3, b3, c3 = st.columns(3)
            with a3: st.text_input("👔 Supervisor",      value=cur["nomesup"]         or "—", disabled=True)
            with b3: st.text_input("🏙️ Praça",           value=cur["praca"]           or "—", disabled=True)
            with c3: st.text_input("📍 Destino",         value=cur["destino"]         or "—", disabled=True)

            # Linha 4: Peso | Valor | Placa Antiga
            a4, b4, c4 = st.columns(3)
            with a4: st.text_input("⚖️ Peso (kg)",       value=f"{cur['pesobrutotot']:.3f}".replace(".",","), disabled=True)
            with b4: st.text_input("💰 Valor Total",      value=br(cur["vltotal"]),              disabled=True)
            with c4:
                placa_antiga = cur.get("placa_road","") or "—"
                st.text_input("🚛 Placa Antiga",          value=placa_antiga,                    disabled=True)

            if cur.get("placa_road"):
                st.markdown(f'<div class="al-w">⚠️ Esta nota já tinha a placa <strong>{cur["placa_road"]}</strong> na entrega anterior.</div>', unsafe_allow_html=True)

            st.markdown('<div class="al-i">💡 A <strong>Nova Placa</strong> e <strong>Data de Saída</strong> serão informadas na aba <strong>Roteirização</strong>.</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True):
                dt_s = dt_t.isoformat()
                if check_dup(cur["numnota"], dt_s):
                    st.markdown(f'<div class="al-e">❌ Nota {cur["numnota"]} já registrada em {fmt_date(dt_s)}.</div>', unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        append_transf({
                            "dt_transferencia": dt_s,
                            "numped":          cur["numped"],
                            "numnota":         cur["numnota"],
                            "nomecliente":     cur["nomecliente"],
                            "dt_liberado":     cur["dt_liberado"],
                            "nomevend":        cur["nomevend"],
                            "nomesup":         cur["nomesup"],
                            "pesobrutotot":    cur["pesobrutotot"],
                            "vltotal":         cur["vltotal"],
                            "praca":           cur["praca"],
                            "numcarregamento": cur["numcarregamento"],
                            "destino":         cur["destino"],
                            "placa_road":      cur.get("placa_road",""),
                        })
                    st.success(f"✅ Transferência registrada! Nota **{cur['numnota']}** aguarda roteirização.")
                    st.session_state.cur = None
                    st.balloons()
                    st.rerun()

    with col_s:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📅 Notas do Dia</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        df_hj = df_all[df_all["dt_transferencia"]==data_str] if not df_all.empty else pd.DataFrame()
        if df_hj.empty:
            st.markdown('<div class="al-i">📭 Nenhuma nota registrada nesta data.</div>', unsafe_allow_html=True)
        else:
            tv = df_hj["vltotal"].sum()
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;margin-bottom:.6rem;border-bottom:1px solid rgba(255,255,255,0.06)">
              <span style="color:#8899aa;font-size:.76rem;font-family:'JetBrains Mono',monospace">{len(df_hj)} nota(s)</span>
              <span style="color:#fb923c;font-weight:700;font-size:.88rem;font-family:'Outfit',sans-serif">{br(tv)}</span>
            </div>
            """, unsafe_allow_html=True)
            for _, row in df_hj.iterrows():
                pl = row.get("placa_veiculo","")
                pl_h = f'<span class="placa-chip">🚗 {pl}</span>' if pl else '<span style="color:#ef4444;font-size:.7rem;font-family:JetBrains Mono,monospace">⏳ Pendente</span>'
                st.markdown(f"""
                <div class="nota-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f0f4ff;font-size:.88rem">{row['numnota']}</div>
                      <div style="color:#8899aa;font-size:.73rem;margin-top:2px">{str(row.get('nomecliente',''))[:26]}</div>
                      <div style="color:#8899aa;font-size:.68rem;margin-top:2px">📅 {row.get('dt_liberado','—')}</div>
                    </div>
                    <div style="text-align:right">
                      <div style="color:#fb923c;font-weight:700;font-size:.8rem;margin-bottom:4px">{br(row['vltotal'])}</div>
                      {pl_h}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("""
        <div class="info-panel">
          <div class="info-panel-title">💡 Fluxo do Sistema</div>
          <div class="info-step"><div class="info-step-num">1</div><span><strong style="color:#f0f4ff">Faturamento</strong> busca a nota e registra a transferência</span></div>
          <div class="info-step"><div class="info-step-num">2</div><span><strong style="color:#f0f4ff">Roteirização</strong> informa a nova placa e data de saída</span></div>
          <div class="info-step"><div class="info-step-num">3</div><span><strong style="color:#fb923c">Histórico</strong> mostra o registro completo da operação</span></div>
        </div>
        """, unsafe_allow_html=True)

# ═══ HISTÓRICO ════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Faturamento</div>
        <div class="page-title">Histórico</div>
        <div style="font-size:0.82rem;color:var(--txt2);margin-top:0.4rem">Período: <span class="period-pill">📅 {periodo_txt}</span> — {len(df)} registro(s)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cf1, cf2, cf3 = st.columns([3,1,1])
    with cf1:
        busca = st.text_input("Buscar", key="hb", label_visibility="collapsed", placeholder="🔍  Nota, cliente, placa, destino...")
    with cf2:
        fst = st.selectbox("Status", ["Todos","pendente","roteirizado"], key="hst", label_visibility="collapsed")
    with cf3:
        sups = ["Todos"]+(sorted(df["nomesup"].dropna().unique().tolist()) if not df.empty else [])
        fsup = st.selectbox("Supervisor", sups, key="hsup", label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst!="Todos": df_s = df_s[df_s["status"]==fst]
        if fsup!="Todos": df_s = df_s[df_s["nomesup"]==fsup]
        if busca:
            m = df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_s = df_s[m]

    if not df_s.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w: df_s.to_excel(w,index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel", out, file_name=f"historico_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Histórico: colunas padronizadas (sem placa nova / dt_saida — essas ficam na Roteirização)
    HIST_COLS = [c for c in STD_COLS_BASE if c in df_s.columns]

    st.markdown(f"""
    <div class="table-wrap">
      <div class="table-header">
        <span class="table-title">📋 Todas as Transferências</span>
        <span class="table-count">{len(df_s)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_s[HIST_COLS].sort_values("numped", ascending=False) if not df_s.empty else df_s,
        use_container_width=True, hide_index=True,
        column_config=STD_CONFIG_BASE
    )

# ═══ ROTEIRIZAÇÃO ═════════════════════════════════════════════════════════════
elif pagina == "🗺️  Roteirização":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Roteirização</div>
        <div class="page-title">Roteirizar Notas</div>
        <div style="font-size:0.82rem;color:var(--txt2);margin-top:0.4rem">Período: <span class="period-pill" style="background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.2);color:#34d399">📅 {periodo_txt}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pend = df_all[df_all["status"]=="pendente"] if not df_all.empty else pd.DataFrame()
    rote = df[df["status"]=="roteirizado"] if not df.empty else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    for col, klass, icon, label, value, sub in [
        (c1,"red","⏳","Pendentes",str(len(pend)),br(pend["vltotal"].sum()) if not pend.empty else "R$ 0,00"),
        (c2,"green","✅","Roteirizadas",str(len(rote)),br(rote["vltotal"].sum()) if not rote.empty else "R$ 0,00"),
        (c3,"orange","⚖️","Peso Pend.",f"{pend['pesobrutotot'].sum():.0f} kg" if not pend.empty else "0 kg","peso pendente"),
        (c4,"purple","⚖️","Peso Rot.",f"{rote['pesobrutotot'].sum():.0f} kg" if not rote.empty else "0 kg","peso roteirizado"),
    ]:
        with col:
            bar_color = {"orange":"#f97316","blue":"#3b82f6","purple":"#8b5cf6","green":"#10b981","red":"#ef4444"}.get(klass,"#f97316")
            st.markdown(f"""
            <div style="background:var(--sur);border:1px solid var(--bdr);border-radius:16px;padding:1.4rem 1.6rem 1.2rem;position:relative;overflow:hidden;">
              <div style="position:absolute;top:0;left:0;right:0;height:3px;background:{bar_color};border-radius:16px 16px 0 0;"></div>
              <div style="position:absolute;bottom:-20px;right:-20px;font-size:5rem;opacity:.04;">{icon}</div>
              <div style="width:36px;height:36px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:1rem;background:{bar_color}20;position:absolute;top:1.2rem;right:1.2rem">{icon}</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--mut);margin-bottom:.75rem">{label}</div>
              <div style="font-family:'Outfit',sans-serif;font-size:2rem;font-weight:800;color:{bar_color};line-height:1;margin-bottom:.35rem">{value}</div>
              <div style="font-size:.72rem;color:var(--txt2)">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pendentes ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="table-wrap" style="border-color:rgba(239,68,68,.2)">
      <div class="table-header" style="border-bottom-color:rgba(239,68,68,.15)">
        <span class="table-title" style="color:#fca5a5">⏳ Notas Pendentes (todas as datas)</span>
        <span class="table-count">{len(pend)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div class="al-s">✅ Nenhuma nota pendente!</div>', unsafe_allow_html=True)
    else:
        pb1, pb2 = st.columns([3,1])
        with pb1:
            bp = st.text_input("Buscar pendentes", key="rbp", label_visibility="collapsed", placeholder="🔍  Nota, cliente, praça...")
        with pb2:
            dp_opts = ["Todas"]+sorted(pend["dt_transferencia"].unique().tolist(), reverse=True)
            dp_opts_fmt = ["Todas"]+[fmt_date(d) for d in dp_opts[1:]]
            fdp_fmt = st.selectbox("Data", dp_opts_fmt, key="rdp", label_visibility="collapsed")
            fdp = to_iso(fdp_fmt) if fdp_fmt!="Todas" else "Todas"

        df_p = pend.copy()
        if fdp!="Todas": df_p = df_p[df_p["dt_transferencia"]==fdp]
        if bp:
            m = df_p.apply(lambda r: bp.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_p = df_p[m]

        # Pendentes: colunas padrão com ID para seleção
        PEND_COLS = ["id"] + [c for c in STD_COLS_BASE if c in df_p.columns]
        PEND_CONFIG = {"id": st.column_config.NumberColumn("ID", width=55), **STD_CONFIG_BASE}

        st.dataframe(
            df_p[PEND_COLS].sort_values("dt_liberado", ascending=False),
            use_container_width=True, hide_index=True,
            column_config=PEND_CONFIG
        )
        st.caption(f"{len(df_p)} nota(s) pendente(s)")

        # ── Formulário de roteirização ─────────────────────────────────────────
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🚗 Informar Nova Placa e Data de Saída</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

        ids_p = df_p["id"].astype(str).tolist()
        if ids_p:
            cs, cp, cd_saida, cok = st.columns([1.5,2,1.8,1])
            with cs:
                sel = st.selectbox("Selecionar ID", ids_p, label_visibility="visible")
            with cp:
                nova_pl = st.text_input("🚗 Nova Placa do Veículo", placeholder="Ex: ABC-1234", key="rpl").upper()
            with cd_saida:
                dt_saida_rot = st.date_input("🚚 Data de Saída", value=None, key="dt_saida_rot",
                                              format="DD/MM/YYYY",
                                              help="Data em que a nota sairá para entrega ao cliente")
            with cok:
                st.markdown("<br>", unsafe_allow_html=True)
                conf = st.button("✅ Confirmar", use_container_width=True)

            # Preview da nota selecionada
            if sel:
                rs = df_p[df_p["id"].astype(str)==sel]
                if not rs.empty:
                    r = rs.iloc[0]
                    pr = r.get("placa_road","")
                    pr_h = f'&nbsp;·&nbsp;<span class="placa-chip">🚛 Placa Antiga: {pr}</span>' if pr else ""
                    st.markdown(f"""
                    <div style="background:var(--sur2);border:1px solid var(--bdr);border-radius:10px;padding:.7rem 1.1rem;font-size:.82rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
                      <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f0f4ff">{r['numnota']}</span>
                      <span style="color:#8899aa">{r.get('nomecliente','')}</span>
                      <span style="color:#fb923c;font-weight:700">{br(r['vltotal'])}</span>
                      <span style="color:#8899aa">📅 Lib: {r.get('dt_liberado','—')}</span>
                      <span style="color:#8899aa">🏙️ {r.get('praca','—')}</span>
                      <span style="color:#8899aa">📍 {r.get('destino','—')}</span>
                      {pr_h}
                    </div>
                    """, unsafe_allow_html=True)

            if conf:
                if not nova_pl.strip():
                    st.markdown('<div class="al-e">⚠️ Por favor, informe a nova placa do veículo!</div>', unsafe_allow_html=True)
                elif not dt_saida_rot:
                    st.markdown('<div class="al-e">⚠️ Por favor, informe a data de saída!</div>', unsafe_allow_html=True)
                else:
                    dt_saida_str = dt_saida_rot.isoformat()
                    with st.spinner("Salvando..."):
                        update_transf(int(sel), {
                            "placa_veiculo":   nova_pl.strip(),
                            "dt_roteirizacao": date.today().strftime("%d/%m/%Y"),
                            "dt_saida":        dt_saida_str,
                            "status":          "roteirizado"
                        })
                    st.success(f"✅ Nota roteirizada! Nova placa **{nova_pl.strip()}** · Saída: **{fmt_date(dt_saida_str)}**")
                    st.rerun()

    # ── Roteirizadas ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="table-wrap" style="margin-top:1.5rem;border-color:rgba(16,185,129,.2)">
      <div class="table-header" style="border-bottom-color:rgba(16,185,129,.15)">
        <span class="table-title" style="color:#34d399">✅ Notas Roteirizadas</span>
        <span class="table-count">{len(rote)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if rote.empty:
        st.markdown('<div class="al-i">📋 Nenhuma nota roteirizada neste período.</div>', unsafe_allow_html=True)
    else:
        br_ = st.text_input("Buscar roteirizadas", key="rbr", label_visibility="collapsed", placeholder="🔍  Nota, cliente, placa...")
        df_r = rote.copy()
        if br_:
            m = df_r.apply(lambda r: br_.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_r = df_r[m]

        # Roteirizadas: colunas padrão + nova placa + dt_saída
        ROT_COLS = [c for c in STD_COLS_BASE + ["placa_veiculo","dt_saida"] if c in df_r.columns]
        ROT_CONFIG = {
            **STD_CONFIG_BASE,
            "placa_veiculo": st.column_config.TextColumn("🚗 Nova Placa",  width=115),
            "dt_saida":      st.column_config.TextColumn("🚚 Dt. Saída",   width=105),
        }

        df_rd = df_r.copy()
        if "dt_saida" in df_rd.columns:
            df_rd = fmt_col(df_rd, "dt_saida")

        st.dataframe(
            df_rd[ROT_COLS].sort_values("dt_liberado", ascending=False),
            use_container_width=True, hide_index=True,
            column_config=ROT_CONFIG
        )
        st.caption(f"{len(df_r)} nota(s) roteirizada(s)")

        # Botão devolver para pendente
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">↩️ Devolver para Pendente</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        ids_r = df_r["id"].astype(str).tolist()
        if ids_r:
            cd1, cd2 = st.columns([3,1])
            with cd1:
                dvid = st.selectbox("ID a devolver", ids_r, key="rdv", label_visibility="collapsed")
            with cd2:
                if st.button("↩️ Devolver", use_container_width=True):
                    update_transf(int(dvid), {"placa_veiculo":"","dt_roteirizacao":"","dt_saida":"","status":"pendente"})
                    st.success("↩️ Nota devolvida para pendentes!")
                    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
