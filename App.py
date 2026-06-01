import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io
import string

# As variáveis de imagem foram mantidas caso queira usar no topo.
# O fundo foi removido via CSS para manter o aspecto "Grafite Escuro" sólido.
BG_B64   = "" # Fundo mantido vazio pois usaremos cor sólida
LOGO_B64 = "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"

st.set_page_config(
    page_title="Sistema de Transferências",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
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
    rows    = vals[1:]
    hdr = [str(c).strip() for c in hdr_raw]
    n   = len(hdr)
    rows_padded = [
        row + [""] * (n - len(row)) if len(row) < n else row[:n]
        for row in rows
    ]
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

    hdr = [str(c).strip() for c in data[0]]

    for col in updates:
        if col not in hdr:
            hdr.append(col)
            col_num = len(hdr)
            ws.update_cell(1, col_num, col)

    col_idx = {c: i + 1 for i, c in enumerate(hdr)}

    row_num = None
    for i, row in enumerate(data[1:], start=2):
        row_padded = row + [""] * (len(hdr) - len(row))
        row_dict = dict(zip(hdr, row_padded))
        if row_dict.get("id", "").strip() == str(tid).strip():
            row_num = i
            break

    if row_num is None:
        st.warning(f"ID {tid} não encontrado na planilha.")
        return

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
        vals = ws.get_all_values()
        if not vals or len(vals) < 2:
            return pd.DataFrame()
        hdr_raw = vals[0]
        rows    = vals[1:]
        hdr = [str(c).upper().strip() for c in hdr_raw]
        n = len(hdr)
        rows_padded = [row + [""] * (n - len(row)) if len(row) < n else row[:n] for row in rows]
        df = pd.DataFrame(rows_padded, columns=hdr)
        df = dedup_columns(df)
        df = df.loc[:, df.columns.str.strip() != ""]
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
        for col in cols:
            v = r.get(col, "")
            sv = str(v).strip()
            if sv not in ("nan", "None", "", "0.0"):
                return sv[:-2] if sv.endswith(".0") else sv
        return ""

    praca_cols = [c for c in df.columns if "PRA" in c]
    praca = ""
    for pc in praca_cols:
        v = str(r.get(pc, "")).strip()
        if v and v not in ("nan", "None", ""):
            praca = v[:-2] if v.endswith(".0") else v
            break

    carr_cols = [c for c in df.columns if c.startswith("CARREG")]
    carr_val = ""
    for cc in carr_cols:
        v = str(r.get(cc, "")).strip()
        if v and v not in ("nan", "None", ""):
            carr_val = v[:-2] if v.endswith(".0") else v
            break

    peso_cols = [c for c in df.columns if c in ("PESO", "PESO BRUTO", "PESOBRUTO", "PESO TOTAL")]
    if not peso_cols:
        peso_cols = [c for c in df.columns if "PESO" in c]
    try:
        raw_p = str(r.get(peso_cols[0] if peso_cols else "PESO", "0")).replace(",", ".").strip()
        peso = float(raw_p)
    except Exception:
        peso = 0.0

    valor_cols = [c for c in df.columns if c in ("VALOR", "VALOR TOTAL", "VL TOTAL")]
    if not valor_cols:
        valor_cols = [c for c in df.columns if "VALOR" in c]
    try:
