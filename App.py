import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
from zoneinfo import ZoneInfo
import io
import base64
from pathlib import Path

st.set_page_config(
    page_title="Delly's — Transferências",
    page_icon="\U0001f69b",
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

TCOLS = [
    "id", "dt_transferencia", "numped", "numnota", "codcliente", "nomecliente",
    "dt_liberado", "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino", "placa_road",
    "placa_veiculo", "dt_saida", "dt_roteirizacao",
    "status", "motivo", "observacao", "criado_em",
]

def ensure_header():
    """
    Garante que a aba 'transferencias' tem EXATAMENTE os cabeçalhos de TCOLS
    nas posições corretas. Sempre reescreve a linha 1 para evitar desalinhamento.
    """
    ws = get_sheet("transferencias")
    hdr = ws.row_values(1)
    # Verifica se já está correto (evita chamada desnecessária à API)
    if hdr[:len(TCOLS)] == TCOLS and len(hdr) >= len(TCOLS):
        return ws
    # Reescreve linha 1 completa com TCOLS
    end_col = chr(ord("A") + len(TCOLS) - 1)  # "T" para 20 colunas
    ws.update(f"A1:{end_col}1", [TCOLS])
    return ws

def dedup_columns(df):
    """Remove colunas duplicadas mantendo a primeira ocorrência."""
    seen = {}
    new_cols = []
    for i, c in enumerate(df.columns):
        if c not in seen:
            seen[c] = i
            new_cols.append(c)
        else:
            new_cols.append(f"{c}__dup{i}")
    df.columns = new_cols
    # Remove colunas com sufixo __dup
    df = df[[c for c in df.columns if "__dup" not in c]]
    return df

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias(_cache_key=None):
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
    # Deriva coluna de data de registro (apenas data, sem horário)
    def _extract_date(s):
        s = str(s).strip()
        if not s:
            return ""
        # Formato dd/mm/yyyy HH:MM:SS
        if len(s) >= 10 and s[2] == "/" and s[5] == "/":
            return s[:10]
        # Formato ISO yyyy-mm-dd...
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                d, m, y = s[8:10], s[5:7], s[0:4]
                return f"{d}/{m}/{y}"
            except Exception:
                return s[:10]
        return s[:10]
    df["data_registro"] = df["criado_em"].apply(_extract_date)
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
    row["criado_em"] = datetime.now(ZoneInfo("America/Manaus")).strftime("%d/%m/%Y %H:%M:%S")
    row.setdefault("status", "pendente")
    row.setdefault("motivo", "")
    row.setdefault("codcliente", "")
    row.setdefault("placa_veiculo", "")
    row.setdefault("placa_road", "")
    row.setdefault("dt_roteirizacao", "")
    row.setdefault("dt_saida", "")
    row.setdefault("observacao", "")
    ws.append_row(
        [str(row.get(c, "")) for c in TCOLS],
        value_input_option="USER_ENTERED",
    )
    load_transferencias.clear()

def update_transf(tid, updates):
    """
    Atualiza campos de um registro pelo ID.
    Sempre relê o cabeçalho real da planilha para mapear colunas.
    Se a coluna não existe no cabeçalho, adiciona ela.
    Usa range notation (ex: "O2") para garantir a célula certa.
    """
    ws = ensure_header()
    # Força leitura fresca sem cache
    data = ws.get_all_values()
    if not data:
        return

    hdr = [str(c).strip() for c in data[0]]

    # Garante que todas as colunas de updates existem no cabeçalho
    for col in updates:
        if col not in hdr:
            # Adiciona a coluna no final do cabeçalho
            hdr.append(col)
            col_num = len(hdr)
            ws.update_cell(1, col_num, col)

    # Monta mapa coluna -> número (1-based)
    col_idx = {c: i + 1 for i, c in enumerate(hdr)}

    # Encontra a linha do registro pelo ID
    row_num = None
    for i, row in enumerate(data[1:], start=2):
        # Padeia a linha se necessário
        row_padded = row + [""] * (len(hdr) - len(row))
        row_dict = dict(zip(hdr, row_padded))
        if row_dict.get("id", "").strip() == str(tid).strip():
            row_num = i
            break

    if row_num is None:
        st.warning(f"ID {tid} não encontrado na planilha.")
        return

    # Atualiza cada campo individualmente usando notação A1 para precisão máxima
    import string
    def col_letter(n):
        """Converte número de coluna (1-based) para letra(s) estilo Excel."""
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
        raw_v = str(r.get(valor_cols[0] if valor_cols else "VALOR", "0"))
        raw_v = raw_v.replace("R$", "").replace(".", "").replace(",", ".").strip()
        vl = float(raw_v)
    except Exception:
        vl = 0.0

    ped_col = next((c for c in df.columns if c == "PEDIDO"), None)
    nf_col = col_nf
    dtlib_col = next((c for c in df.columns if "DATA" in c and ("LIBER" in c or "LIB" in c)), None)
    if dtlib_col is None:
        dtlib_col = next((c for c in df.columns if "LIBERADO" in c or "LIBERACAO" in c), None)

    placa_cols = [c for c in df.columns if "PLACA" in c]
    placa_road = ""
    for pc in placa_cols:
        v = str(r.get(pc, "")).strip()
        if v and v not in ("nan", "None", ""):
            placa_road = v[:-2] if v.endswith(".0") else v
            break

    vend_cols = [c for c in df.columns if "VEND" in c]
    vend_val = ""
    for vc in vend_cols:
        v = str(r.get(vc, "")).strip()
        if v and v not in ("nan", "None", ""):
            vend_val = v
            break

    sup_cols = [c for c in df.columns if "SUP" in c]
    sup_val = ""
    for sc in sup_cols:
        v = str(r.get(sc, "")).strip()
        if v and v not in ("nan", "None", ""):
            sup_val = v
            break

    dest_cols = [c for c in df.columns if "DEST" in c]
    dest_val = ""
    for dc in dest_cols:
        v = str(r.get(dc, "")).strip()
        if v and v not in ("nan", "None", ""):
            dest_val = v
            break

    # Código do cliente: busca coluna específica "CODIGO DO CLIENTE" ou variações
    cod_cli_cols = [c for c in df.columns if c in ("CODIGO DO CLIENTE", "CODIGO_DO_CLIENTE", "CODCLIENTE", "COD_CLI", "CODIGO CLIENTE", "CODIGO_CLIENTE")
                    or ("COD" in c and "CLI" in c)]
    cod_cli_val = ""
    for cc in cod_cli_cols:
        v = str(r.get(cc, "")).strip()
        if v and v not in ("nan", "None", "", "0.0"):
            cod_cli_val = v[:-2] if v.endswith(".0") else v
            break

    # Nome do cliente: busca coluna específica "CLIENTE" ou variações, excluindo colunas de código
    nome_cli_priority = [c for c in df.columns if c in ("CLIENTE", "NOMECLIENTE", "NOME CLIENTE", "NOME_CLIENTE")]
    nome_cli_fallback = [c for c in df.columns if "CLIEN" in c and "COD" not in c and c not in nome_cli_priority]
    cli_cols = nome_cli_priority + nome_cli_fallback
    cli_val = ""
    for clc in cli_cols:
        v = str(r.get(clc, "")).strip()
        if v and v not in ("nan", "None", ""):
            cli_val = v
            break

    return {
        "numped":          safe(ped_col or "PEDIDO"),
        "numnota":         safe(nf_col),
        "codcliente":      cod_cli_val,
        "nomecliente":     cli_val or safe("CLIENTE", "NOMECLIENTE", "NOME CLIENTE", "NOME_CLIENTE"),
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

def br(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("", "nan", "None", "\u2014"):
        return "\u2014"
    s = str(s).strip()
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        parts = s[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s

def to_iso(dt_str):
    if not dt_str or dt_str == "\u2014":
        return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str) == 10 and dt_str[2] == "/" and dt_str[5] == "/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

def safe_dataframe(df, cols):
    """Retorna df apenas com colunas existentes e sem duplicatas."""
    valid = [c for c in cols if c in df.columns]
    result = df[valid].copy()
    # Garante sem duplicatas de coluna
    result = dedup_columns(result)
    return result

# ─── Imagens em Base64 (fundo + logo) ─────────────────────────────────────────
@st.cache_data(show_spinner=False)
def img_to_base64(path):
    """
    Lê um arquivo de imagem do disco e retorna seu conteúdo em base64 (str).
    Retorna string vazia se o arquivo não existir, para o app não quebrar.
    """
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()

def find_first_existing(*candidates):
    """Retorna o primeiro caminho que existir dentre os candidatos."""
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]  # devolve o primeiro mesmo que não exista (vai gerar "")

# Ajuste os caminhos abaixo para onde os arquivos realmente estão no seu repositório.
# Procura em "assets/" e também na raiz do projeto, como fallback.
BG_PATH = find_first_existing(
    "assets/fundo.png",
    "assets/background.png",
    "fundo.png",
    "background.png",
)
LOGO_PATH = find_first_existing(
    "assets/logo.webp",
    "assets/logo.png",
    "logo.webp",
    "logo.png",
)

BG_B64 = img_to_base64(BG_PATH)
LOGO_B64 = img_to_base64(LOGO_PATH)

# ─── CSS + Imagem de Fundo + Logo ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
  --bg:           #080e17;
  --white:        #ffffff;
  --sur:          rgba(255,255,255,0.05);
  --sur2:         rgba(255,255,255,0.03);
  --bdr:          rgba(255,255,255,0.10);
  --bdr2:         rgba(255,255,255,0.18);
  --bdr-hover:    rgba(255,255,255,0.28);
  --acc:          #4c8cf5;
  --acc-lt:       rgba(76,140,245,0.12);
  --acc-mid:      rgba(76,140,245,0.24);
  --acc-hover:    #2f6fe0;
  --acc-glow:     rgba(76,140,245,0.35);
  --grn:          #3ddba0;
  --grn-dk:       #12b981;
  --grn-lt:       rgba(61,219,160,0.12);
  --grn-bdr:      rgba(61,219,160,0.32);
  --red:          #fb7c8f;
  --red-lt:       rgba(251,124,143,0.12);
  --red-bdr:      rgba(251,124,143,0.32);
  --ylw:          #fbc245;
  --ylw-lt:       rgba(251,194,69,0.12);
  --ylw-bdr:      rgba(251,194,69,0.32);
  --txt:          #f4f8ff;
  --txt2:         #96acc9;
  --txt3:         #5d7794;
  --nav-bg:       rgba(7,13,24,0.92);
  --nav-txt:      #5d7794;
  --nav-act:      #ffffff;
  --nav-acc:      #4c8cf5;
  --glass:        rgba(13,21,35,0.72);
  --glass2:       rgba(13,21,35,0.48);
  --glass-light:  rgba(255,255,255,0.045);
  --shadow-sm:    0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md:    0 4px 16px rgba(0,0,0,0.45), 0 2px 6px rgba(0,0,0,0.3);
  --shadow-lg:    0 12px 40px rgba(0,0,0,0.55), 0 4px 12px rgba(0,0,0,0.35);
  --shadow-acc:   0 0 24px rgba(76,140,245,0.20);

  /* ── Escala de espaçamento premium (ritmo consistente) ── */
  --space-1:  6px;
  --space-2:  10px;
  --space-3:  16px;
  --space-4:  24px;
  --space-5:  32px;
  --space-6:  48px;
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 20px;
  --content-max: 1400px;
}}

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"], .stApp {{
  font-family: 'Sora', sans-serif !important;
  color: var(--txt) !important;
}}

/* ── Fundo com imagem desfocada + overlay gradiente ── */
.stApp::before {{
  content: '';
  position: fixed;
  inset: 0;
  background-image: url('data:image/png;base64,{BG_B64}');
  background-size: cover;
  background-position: center;
  filter: blur(6px) brightness(0.25) saturate(0.6);
  transform: scale(1.06);
  z-index: -2;
}}
.stApp::after {{
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 10% 0%, rgba(59,130,246,0.08) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 90% 100%, rgba(16,185,129,0.05) 0%, transparent 60%),
    linear-gradient(180deg, rgba(6,10,20,0.55) 0%, rgba(6,10,20,0.20) 100%);
  z-index: -1;
  pointer-events: none;
}}
.stApp {{
  background: transparent !important;
}}

#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
section[data-testid="stSidebar"] {{ display: none !important; }}
.main .block-container {{ padding: 0 !important; max-width: 100% !important; }}

/* ══════════════════════════════════════════════════════════════════════════
   CABEÇALHO PREMIUM — logo, título, abas, avatar, notificações, tema
   ══════════════════════════════════════════════════════════════════════════ */
.st-key-app_header {{
  background: var(--nav-bg);
  backdrop-filter: blur(26px) saturate(180%);
  -webkit-backdrop-filter: blur(26px) saturate(180%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg), 0 0 46px rgba(76,140,245,0.10), inset 0 1px 0 rgba(255,255,255,0.06);
  margin: 14px 22px 0;
  padding: 14px 22px;
  position: sticky;
  top: 12px;
  z-index: 999;
  transition: box-shadow .25s ease;
}}
.st-key-app_header::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(120deg, rgba(76,140,245,0.35), transparent 30%, transparent 70%, rgba(61,219,160,0.20));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.st-key-app_header [data-testid="stVerticalBlockBorderWrapper"] {{ position: relative; }}
.st-key-app_header [data-testid="stHorizontalBlock"] {{
  align-items: center !important;
  gap: 0.5rem !important;
}}

/* Marca / logo */
.hdr-brand {{
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}}
.hdr-logo-ring {{
  position: relative;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #4c8cf5, #3ddba0);
  padding: 2px;
  box-shadow: 0 0 22px rgba(76,140,245,0.45), var(--shadow-sm);
}}
.hdr-logo-ring img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  border: 2px solid rgba(8,14,23,0.9);
  display: block;
}}
.hdr-brand-text {{
  display: flex;
  flex-direction: column;
  line-height: 1.18;
  min-width: 0;
}}
.hdr-title {{
  font-family: 'Sora', sans-serif;
  font-weight: 800;
  font-size: 1.32rem;
  color: #f4f8ff;
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.hdr-title span {{ color: #4c8cf5; }}
.hdr-sub {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.60rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--txt2);
  margin-top: 2px;
}}

/* Abas (st.radio) estilizadas como pill-tabs dentro do cabeçalho */
.st-key-app_header div[data-testid="stRadio"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  position: static !important;
  padding: 0 !important;
}}
.st-key-app_header div[data-testid="stRadio"] > label {{ display: none !important; }}
.st-key-app_header div[data-testid="stRadio"] > div {{
  display: flex !important;
  flex-direction: row !important;
  justify-content: center !important;
  align-items: center !important;
  gap: 4px !important;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--bdr);
  border-radius: 14px;
  padding: 4px !important;
  width: fit-content !important;
  margin: 0 auto !important;
}}
.st-key-app_header div[data-testid="stRadio"] > div > label {{
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 9px 20px !important;
  font-size: 0.66rem !important;
  font-weight: 700 !important;
  cursor: pointer !important;
  border: none !important;
  color: var(--nav-txt) !important;
  font-family: 'Sora', sans-serif !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  transition: all 0.25s cubic-bezier(0.4,0,0.2,1) !important;
  border-radius: 10px !important;
  background: transparent !important;
  margin: 0 !important;
}}
.st-key-app_header div[data-testid="stRadio"] > div > label:hover {{
  color: rgba(240,246,255,0.85) !important;
  background: rgba(255,255,255,0.05) !important;
}}
.st-key-app_header div[data-testid="stRadio"] > div > label[data-selected="true"] {{
  color: #fff !important;
  background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
  box-shadow: 0 4px 16px rgba(59,130,246,0.45), 0 1px 3px rgba(0,0,0,0.3) !important;
}}
.st-key-app_header div[data-testid="stRadio"] > div > label > div:first-child {{
  display: none !important;
}}

/* Botões de ação do cabeçalho (tema / notificações / avatar) */
.st-key-app_header .stButton,
.st-key-app_header [data-testid="stPopover"] {{
  display: flex !important;
  justify-content: center !important;
}}
.st-key-app_header .stButton > button,
.st-key-app_header [data-testid="stPopover"] > div > button {{
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 12px !important;
  color: var(--txt) !important;
  font-size: 0.95rem !important;
  padding: 8px 12px !important;
  min-width: 0 !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
}}
.st-key-app_header .stButton > button:hover,
.st-key-app_header [data-testid="stPopover"] > div > button:hover {{
  background: rgba(255,255,255,0.10) !important;
  border-color: var(--bdr-hover) !important;
  transform: translateY(-2px) !important;
  box-shadow: var(--shadow-md), 0 0 14px rgba(76,140,245,0.20) !important;
}}

/* Avatar circular (5ª coluna do cabeçalho) */
.st-key-app_header [data-testid="column"]:nth-of-type(5) [data-testid="stPopover"] > div > button {{
  border-radius: 50% !important;
  width: 42px !important;
  height: 42px !important;
  padding: 0 !important;
  background: linear-gradient(135deg, #4c8cf5, #2f6fe0) !important;
  color: #fff !important;
  font-weight: 800 !important;
  font-size: 0.82rem !important;
  border: 2px solid rgba(255,255,255,0.18) !important;
  box-shadow: 0 0 14px rgba(76,140,245,0.45), var(--shadow-sm) !important;
}}

/* Badge de notificações (4ª coluna do cabeçalho) */
.st-key-app_header [data-testid="column"]:nth-of-type(4) {{ position: relative; }}
.hdr-badge {{
  position: absolute;
  top: -4px;
  right: 10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: linear-gradient(135deg, #fb7c8f, #ef4444);
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.56rem;
  font-weight: 800;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 10px rgba(251,124,143,0.6);
  z-index: 20;
  pointer-events: none;
}}

/* Painel dos popovers (notificações / usuário) */
div[data-testid="stPopoverBody"] {{
  background: var(--glass) !important;
  backdrop-filter: blur(22px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(22px) saturate(180%) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-lg) !important;
}}
.hdr-pop-title {{
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--txt);
  margin-bottom: 4px;
}}
.hdr-notif-item {{
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 7px 0;
  border-bottom: 1px solid var(--bdr);
  font-size: 0.76rem;
  color: var(--txt2);
}}
.hdr-notif-item:last-child {{ border-bottom: none; }}
.hdr-notif-dot {{
  width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
}}
.hdr-user-name {{ font-size: 0.86rem; font-weight: 700; color: var(--txt); }}
.hdr-user-mail {{ font-size: 0.70rem; color: var(--txt3); margin-bottom: 8px; }}
</style>
""", unsafe_allow_html=True)


# ─── Cabeçalho Premium — logo, título, abas, tema, notificações e avatar ─────
if "_tema_claro" not in st.session_state:
    st.session_state["_tema_claro"] = False

header_ctr = st.container(key="app_header")
with header_ctr:
    hcol_brand, hcol_tabs, hcol_theme, hcol_notif, hcol_user = st.columns(
        [2.6, 4.2, 0.55, 0.55, 0.55], gap="small"
    )

    with hcol_brand:
        _logo_html = (
            f'<img src="data:image/webp;base64,{LOGO_B64}" alt="Delly\'s Logo"/>'
            if LOGO_B64 else ""
        )
        st.markdown(
            '<div class="hdr-brand">'
            f'<div class="hdr-logo-ring">{_logo_html}</div>'
            '<div class="hdr-brand-text">'
            '<span class="hdr-title">Delly\'s <span>Transferências</span></span>'
            '<span class="hdr-sub">Registro de Transferência</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with hcol_tabs:
        pagina = st.radio(
            "nav",
            ["📝  Registro", "🗺️  Roteirização", "📋  Histórico"],
            horizontal=True,
            label_visibility="collapsed",
            key="nav_main",
        )

    with hcol_theme:
        _tema_icon = "☀️" if st.session_state["_tema_claro"] else "🌙"
        if st.button(_tema_icon, key="btn_tema_header", help="Alternar tema claro/escuro"):
            st.session_state["_tema_claro"] = not st.session_state["_tema_claro"]
            st.rerun()

    with hcol_notif:
        st.markdown('<span class="hdr-badge">2</span>', unsafe_allow_html=True)
        with st.popover("🔔", help="Notificações"):
            st.markdown('<div class="hdr-pop-title">Notificações</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="hdr-notif-item"><span class="hdr-notif-dot" style="background:#fbc245"></span>'
                'Existem notas pendentes de roteirização hoje.</div>'
                '<div class="hdr-notif-item"><span class="hdr-notif-dot" style="background:#4c8cf5"></span>'
                'Sincronização com a base ROAD concluída.</div>',
                unsafe_allow_html=True,
            )

    with hcol_user:
        with st.popover("N", help="Minha conta"):
            st.markdown(
                '<div class="hdr-user-name">Ney</div>'
                '<div class="hdr-user-mail">Painel de Transferências · Delly\'s</div>',
                unsafe_allow_html=True,
            )
            st.button("🚪 Sair", key="btn_logout_header", use_container_width=True)

# ─── Filter Bar ───────────────────────────────────────────────────────────────
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
fc0, fc1, fc2, fc5 = st.columns([3.4, 1.4, 1.1, 3.4], gap="medium")
with fc1:
    data_filtro = st.date_input(
        "📅 Data",
        value=st.session_state.get("_ultima_data_filtro", date.today()),
        key="data_global",
        format="DD/MM/YYYY",
    )
with fc2:
    st.markdown("<br>", unsafe_allow_html=True)
    _vt_ativo = st.session_state.get("_ver_todas", False)
    _label_toggle = ("✓ Todas as datas") if _vt_ativo else "Todas as datas"
    _bg    = "rgba(59,130,246,0.2)"  if _vt_ativo else "rgba(255,255,255,0.05)"
    _borda = "#3b82f6"               if _vt_ativo else "rgba(255,255,255,0.12)"
    _color = "#93c5fd"               if _vt_ativo else "rgba(255,255,255,0.38)"
    st.markdown(f"""<style>
    div[data-testid="stButton"] button[kind="secondary"]#btn_ver_todas,
    div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] > button {{
        background: {_bg} !important;
        border: 1px solid {_borda} !important;
        color: {_color} !important;
        font-size: 0.7rem !important;
        font-weight: 500 !important;
        padding: 3px 10px !important;
        height: auto !important;
        min-height: 0 !important;
        border-radius: 6px !important;
        margin-top: 20px !important;
        box-shadow: none !important;
        letter-spacing: .04em !important;
    }}
    </style>""", unsafe_allow_html=True)
    if st.button(_label_toggle, key="btn_ver_todas"):
        st.session_state["_ver_todas"] = not _vt_ativo
        load_transferencias.clear()
        st.rerun()
    ver_todas = st.session_state.get("_ver_todas", False)
with fc5:
    pass
st.markdown("</div>", unsafe_allow_html=True)

# ─── Detecta mudança de data e recarrega dashboard ────────────────────────────
if "_ultima_data_filtro" not in st.session_state:
    st.session_state["_ultima_data_filtro"] = data_filtro

if "_ver_todas" not in st.session_state:
    st.session_state["_ver_todas"] = False

_data_changed = data_filtro != st.session_state["_ultima_data_filtro"]

if _data_changed:
    st.session_state["_ultima_data_filtro"] = data_filtro
    load_transferencias.clear()
    st.rerun()

# ─── Carrega dados ────────────────────────────────────────────────────────────
data_str     = data_filtro.isoformat()
data_display = data_filtro.strftime("%d/%m/%Y")
usar_intervalo = False

df_all = load_transferencias(_cache_key="all" if ver_todas else data_str)
if ver_todas:
    df = df_all.copy() if not df_all.empty else pd.DataFrame(columns=TCOLS)
    periodo_txt = "Todas as datas"
else:
    df = (
        df_all[df_all["data_registro"] == data_display].copy()
        if not df_all.empty
        else pd.DataFrame(columns=TCOLS)
    )
    periodo_txt = data_display

# ─── Colunas padrão de exibição ───────────────────────────────────────────────
STD_COLS = [
    "data_registro", "placa_road", "motivo", "observacao",
    "numnota", "numped", "codcliente", "nomecliente", "dt_liberado",
    "nomevend", "nomesup", "pesobrutotot", "vltotal",
    "praca", "numcarregamento", "destino",
]
STD_CONFIG = {
    "data_registro":   st.column_config.TextColumn("Data de Registro", width="small"),
    "numnota":         st.column_config.TextColumn("Nota Fiscal",    width="small"),
    "numped":          st.column_config.TextColumn("Pedido",         width="small"),
    "codcliente":      st.column_config.TextColumn("Cód. Cliente",   width="small"),
    "nomecliente":     st.column_config.TextColumn("Cliente",        width="medium"),
    "dt_liberado":     st.column_config.TextColumn("Dt. Liberado",   width="small"),
    "nomevend":        st.column_config.TextColumn("Vendedor",       width="small"),
    "nomesup":         st.column_config.TextColumn("Supervisor",     width="small"),
    "pesobrutotot":    st.column_config.NumberColumn("Peso (kg)",    format="%.3f", width="small"),
    "vltotal":         st.column_config.NumberColumn("Valor (R$)",   format="R$ %.2f", width="small"),
    "praca":           st.column_config.TextColumn("Praça",          width="small"),
    "numcarregamento": st.column_config.TextColumn("Carregamento",   width="small"),
    "destino":         st.column_config.TextColumn("Destino",        width="small"),
    "placa_road":      st.column_config.TextColumn("Placa Antiga",   width="small"),
    "motivo":          st.column_config.TextColumn("Motivo",         width="medium"),
    "observacao":      st.column_config.TextColumn("Observação",     width="medium"),
}

st.markdown('<div class="page-body">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD OVERVIEW (topo sempre visível)
# ═══════════════════════════════════════════════════════════════════════════════
_df_all_dash = load_transferencias(_cache_key=data_str)
_today_str   = date.today().strftime("%d/%m/%Y")
_df_today    = _df_all_dash[_df_all_dash["data_registro"] == _today_str] if not _df_all_dash.empty else pd.DataFrame()
_df_pend_all = _df_all_dash[_df_all_dash["status"].isin(["pendente",""])  | _df_all_dash["status"].isna()] if not _df_all_dash.empty else pd.DataFrame()
_df_rot_all  = _df_all_dash[_df_all_dash["status"] == "roteirizado"] if not _df_all_dash.empty else pd.DataFrame()
_n_today     = len(_df_today)
_n_pend      = len(_df_pend_all)
_n_rot       = len(_df_rot_all)
_n_total     = len(_df_all_dash)
_vl_today    = _df_today["vltotal"].sum() if not _df_today.empty else 0
_vl_total    = _df_all_dash["vltotal"].sum() if not _df_all_dash.empty else 0
_peso_today  = _df_today["pesobrutotot"].sum() if not _df_today.empty else 0
_pct_rot     = int((_n_rot / _n_total * 100) if _n_total > 0 else 0)
_pct_pend    = 100 - _pct_rot

# ── Agregações para os gráficos ───────────────────────────────────────────────
# Top supervisores por valor
_top_sup = pd.DataFrame()
if not _df_all_dash.empty and "nomesup" in _df_all_dash.columns:
    _top_sup = _df_all_dash.groupby("nomesup")["vltotal"].sum().sort_values(ascending=False).head(7).reset_index()
    _top_sup.columns = ["supervisor", "valor"]

# Top praças por qtd de NFs
_top_praca = pd.DataFrame()
if not _df_all_dash.empty and "praca" in _df_all_dash.columns:
    _top_praca = _df_all_dash.groupby("praca")["numnota"].count().sort_values(ascending=False).head(7).reset_index()
    _top_praca.columns = ["praca", "qtd"]

# Top veículos (placa_road) por qtd de transferências
_top_veiculo = pd.DataFrame()
if not _df_all_dash.empty and "placa_road" in _df_all_dash.columns:
    _df_veic = _df_all_dash[_df_all_dash["placa_road"].notna() & (_df_all_dash["placa_road"].astype(str).str.strip() != "")]
    if not _df_veic.empty:
        _top_veiculo = _df_veic.groupby("placa_road")["numnota"].count().sort_values(ascending=False).reset_index()
        _top_veiculo.columns = ["placa", "qtd"]

# Top vendedores por qtd de NFs
_top_vend = pd.DataFrame()
if not _df_all_dash.empty and "nomevend" in _df_all_dash.columns:
    _top_vend = _df_all_dash.groupby("nomevend")["numnota"].count().sort_values(ascending=False).head(7).reset_index()
    _top_vend.columns = ["vendedor", "qtd"]

# Top clientes por valor (para gráfico de barras estilo imagem)
_top_cli = pd.DataFrame()
if not _df_all_dash.empty and "nomecliente" in _df_all_dash.columns:
    _grp_cli = _df_all_dash.groupby("nomecliente").agg(
        valor=("vltotal", "sum"),
        qtd=("numnota", "count")
    ).sort_values("valor", ascending=False).head(12).reset_index()
    _grp_cli.columns = ["cliente", "valor", "qtd"]
    _top_cli = _grp_cli

# Last 5 notas
_last5 = _df_all_dash.tail(5)[::-1] if not _df_all_dash.empty else pd.DataFrame()

_vl_pend = _df_pend_all["vltotal"].sum() if not _df_pend_all.empty else 0

# ── Helper: gráfico de barras horizontal em HTML puro ─────────────────────────
def _bar_chart_html(rows, label_key, value_key, color, fmt_val=None):
    if not rows:
        return '<div style="padding:.75rem;color:#5d7794;font-size:.78rem;text-align:center">Sem dados</div>'
    max_v = max(r[value_key] for r in rows) or 1
    bars = ""
    for i, r in enumerate(rows):
        lbl   = str(r[label_key])[:20] or "—"
        val   = r[value_key]
        pct   = int(val / max_v * 100)
        shown = fmt_val(val) if fmt_val else str(val)
        bars += f'''
        <div style="display:grid;grid-template-columns:140px 1fr 70px;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
          <div style="font-size:.75rem;color:#96acc9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{lbl}">{lbl}</div>
          <div style="background:rgba(255,255,255,0.05);border-radius:4px;height:8px;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;transition:width .4s ease"></div>
          </div>
          <div style="font-size:.75rem;font-weight:700;color:#f0f6ff;text-align:right;white-space:nowrap">{shown}</div>
        </div>'''
    return bars

# ── Helper: gráfico de colunas verticais em HTML puro ─────────────────────────
def _col_chart_html(rows, label_key, value_key, color, fmt_val=None, height=90):
    if not rows:
        return '<div style="padding:.75rem;color:#5d7794;font-size:.78rem;text-align:center">Sem dados</div>'
    max_v = max(r[value_key] for r in rows) or 1
    cols_html = ""
    for r in rows:
        lbl   = str(r[label_key])
        # shorten label
        short = lbl[:8] + "…" if len(lbl) > 9 else lbl
        val   = r[value_key]
        pct   = int(val / max_v * 100)
        bar_h = max(4, int(pct / 100 * height))
        shown = fmt_val(val) if fmt_val else str(val)
        cols_html += f'''
        <div style="display:flex;flex-direction:column;align-items:center;gap:3px;flex:1;min-width:0">
          <div style="font-size:.68rem;font-weight:700;color:#f0f6ff">{shown}</div>
          <div style="width:100%;display:flex;align-items:flex-end;justify-content:center;height:{height}px">
            <div style="width:70%;background:{color};border-radius:4px 4px 0 0;height:{bar_h}px;min-height:4px;box-shadow:0 0 8px {color}55"></div>
          </div>
          <div style="font-size:.62rem;color:#96acc9;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;padding:0 2px" title="{lbl}">{short}</div>
        </div>'''
    return f'<div style="display:flex;gap:4px;align-items:flex-end;padding:.5rem .25rem 0">{cols_html}</div>'



# ── Helper: gera SVG de colunas verticais com linha de qtd ────────────────────
def _svg_col_line(rows, label_key, val_key, qtd_key, bar_color_1, bar_color_2, line_color="#fbbf24", fmt_val=None):
    """Retorna string SVG: barras verticais + polyline de quantidade."""
    if not rows:
        return '<p style="color:#5d7794;font-size:.78rem;text-align:center;padding:1rem">Sem dados</p>'
    n        = len(rows)
    MIN_SLOT = 60   # largura mínima por coluna para não ficar espremido
    SVG_W    = max(560, n * MIN_SLOT)
    TOP_PAD  = 56   # espaço acima das barras (rótulos de valor)
    BAR_AREA = 160  # altura da área de barras
    BOT_PAD  = 30   # espaço abaixo para rótulos de nome
    SVG_H    = TOP_PAD + BAR_AREA + BOT_PAD
    slot_w   = SVG_W / max(n, 1)
    bar_w    = min(slot_w * 0.55, 80)  # máx 80px para não estourar com poucos itens
    max_val  = max(r[val_key] for r in rows) or 1
    max_qtd  = max(r[qtd_key] for r in rows) if qtd_key else 1

    defs  = f'<defs><linearGradient id="gcol" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="{bar_color_1}"/><stop offset="100%" stop-color="{bar_color_2}"/></linearGradient></defs>'
    rects = ""
    labels= ""
    pts   = []

    for i, r in enumerate(rows):
        lbl   = str(r[label_key])
        short = (lbl[:9] + "…") if len(lbl) > 10 else lbl
        val   = r[val_key]
        bh    = max(4, int(val / max_val * BAR_AREA))
        cx    = slot_w * i + slot_w / 2
        bx    = cx - bar_w / 2
        by    = TOP_PAD + BAR_AREA - bh
        shown = fmt_val(val) if fmt_val else str(int(val))

        rects += f'<rect x="{bx:.1f}" y="{by}" width="{bar_w:.1f}" height="{bh}" rx="3" fill="url(#gcol)" opacity="0.9"/>'
        # valor dentro da barra (10px abaixo do topo), só mostra fora se barra for muito pequena
        val_ty = by + 14
        if bh >= 18:
            rects += f'<text x="{cx:.1f}" y="{val_ty}" text-anchor="middle" font-size="11" font-weight="700" fill="#f0f6ff">{shown}</text>'
        else:
            rects += f'<text x="{cx:.1f}" y="{by - 4}" text-anchor="middle" font-size="11" font-weight="700" fill="#f0f6ff">{shown}</text>'
        labels+= f'<text x="{cx:.1f}" y="{TOP_PAD + BAR_AREA + 16}" text-anchor="middle" font-size="11" font-weight="600" fill="#a9bfd9">{short}</text>'

        if qtd_key:
            qtd    = int(r[qtd_key])
            # linha amarela flutua 18px acima do topo de cada barra
            dot_y  = by - 20
            pts.append((cx, dot_y, qtd))

    poly = ""
    dots = ""
    if pts:
        poly_str = " ".join(f"{x:.1f},{y}" for x, y, _ in pts)
        poly = f'<polyline points="{poly_str}" fill="none" stroke="{line_color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>'
        for x, y, q in pts:
            dots += f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{line_color}" stroke="#141e2b" stroke-width="1.5"/>'
            dots += f'<text x="{x:.1f}" y="{y - 9}" text-anchor="middle" font-size="11" font-weight="700" fill="{line_color}">{q}</text>'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'style="width:100%;height:auto;display:block">'
        f'{defs}{rects}{labels}{poly}{dots}</svg>'
    )


# ── Helper: gera SVG de barras horizontais ────────────────────────────────────
def _svg_bar_horiz(rows, label_key, val_key, bar_color_1, bar_color_2, fmt_val=None):
    """Retorna string SVG: barras horizontais."""
    if not rows:
        return '<p style="color:#5d7794;font-size:.78rem;text-align:center;padding:1rem">Sem dados</p>'
    n        = len(rows)
    LABEL_W  = 70   # largura da coluna de rótulos
    BAR_H    = 10   # altura de cada barra
    ROW_H    = 28   # altura por linha
    VAL_W    = 55   # largura coluna de valores
    SVG_W    = 400
    SVG_H    = n * ROW_H + 8
    BAR_AREA = SVG_W - LABEL_W - VAL_W - 8
    max_val  = max(r[val_key] for r in rows) or 1

    defs = f'<defs><linearGradient id="gbar" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="{bar_color_1}"/><stop offset="100%" stop-color="{bar_color_2}"/></linearGradient></defs>'
    els  = ""

    for i, r in enumerate(rows):
        lbl   = str(r[label_key])
        short = (lbl[:9] + "…") if len(lbl) > 10 else lbl
        val   = r[val_key]
        bw    = max(4, int(val / max_val * BAR_AREA))
        y_mid = i * ROW_H + ROW_H / 2 + 4
        bar_y = y_mid - BAR_H / 2
        shown = fmt_val(val) if fmt_val else str(int(val))

        # linha de fundo
        els += f'<rect x="{LABEL_W}" y="{bar_y:.1f}" width="{BAR_AREA}" height="{BAR_H}" rx="3" fill="rgba(255,255,255,0.05)"/>'
        # barra colorida
        els += f'<rect x="{LABEL_W}" y="{bar_y:.1f}" width="{bw}" height="{BAR_H}" rx="3" fill="url(#gbar)" opacity="0.9"/>'
        # rótulo esquerdo
        els += f'<text x="{LABEL_W - 4}" y="{y_mid:.1f}" text-anchor="end" dominant-baseline="middle" font-size="8.5" fill="#96acc9">{short}</text>'
        # valor direito
        els += f'<text x="{LABEL_W + BAR_AREA + 4}" y="{y_mid:.1f}" dominant-baseline="middle" font-size="8.5" font-weight="700" fill="#f0f6ff">{shown}</text>'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'style="width:100%;height:auto;display:block">'
        f'{defs}{els}</svg>'
    )


# ── Gráficos movidos para a aba Histórico (ver abaixo) ────────────────────────



# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRO
# ═══════════════════════════════════════════════════════════════════════════════
if pagina == "📝  Registro":

    _c_left, col_form, _c_right = st.columns([1, 3, 1], gap="large")

    with col_form:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("""
        <div class="card-head">
          <span class="card-title">🔍 Buscar Nota Fiscal</span>
        </div>
        <div class="card-body">
        """, unsafe_allow_html=True)

        ca, cb = st.columns([2, 1], gap="medium")
        with ca:
            nota_inp = st.text_input(
                "Número da Nota Fiscal",
                placeholder="Ex: 398234",
                key="nota_inp",
            )
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar_btn = st.button("🔍 Buscar", use_container_width=True, key="buscar_btn")

        st.markdown("</div></div>", unsafe_allow_html=True)


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

            r1a, r1b, r1c = st.columns(3, gap="medium")
            with r1a: st.text_input("Pedido",       value=cur["numped"]          or "—", disabled=True, key="d_ped")
            with r1b: st.text_input("Nota Fiscal",   value=cur["numnota"],                disabled=True, key="d_nf")
            with r1c: st.text_input("Carregamento",  value=cur["numcarregamento"] or "—", disabled=True, key="d_car")

            r2a, r2b, r2c = st.columns(3, gap="medium")
            with r2a: st.text_input("Cliente",       value=cur["nomecliente"],             disabled=True, key="d_cli")
            with r2b: st.text_input("Cód. Cliente",  value=cur.get("codcliente", "") or "—", disabled=True, key="d_codcli")
            with r2c: st.text_input("Data Liberado", value=cur["dt_liberado"]    or "—", disabled=True, key="d_dtl")

            r3a, r3b, r3c = st.columns(3, gap="medium")
            with r3a: st.text_input("Vendedor",      value=cur["nomevend"]        or "—", disabled=True, key="d_vnd")
            with r3b: st.text_input("Supervisor",    value=cur["nomesup"]         or "—", disabled=True, key="d_sup")
            with r3c: st.text_input("Praça",         value=cur["praca"]           or "—", disabled=True, key="d_prc")

            r4a, r4b, r4c = st.columns(3, gap="medium")
            with r4a: st.text_input("Destino",       value=cur["destino"]         or "—", disabled=True, key="d_dst")
            with r4b: st.text_input("Peso (kg)", value=f"{cur['pesobrutotot']:.3f}".replace(".", ","), disabled=True, key="d_pes")
            with r4c: st.text_input("Valor Total",  value=br(cur["vltotal"]),              disabled=True, key="d_vl")

            r5a, r5b, r5c = st.columns(3, gap="medium")
            with r5a:
                placa_antiga = cur.get("placa_road", "") or "—"
                st.text_input("Placa Anterior",       value=placa_antiga,                  disabled=True, key="d_pl")

            if cur.get("placa_road"):
                st.markdown(f'<div class="al-w">⚠️ Essa nota teve entrega anterior com placa <strong>{cur["placa_road"]}</strong>.</div>', unsafe_allow_html=True)

            st.markdown('<div class="al-i">ℹ️ A nova placa e data de saída serão informadas pela <strong>Roteirização</strong>.</div>', unsafe_allow_html=True)

            st.markdown("""
            <div class="sec-div" style="margin-top:1.1rem">
              <div class="sec-div-line"></div>
              <div class="sec-div-txt">📋 Motivo da Transferência</div>
              <div class="sec-div-line"></div>
            </div>
            """, unsafe_allow_html=True)
            MOTIVOS = [
                "— Selecione um motivo —",
                "Falta de Mercadoria na Carga",
                "Produto Descongelado avariado",
                "Atraso na entrega",
                "Fora de rota/geolocalização",
                "Sinistro/roubo",
                "Cliente não fez o pedido",
                "Cliente Fechado",
                "Pedido incorreto",
                "Produto de padrão do cliente",
                "Preço incorreto",
                "Pedido duplicado",
                "Cliente cancelou/Desistiu",
                "✏️ Outro (digitar)",
            ]
            motivo_sel = st.selectbox(
                "Motivo",
                options=MOTIVOS,
                key="motivo_input",
                label_visibility="collapsed",
            )
            if motivo_sel == "✏️ Outro (digitar)":
                motivo_outro = st.text_input(
                    "Descreva o motivo",
                    placeholder="Digite o motivo da transferência...",
                    key="motivo_outro_input",
                )
                motivo_input = motivo_outro.strip() if motivo_outro else ""
            else:
                motivo_input = motivo_sel

            st.markdown("""
            <div class="sec-div" style="margin-top:1.1rem">
              <div class="sec-div-line"></div>
              <div class="sec-div-txt">💬 Observação (opcional)</div>
              <div class="sec-div-line"></div>
            </div>
            """, unsafe_allow_html=True)
            obs_input = st.text_area(
                "Observação",
                placeholder="Ex: Entrega fracionada, cliente solicitou reagendamento, carga especial...",
                key="obs_input",
                height=80,
                label_visibility="collapsed",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True, key="confirm_btn"):
                if not motivo_input or motivo_input == "— Selecione um motivo —":
                    if motivo_sel == "✏️ Outro (digitar)":
                        st.markdown('<div class="al-e">❌ Digite o <strong>Motivo</strong> no campo acima antes de confirmar.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="al-e">❌ Selecione um <strong>Motivo</strong> antes de confirmar.</div>', unsafe_allow_html=True)
                else:
                    dt_s = date.today().isoformat()  # data de registro gerada automaticamente pelo sistema
                    if check_dup(cur["numnota"], dt_s):
                        st.markdown(f'<div class="al-e">❌ Nota {cur["numnota"]} já registrada em {fmt_date(dt_s)}.</div>', unsafe_allow_html=True)
                    else:
                        with st.spinner("Salvando..."):
                            append_transf({
                                "dt_transferencia": dt_s,
                                "numped":          cur["numped"],
                                "numnota":         cur["numnota"],
                                "codcliente":      cur.get("codcliente", ""),
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
                                "motivo":          motivo_input.strip(),
                                "observacao":      obs_input.strip() if obs_input else "",
                            })
                        st.success(f"✅ Transferência registrada! Nota {cur['numnota']} aguarda roteirização.")
                        st.session_state.cur = None
                        st.balloons()
                        st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="border-style:dashed;border-color:rgba(255,255,255,0.15)">
              <div class="card-body" style="text-align:center;padding:2.5rem;color:var(--txt3)">
                <div style="font-size:2.5rem;margin-bottom:.6rem">🧾</div>
                <div style="font-size:.85rem">Informe o número da nota e clique em <strong style="color:var(--acc)">Buscar</strong></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    df_hj = (
        df_all[df_all["data_registro"] == data_display]
        if not df_all.empty
        else pd.DataFrame()
    )
    n_hj = len(df_hj)

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
        df_show = dedup_columns(df_hj[SHOW].copy())
        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={k: v for k, v in STD_CONFIG.items() if k in df_show.columns},
        )
        st.markdown('<div style="padding:.75rem 1.25rem;border-top:1px solid var(--bdr)">', unsafe_allow_html=True)
        ids_hj = df_hj["id"].astype(str).tolist()
        cd1, cd2, _ = st.columns([2, 1, 3], gap="medium")
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
    # pend e rote: filtrados pela data de registro (ou todas as datas se ver_todas)
    _base_pend = df_all[df_all["status"].isin(["pendente", ""]) | df_all["status"].isna()].copy() if not df_all.empty else pd.DataFrame()
    rote_base  = df_all[df_all["status"] == "roteirizado"].copy() if not df_all.empty else pd.DataFrame()

    if ver_todas:
        pend = _base_pend
        rote = rote_base
    else:
        pend = _base_pend[_base_pend["data_registro"] == data_display].copy() if not _base_pend.empty else pd.DataFrame()
        rote = rote_base[rote_base["data_registro"] == data_display].copy() if not rote_base.empty else pd.DataFrame()

    # Garante que colunas de roteirização existem
    for _c in ["placa_veiculo", "dt_saida", "dt_roteirizacao"]:
        if not pend.empty and _c not in pend.columns:
            pend[_c] = ""
        if not rote.empty and _c not in rote.columns:
            rote[_c] = ""



    st.markdown('<div class="card" style="border-top:3px solid #f87171">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#f87171">⏳ Notas Pendentes</span>
      <span class="card-count">{len(pend)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div style="padding:1.5rem;text-align:center"><span class="al-s" style="justify-content:center">✅ Nenhuma nota pendente!</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-body" style="padding-bottom:.5rem">', unsafe_allow_html=True)
        pb1, pb2 = st.columns([3, 1], gap="medium")
        with pb1:
            bp = st.text_input("Buscar", key="rbp", label_visibility="collapsed", placeholder="🔍 Nota, cliente, praça...")
        with pb2:
            datas_pend = sorted(pend["data_registro"].dropna().unique().tolist(), reverse=True)
            datas_fmt = ["Todas"] + [d for d in datas_pend]
            fdp_fmt = st.selectbox("Data", datas_fmt, key="rdp", label_visibility="collapsed")
            fdp = fdp_fmt

        df_p = pend.copy()
        if fdp != "Todas":
            df_p = df_p[df_p["data_registro"] == fdp]
        if bp:
            m = df_p.apply(lambda r: bp.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_p = df_p[m]

        st.caption(f"{len(df_p)} nota(s) pendentes")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Tabela nativa (st.dataframe) + painel de roteirização ───────────
        PEND_COLS = [c for c in [
            "data_registro", "placa_road", "motivo", "observacao",
            "numnota", "numped", "codcliente", "nomecliente", "dt_liberado",
            "nomevend", "nomesup", "pesobrutotot", "vltotal",
            "praca", "numcarregamento", "destino",
        ] if c in df_p.columns]

        PEND_CONFIG = {
            "data_registro":   st.column_config.TextColumn("Data de Registro", width="small"),
            "numnota":         st.column_config.TextColumn("Nota Fiscal",   width="small"),
            "numped":          st.column_config.TextColumn("Pedido",        width="small"),
            "codcliente":      st.column_config.TextColumn("Cód. Cliente",  width="small"),
            "nomecliente":     st.column_config.TextColumn("Cliente",       width="medium"),
            "dt_liberado":     st.column_config.TextColumn("Dt. Liberado",  width="small"),
            "nomevend":        st.column_config.TextColumn("Vendedor",      width="small"),
            "nomesup":         st.column_config.TextColumn("Supervisor",    width="small"),
            "pesobrutotot":    st.column_config.NumberColumn("Peso (kg)",   format="%.3f", width="small"),
            "vltotal":         st.column_config.NumberColumn("Valor (R$)",  format="R$ %.2f", width="small"),
            "praca":           st.column_config.TextColumn("Praça",         width="small"),
            "numcarregamento": st.column_config.TextColumn("Carregamento",  width="small"),
            "destino":         st.column_config.TextColumn("Destino",       width="small"),
            "placa_road":      st.column_config.TextColumn("Placa Antiga",  width="small"),
            "motivo":          st.column_config.TextColumn("Motivo",        width="medium"),
            "observacao":      st.column_config.TextColumn("Observação",    width="medium"),
        }

        if df_p.empty:
            st.markdown('<div class="al-i" style="margin:1rem 1.25rem">Nenhuma nota pendente nos filtros.</div>', unsafe_allow_html=True)
        else:
            df_p_sorted = df_p.sort_values("dt_liberado", ascending=False).reset_index(drop=True)
            df_p_display = dedup_columns(df_p_sorted[PEND_COLS].copy()) if PEND_COLS else df_p_sorted

            st.dataframe(
                df_p_display,
                use_container_width=True,
                hide_index=True,
                column_config={k: v for k, v in PEND_CONFIG.items() if k in df_p_display.columns},
            )

            st.markdown('<div class="sec-div" style="margin-top:.5rem"><div class="sec-div-line"></div><div class="sec-div-txt">🗺️ Roteirizar notas</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)

            # ── Monta tabela de seleção com checkbox ─────────────────────────
            df_sel = df_p_sorted[["numnota", "numped", "nomecliente", "observacao", "numcarregamento", "placa_road", "pesobrutotot", "vltotal", "praca", "id"]].copy()
            df_sel.insert(0, "✓", False)
            df_sel = df_sel.rename(columns={
                "numnota":        "Nota",
                "numped":         "Pedido",
                "nomecliente":    "Cliente",
                "observacao":     "Observação",
                "numcarregamento":"Carregamento",
                "placa_road":     "Placa Antiga",
                "pesobrutotot":   "Peso (kg)",
                "vltotal":        "Valor (R$)",
                "praca":          "Praça",
                "id":             "_id",
            })

            df_edited = st.data_editor(
                df_sel,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "✓":            st.column_config.CheckboxColumn("✓",              width="small"),
                    "Nota":         st.column_config.TextColumn("Nota Fiscal",        width="small"),
                    "Pedido":       st.column_config.TextColumn("Pedido",             width="small"),
                    "Cliente":      st.column_config.TextColumn("Cliente",            width="medium"),
                    "Observação":   st.column_config.TextColumn("Observação",         width="medium"),
                    "Carregamento": st.column_config.TextColumn("Carregamento",       width="small"),
                    "Placa Antiga": st.column_config.TextColumn("Placa Antiga",       width="small"),
                    "Peso (kg)":    st.column_config.NumberColumn("Peso (kg)",        format="%.0f kg", width="small"),
                    "Valor (R$)":   st.column_config.NumberColumn("Valor (R$)",       format="R$ %.2f", width="small"),
                    "Praça":        st.column_config.TextColumn("Praça",              width="small"),
                    "_id":          st.column_config.TextColumn("ID",                 width="small"),
                },
                disabled=["Nota","Pedido","Cliente","Observação","Carregamento","Placa Antiga","Peso (kg)","Valor (R$)","Praça","_id"],
                key="rot_editor",
            )

            selecionadas = df_edited[df_edited["✓"] == True]
            n_sel = len(selecionadas)

            # ── Resumo das selecionadas ───────────────────────────────────────
            if n_sel > 0:
                _peso_sel    = selecionadas["Peso (kg)"].sum()
                _valor_sel   = selecionadas["Valor (R$)"].sum()
                _n_clientes  = selecionadas["Cliente"].nunique()
                _valor_fmt   = f"R$ {_valor_sel:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                _peso_fmt    = f"{_peso_sel:,.0f} kg".replace(",",".")
                st.markdown(f"""
                <div style="display:flex;gap:1rem;flex-wrap:wrap;margin:.5rem 0 .75rem">
                  <div style="background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.3);border-radius:8px;padding:.4rem .9rem;font-size:.75rem;color:#93c5fd">
                    <span style="font-weight:700;font-size:1rem;color:#f0f6ff">{n_sel}</span> &nbsp;nota(s) selecionada(s)
                  </div>
                  <div style="background:rgba(167,139,250,0.10);border:1px solid rgba(167,139,250,0.30);border-radius:8px;padding:.4rem .9rem;font-size:.75rem;color:#c4b5fd">
                    👤 <span style="font-weight:700;font-size:1rem;color:#f0f6ff">{_n_clientes}</span> &nbsp;cliente(s)
                  </div>
                  <div style="background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.25);border-radius:8px;padding:.4rem .9rem;font-size:.75rem;color:#6ee7b7">
                    ⚖️ <span style="font-weight:700">{_peso_fmt}</span>
                  </div>
                  <div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);border-radius:8px;padding:.4rem .9rem;font-size:.75rem;color:#fde68a">
                    💰 <span style="font-weight:700">{_valor_fmt}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="al-i" style="margin:.4rem 0 .75rem">☝️ Marque uma ou mais notas na tabela acima para roteirizar em lote.</div>', unsafe_allow_html=True)

            # ── Placa + Data de saída compartilhadas ─────────────────────────
            c_nova_pl, c_dt_saida, c_btn = st.columns([1.4, 1.1, 0.8], gap="medium")
            with c_nova_pl:
                nova_pl_i = st.text_input("Nova Placa", placeholder="Ex: ABC-1234", key="pl_lote")
            with c_dt_saida:
                dt_saida_i = st.date_input("Data de Saída", value=None, key="dt_lote", format="DD/MM/YYYY")
            with c_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                _btn_label = f"✅ Roteirizar {n_sel} nota(s)" if n_sel > 0 else "✅ Roteirizar"
                roteirizar_btn = st.button(_btn_label, key="btn_lote", use_container_width=True, type="primary")

            if roteirizar_btn:
                if n_sel == 0:
                    st.markdown('<div class="al-e">⚠️ Selecione ao menos uma nota na tabela!</div>', unsafe_allow_html=True)
                elif not nova_pl_i.strip():
                    st.markdown('<div class="al-e">⚠️ Informe a nova placa!</div>', unsafe_allow_html=True)
                elif not dt_saida_i:
                    st.markdown('<div class="al-e">⚠️ Informe a data de saída!</div>', unsafe_allow_html=True)
                else:
                    import string as _string
                    def _col_letter(n):
                        res = ""
                        while n > 0:
                            n, r2 = divmod(n - 1, 26)
                            res = _string.ascii_uppercase[r2] + res
                        return res

                    ws_direct   = get_sheet("transferencias")
                    data_direct = ws_direct.get_all_values()
                    hdr_direct  = [str(c).strip() for c in data_direct[0]]
                    needed = ["placa_veiculo", "dt_saida", "dt_roteirizacao", "status"]
                    for _nc in needed:
                        if _nc not in hdr_direct:
                            hdr_direct.append(_nc)
                            ws_direct.update_cell(1, len(hdr_direct), _nc)
                    col_map = {c: i+1 for i, c in enumerate(hdr_direct)}

                    ids_para_roteirizar = selecionadas["_id"].astype(str).tolist()
                    to_write = {
                        "placa_veiculo":   nova_pl_i.strip().upper(),
                        "dt_saida":        dt_saida_i.isoformat(),
                        "dt_roteirizacao": date.today().strftime("%d/%m/%Y"),
                        "status":          "roteirizado",
                    }

                    _ok = 0
                    _erros = []
                    _prog = st.progress(0, text="Roteirizando...")
                    for _idx, _rid in enumerate(ids_para_roteirizar):
                        _target_row = None
                        for _i, _row in enumerate(data_direct[1:], start=2):
                            _row_pad = _row + [""] * (len(hdr_direct) - len(_row))
                            if _row_pad[col_map["id"]-1].strip() == str(_rid):
                                _target_row = _i
                                break
                        if _target_row:
                            for _col, _val in to_write.items():
                                _cn  = col_map[_col]
                                _ref = f"{_col_letter(_cn)}{_target_row}"
                                ws_direct.update(_ref, [[_val]], value_input_option="USER_ENTERED")
                            _ok += 1
                        else:
                            _erros.append(_rid)
                        _prog.progress((_idx + 1) / len(ids_para_roteirizar), text=f"Roteirizando... {_idx+1}/{len(ids_para_roteirizar)}")

                    _prog.empty()
                    load_transferencias.clear()
                    if _ok:
                        notas_str = ", ".join(
                            selecionadas[selecionadas["_id"].astype(str).isin(ids_para_roteirizar)]["Nota"].astype(str).tolist()
                        )
                        st.success(f"✅ {_ok} nota(s) roteirizada(s) com placa {nova_pl_i.strip().upper()}! Notas: {notas_str}")
                    if _erros:
                        st.error(f"⚠️ {len(_erros)} ID(s) não encontrado(s): {', '.join(_erros)}")
                    st.rerun()



    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="height:var(--space-4)"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card" style="border-top:3px solid #10b981">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#10b981">✅ Notas Roteirizadas</span>
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

        # Garante colunas de roteirização no df_r
        for _c in ["placa_veiculo", "dt_saida"]:
            if _c not in df_r.columns:
                df_r[_c] = ""
        _rot_front = ["data_registro", "placa_road", "placa_veiculo", "motivo", "observacao", "numcarregamento", "dt_saida"]
        _rot_rest  = [c for c in STD_COLS + ["placa_veiculo", "dt_saida", "motivo", "observacao"] if c not in _rot_front]
        ROT_COLS   = [c for c in _rot_front + _rot_rest if c in df_r.columns]
        ROT_CONFIG = {
            **STD_CONFIG,
            "data_registro":   st.column_config.TextColumn("Data de Registro", width="small"),
            "placa_veiculo":   st.column_config.TextColumn("Nova Placa",    width="small"),
            "numcarregamento": st.column_config.TextColumn("Carregamento",  width="small"),
            "dt_saida":        st.column_config.TextColumn("Dt. Saída",     width="small"),
            "motivo":          st.column_config.TextColumn("Motivo",        width="medium"),
            "observacao":      st.column_config.TextColumn("Observação",    width="medium"),
        }
        df_rd = dedup_columns(df_r[ROT_COLS].copy())
        if "dt_saida" in df_rd.columns:
            df_rd["dt_saida"] = df_rd["dt_saida"].apply(fmt_date)
        # Substitui vazios por traço para exibição limpa
        for _c2 in ["placa_veiculo", "dt_saida"]:
            if _c2 in df_rd.columns:
                df_rd[_c2] = df_rd[_c2].replace({"": "—", "nan": "—", "None": "—"})

        df_rd_sorted = df_rd.sort_values("dt_liberado", ascending=False).reset_index(drop=True) if not df_rd.empty else df_rd
        df_r_sorted  = df_r.sort_values("dt_liberado", ascending=False).reset_index(drop=True) if not df_r.empty else df_r

        # ── Tabela nativa (planilha bonita) ──────────────────────────────────
        st.dataframe(
            df_rd_sorted,
            use_container_width=True,
            hide_index=True,
            column_config={k: v for k, v in ROT_CONFIG.items() if k in df_rd_sorted.columns},
        )
        st.caption(f"{len(df_r)} nota(s)")

        # ── Lixeira por linha: selectbox de nota + botão devolver ────────────
        if not df_r_sorted.empty:
            st.markdown('<div class="sec-div" style="margin:.6rem 0 .4rem"><div class="sec-div-line"></div><div class="sec-div-txt">↩️ Devolver para pendente</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)
            _nota_opts = [
                f"🗑️  {str(row['numnota'])} — {str(row.get('nomecliente', ''))[:28]}"
                for _, row in df_r_sorted.iterrows()
            ]
            _nota_ids = df_r_sorted["id"].tolist()
            _dv_col1, _dv_col2, _ = st.columns([3, 1, 2], gap="medium")
            with _dv_col1:
                _sel_idx = st.selectbox("Nota para devolver", range(len(_nota_opts)),
                                        format_func=lambda i: _nota_opts[i],
                                        key="rdv2", label_visibility="collapsed")
            with _dv_col2:
                if st.button("↩️ Devolver", key="devolver_btn2", use_container_width=True):
                    update_transf(int(_nota_ids[_sel_idx]), {
                        "placa_veiculo": "",
                        "dt_roteirizacao": "",
                        "dt_saida": "",
                        "status": "pendente",
                    })
                    st.success("↩️ Devolvida para pendentes.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div style="height:var(--space-4)"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card" style="border-top:3px solid #3b82f6">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#60a5fa">📊 Relatório por Placa</span>
      <span class="card-count">{len(rote)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if rote.empty:
        st.markdown(f'<div style="padding:1.25rem"><div class="al-i">Nenhum dado roteirizado em {periodo_txt}.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-body" style="padding-bottom:.5rem">', unsafe_allow_html=True)

        _df_rep = rote.copy()
        _df_rep["placa_veiculo"] = _df_rep["placa_veiculo"].replace("", "—").fillna("—")
        _df_rep["nomecliente"]   = _df_rep["nomecliente"].fillna("")

        df_placa = (
            _df_rep.groupby(["data_registro", "placa_veiculo"])
            .agg(
                qtd_clientes=("nomecliente", "nunique"),
                peso=("pesobrutotot", "sum"),
                valor=("vltotal", "sum"),
            )
            .reset_index()
        )
        df_placa["_ord"] = df_placa["data_registro"].apply(to_iso)
        df_placa = (
            df_placa.sort_values(["_ord", "placa_veiculo"], ascending=[False, True])
            .drop(columns="_ord")
            .reset_index(drop=True)
        )

        PLACA_CONFIG = {
            "data_registro": st.column_config.TextColumn("Data", width="small"),
            "placa_veiculo": st.column_config.TextColumn("Placa", width="small"),
            "qtd_clientes":  st.column_config.NumberColumn("Qtd. Clientes", format="%d", width="small"),
            "peso":          st.column_config.NumberColumn("Peso (kg)", format="%.3f", width="small"),
            "valor":         st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", width="small"),
        }

        st.dataframe(
            df_placa,
            use_container_width=True,
            hide_index=True,
            column_config={k: v for k, v in PLACA_CONFIG.items() if k in df_placa.columns},
        )

        _tot_placas    = df_placa["placa_veiculo"].nunique()
        _tot_clientes  = _df_rep["nomecliente"].nunique()
        _tot_peso_fmt  = f"{df_placa['peso'].sum():,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
        _tot_valor_fmt = br(df_placa["valor"].sum())
        st.caption(f"🚚 {_tot_placas} placa(s) · 👤 {_tot_clientes} cliente(s) único(s) · ⚖️ {_tot_peso_fmt} kg · 💰 {_tot_valor_fmt}")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    _total_nfs   = len(df)
    _total_valor = df["vltotal"].sum() if not df.empty else 0
    _total_peso  = df["pesobrutotot"].sum() if not df.empty else 0
    _total_rot   = len(df[df["status"] == "roteirizado"]) if not df.empty else 0
    _total_pend  = len(df[df["status"].isin(["pendente", ""]) | df["status"].isna()]) if not df.empty else 0

    def _fmt_brl_kpi(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    def _fmt_kg(v):
        return f"{v:,.0f} kg".replace(",", ".")

    st.markdown(f"""
    <div class="dash-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:var(--space-5)">
      <div class="kpi-card kpi-card-accent">
        <span class="kpi-card-icon">🧾</span>
        <div class="kpi-card-label">Total de Notas</div>
        <div class="kpi-card-value">{_total_nfs}</div>
        <div class="kpi-card-sub">{periodo_txt}</div>
      </div>
      <div class="kpi-card kpi-card-green">
        <span class="kpi-card-icon">💰</span>
        <div class="kpi-card-label">Valor Total</div>
        <div class="kpi-card-value" style="font-size:1.35rem">{_fmt_brl_kpi(_total_valor)}</div>
        <div class="kpi-card-sub">{periodo_txt}</div>
      </div>
      <div class="kpi-card kpi-card-yellow">
        <span class="kpi-card-icon">⚖️</span>
        <div class="kpi-card-label">Peso Total</div>
        <div class="kpi-card-value" style="font-size:1.35rem">{_fmt_kg(_total_peso)}</div>
        <div class="kpi-card-sub">{periodo_txt}</div>
      </div>
      <div class="kpi-card kpi-card-red">
        <span class="kpi-card-icon">🗺️</span>
        <div class="kpi-card-label">Roteirizadas / Pendentes</div>
        <div class="kpi-card-value">{_total_rot} <span style="font-size:1rem;color:var(--txt2)">/ {_total_pend}</span></div>
        <div class="kpi-card-sub">{periodo_txt}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Gráficos lado a lado: Vendedor | Motivo ──────────────────────────────
    _col_vend, _col_mot = st.columns(2, gap="large")

    # — Gráfico Veículo Antigo —
    with _col_vend:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-head">'
            '<span class="chart-title" style="color:#ef4444;font-size:.78rem">🚛 Por Veículo</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="chart-body">', unsafe_allow_html=True)

        _rows_vend2 = []
        if not df.empty and "placa_road" in df.columns:
            _df_veic2 = df[df["placa_road"].notna() & (df["placa_road"].astype(str).str.strip() != "")]
            if not _df_veic2.empty:
                _veic_qtd2 = _df_veic2.groupby("placa_road")["numnota"].count().reset_index()
                _veic_qtd2.columns = ["veiculo", "qtd"]
                _veic_val2 = _df_veic2.groupby("placa_road")["vltotal"].sum().reset_index()
                _veic_val2.columns = ["veiculo", "valor"]
                _tv2 = _veic_qtd2.merge(_veic_val2, on="veiculo", how="left").fillna(0)
                _tv2 = _tv2.sort_values("valor", ascending=False)
                _rows_vend2 = _tv2.to_dict("records")

        def _fmt_brl(v):
            s = f"{int(round(v)):,}".replace(",", ".")
            return f"R {s}"

        st.markdown(
            _svg_col_line(
                _rows_vend2,
                label_key="veiculo", val_key="valor", qtd_key="qtd",
                bar_color_1="#ef4444", bar_color_2="#b91c1c",
                line_color="#fbbf24",
                fmt_val=_fmt_brl,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-top:6px;padding:0 .25rem">'
            '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#fbbf24" stroke-width="2"/>'
            '<circle cx="18" cy="5" r="3.5" fill="#fbbf24"/></svg>'
            '<span style="font-size:.68rem;color:#96acc9">Linha = quantidade de NFs</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)

    # — Gráfico Motivo —
    with _col_mot:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-head">'
            '<span class="chart-title" style="color:#ef4444;font-size:.78rem">📋 Por Motivos</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="chart-body">', unsafe_allow_html=True)

        _rows_motivo = []
        if not df.empty and "motivo" in df.columns:
            _df_mot = df[
                df["motivo"].notna() &
                (df["motivo"].astype(str).str.strip() != "") &
                (df["motivo"].astype(str).str.strip() != "— Selecione um motivo —")
            ]
            if not _df_mot.empty:
                _top_mot = (
                    _df_mot.groupby("motivo")["numnota"]
                    .count()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                _top_mot.columns = ["motivo", "qtd"]
                _rows_motivo = _top_mot.to_dict("records")

        if _rows_motivo:
            _nm_m      = len(_rows_motivo)
            # calcula BOT_PAD dinamicamente: texto rotacionado -40° projetado no eixo X
            # comprimento máximo do label * ~6px por char * sin(40°) ≈ * 0.64
            _max_lbl_len = max(len(str(r["motivo"])) for r in _rows_motivo)
            _BOT_M     = max(130, int(_max_lbl_len * 6 * 0.64) + 20)
            # margem esquerda para o primeiro rótulo não ser cortado
            _LEFT_PAD  = max(10, int(_max_lbl_len * 6 * 0.77) - 20)
            _SVG_W_M   = 560 + _LEFT_PAD
            _TOP_M     = 56
            _BAR_M     = 160
            _SVG_H_M   = _TOP_M + _BAR_M + _BOT_M
            _slot_m    = (_SVG_W_M - _LEFT_PAD) / max(_nm_m, 1)
            _barw_m    = min(_slot_m * 0.55, 80)
            _max_qtd_m = max(r["qtd"] for r in _rows_motivo) or 1

            _defs_m = (
                '<defs><linearGradient id="gmotv" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0%" stop-color="#ef4444"/>'
                '<stop offset="100%" stop-color="#b91c1c"/>'
                '</linearGradient></defs>'
            )
            _rects_m = ""
            _lbls_m  = ""
            _pts_m   = []

            for _i, _r in enumerate(_rows_motivo):
                _lbl  = str(_r["motivo"])
                _qtd  = int(_r["qtd"])
                _bh   = max(4, int(_qtd / _max_qtd_m * _BAR_M))
                _cx   = _LEFT_PAD + _slot_m * _i + _slot_m / 2
                _bx   = _cx - _barw_m / 2
                _by   = _TOP_M + _BAR_M - _bh

                _rects_m += f'<rect x="{_bx:.1f}" y="{_by}" width="{_barw_m:.1f}" height="{_bh}" rx="3" fill="url(#gmotv)" opacity="0.9"/>'
                _vty = _by + 14
                if _bh >= 18:
                    _rects_m += f'<text x="{_cx:.1f}" y="{_vty}" text-anchor="middle" font-size="11" font-weight="700" fill="#f0f6ff">{_qtd}</text>'
                else:
                    _rects_m += f'<text x="{_cx:.1f}" y="{_by - 4}" text-anchor="middle" font-size="11" font-weight="700" fill="#f0f6ff">{_qtd}</text>'

                _lbls_m += f'<text transform="translate({_cx:.1f},{_TOP_M + _BAR_M + 10}) rotate(-40)" text-anchor="end" font-size="11" font-weight="600" fill="#a9bfd9">{_lbl}</text>'
                _pts_m.append((_cx, _by - 20, _qtd))

            _poly_m = ""
            _dots_m = ""
            if _pts_m:
                _ps = " ".join(f"{x:.1f},{y}" for x, y, _ in _pts_m)
                _poly_m = f'<polyline points="{_ps}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>'
                for _x, _y, _q in _pts_m:
                    _dots_m += f'<circle cx="{_x:.1f}" cy="{_y}" r="5" fill="#fbbf24" stroke="#141e2b" stroke-width="1.5"/>'
                    _dots_m += f'<text x="{_x:.1f}" y="{_y - 9}" text-anchor="middle" font-size="11" font-weight="700" fill="#fbbf24">{_q}</text>'

            _svg_m = (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_SVG_W_M} {_SVG_H_M}" '
                f'style="width:100%;height:auto;display:block">'
                f'{_defs_m}{_rects_m}{_lbls_m}{_poly_m}{_dots_m}</svg>'
            )
            st.markdown(_svg_m, unsafe_allow_html=True)
            st.markdown(
                '<div style="display:flex;align-items:center;gap:6px;margin-top:6px;padding:0 .25rem">'
                '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#fbbf24" stroke-width="2"/>'
                '<circle cx="18" cy="5" r="3.5" fill="#fbbf24"/></svg>'
                '<span style="font-size:.68rem;color:#96acc9">Linha = quantidade de NFs</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="color:#5d7794;font-size:.78rem;text-align:center;padding:1.5rem 0">'
                'Nenhum motivo registrado no período.</p>',
                unsafe_allow_html=True,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
    # ── Tabela do histórico ───────────────────────────────────────────────────
    # ── Linha 1 de filtros: busca + excel ────────────────────────────────────
    fst  = "Todos"
    fsup = "Todos"
    hf1, hf4 = st.columns([6.7, 1], gap="medium")
    with hf1:
        busca_h = st.text_input("Buscar", key="hb", label_visibility="collapsed", placeholder="🔍 Nota, cliente, placa, destino...")
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

    # ── Linha 2 de filtros: data de saída ────────────────────────────────────
    st.markdown(
        '<div style="margin-top:10px;margin-bottom:2px;display:flex;align-items:center;gap:8px">'
        '<span style="font-size:.68rem;font-weight:600;color:#96acc9;text-transform:uppercase;letter-spacing:.08em">&#128197; Filtrar por Data de Sa&#237;da</span>'
        '<div style="flex:1;height:1px;background:rgba(255,255,255,0.07)"></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    hf5, hf6, _hf_spacer = st.columns([1.3, 1.3, 4], gap="medium")
    with hf5:
        dt_saida_de = st.date_input(
            "Dt. Saída — De",
            value=None,
            key="h_dt_saida_de",
            format="DD/MM/YYYY",
            label_visibility="visible",
        )
    with hf6:
        dt_saida_ate = st.date_input(
            "Dt. Saída — Até",
            value=None,
            key="h_dt_saida_ate",
            format="DD/MM/YYYY",
            label_visibility="visible",
        )

    # ── Linha 3 de filtros: nova placa ───────────────────────────────────────
    hf7, _hf_spacer2 = st.columns([1.3, 5.3], gap="medium")
    with hf7:
        _placas_opts = ["Todos"] + sorted(df["placa_veiculo"].dropna().unique().tolist()) if not df.empty and "placa_veiculo" in df.columns else ["Todos"]
        filtro_nova_placa = st.selectbox("Nova Placa", _placas_opts, key="h_nova_placa", label_visibility="visible")

    df_h = df_all.copy() if not df_all.empty else pd.DataFrame(columns=TCOLS)
    if not df_h.empty:
        if fst != "Todos":
            df_h = df_h[df_h["status"] == fst]
        if fsup != "Todos":
            df_h = df_h[df_h["nomesup"] == fsup]
        # Filtro por nova placa
        if filtro_nova_placa != "Todos" and "placa_veiculo" in df_h.columns:
            df_h = df_h[df_h["placa_veiculo"] == filtro_nova_placa]
        # Filtro por data de saída
        if (dt_saida_de is not None or dt_saida_ate is not None) and "dt_saida" in df_h.columns:
            def _parse_dt_saida(s):
                s = str(s).strip()
                try:
                    if len(s) == 10 and s[4] == "-" and s[7] == "-":
                        return date.fromisoformat(s)
                    if len(s) == 10 and s[2] == "/" and s[5] == "/":
                        d, m, y = s.split("/")
                        return date(int(y), int(m), int(d))
                except Exception:
                    pass
                return None
            _parsed = df_h["dt_saida"].apply(_parse_dt_saida)
            if dt_saida_de is not None:
                df_h = df_h[_parsed.apply(lambda d: d is not None and d >= dt_saida_de)]
                _parsed = _parsed[df_h.index]
            if dt_saida_ate is not None:
                df_h = df_h[_parsed.apply(lambda d: d is not None and d <= dt_saida_ate)]
        if busca_h:
            m = df_h.apply(lambda r: busca_h.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_h = df_h[m]

    for _col in ["placa_veiculo", "dt_saida", "status"]:
        if _col not in df_h.columns:
            df_h[_col] = ""

    _hist_front = ["data_registro", "placa_road", "placa_veiculo", "motivo", "observacao", "numcarregamento"]
    _hist_rest  = [c for c in STD_COLS + ["dt_saida", "status", "motivo", "observacao"] if c not in _hist_front]
    HIST_COLS = [c for c in _hist_front + _hist_rest if c in df_h.columns]
    HIST_CONFIG = {
        **STD_CONFIG,
        "data_registro":   st.column_config.TextColumn("Data de Registro", width="small"),
        "placa_veiculo":   st.column_config.TextColumn("Nova Placa",   width="small"),
        "motivo":          st.column_config.TextColumn("Motivo",       width="medium"),
        "observacao":      st.column_config.TextColumn("Observação",   width="medium"),
        "numcarregamento": st.column_config.TextColumn("Carregamento", width="small"),
        "dt_saida":        st.column_config.TextColumn("Dt. Saída",    width="small"),
        "status":          st.column_config.TextColumn("Status",       width="small"),
    }

    n_pend = int((df_h["status"] == "pendente").sum()) if not df_h.empty else 0
    n_rot  = int((df_h["status"] == "roteirizado").sum()) if not df_h.empty else 0
    vt_h   = df_h["vltotal"].sum() if not df_h.empty else 0

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
        if "dt_saida" in df_hd.columns:
            df_hd["dt_saida"] = df_hd["dt_saida"].apply(fmt_date)
        st.dataframe(
            df_hd.sort_values("numnota", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={k: v for k, v in HIST_CONFIG.items() if k in df_hd.columns},
        )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
