import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

st.set_page_config(
    page_title="Delly's — Transferências",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

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

# ─── Colunas da aba transferencias ───────────────────────────────────────────
TCOLS = [
    "id", "dt_transferencia", "numped", "numnota", "nomecliente",
    "dt_liberado", "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino", "placa_road",
    "placa_veiculo", "dt_saida", "dt_roteirizacao",
    "status", "criado_em",
]

def ensure_header():
    """
    Garante que a aba 'transferencias' existe e que a linha 1
    contém EXATAMENTE os cabeçalhos em TCOLS (na ordem correta).
    Se existirem colunas extras após TCOLS, elas são mantidas no final.
    """
    ws = get_sheet("transferencias")
    hdr = ws.row_values(1)
    if not hdr:
        # Aba vazia: escreve cabeçalho do zero
        ws.update("A1", [TCOLS])
    else:
        # Verifica se os primeiros N cabeçalhos batem com TCOLS
        mismatch = (hdr[:len(TCOLS)] != TCOLS)
        missing = [c for c in TCOLS if c not in hdr]
        if mismatch or missing:
            # Reescreve as colunas de TCOLS nas posições corretas (1-indexed)
            for idx, col in enumerate(TCOLS, start=1):
                if idx > len(hdr) or hdr[idx-1] != col:
                    ws.update_cell(1, idx, col)
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
    for c in ["pesobrutotot", "vltotal"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    for c in TCOLS:
        if c not in df.columns:
            df[c] = ""
    return df

def next_id(df):
    if df.empty:
        return 1
    v = pd.to_numeric(df["id"], errors="coerce").dropna()
    return int(v.max() + 1) if len(v) else 1

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
    ws.append_row(
        [str(row.get(c, "")) for c in TCOLS],
        value_input_option="USER_ENTERED",
    )
    load_transferencias.clear()

def update_transf(tid, updates):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data:
        return
    hdr = data[0]
    for col in updates:
        if col not in hdr:
            ws.update_cell(1, len(hdr) + 1, col)
            hdr = hdr + [col]
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(hdr, row)).get("id", "") == str(tid):
            for col, val in updates.items():
                if col in hdr:
                    ws.update_cell(i, hdr.index(col) + 1, str(val))
            break
    load_transferencias.clear()

def delete_transf(tid):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data:
        return
    hdr = data[0]
    for i, row in enumerate(data[1:], start=2):
        if dict(zip(hdr, row)).get("id", "") == str(tid):
            ws.delete_rows(i)
            break
    load_transferencias.clear()

def check_dup(numnota, dt):
    df = load_transferencias()
    if df.empty:
        return False
    return bool(
        (
            (df["numnota"].astype(str) == str(numnota))
            & (df["dt_transferencia"].astype(str) == str(dt))
        ).any()
    )

@st.cache_data(ttl=60, show_spinner=False)
def load_road():
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
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df.columns = [str(c).upper().strip() for c in df.columns]
        for c in ["NOTA FISCAL", "PEDIDO"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.split(".").str[0].str.strip()
        return df
    except Exception:
        return pd.DataFrame()

def buscar_nota(numnota):
    df = load_road()
    if df.empty:
        return None

    # Tenta encontrar a coluna "NOTA FISCAL" com variações de nome
    col_nf = None
    for c in df.columns:
        if "NOTA" in c and "FISCAL" in c:
            col_nf = c
            break
        if c in ("NF", "NOTAFISCAL", "NOTA_FISCAL"):
            col_nf = c
            break
    if col_nf is None:
        return None

    row = df[df[col_nf].astype(str).str.strip() == numnota.strip()]
    if row.empty:
        return None
    r = row.iloc[0]

    def safe(*cols):
        """Tenta cada nome de coluna em ordem, retorna o primeiro valor não-vazio."""
        for col in cols:
            v = r.get(col, "")
            sv = str(v).strip()
            if sv not in ("nan", "None", "", "0.0"):
                return sv[:-2] if sv.endswith(".0") else sv
        return ""

    # Praça: tenta várias grafias possíveis (encoding pode variar)
    praca_cols = [c for c in df.columns if "PRA" in c]
    praca = ""
    for pc in praca_cols:
        v = str(r.get(pc, "")).strip()
        if v and v not in ("nan", "None", ""):
            praca = v[:-2] if v.endswith(".0") else v
            break

    # Carregamento: pode ser "CARREGAMENTO" ou truncado "CARREGAMEN"
    carr_cols = [c for c in df.columns if c.startswith("CARREG")]
    carr_val = ""
    for cc in carr_cols:
        v = str(r.get(cc, "")).strip()
        if v and v not in ("nan", "None", ""):
            carr_val = v[:-2] if v.endswith(".0") else v
            break

    # Peso
    peso_cols = [c for c in df.columns if c in ("PESO", "PESO BRUTO", "PESOBRUTO", "PESO TOTAL")]
    if not peso_cols:
        peso_cols = [c for c in df.columns if "PESO" in c]
    try:
        raw_p = str(r.get(peso_cols[0] if peso_cols else "PESO", "0")).replace(",", ".").strip()
        peso = float(raw_p)
    except Exception:
        peso = 0.0

    # Valor
    valor_cols = [c for c in df.columns if c in ("VALOR", "VALOR TOTAL", "VL TOTAL")]
    if not valor_cols:
        valor_cols = [c for c in df.columns if "VALOR" in c]
    try:
        raw_v = str(r.get(valor_cols[0] if valor_cols else "VALOR", "0"))
        raw_v = raw_v.replace("R$", "").replace(".", "").replace(",", ".").strip()
        vl = float(raw_v)
    except Exception:
        vl = 0.0

    # Coluna PEDIDO
    ped_col = next((c for c in df.columns if c == "PEDIDO"), None)
    # Coluna NOTA FISCAL
    nf_col = col_nf
    # Coluna DATA LIBERADO
    dtlib_col = next((c for c in df.columns if "DATA" in c and ("LIBER" in c or "LIB" in c)), None)
    if dtlib_col is None:
        dtlib_col = next((c for c in df.columns if "LIBERADO" in c or "LIBERACAO" in c), None)

    # Placa antiga: busca qualquer coluna que contenha "PLACA"
    placa_cols = [c for c in df.columns if "PLACA" in c]
    placa_road = ""
    for pc in placa_cols:
        v = str(r.get(pc, "")).strip()
        if v and v not in ("nan", "None", ""):
            placa_road = v[:-2] if v.endswith(".0") else v
            break

    # Vendedor: coluna pode ser "VENDEDOR" ou conter "VEND"
    vend_cols = [c for c in df.columns if "VEND" in c]
    vend_val = ""
    for vc in vend_cols:
        v = str(r.get(vc, "")).strip()
        if v and v not in ("nan", "None", ""):
            vend_val = v
            break

    # Supervisor: coluna pode conter "SUP"
    sup_cols = [c for c in df.columns if "SUP" in c]
    sup_val = ""
    for sc in sup_cols:
        v = str(r.get(sc, "")).strip()
        if v and v not in ("nan", "None", ""):
            sup_val = v
            break

    # Destino: coluna pode conter "DEST"
    dest_cols = [c for c in df.columns if "DEST" in c]
    dest_val = ""
    for dc in dest_cols:
        v = str(r.get(dc, "")).strip()
        if v and v not in ("nan", "None", ""):
            dest_val = v
            break

    # Cliente: coluna pode conter "CLIEN"
    cli_cols = [c for c in df.columns if "CLIEN" in c]
    cli_val = ""
    for clc in cli_cols:
        v = str(r.get(clc, "")).strip()
        if v and v not in ("nan", "None", ""):
            cli_val = v
            break

    return {
        "numped":          safe(ped_col or "PEDIDO"),
        "numnota":         safe(nf_col),
        "nomecliente":     cli_val or safe("CLIENTE"),
        "dt_liberado":     safe(dtlib_col or "DATA LIBERADO", "DATA LIBERADO", "DT LIBERADO"),
        "nomevend":        vend_val or safe("VENDEDOR"),
        "nomesup":         sup_val or safe("SUPERVISOR"),
        "pesobrutotot":    peso,
        "vltotal":         vl,
        "praca":           praca,
        "numcarregamento": carr_val,
        "destino":         dest_val or safe("DESTINO"),
        "placa_road":      placa_road,
    }

# ─── Formatação ───────────────────────────────────────────────────────────────
def br(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("", "nan", "None", "—"):
        return "—"
    s = str(s).strip()
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        parts = s[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s

def to_iso(dt_str):
    if not dt_str or dt_str == "—":
        return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str) == 10 and dt_str[2] == "/" and dt_str[5] == "/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

# ─── CSS Profissional ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --bg:       #f4f5f7;
  --white:    #ffffff;
  --sur:      #ffffff;
  --sur2:     #f9fafb;
  --bdr:      #e5e7eb;
  --bdr2:     #d1d5db;
  --acc:      #1a56db;
  --acc-lt:   #eff6ff;
  --acc-hover:#1e429f;
  --grn:      #057a55;
  --grn-lt:   #f0fdf4;
  --grn-bdr:  #a7f3d0;
  --red:      #c81e1e;
  --red-lt:   #fef2f2;
  --red-bdr:  #fca5a5;
  --ylw:      #92400e;
  --ylw-lt:   #fffbeb;
  --ylw-bdr:  #fcd34d;
  --txt:      #111827;
  --txt2:     #6b7280;
  --txt3:     #9ca3af;
  --nav-bg:   #1e2939;
  --nav-txt:  #9ca3af;
  --nav-act:  #ffffff;
  --nav-acc:  #3b82f6;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
  font-family: 'IBM Plex Sans', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--txt) !important;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Top bar ── */
.topbar {
  background: var(--nav-bg);
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  gap: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.topbar-brand {
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
}
.topbar-sub {
  font-size: 0.72rem;
  color: var(--nav-txt);
  font-family: 'IBM Plex Mono', monospace;
}
.topbar-dot {
  width: 7px; height: 7px;
  background: #22c55e;
  border-radius: 50%;
  box-shadow: 0 0 6px #22c55e;
  margin-left: auto;
}

/* ── Nav tabs ── */
.nav-wrap {
  background: var(--nav-bg);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding: 0 2rem;
}
.nav-wrap div[data-testid="stRadio"] > label { display: none !important; }
.nav-wrap div[data-testid="stRadio"] > div {
  display: flex !important;
  flex-direction: row !important;
  gap: 0 !important;
  padding: 0 !important;
  background: transparent !important;
}
.nav-wrap div[data-testid="stRadio"] > div > label {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 12px 20px !important;
  font-size: 0.78rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  border: none !important;
  border-bottom: 3px solid transparent !important;
  color: var(--nav-txt) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  transition: all 0.15s !important;
  border-radius: 0 !important;
  background: transparent !important;
  margin: 0 !important;
}
.nav-wrap div[data-testid="stRadio"] > div > label:hover {
  color: #e5e7eb !important;
  background: rgba(255,255,255,0.04) !important;
}
.nav-wrap div[data-testid="stRadio"] > div > label[data-selected="true"] {
  color: #fff !important;
  border-bottom-color: var(--nav-acc) !important;
  background: rgba(59,130,246,0.08) !important;
}
.nav-wrap div[data-testid="stRadio"] > div > label > div:first-child {
  display: none !important;
}

/* ── Filter bar ── */
.filter-bar {
  background: var(--white);
  border-bottom: 1px solid var(--bdr);
  padding: 0.6rem 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* ── Page body ── */
.page-body { padding: 2rem 2rem; max-width: 1400px; margin: 0 auto; }

/* ── Page title ── */
.page-title-block { margin-bottom: 1.5rem; }
.page-eyebrow {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.62rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--acc);
  margin-bottom: 4px;
}
.page-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--txt);
  letter-spacing: -0.02em;
}
.page-sub { font-size: 0.8rem; color: var(--txt2); margin-top: 2px; }

/* ── Cards ── */
.card {
  background: var(--white);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.25rem;
}
.card-head {
  padding: 0.9rem 1.25rem;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--sur2);
}
.card-title {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 7px;
}
.card-count {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.68rem;
  color: var(--txt2);
  background: var(--bg);
  border: 1px solid var(--bdr);
  border-radius: 20px;
  padding: 2px 10px;
}
.card-body { padding: 1.25rem; }

