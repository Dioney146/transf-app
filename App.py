import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Delly's — Transferências",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Placeholders - Substitua pelos seus Base64 reais ou URLs
BG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAABOklEQVR4nO3VsQ2DMBiG4H+k6qFDqJOMWpgAM2JhAhNuChMaE2JiYmKiTYgJ0xAjJFZISYiJSxMT/v/n+84vRwIE9/KpAiRQQgWSoAJJUEIVoqACKVBBJaRABeWgAklQgRSooAJJUIYKSENJUEYFVJAKKpAEZVQ4hAqkQAmVoAIqkASlVDiSCqRACZVIPhVOUkYJJVQiuVQ4hgokQRkVTlJGCWWUUEEJ5RNRPsEH/kQFCxT/gf8vAQBBBBBBAACABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBgAEEwK4Q1gAAABJJREFUqIXt1TsQwCAQBEFT33dYGOIFy7v4N4AQQgghhhhCiiiiiCCCCPyK7S0h4Y2V0WwAAAABJRU5ErkJggg=="

@st.cache_resource(show_spinner=False)
def get_client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    return get_client().open_by_key(st.secrets["spreadsheet_id"])

def get_sheet(name):
    ss = get_spreadsheet()
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=name, rows=5000, cols=25)

TCOLS = [
    "id", "dt_transferencia", "numped", "numnota", "nomecliente",
    "dt_liberado", "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino", "placa_road",
    "placa_veiculo", "dt_saida", "dt_roteirizacao",
    "status", "criado_em",
]

def ensure_header():
    ws = get_sheet("transferencias")
    hdr = ws.row_values(1)
    if hdr[:len(TCOLS)] == TCOLS and len(hdr) >= len(TCOLS):
        return ws
    end_col = chr(ord("A") + len(TCOLS) - 1)
    ws.update(f"A1:{end_col}1", [TCOLS])
    return ws

