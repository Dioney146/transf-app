<think>
O usuário está tentado executar o código que eu forneci, mas há erros de sintaxe. Deixe-me ver o código que eu enviei e corrigir os problemas.

Olhando para o código que eu forneci, há alguns problemas:
1. O código foi cortado no meio em --bg-card) ! (
2. Há strings não terminadas

Vou reescrever o código de forma completa e correta agora.
</think>

Está havendo erros de truncação no meu código. Deixe-me fornecer uma versão **inteira, corrigida e melhorada** num único bloco paste-ready:

```python
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

# ============================
# 1. CONFIG & SETUP
# ============================
st.set_page_config(
    page_title="Delly's — Transferências",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Placeholders - SUBSTITUA pelos seus Base64 reais
BG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAABOklEQVR4nO3VsQ2DMBiG4H+k6qFDqJOMWpgAM2JhAhNuChMaE2JiYmKiTYgJ0xAjJFZISYiJSxMT/v/n+84vRwIE9/KpAiRQQgWSoAJJUEIVoqACKVBBJaRABeWgAklQgRSooAJJUIYKSENJUEYFVJAKKpAEZVQ4hAqkQAmVoAIqkASlVDiSCqRACZVIPhVOUkYJJVQiuVQ4hgokQRkVTlJGCWWUUEEJ5RNRPsEH/kQFCxT/gf8vAQBBBBBBAACABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBBAAAACCAAEEAAAACAAABBgAEEwK4Q1gAAABJJREFUqIXt1TsQwCAQBEFT33dYGOIFy7v4N4AQQgghhhhCiiiiiCCCCPyK7S0h4Y2V0WwAAAABJRU5ErkJggg=="

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
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=name, rows=5000, cols=25)

# ============================
# 2. LÓGICA & DADOS
# ============================
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
    seen, new_cols = {}, []
    for i, c in enumerate(df.columns):
        seen[c] = i if c not in seen else seen[c]
        new_cols.append(c if c not in seen else f"{c}__dup{i}")
    df.columns = new_cols
    return df[[c for c in df.columns if "__dup" not in c]]

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias():
    ws = ensure_header()
    vals = ws.get_all_values()
    if not vals or len(vals) < 2: return pd.DataFrame(columns=TCOLS)
    hdr, rows = [str(c).strip() for c in vals[0]], vals[1:]
    n = len(hdr)
    rows_padded = [row + [""] * (n - len(row)) if len(row) < n else row[:n] for row in rows]
    df = pd.DataFrame(rows_padded, columns=hdr)
    df = dedup_columns(df)
    df = df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)]
    for c in ["pesobrutotot", "vltotal"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
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
    import string
    def col_letter(n):
        result = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result = string.ascii_uppercase[rem] + result
        return result
    row_num = next((i + 2 for i, r in enumerate(data[1:]) if dict(zip(hdr, r + [""] * (len(hdr) - len(r)))).get("id", "").strip() == str(tid).strip()), None)
    if not row_num: return
    for col, val in updates.items():
        if col in col_idx:
            ws.update(f"{col_letter(col_idx[col])}{row_num}", [[str(val)]], value_input_option="USER_ENTERED")
    load_transferencias.clear()

def delete_transf(tid):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(data[0], row)).get("id", "") == str(tid):
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
        if not vals or len(vals) < 2: return pd.DataFrame()
        hdr = [str(c).upper().strip() for c in vals[0]]
        rows = vals[1:]
        n = len(hdr)
        df = pd.DataFrame([r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows], columns=hdr)
        df = dedup_columns(df)
        return df.loc[:, df.columns.str.strip() != ""]
    except: return pd.DataFrame()

def buscar_nota(numnota):
    df = load_road()
    if df.empty: return None
    col_nf = next((c for c in df.columns if "NOTA" in c), None)
    if not col_nf: return None
    row = df[df[col_nf].astype(str).str.strip() == numnota.strip()]
    if row.empty: return None
    r = row.iloc[0]
    def safe(*cols):
        for c in cols:
            v = str(r.get(c, "")).strip()
            if v not in ("nan", "None", "", "0.0"): return v[:-2] if v.endswith(".0") else v
        return ""
    return {
        "numped": safe("PEDIDO"), "numnota": safe("NF", "NOTA FISCAL"), "nomecliente": safe("CLIENTE"),
        "dt_liberado": safe("DATA LIBERADO"), "nomevend": safe("VENDEDOR"), "nomesup": safe("SUPERVISOR"),
        "pesobrutotot": float(str(safe("PESO")).replace(",", ".")) or 0.0,
        "vltotal": float(str(safe("VALOR")).replace("R$", "").replace(",", ".")) or 0.0,
        "praca": safe("PRACA"), "numcarregamento": safe("CARREGAMENTO"),
        "destino": safe("DESTINO"), "placa_road": safe("PLACA")
    }

def br(v):
    try: return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("", "nan", "None", "—"): return "—"
    return str(s).strip()

# ============================
# 3. CSS (DARK PREMIUM)
# ============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
:root {
  --bg-app: #05070a;
  --bg-card: rgba(15, 23, 42, 0.65);
  --primary: #3b82f6;
  --primary-glow: rgba(59, 130, 246, 0.2);
  --green: #10b981;
  --green-bg: rgba(16, 185, 129, 0.15);
  --red: #ef4444;
  --red-bg: rgba(239, 68, 68, 0.15);
  --yellow: #fbbf24;
  --yellow-bg: rgba(251, 191, 36, 0.15);
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
  --text-dim: #64748b;
  --border: rgba(255, 255, 255, 0.08);
}
html, body, [class*="css"], .stApp {
  font-family: 'Outfit', sans-serif !important;
  background: var(--bg-app) !important;
  color: var(--text-main) !important;
}
.stApp::before {
  content: ''; position: fixed; inset: 0;
  background: radial-gradient(circle at top left, #1e293b 0%, transparent 40%),
              radial-gradient(circle at bottom right, #0f172a 0%, transparent 40%),
              linear-gradient(to bottom, #05070a, #0f172a);
  background-size: cover; z-index: -1;
}
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stDecoration"] { display: none; }

/* Topbar */
.topbar {
  background: rgba(10, 15, 25, 0.8); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border); height: 64px; display: flex;
  align-items: center; padding: 0 2rem; gap: 1.2rem;
}
.topbar-logo { height: 32px; border-radius: 6px; }
.topbar-brand { font-size: 1.1rem; font-weight: 700; letter-spacing: -0.02em; }
.topbar-sub { font-size: 0.75rem; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; }
.topbar-dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; box-shadow: 0 0 8px var(--green); margin-left: auto; animation: pulse 2.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* Nav */
.nav-wrap { background: rgba(10, 15, 25, 0.8); backdrop-filter: blur(8px); border-bottom: 1px solid var(--border); padding: 0 2rem; display: flex; }
.nav-wrap label { color: var(--text-dim) !important; font-weight: 600 !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em; padding: 1rem 1.5rem !important; border-bottom: 2px solid transparent !important; transition: all 0.2s ease; }
.nav-wrap label:hover { color: var(--text-main) !important; background: rgba(255,255,255,0.03); }
.nav-wrap label[data-selected="true"] { color: var(--primary) !important; border-bottom-color: var(--primary) !important; background: var(--primary-glow) !important; }

/* Card */
.card { background: var(--bg-card) !important; backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; margin-bottom: 1.5rem; box-shadow: 0 4px 24px rgba(0,0,0,0.2); }
.card-head { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); }
.card-body { padding: 1.5rem; }
.card-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-main); display: flex; align-items: center; gap: 8px; }
.card-count { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 20px; padding: 3px 10px; }

/* KPIs */
.kpi-mini { background: var(--bg-card); backdrop-filter: blur(12px); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; }
.kpi-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); font-family: 'JetBrains Mono', monospace; margin-bottom: 0.5rem; }
.kpi-value { font-size: 1.75rem; font-weight: 800; color: var(--text-main); letter-spacing: -0.03em; }
.kpi-sub { font-size: 0.75rem; color: var(--text-dim); margin-top: 2px; }

/* Inputs */
.stTextInput > div > div > input, .stDateInput > div > div > input {
  background: rgba(255,255,255,0.04) !important; color: var(--text-main) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  font-family: 'Outfit', sans-serif !important; font-size: 0.9rem !important;
  padding: 0.6rem 0.8rem !important;
}
.stTextInput > div > div > input:focus, .stDateInput > div > div > input:focus {
  border-color: var(--primary) !important; box-shadow: 0 0 0 3px var(--primary-glow) !important;
  background: rgba(255,255,255,0.07) !important;
}
.stTextInput label, .stDateInput label {
  color: var(--text-muted) !important; font-size: 0.7rem !important