/* ── Status badges ── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  font-family: 'IBM Plex Mono', monospace;
}
.badge-pend { background: var(--ylw-lt); color: var(--ylw); border: 1px solid var(--ylw-bdr); }
.badge-rot  { background: var(--grn-lt); color: var(--grn); border: 1px solid var(--grn-bdr); }

/* ── Alerts ── */
.al-s { background:var(--grn-lt); border:1px solid var(--grn-bdr); color:var(--grn); border-radius:6px; padding:.65rem 1rem; font-size:.82rem; margin:.4rem 0; display:flex; align-items:center; gap:8px; }
.al-e { background:var(--red-lt); border:1px solid var(--red-bdr); color:var(--red); border-radius:6px; padding:.65rem 1rem; font-size:.82rem; margin:.4rem 0; display:flex; align-items:center; gap:8px; }
.al-i { background:var(--acc-lt); border:1px solid #bfdbfe; color:var(--acc); border-radius:6px; padding:.65rem 1rem; font-size:.82rem; margin:.4rem 0; display:flex; align-items:center; gap:8px; }
.al-w { background:var(--ylw-lt); border:1px solid var(--ylw-bdr); color:var(--ylw); border-radius:6px; padding:.65rem 1rem; font-size:.82rem; margin:.4rem 0; display:flex; align-items:center; gap:8px; }

/* ── Data box (nota encontrada) ── */
.data-found-box {
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-left: 4px solid var(--acc);
  border-radius: 6px;
  padding: 1rem 1.25rem;
  margin: .75rem 0;
}
.data-found-label {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--acc);
  margin-bottom: 0.6rem;
}

