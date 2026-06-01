import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io
import base64

# --- Configuração Inicial da Página ---
st.set_page_config(
    page_title="Delly's — Transferências",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- constantes e Configurações ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- Imagens (Placeholders base64 para exemplo - Substitua pelos seus Assets reais) ---
# Imagem de fundo abstrata (gradiente escuro)
BG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
# Logo Delly's (Exemplo字母 D simples em Base64)
LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAABJUlEQVR4nO2WMQ6CQBBFZ0MlNhZEcAHiCbyAN/AGHsELSExMLCwsLLQhNibRXYkNJDYmxgaS7MrCMNyFf/G+ZGf+7M7OLMBCC/xVHxWwQaYVwAYZKM+AtgB0hN8qQJuAhB6hAOeYfYQCbJC5IgF8gD3AUkLvhgKkJviVJqA8E+ASqM+A8kzASqCD8kzoBQVIwB3gS0A+BkozIS+BNkBphvwk8EY4J4EaUDsJKEEGPgBdAeoYKM2EvARaA2UZcJdAHegF6hMgL4E6UDuJKM2EvARaA2UZcJdAHegF2gj0Am0EeoE2Ar1AG4FeoI1AL9BGoBdoI9ALtBHoBdoJTAJN9J5A7X8Ctf+JTP+V3xN9AP6WjN8T/fQAAAAASUVORK5CYII="

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

# ---TCOLS ( Colunas do Google Sheets )---
TCOLS = [
    "id", "dt_transferencia", "numped", "numnota", "nomecliente",
    "dt_liberado", "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino", "placa_road",
    "placa_veiculo", "dt_saida", "dt_roteirizacao",
    "status", "criado_em",
]

# --- Funções de Banco de Dados (Mantidas idênticas para não quebrar a lógica) ---
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
        return
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
        rows = vals[1:]
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

    # --- Lógica de busca de colunas na planilha ROAD (Simplificada para o exemplo) ---
    # Você pode precisar ajustar se os nomes das colunas no seu Google Sheets forem diferentes
    praca = safe("PRACA", "PRAÇA")
    carr = safe("CARREGAMENTO", "CARREG")
    peso = safe("PESO", "PESO BRUTO")
    valor = safe("VALOR", "VALOR TOTAL")
    
    return {
        "numped": safe("PEDIDO"),
        "numnota": safe("NF", "NOTA FISCAL"),
        "nomecliente": safe("CLIENTE", "NOME CLIENTE"),
        "dt_liberado": safe("DATA LIBERADO", "DT LIB"),
        "nomevend": safe("VENDEDOR", "VEND"),
        "nomesup": safe("SUPERVISOR", "SUP"),
        "pesobrutotot": float(str(peso).replace(",", ".")) if peso else 0.0,
        "vltotal": float(str(valor).replace("R$", "").replace(".", "").replace(",", ".")) if valor else 0.0,
        "praca": praca,
        "numcarregamento": carr,
        "destino": safe("DESTINO", "DEST"),
        "placa_road": "",
    }

# --- Funções de Formatação ---
def br(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("", "nan", "None", "—"):
        return "—"
    return str(s).strip()

def to_iso(dt_str):
    if not dt_str or dt_str == "—":
        return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str) == 10 and dt_str[2] == "/" and dt_str[5] == "/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

# --- CSS Avançado ( Dark Mode Premium ) ---
st.markdown("""
<style>
/* --- Fontes --- */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* --- Variáveis de Cores Refinadas --- */
:root {
  --bg-body: #090b10;
  --bg-panel: #0e1116;
  --bg-card: rgba(22, 27, 34, 0.7);
  
  --primary: #3b82f6;
  --primary-hover: #60a5fa;
  --primary-glow: rgba(59, 130, 246, 0.4);
  
  --accent-green: #10b981;
  --accent-green-light: rgba(16, 185, 129, 0.15);
  
  --accent-yellow: #fbbf24;
  --accent-yellow-light: rgba(251, 191, 36, 0.15);
  
  --accent-red: #ef4444;
  --accent-red-light: rgba(239, 68, 68, 0.15);
  
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --text