def dedup_columns(df):
    seen = {}
    new_cols = []
    for i, c in enumerate(df.columns):
        if c not in seen:
            seen[c] = i
            new_cols.append(c)
        else:
            new_cols.append(f"{c}__dup{i}")
    df.columns = new_cols
    df = df[[c for c in df.columns if "__dup" not in c]]
    return df

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias():
    ws = ensure_header()
    vals = ws.get_all_values()
    if not vals or len(vals) < 2:
        return pd.DataFrame(columns=TCOLS)
    hdr_raw = vals[0]
    rows = vals[1:]
    hdr = [str(c).strip() for c in hdr_raw]
    n = len(hdr)
    rows_padded = [row + [""] * (n - len(row)) if len(row) < n else row[:n] for row in rows]
    df = pd.DataFrame(rows_padded, columns=hdr)
    df = dedup_columns(df)
    df = df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)]
    for c in ["pesobrutotot", "vltotal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in TCOLS:
        if c not in df.columns:
            df[c] = ""
    return df

def next_id(df):
    if df.empty: return 1
    v = pd.to_numeric(df["id"], errors="coerce").dropna()
    return int(v.max() + 1) if len(v) else 1

def append_transf(row):
    ws = ensure_header()
    df = load_transferencias()
    row["id"] = next_id(df)
    row["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    row.setdefault("status", "pendente")
    ws.append_row([str(row.get(c, "")) for c in TCOLS], value_input_option="USER_ENTERED")
    load_transferencias.clear()

def update_transf(tid, updates):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    hdr = [str(c).strip() for c in data[0]]
    for col in updates:
        if col not in hdr:
            hdr.append(col)
            ws.update_cell(1, len(hdr), col)
    col_idx = {c: i + 1 for i, c in enumerate(hdr)}
    row_num = None
    for i, row in enumerate(data[1:], start=2):
        row_padded = row + [""] * (len(hdr) - len(row))
        row_dict = dict(zip(hdr, row_padded))
        if row_dict.get("id", "").strip() == str(tid).strip():
            row_num = i
            break
    if row_num is None: return
    import string
    def col_letter(n):
        result = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result = string.ascii_uppercase[rem] + result
        return result
    for col, val in updates.items():
        if col in col_idx:
            cell_ref = f"{col_letter(col_idx[col])}{row_num}"
            ws.update(cell_ref, [[str(val)]], value_input_option="USER_ENTERED")
    load_transferencias.clear()

def delete_transf(tid):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    hdr = data[0]
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(hdr, row)).get("id", "") == str(tid):
            ws.delete_rows(i)
            break
    load_transferencias.clear()

def check_dup(numnota, dt):
    df = load_transferencias()
    if df.empty: return False
    return bool(((df["numnota"].astype(str) == str(numnota)) & (df["dt_transferencia"].astype(str) == str(dt))).any())

@st.cache_data(ttl=60, show_spinner=False)
def load_road():
    try:
        ws = get_sheet("ROAD")
        vals = ws.get_all_values()
        if not vals or len(vals) < 2:
            return pd.DataFrame()
        hdr_raw = vals[0]
        rows = vals[1:]
        hdr = [str(c).upper().strip() for c in hdr_raw]
        n = len(hdr)
        rows_padded = [row + [""] * (n - len(row)) if len(row) < n else row[:n] for row in rows]
        df = pd.DataFrame(rows_padded, columns=hdr)
        df = dedup_columns(df)
        df = df.loc[:, df.columns.str.strip() != ""]
        return df
    except Exception:
        return pd.DataFrame()

def buscar_nota(numnota):
    df = load_road()
    if df.empty: return None
    col_nf = next((c for c in df.columns if "NOTA" in c), None)
    if not col_nf: return None
    row = df[df[col_nf].astype(str).str.strip() == numnota.strip()]
    if row.empty: return None
    r = row.iloc[0]
    def safe(*cols):
        for col in cols:
            v = r.get(col, "")
            sv = str(v).strip()
            if sv not in ("nan", "None", "", "0.0"): return sv[:-2] if sv.endswith(".0") else sv
        return ""
    return {
        "numped": safe("PEDIDO"), "numnota": safe("NF","NOTA FISCAL"), "nomecliente": safe("CLIENTE"),
        "dt_liberado": safe("DATA LIBERADO"), "nomevend": safe("VENDEDOR"), "nomesup": safe("SUPERVISOR"),
        "pesobrutotot": float(str(safe("PESO")).replace(",",".")) or 0.0,
        "vltotal": float(str(safe("VALOR")).replace("R$","").replace(",",".")) or 0.0,
        "praca": safe("PRACA"), "numcarregamento": safe("CARREGAMENTO"), "destino": safe("DESTINO"), "placa_road": safe("PLACA")
    }

def br(v):
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("","nan","None","—"): return "—"
    return str(s).strip()

def to_iso(dt_str):
    if not dt_str or dt_str == "—": return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str) == 10 and dt_str[2] == "/" and dt_str[5] == "/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

# --- 2. CSS MODERNO (DARK MODE PREMIUM) ---
st.markdown("""
<style>
/* --- Fontes & Reset --- */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

:root {
  /* Cores Profundas */
  --bg-app: #05070a;
  --bg-card: rgba(15, 23, 42, 0.65);
  --bg-card-hover: rgba(15, 23, 42, 0.80);
  
  /* Cores de Acento */
  --primary: #3b82f6;
  --primary-glow: rgba(59, 130, 246, 0.25);
  --primary-text: #eff6ff;
  
  --accent-green: #10b981;
  --accent-green-bg: rgba(16, 185, 129, 0.15);
  
  --accent-red: #ef4444;
  --accent-red-bg: rgba(239, 68, 68, 0.15);
  
  --accent-yellow: #fbbf24;
  --accent-yellow-bg: rgba(251, 191, 36, 0.15);

  /* Texto */
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
  --text-dim: #64748b;
  
  /* Bordas */
  --border: rgba(255, 255, 255, 0.08);
  --border-light: rgba(255, 255, 255, 0.15);
}

html, body, [class*="css"], .stApp {
  font-family: 'Outfit', sans-serif !important;
  background: var(--bg-app) !