/* ── Form inputs ── */
.stTextInput > div > div > input,
.stDateInput > div > div > input {
  background: var(--white) !important;
  color: var(--txt) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 6px !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.88rem !important;
  padding: 0.5rem 0.75rem !important;
  transition: border-color .15s, box-shadow .15s !important;
}
.stTextInput > div > div > input:focus,
.stDateInput > div > div > input:focus {
  border-color: var(--acc) !important;
  box-shadow: 0 0 0 3px rgba(26,86,219,.12) !important;
}
.stTextInput > div > div > input:disabled {
  background: var(--sur2) !important;
  color: var(--txt2) !important;
  cursor: default !important;
}
.stSelectbox > div > div {
  background: var(--white) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 6px !important;
  color: var(--txt) !important;
}
.stTextInput label, .stDateInput label, .stSelectbox label,
.stTextArea label, .stNumberInput label, .stCheckbox label span {
  color: var(--txt2) !important;
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Buttons ── */
.stButton > button {
  background: var(--acc) !important;
  color: white !important;
  border: none !important;
  border-radius: 6px !important;
  font-weight: 600 !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.84rem !important;
  transition: background .15s !important;
  letter-spacing: 0.01em !important;
  padding: 0.5rem 1.25rem !important;
}
.stButton > button:hover {
  background: var(--acc-hover) !important;
}
.stDownloadButton > button {
  background: var(--white) !important;
  color: var(--txt2) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 6px !important;
  font-weight: 600 !important;
}
.stDownloadButton > button:hover {
  background: var(--sur2) !important;
  color: var(--txt) !important;
}

/* ── Table ── */
.stDataFrame { border-radius: 0 !important; border: none !important; }
.stDataFrame thead tr th {
  background: var(--sur2) !important;
  color: var(--txt2) !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.6rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  border-bottom: 1px solid var(--bdr) !important;
  padding: 9px 12px !important;
  font-weight: 600 !important;
}
.stDataFrame tbody tr:nth-child(even) td {
  background: var(--sur2) !important;
}
.stDataFrame tbody tr:hover td {
  background: var(--acc-lt) !important;
}
.stDataFrame tbody td {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.83rem !important;
  border-bottom: 1px solid var(--bdr) !important;
  color: var(--txt) !important;
  padding: 9px 12px !important;
}

/* ── Note card (sidebar list) ── */
.nota-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .6rem .9rem;
  border-bottom: 1px solid var(--bdr);
  font-size: .82rem;
  transition: background .12s;
}
.nota-row:hover { background: var(--sur2); }
.nota-row:last-child { border-bottom: none; }
.nota-num { font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:.8rem; color:var(--txt); }
.nota-cli { color:var(--txt2); font-size:.75rem; }
.nota-val { font-weight:700; color:var(--acc); font-size:.8rem; }

/* ── Divider ── */
.sec-div {
  display: flex; align-items: center; gap: .75rem;
  margin: 1.25rem 0 1rem;
}
.sec-div-line { flex:1; height:1px; background:var(--bdr); }
.sec-div-txt {
  font-family:'IBM Plex Mono',monospace;
  font-size:.6rem; font-weight:700;
  text-transform:uppercase; letter-spacing:.1em;
  color:var(--txt3); white-space:nowrap;
}

/* ── KPI mini ── */
.kpi-mini {
  background: var(--white);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 1rem 1.25rem;
}
.kpi-mini-label {
  font-size:.65rem; font-weight:700; text-transform:uppercase;
  letter-spacing:.08em; color:var(--txt2); margin-bottom:.4rem;
  font-family:'IBM Plex Mono',monospace;
}
.kpi-mini-value {
  font-size:1.5rem; font-weight:700; color:var(--txt); letter-spacing:-.02em;
}
.kpi-mini-sub { font-size:.72rem; color:var(--txt3); margin-top:2px; }

/* ── Placa chip ── */
.placa-chip {
  display:inline-flex; align-items:center; gap:4px;
  background:#fef9c3; border:1px solid #fde047;
  border-radius:5px; padding:2px 8px;
  font-family:'IBM Plex Mono',monospace;
  font-size:.72rem; font-weight:700; color:#854d0e;
}

input[type="date"] { color-scheme: light !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--bdr2); border-radius:99px; }
</style>
""", unsafe_allow_html=True)

# ─── Top Bar ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="1" y="6" width="15" height="12" rx="2" fill="#3b82f6"/>
    <path d="M16 10h4l3 4v3h-7V10z" fill="#60a5fa"/>
    <circle cx="5.5" cy="18.5" r="1.5" fill="#1e2939" stroke="#bfdbfe" stroke-width="1"/>
    <circle cx="18.5" cy="18.5" r="1.5" fill="#1e2939" stroke="#bfdbfe" stroke-width="1"/>
  </svg>
  <span class="topbar-brand">Delly's Food Service</span>
  <span class="topbar-sub">/ Sistema de Transferências</span>
  <div class="topbar-dot"></div>
</div>
""", unsafe_allow_html=True)

# ─── Navigation ───────────────────────────────────────────────────────────────
st.markdown('<div class="nav-wrap">', unsafe_allow_html=True)
pagina = st.radio(
    "nav",
    ["📝  Registro", "🗺️  Roteirização", "📋  Histórico"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_main",
)
st.markdown("</div>", unsafe_allow_html=True)

# ─── Filter Bar ───────────────────────────────────────────────────────────────
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
fc1, fc2, fc3, fc4 = st.columns([1.6, 1.4, 1.4, 4])
with fc1:
    data_filtro = st.date_input(
        "📅 Filtrar por data",
        value=date.today(),
        key="data_global",
        format="DD/MM/YYYY",
    )
with fc2:
    ver_todas = st.checkbox("Todas as datas", value=False, key="ver_todas_cb")
with fc3:
    st.markdown("<br style='line-height:.8'>", unsafe_allow_html=True)
    if st.button("🔄 Atualizar", key="refresh_btn"):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()
with fc4:
    pass
st.markdown("</div>", unsafe_allow_html=True)

# ─── Carrega dados ────────────────────────────────────────────────────────────
data_str = data_filtro.isoformat()
data_display = data_filtro.strftime("%d/%m/%Y")

df_all = load_transferencias()
df = (
    df_all.copy()
    if ver_todas
    else (
        df_all[df_all["dt_transferencia"] == data_str].copy()
        if not df_all.empty
        else pd.DataFrame(columns=TCOLS)
    )
)
periodo_txt = "Todas as datas" if ver_todas else data_display

# ─── Colunas padrão de exibição ───────────────────────────────────────────────
STD_COLS = [
    "numnota", "numped", "nomecliente", "dt_liberado",
    "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino", "placa_road",
]
STD_CONFIG = {
    "numnota":         st.column_config.TextColumn("Nota Fiscal",    width=105),
    "numped":          st.column_config.TextColumn("Pedido",         width=100),
    "nomecliente":     st.column_config.TextColumn("Cliente",        width=200),
    "dt_liberado":     st.column_config.TextColumn("Dt. Liberado",   width=105),
    "nomevend":        st.column_config.TextColumn("Vendedor",       width=160),
    "nomesup":         st.column_config.TextColumn("Supervisor",     width=140),
    "pesobrutotot":    st.column_config.NumberColumn("Peso (kg)",    format="%.3f", width=95),
    "vltotal":         st.column_config.NumberColumn("Valor (R$)",   format="R$ %.2f", width=120),
    "praca":           st.column_config.TextColumn("Praça",          width=130),
    "numcarregamento": st.column_config.TextColumn("Carregamento",   width=115),
    "destino":         st.column_config.TextColumn("Destino",        width=160),
    "placa_road":      st.column_config.TextColumn("Placa Antiga",   width=110),
}

st.markdown('<div class="page-body">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRO
# ═══════════════════════════════════════════════════════════════════════════════
if pagina == "📝  Registro":
    st.markdown(f"""
    <div class="page-title-block">
      <div class="page-eyebrow">Faturamento</div>
      <div class="page-title">Registro de Transferência</div>
      <div class="page-sub">Data: {data_display} — Registre a nota fiscal e envie para roteirização</div>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_side = st.columns([1.5, 0.7])

    with col_form:
        # ── Busca de nota ──────────────────────────────────────────────────────
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        <div class="card-head">
          <span class="card-title">🔍 Buscar Nota Fiscal</span>
        </div>
        <div class="card-body">
        """, unsafe_allow_html=True)

        ca, cb, cc = st.columns([1.2, 2, 1])
        with ca:
            dt_t = st.date_input(
                "Data da Transferência",
                value=data_filtro,
                format="DD/MM/YYYY",
                key="dt_transf_input",
            )
        with cb:
            nota_inp = st.text_input(
                "Número da Nota Fiscal",
                placeholder="Ex: 398234",
                key="nota_inp",
            )
        with cc:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar_btn = st.button("🔍 Buscar", use_container_width=True, key="buscar_btn")

        st.markdown("</div></div>", unsafe_allow_html=True)

        # ── Debug: mostrar colunas reais da aba ROAD ──────────────────────────
        with st.expander("🔧 Debug — Colunas da aba ROAD", expanded=False):
            df_dbg = load_road()
            if df_dbg.empty:
                st.warning("Aba ROAD não encontrada ou vazia.")
            else:
                st.write("**Colunas encontradas:**")
                st.code(", ".join(df_dbg.columns.tolist()))
                st.write(f"**Total de linhas:** {len(df_dbg)}")
                placa_cols_dbg = [c for c in df_dbg.columns if "PLACA" in c]
                st.write(f"**Colunas com 'PLACA':** {placa_cols_dbg}")
                if placa_cols_dbg:
                    amostra_placa = df_dbg[placa_cols_dbg[0]].dropna().astype(str)
                    amostra_placa = amostra_placa[amostra_placa.str.strip() != ""].head(5).tolist()
                    st.write(f"**Amostra da coluna `{placa_cols_dbg[0]}`:** {amostra_placa}")

        if "cur" not in st.session_state:
            st.session_state.cur = None

        if buscar_btn and nota_inp.strip():
            with st.spinner("Consultando base ROAD..."):
                df_road_dbg = load_road()
                r = buscar_nota(nota_inp.strip())
            if r:
                st.session_state.cur = r
                st.markdown('<div class="al-s">✅ Nota encontrada! Dados preenchidos automaticamente.</div>', unsafe_allow_html=True)
            else:
                st.session_state.cur = None
                st.markdown(f'<div class="al-e">❌ Nota "{nota_inp.strip()}" não encontrada na base ROAD.</div>', unsafe_allow_html=True)
                if not df_road_dbg.empty:
                    st.markdown(f'<div class="al-i">🔍 Colunas encontradas na aba ROAD: <code>{", ".join(df_road_dbg.columns.tolist())}</code></div>', unsafe_allow_html=True)
                    nf_col_found = next((c for c in df_road_dbg.columns if "NOTA" in c), None)
                    if nf_col_found:
                        amostra = df_road_dbg[nf_col_found].astype(str).head(5).tolist()
                        st.markdown(f'<div class="al-i">📋 Primeiras NFs na base: <code>{", ".join(amostra)}</code></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="al-e">⚠️ Aba ROAD vazia ou não encontrada.</div>', unsafe_allow_html=True)
        elif buscar_btn:
            st.markdown('<div class="al-w">⚠️ Informe o número da nota fiscal.</div>', unsafe_allow_html=True)

        cur = st.session_state.cur
        if cur:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("""
            <div class="card-head">
              <span class="card-title">📄 Dados da Nota — Base ROAD</span>
            </div>
            <div class="card-body">
            """, unsafe_allow_html=True)

            r1a, r1b, r1c = st.columns(3)
            with r1a: st.text_input("Pedido",       value=cur["numped"]          or "—", disabled=True, key="d_ped")
            with r1b: st.text_input("Nota Fiscal",   value=cur["numnota"],                disabled=True, key="d_nf")
            with r1c: st.text_input("Carregamento",  value=cur["numcarregamento"] or "—", disabled=True, key="d_car")

            r2a, r2b, r2c = st.columns(3)
            with r2a: st.text_input("Cliente",       value=cur["nomecliente"],             disabled=True, key="d_cli")
            with r2b: st.text_input("Data Liberado", value=cur["dt_liberado"]    or "—", disabled=True, key="d_dtl")
            with r2c: st.text_input("Vendedor",      value=cur["nomevend"]        or "—", disabled=True, key="d_vnd")

            r3a, r3b, r3c = st.columns(3)
            with r3a: st.text_input("Supervisor",    value=cur["nomesup"]         or "—", disabled=True, key="d_sup")
            with r3b: st.text_input("Praça",         value=cur["praca"]           or "—", disabled=True, key="d_prc")
            with r3c: st.text_input("Destino",       value=cur["destino"]         or "—", disabled=True, key="d_dst")

            r4a, r4b, r4c = st.columns(3)
            with r4a: st.text_input("Peso (kg)", value=f"{cur['pesobrutotot']:.3f}".replace(".", ","), disabled=True, key="d_pes")
            with r4b: st.text_input("Valor Total",  value=br(cur["vltotal"]),              disabled=True, key="d_vl")
            with r4c:
                placa_antiga = cur.get("placa_road", "") or "—"
                st.text_input("Placa Anterior",       value=placa_antiga,                  disabled=True, key="d_pl")

            if cur.get("placa_road"):
                st.markdown(f'<div class="al-w">⚠️ Essa nota teve entrega anterior com placa <strong>{cur["placa_road"]}</strong>.</div>', unsafe_allow_html=True)

            st.markdown('<div class="al-i">ℹ️ A nova placa e data de saída serão informadas pela <strong>Roteirização</strong>.</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True, key="confirm_btn"):
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
                            "placa_road":      cur.get("placa_road", ""),
                        })
                    st.success(f"✅ Transferência registrada! Nota {cur['numnota']} aguarda roteirização.")
                    st.session_state.cur = None
                    st.balloons()
                    st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="border-style:dashed">
              <div class="card-body" style="text-align:center;padding:2.5rem;color:var(--txt3)">
                <div style="font-size:2rem;margin-bottom:.5rem">🧾</div>
                <div style="font-size:.88rem">Informe o número da nota e clique em <strong style="color:var(--acc)">Buscar</strong></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    with col_side:
        # ── Notas do dia ──────────────────────────────────────────────────────
        df_hj = (
            df_all[df_all["dt_transferencia"] == data_str]
            if not df_all.empty
            else pd.DataFrame()
        )
        n_hj = len(df_hj)
        tv_hj = df_hj["vltotal"].sum() if not df_hj.empty else 0

        st.markdown(f"""
        <div class="kpi-mini" style="margin-bottom:1rem">
          <div class="kpi-mini-label">Notas registradas — {data_display}</div>
          <div style="display:flex;justify-content:space-between;align-items:flex-end">
            <div class="kpi-mini-value">{n_hj}</div>
            <div style="font-weight:700;font-size:.9rem;color:var(--acc)">{br(tv_hj)}</div>
          </div>
          <div class="kpi-mini-sub">transferências na data selecionada</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card-head">
          <span class="card-title">📋 Notas do dia</span>
          <span class="card-count">{n_hj}</span>
        </div>
        """, unsafe_allow_html=True)

        if df_hj.empty:
            st.markdown('<div style="padding:1.25rem;text-align:center;color:var(--txt3);font-size:.82rem">Nenhuma nota registrada.</div>', unsafe_allow_html=True)
        else:
            for _, rr in df_hj.iterrows():
                pl = rr.get("placa_veiculo", "")
                pl_h = (
                    f'<span class="placa-chip">🚗 {pl}</span>'
                    if pl
                    else '<span style="color:var(--txt3);font-size:.7rem;font-family:IBM Plex Mono,monospace">⏳ Pendente</span>'
                )
                st.markdown(f"""
                <div class="nota-row">
                  <div>
                    <div class="nota-num">{rr['numnota']}</div>
                    <div class="nota-cli">{str(rr.get('nomecliente',''))[:22]}</div>
                  </div>
                  <div style="text-align:right">
                    <div class="nota-val">{br(rr['vltotal'])}</div>
                    <div style="margin-top:3px">{pl_h}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Fluxo ─────────────────────────────────────────────────────────────
        st.markdown("""
        <div class="card" style="margin-top:1rem">
          <div class="card-head"><span class="card-title">💡 Fluxo</span></div>
          <div style="padding:.85rem 1rem">
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:.6rem;font-size:.78rem;color:var(--txt2)">
              <div style="min-width:20px;height:20px;background:var(--acc-lt);border:1px solid #bfdbfe;border-radius:50%;font-size:.65rem;font-weight:700;color:var(--acc);display:flex;align-items:center;justify-content:center;flex-shrink:0">1</div>
              <span><strong style="color:var(--txt)">Faturamento</strong> busca a nota e registra a transferência</span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:.6rem;font-size:.78rem;color:var(--txt2)">
              <div style="min-width:20px;height:20px;background:var(--acc-lt);border:1px solid #bfdbfe;border-radius:50%;font-size:.65rem;font-weight:700;color:var(--acc);display:flex;align-items:center;justify-content:center;flex-shrink:0">2</div>
              <span><strong style="color:var(--txt)">Roteirização</strong> informa a nova placa e data de saída</span>
            </div>
            <div style="display:flex;align-items:flex-start;gap:10px;font-size:.78rem;color:var(--txt2)">
              <div style="min-width:20px;height:20px;background:var(--acc-lt);border:1px solid #bfdbfe;border-radius:50%;font-size:.65rem;font-weight:700;color:var(--acc);display:flex;align-items:center;justify-content:center;flex-shrink:0">3</div>
              <span><strong style="color:var(--txt)">Histórico</strong> registra o ciclo completo da transferência</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Notas registradas hoje (tabela) ───────────────────────────────────────
    if not df_hj.empty:
        st.markdown('<div class="sec-div"><div class="sec-div-line"></div><div class="sec-div-txt">Notas registradas na data selecionada</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card-head">
          <span class="card-title">📋 Lista completa — {data_display}</span>
          <span class="card-count">{len(df_hj)} notas · {br(df_hj['vltotal'].sum())}</span>
        </div>
        """, unsafe_allow_html=True)
        SHOW = [c for c in STD_COLS if c in df_hj.columns]
        st.dataframe(
            df_hj[SHOW],
            use_container_width=True,
            hide_index=True,
            column_config=STD_CONFIG,
        )
        # Excluir
        st.markdown('<div style="padding:.75rem 1.25rem;border-top:1px solid var(--bdr)">', unsafe_allow_html=True)
        ids_hj = df_hj["id"].astype(str).tolist()
        cd1, cd2, _ = st.columns([2, 1, 3])
        with cd1:
            del_id = st.selectbox("Excluir por ID", ["—"] + ids_hj, key="del_id", label_visibility="visible")
        with cd2:
            st.markdown("<br>", unsafe_allow_html=True)
            if del_id != "—" and st.button("🗑️ Excluir", key="del_btn"):
                delete_transf(int(del_id))
                st.success("Registro excluído.")
                st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ROTEIRIZAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗺️  Roteirização":
    pend = df_all[df_all["status"].isin(["pendente", ""]) | df_all["status"].isna()] if not df_all.empty else pd.DataFrame()
    rote = df[df["status"] == "roteirizado"] if not df.empty else pd.DataFrame()

    st.markdown(f"""
    <div class="page-title-block">
      <div class="page-eyebrow">Roteirização</div>
      <div class="page-title">Roteirizar Notas</div>
      <div class="page-sub">Período: {periodo_txt}</div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    for col, label, value, sub, color in [
        (k1, "Pendentes",    str(len(pend)),  br(pend["vltotal"].sum()) if not pend.empty else "R$ 0,00",  "#ef4444"),
        (k2, "Roteirizadas", str(len(rote)),  br(rote["vltotal"].sum()) if not rote.empty else "R$ 0,00",  "#057a55"),
        (k3, "Peso Pend.",   f"{pend['pesobrutotot'].sum():.0f} kg" if not pend.empty else "0 kg", "total", "#92400e"),
        (k4, "Peso Rot.",    f"{rote['pesobrutotot'].sum():.0f} kg" if not rote.empty else "0 kg", "total", "#1a56db"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-mini">
              <div class="kpi-mini-label">{label}</div>
              <div class="kpi-mini-value" style="color:{color}">{value}</div>
              <div class="kpi-mini-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pendentes ─────────────────────────────────────────────────────────────
    st.markdown('<div class="card" style="border-top:3px solid #ef4444">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#c81e1e">⏳ Notas Pendentes</span>
      <span class="card-count">{len(pend)} · todas as datas</span>
    </div>
    """, unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div style="padding:1.5rem;text-align:center"><span class="al-s" style="justify-content:center">✅ Nenhuma nota pendente!</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-body" style="padding-bottom:.5rem">', unsafe_allow_html=True)
        pb1, pb2 = st.columns([3, 1])
        with pb1:
            bp = st.text_input("Buscar", key="rbp", label_visibility="collapsed", placeholder="🔍 Nota, cliente, praça...")
        with pb2:
            datas_pend = sorted(pend["dt_transferencia"].dropna().unique().tolist(), reverse=True)
            datas_fmt = ["Todas"] + [fmt_date(d) for d in datas_pend]
            fdp_fmt = st.selectbox("Data", datas_fmt, key="rdp", label_visibility="collapsed")
            fdp = to_iso(fdp_fmt) if fdp_fmt != "Todas" else "Todas"

        df_p = pend.copy()
        if fdp != "Todas":
            df_p = df_p[df_p["dt_transferencia"] == fdp]
        if bp:
            m = df_p.apply(lambda r: bp.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_p = df_p[m]

        PEND_COLS = ["id"] + [c for c in STD_COLS if c in df_p.columns]
        PEND_CONFIG = {"id": st.column_config.NumberColumn("ID", width=55), **STD_CONFIG}

        st.dataframe(
            df_p[PEND_COLS].sort_values("dt_liberado", ascending=False) if not df_p.empty else df_p,
            use_container_width=True,
            hide_index=True,
            column_config=PEND_CONFIG,
        )
        st.caption(f"{len(df_p)} nota(s)")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Formulário de roteirização ─────────────────────────────────────────
        st.markdown('<div style="padding:1rem 1.25rem;border-top:1px solid var(--bdr)">', unsafe_allow_html=True)
        st.markdown('<div class="sec-div" style="margin-top:0"><div class="sec-div-line"></div><div class="sec-div-txt">🚗 Informar nova placa e data de saída</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)

        ids_p = df_p["id"].astype(str).tolist() if not df_p.empty else []
        if ids_p:
            cs, cp, cds, cok = st.columns([1.2, 2, 1.8, 1])
            with cs:
                sel = st.selectbox("ID", ids_p, key="rot_sel", label_visibility="visible")
            with cp:
                nova_pl = st.text_input("Nova Placa", placeholder="Ex: ABC-1234", key="rot_pl").upper()
            with cds:
                dt_saida_rot = st.date_input(
                    "Data de Saída",
                    value=None,
                    key="rot_dt_saida",
                    format="DD/MM/YYYY",
                )
            with cok:
                st.markdown("<br>", unsafe_allow_html=True)
                conf = st.button("✅ Confirmar", use_container_width=True, key="rot_conf")

            # Preview
            if sel:
                rs = df_p[df_p["id"].astype(str) == sel]
                if not rs.empty:
                    r = rs.iloc[0]
                    pr = r.get("placa_road", "")
                    pr_h = f' · <span class="placa-chip">🚛 Ant: {pr}</span>' if pr else ""
                    st.markdown(f"""
                    <div style="background:var(--sur2);border:1px solid var(--bdr);border-radius:6px;padding:.6rem 1rem;font-size:.82rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;margin-top:.4rem">
                      <span style="font-family:'IBM Plex Mono',monospace;font-weight:600">{r['numnota']}</span>
                      <span style="color:var(--txt2)">{r.get('nomecliente','')}</span>
                      <span style="font-weight:700;color:var(--acc)">{br(r['vltotal'])}</span>
                      <span style="color:var(--txt2)">📍 {r.get('destino','—')}</span>
                      <span style="color:var(--txt2)">🏙️ {r.get('praca','—')}</span>
                      {pr_h}
                    </div>
                    """, unsafe_allow_html=True)

            if conf:
                if not nova_pl.strip():
                    st.markdown('<div class="al-e">⚠️ Informe a nova placa!</div>', unsafe_allow_html=True)
                elif not dt_saida_rot:
                    st.markdown('<div class="al-e">⚠️ Informe a data de saída!</div>', unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        update_transf(int(sel), {
                            "placa_veiculo":   nova_pl.strip(),
                            "dt_roteirizacao": date.today().strftime("%d/%m/%Y"),
                            "dt_saida":        dt_saida_rot.isoformat(),
                            "status":          "roteirizado",
                        })
                    st.success(f"✅ Nota roteirizada! Placa: {nova_pl.strip()} · Saída: {fmt_date(dt_saida_rot.isoformat())}")
                    st.rerun()
        else:
            st.markdown('<div class="al-i">Nenhuma nota pendente nos filtros selecionados.</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Roteirizadas ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="card" style="border-top:3px solid #057a55">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#057a55">✅ Notas Roteirizadas</span>
      <span class="card-count">{len(rote)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if rote.empty:
        st.markdown(f'<div style="padding:1.25rem"><div class="al-i">Nenhuma nota roteirizada em {periodo_txt}.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-body" style="padding-bottom:.5rem">', unsafe_allow_html=True)
        br_input = st.text_input("Buscar roteirizadas", key="rbr", label_visibility="collapsed", placeholder="🔍 Nota, cliente, placa...")
        df_r = rote.copy()
        if br_input:
            m = df_r.apply(lambda r: br_input.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_r = df_r[m]

        ROT_COLS = [c for c in STD_COLS + ["placa_veiculo", "dt_saida"] if c in df_r.columns]
        ROT_CONFIG = {
            **STD_CONFIG,
            "placa_veiculo": st.column_config.TextColumn("Nova Placa", width=110),
            "dt_saida":      st.column_config.TextColumn("Dt. Saída",  width=100),
        }
        df_rd = df_r.copy()
        if "dt_saida" in df_rd.columns:
            df_rd["dt_saida"] = df_rd["dt_saida"].apply(fmt_date)

        st.dataframe(
            df_rd[ROT_COLS].sort_values("dt_liberado", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config=ROT_CONFIG,
        )
        st.caption(f"{len(df_r)} nota(s)")
        st.markdown("</div>", unsafe_allow_html=True)

        # Devolver para pendente
        st.markdown('<div style="padding:.75rem 1.25rem;border-top:1px solid var(--bdr)">', unsafe_allow_html=True)
        st.markdown('<div class="sec-div" style="margin-top:0"><div class="sec-div-line"></div><div class="sec-div-txt">↩️ Devolver para pendente</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)
        ids_r = df_r["id"].astype(str).tolist()
        if ids_r:
            dv1, dv2, _ = st.columns([2, 1, 3])
            with dv1:
                dvid = st.selectbox("ID", ids_r, key="rdv", label_visibility="collapsed")
            with dv2:
                if st.button("↩️ Devolver", key="devolver_btn"):
                    update_transf(int(dvid), {
                        "placa_veiculo": "",
                        "dt_roteirizacao": "",
                        "dt_saida": "",
                        "status": "pendente",
                    })
                    st.success("↩️ Devolvida para pendentes.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":
    st.markdown(f"""
    <div class="page-title-block">
      <div class="page-eyebrow">Faturamento</div>
      <div class="page-title">Histórico de Transferências</div>
      <div class="page-sub">Período: {periodo_txt} — {len(df)} registro(s)</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Filtros ────────────────────────────────────────────────────────────────
    hf1, hf2, hf3, hf4 = st.columns([3, 1.2, 1.5, 1])
    with hf1:
        busca_h = st.text_input("Buscar", key="hb", label_visibility="collapsed", placeholder="🔍 Nota, cliente, placa, destino...")
    with hf2:
        fst = st.selectbox("Status", ["Todos", "pendente", "roteirizado"], key="hst", label_visibility="collapsed")
    with hf3:
        sups = ["Todos"] + (sorted(df["nomesup"].dropna().unique().tolist()) if not df.empty else [])
        fsup = st.selectbox("Supervisor", sups, key="hsup", label_visibility="collapsed")
    with hf4:
        if not df.empty:
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as w:
                df.to_excel(w, index=False)
            out.seek(0)
            st.download_button(
                "⬇️ Excel",
                out,
                file_name=f"historico_{data_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # Histórico usa df_all para mostrar TODOS os registros, incluindo
    # roteirizados em datas diferentes. O filtro de data do topo é aplicado
    # como filtro adicional (não exclui automaticamente).
    df_h = df_all.copy() if not df_all.empty else pd.DataFrame(columns=TCOLS)
    if not df_h.empty:
        # Aplica filtro de data somente se NÃO for "ver todas"
        if not ver_todas:
            df_h = df_h[df_h["dt_transferencia"] == data_str]
        if fst != "Todos":
            df_h = df_h[df_h["status"] == fst]
        if fsup != "Todos":
            df_h = df_h[df_h["nomesup"] == fsup]
        if busca_h:
            m = df_h.apply(lambda r: busca_h.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_h = df_h[m]

    # ── Tabela completa ────────────────────────────────────────────────────────
    # Garante que colunas de roteirização existem no df (mesmo que vazias)
    for _col in ["placa_veiculo", "dt_saida", "status"]:
        if _col not in df_h.columns:
            df_h[_col] = ""
    HIST_COLS = [c for c in STD_COLS + ["placa_veiculo", "dt_saida", "status"] if c in df_h.columns]
    HIST_CONFIG = {
        **STD_CONFIG,
        "placa_veiculo": st.column_config.TextColumn("Nova Placa", width=110),
        "dt_saida":      st.column_config.TextColumn("Dt. Saída",  width=100),
        "status":        st.column_config.TextColumn("Status",     width=110),
    }

    n_pend = int((df_h["status"] == "pendente").sum()) if not df_h.empty else 0
    n_rot  = int((df_h["status"] == "roteirizado").sum()) if not df_h.empty else 0
    vt_h   = df_h["vltotal"].sum() if not df_h.empty else 0

    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Total de Notas</div>
          <div class="kpi-mini-value">{len(df_h)}</div>
          <div class="kpi-mini-sub">{br(vt_h)}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Pendentes</div>
          <div class="kpi-mini-value" style="color:#ef4444">{n_pend}</div>
          <div class="kpi-mini-sub">aguardando roteirização</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="kpi-mini">
          <div class="kpi-mini-label">Roteirizadas</div>
          <div class="kpi-mini-value" style="color:#057a55">{n_rot}</div>
          <div class="kpi-mini-sub">com placa definida</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
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
        df_hd = df_h.copy()
        if "dt_saida" in df_hd.columns:
            df_hd["dt_saida"] = df_hd["dt_saida"].apply(fmt_date)
        st.dataframe(
            df_hd[HIST_COLS].sort_values("numnota", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config=HIST_CONFIG,
        )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
