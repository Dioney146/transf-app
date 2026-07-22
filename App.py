import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
from zoneinfo import ZoneInfo
import io
import base64
import hmac
import hashlib
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════
# LOGIN — gate de autenticação (usuário/senha via st.secrets)
# ══════════════════════════════════════════════════════════════════════════
def check_login():
    """Gate de autenticação. Retorna True se o usuário já estiver logado."""
    if st.session_state.get("_autenticado", False):
        return True

    st.set_page_config(
        page_title="Delly's — Login",
        page_icon="\U0001f512",
        layout="centered",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&display=swap');
        html, body, [class*="css"], .stApp { font-family: 'Sora', sans-serif !important; }
        .stApp {
            background: radial-gradient(ellipse 90% 60% at 78% 18%, rgba(37,99,235,0.16) 0%, transparent 55%),
                        linear-gradient(160deg, #050914 0%, #060B16 38%, #071021 68%, #050914 100%);
        }
        #MainMenu, footer, header { visibility: hidden; }
        .login-title { text-align:center; color:#F8FAFC; font-weight:800; font-size:1.6rem; margin-bottom:.25rem; }
        .login-sub { text-align:center; color:#94A3B8; font-size:.85rem; margin-bottom:1.5rem; }
        div[data-testid="stForm"] {
            background: rgba(15,23,42,0.72);
            backdrop-filter: blur(22px) saturate(170%);
            border: 1px solid rgba(248,250,252,0.14);
            border-radius: 20px;
            padding: 2rem 1.75rem;
            box-shadow: 0 12px 40px rgba(0,0,0,0.55);
        }
        div[data-testid="stForm"] button {
            background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
            border: none !important;
            font-weight: 700 !important;
            box-shadow: 0 6px 22px rgba(37,99,235,0.40) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-title">🔒 Delly\'s — Transferências</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Faça login para continuar</div>', unsafe_allow_html=True)

    _c1, _c2, _c3 = st.columns([1, 2, 1])
    with _c2:
        with st.form("login_form"):
            usuario = st.text_input("Usuário").strip().lower()
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        if entrar:
            try:
                usuarios = st.secrets["credentials"]["usernames"]
                hashes = st.secrets["credentials"]["password_hashes"]
            except Exception:
                st.error("⚠️ Credenciais não configuradas em st.secrets. Veja as instruções no final do arquivo.")
                return False

            if usuario in usuarios:
                idx = usuarios.index(usuario)
                hash_esperado = hashes[idx]
                hash_digitado = hashlib.sha256(senha.encode()).hexdigest()

                if hmac.compare_digest(hash_digitado, hash_esperado):
                    st.session_state["_autenticado"] = True
                    st.session_state["_usuario_logado"] = usuario
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
            else:
                st.error("❌ Usuário ou senha incorretos.")

    return False


if not check_login():
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# A PARTIR DAQUI: aplicativo original (só executa depois do login)
# ══════════════════════════════════════════════════════════════════════════

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
    "status", "motivo", "bairro", "criado_em",
]

# Lista oficial dos bairros de Manaus (IMPLURB/Prefeitura de Manaus),
# organizada alfabeticamente para uso no campo de busca/autocomplete.
BAIRROS_MANAUS = [
    "Adrianópolis", "Aleixo", "Alvorada", "Armando Mendes", "Bairro da Paz",
    "Betânia", "Cachoeirinha", "Centro", "Chapada", "Cidade de Deus",
    "Cidade Nova", "Colônia Antônio Aleixo", "Colônia Oliveira Machado",
    "Colônia Santo Antônio", "Colônia Terra Nova", "Compensa", "Coroado",
    "Crespo", "Distrito Industrial I", "Distrito Industrial II", "Dom Pedro",
    "Educandos", "Flores", "Gilberto Mestrinho", "Glória", "Japiim",
    "Jorge Teixeira", "Lago Azul", "Lírio do Vale", "Mauazinho",
    "Monte das Oliveiras", "Morro da Liberdade", "Nossa Senhora das Graças",
    "Nossa Senhora de Aparecida", "Nova Cidade", "Nova Esperança",
    "Novo Aleixo", "Novo Israel", "Parque 10 de Novembro", "Petrópolis",
    "Planalto", "Ponta Negra", "Praça 14 de Janeiro", "Presidente Vargas",
    "Puraquequara", "Raiz", "Redenção", "Santa Etelvina", "Santa Luzia",
    "Santo Agostinho", "Santo Antônio", "São Francisco", "São Geraldo",
    "São Jorge", "São José Operário", "São Lázaro", "São Raimundo",
    "Tancredo Neves", "Tarumã", "Tarumã-Açu", "Vila Buriti", "Vila da Prata",
    "Zumbi dos Palmares",
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
    row.setdefault("bairro", "")
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

# ══════════════════════════════════════════════════════════════════════════
# PRESENÇA — registra e conta usuários ativos no site (aba "presencas")
# ══════════════════════════════════════════════════════════════════════════
PCOLS = ["usuario", "last_seen"]
JANELA_ATIVO_MIN = 3  # considera "ativo" quem teve atividade nos últimos N minutos

def ensure_presence_header():
    ws = get_sheet("presencas")
    hdr = ws.row_values(1)
    if hdr[:len(PCOLS)] != PCOLS:
        ws.update("A1:B1", [PCOLS])
    return ws

def registrar_presenca(usuario):
    """Atualiza (ou cria) o timestamp de última atividade do usuário logado.
    Throttlado para no máximo 1 escrita a cada 20s por sessão, evitando
    excesso de chamadas à API do Google Sheets a cada rerun do Streamlit."""
    if not usuario:
        return
    agora = datetime.now(ZoneInfo("America/Manaus"))
    _ultimo = st.session_state.get("_presenca_ultimo_registro")
    if _ultimo is not None and (agora - _ultimo).total_seconds() < 20:
        return
    st.session_state["_presenca_ultimo_registro"] = agora
    try:
        ws = ensure_presence_header()
        data = ws.get_all_values()
        linha_alvo = None
        for i, row in enumerate(data[1:], start=2):
            if row and row[0].strip().lower() == usuario.strip().lower():
                linha_alvo = i
                break
        ts = agora.strftime("%d/%m/%Y %H:%M:%S")
        if linha_alvo:
            ws.update(f"B{linha_alvo}", [[ts]], value_input_option="USER_ENTERED")
        else:
            ws.append_row([usuario.strip().lower(), ts], value_input_option="USER_ENTERED")
        usuarios_ativos.clear()
    except Exception:
        pass  # falha silenciosa — não deve travar o app por causa da presença

@st.cache_data(ttl=15, show_spinner=False)
def usuarios_ativos(_cache_key=None):
    """Retorna lista de usuários com atividade nos últimos JANELA_ATIVO_MIN minutos."""
    try:
        ws = ensure_presence_header()
        data = ws.get_all_values()
    except Exception:
        return []
    if len(data) < 2:
        return []
    agora = datetime.now(ZoneInfo("America/Manaus"))
    ativos = []
    for row in data[1:]:
        if len(row) < 2 or not row[0].strip():
            continue
        try:
            ts = datetime.strptime(row[1].strip(), "%d/%m/%Y %H:%M:%S").replace(tzinfo=ZoneInfo("America/Manaus"))
        except Exception:
            continue
        if (agora - ts).total_seconds() <= JANELA_ATIVO_MIN * 60:
            ativos.append(row[0].strip())
    return sorted(set(ativos))

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

# ─── Partículas do fundo tecnológico (geradas uma vez, posições fixas) ───────
import random as _bgrandom
_bgrandom.seed(42)

def _gen_star_shadows(n, min_op, max_op, size_px=1):
    """Gera uma lista de box-shadow (x y color) espalhados pela viewport para
    simular um campo de partículas/estrelas discreto via CSS puro."""
    parts = []
    for _ in range(n):
        x = round(_bgrandom.uniform(0, 100), 2)
        y = round(_bgrandom.uniform(0, 100), 2)
        op = round(_bgrandom.uniform(min_op, max_op), 2)
        parts.append(f"{x}vw {y}vh 0 rgba(148,197,255,{op})")
    return ",\n    ".join(parts)

_STARS_FAR  = _gen_star_shadows(70, 0.10, 0.28)
_STARS_NEAR = _gen_star_shadows(30, 0.20, 0.42)

# ─── CSS + Imagem de Fundo + Logo ─────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
  --bg:           #060B16;
  --white:        #F8FAFC;
  --sur:          rgba(248,250,252,0.05);
  --sur2:         rgba(248,250,252,0.03);
  --bdr:          rgba(248,250,252,0.10);
  --bdr2:         rgba(248,250,252,0.18);
  --bdr-hover:    rgba(248,250,252,0.28);
  --acc:          #3B82F6;
  --acc-lt:       rgba(59,130,246,0.12);
  --acc-mid:      rgba(59,130,246,0.24);
  --acc-hover:    #2563EB;
  --acc-glow:     rgba(59,130,246,0.35);
  --pur:          #7C3AED;
  --pur-lt:       rgba(124,58,237,0.12);
  --pur-mid:      rgba(124,58,237,0.24);
  --pur-hover:    #6D28D9;
  --pur-bdr:      rgba(124,58,237,0.32);
  --grn:          #22C55E;
  --grn-dk:       #16A34A;
  --grn-lt:       rgba(34,197,94,0.12);
  --grn-bdr:      rgba(34,197,94,0.32);
  --red:          #fb7c8f;
  --red-lt:       rgba(251,124,143,0.12);
  --red-bdr:      rgba(251,124,143,0.32);
  --ylw:          #fbc245;
  --ylw-lt:       rgba(251,194,69,0.12);
  --ylw-bdr:      rgba(251,194,69,0.32);
  --txt:          #F8FAFC;
  --txt2:         #94A3B8;
  --txt3:         #64748B;
  --nav-bg:       rgba(6,11,22,0.92);
  --nav-txt:      #64748B;
  --nav-act:      #F8FAFC;
  --nav-acc:      #3B82F6;
  --glass:        rgba(15,23,42,0.72);
  --glass2:       rgba(15,23,42,0.48);
  --glass-light:  rgba(248,250,252,0.045);
  --shadow-sm:    0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md:    0 4px 16px rgba(0,0,0,0.45), 0 2px 6px rgba(0,0,0,0.3);
  --shadow-lg:    0 12px 40px rgba(0,0,0,0.55), 0 4px 12px rgba(0,0,0,0.35);
  --shadow-acc:   0 0 24px rgba(59,130,246,0.20);

  /* ── Escala de espaçamento premium (ritmo consistente, base 4px) ── */
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  16px;
  --space-4:  24px;
  --space-5:  32px;
  --space-6:  48px;
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 20px;
  --content-max: 1400px;

  /* ── Escala tipográfica premium (proporção ~1.15, base 13px) ── */
  --fs-2xs: 0.60rem;
  --fs-xs:  0.68rem;
  --fs-sm:  0.76rem;
  --fs-base: 0.84rem;
  --fs-md:  0.92rem;
  --fs-lg:  1.05rem;
  --fs-xl:  1.32rem;
  --fs-2xl: 1.75rem;
}}

*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [class*="css"], .stApp {{
  font-family: 'Sora', sans-serif !important;
  color: var(--txt) !important;
  font-size: var(--fs-base);
}}

/* ══════════════════════════════════════════════════════════════════════════
   FUNDO TECNOLÓGICO — Terra (região Amazônica), gradientes azuis,
   iluminação sutil e partículas discretas. Camadas 100% CSS, fixas,
   atrás de todo o conteúdo (z-index negativo) para não afetar leitura.
   ══════════════════════════════════════════════════════════════════════════ */

/* Camada 0 — base do espaço profundo (gradiente azul-marinho) */
.stApp::before {{
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 90% 60% at 78% 18%, rgba(37,99,235,0.16) 0%, transparent 55%),
    radial-gradient(ellipse 70% 50% at 8% 92%, rgba(124,58,237,0.08) 0%, transparent 60%),
    linear-gradient(160deg, #050914 0%, #060B16 38%, #071021 68%, #050914 100%);
  z-index: -6;
}}

/* Camada 1 — grade tecnológica sutil (perspectiva de "painel de controle") */
.stApp::after {{
  content: '';
  position: fixed;
  inset: -10%;
  background-image:
    linear-gradient(rgba(59,130,246,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.05) 1px, transparent 1px);
  background-size: 46px 46px;
  -webkit-mask-image: radial-gradient(ellipse 75% 70% at 50% 40%, #000 30%, transparent 78%);
  mask-image: radial-gradient(ellipse 75% 70% at 50% 40%, #000 30%, transparent 78%);
  opacity: 0.55;
  z-index: -5;
  pointer-events: none;
}}

/* Campo de partículas — estrelas distantes (estáticas, bem discretas) */
.bg-stars-far {{
  content: '';
  position: fixed;
  inset: 0;
  width: 1px; height: 1px;
  background: transparent;
  box-shadow: {_STARS_FAR};
  z-index: -4;
  pointer-events: none;
  animation: bgTwinkleFar 9s ease-in-out infinite alternate;
}}
/* Campo de partículas — mais próximas, leve brilho e cintilação */
.bg-stars-near {{
  content: '';
  position: fixed;
  inset: 0;
  width: 2px; height: 2px;
  background: transparent;
  box-shadow: {_STARS_NEAR};
  border-radius: 50%;
  z-index: -4;
  pointer-events: none;
  animation: bgTwinkleNear 6s ease-in-out infinite alternate;
}}
@keyframes bgTwinkleFar {{
  0%   {{ opacity: 0.5; }}
  100% {{ opacity: 1; }}
}}
@keyframes bgTwinkleNear {{
  0%   {{ opacity: 0.6; transform: translateY(0); }}
  100% {{ opacity: 1; transform: translateY(-3px); }}
}}

/* Planeta Terra — esfera 100% CSS, com oceano azul, continente
   (América do Sul) e um brilho verde-esmeralda sutil sobre a região
   Amazônica, além de anel de atmosfera e halo tecnológico. */
.bg-earth-wrap {{
  position: fixed;
  right: -14vw;
  bottom: -20vw;
  width: min(52vw, 720px);
  height: min(52vw, 720px);
  z-index: -3;
  pointer-events: none;
  animation: bgEarthFloat 14s ease-in-out infinite;
}}
@keyframes bgEarthFloat {{
  0%, 100% {{ transform: translateY(0); }}
  50%      {{ transform: translateY(-14px); }}
}}
.bg-earth-atmo {{
  position: absolute;
  inset: -6%;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 32%, rgba(96,165,250,0.35), transparent 62%);
  filter: blur(18px);
  opacity: 0.8;
}}
.bg-earth-globe {{
  position: absolute;
  inset: 0;
  border-radius: 50%;
  overflow: hidden;
  background:
    radial-gradient(circle at 30% 26%, rgba(191,219,254,0.55) 0%, transparent 12%),
    radial-gradient(circle at 34% 30%, #1d4ed8 0%, #1e3a8a 42%, #0b1533 78%, #050a17 100%);
  box-shadow:
    inset -60px -50px 110px rgba(0,0,0,0.65),
    inset 22px 18px 60px rgba(147,197,253,0.18),
    0 0 90px 20px rgba(59,130,246,0.20);
}}
/* Manchas de "continente" — silhueta estilizada da América do Sul,
   com destaque verde-esmeralda pulsante sobre a Amazônia. */
.bg-earth-continent {{
  position: absolute;
  width: 46%;
  height: 58%;
  left: 27%;
  top: 18%;
  background:
    radial-gradient(ellipse 60% 70% at 45% 30%, rgba(34,197,94,0.55) 0%, rgba(21,128,61,0.42) 45%, transparent 72%),
    radial-gradient(ellipse 50% 40% at 55% 62%, rgba(101,163,13,0.35) 0%, transparent 70%);
  border-radius: 46% 54% 50% 50% / 55% 50% 55% 45%;
  filter: blur(1.5px);
  opacity: 0.92;
  transform: rotate(-8deg);
}}
.bg-earth-amazon-glow {{
  position: absolute;
  width: 26%;
  height: 20%;
  left: 38%;
  top: 34%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(74,222,128,0.85) 0%, rgba(34,197,94,0.35) 45%, transparent 75%);
  filter: blur(4px);
  mix-blend-mode: screen;
  animation: bgAmazonPulse 4.5s ease-in-out infinite;
}}
@keyframes bgAmazonPulse {{
  0%, 100% {{ opacity: 0.55; transform: scale(1); }}
  50%      {{ opacity: 0.95; transform: scale(1.12); }}
}}
/* Nuvens finas / terminador (sombra do lado noturno) */
.bg-earth-clouds {{
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background:
    radial-gradient(ellipse 70% 30% at 60% 15%, rgba(248,250,252,0.10) 0%, transparent 60%),
    radial-gradient(ellipse 50% 20% at 30% 70%, rgba(248,250,252,0.06) 0%, transparent 65%);
  mix-blend-mode: screen;
}}
.bg-earth-terminator {{
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle at 72% 68%, transparent 30%, rgba(2,6,18,0.82) 68%);
}}
/* Anel tecnológico orbital, tracejado, girando lentamente */
.bg-earth-ring {{
  position: absolute;
  inset: -9%;
  border-radius: 50%;
  border: 1px dashed rgba(96,165,250,0.28);
  animation: bgRingSpin 60s linear infinite;
}}
.bg-earth-ring::before {{
  content: '';
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  margin-left: -4px;
  border-radius: 50%;
  background: #60a5fa;
  box-shadow: 0 0 10px 3px rgba(96,165,250,0.8);
}}
@keyframes bgRingSpin {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(360deg); }}
}}

/* Camada final — véu de contraste para preservar a leitura do conteúdo
   por cima do fundo tecnológico (mantém cards e textos nítidos). */
.bg-scrim {{
  position: fixed;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(6,11,22,0.62) 0%, rgba(6,11,22,0.30) 22%, rgba(6,11,22,0.42) 100%),
    radial-gradient(ellipse 65% 45% at 50% 0%, rgba(6,11,22,0.35) 0%, transparent 60%);
  z-index: -2;
  pointer-events: none;
}}

.stApp {{
  background: transparent !important;
}}

#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
section[data-testid="stSidebar"] {{ display: none !important; }}
.main .block-container {{ padding: 0 !important; max-width: 100% !important; }}

/* Ritmo vertical consistente entre blocos gerados pelo Streamlit */
.main .block-container [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {{
  margin-bottom: 0 !important;
}}
div[data-testid="stMarkdownContainer"] > p {{ margin-bottom: 0; }}

/* ══════════════════════════════════════════════════════════════════════════
   CABEÇALHO PREMIUM — logo, título, abas, avatar, notificações, tema
   ══════════════════════════════════════════════════════════════════════════ */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) {{
  background: var(--nav-bg);
  backdrop-filter: blur(26px) saturate(180%);
  -webkit-backdrop-filter: blur(26px) saturate(180%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg), 0 0 46px rgba(59,130,246,0.10), inset 0 1px 0 rgba(248,250,252,0.06);
  margin: var(--space-3) 22px 0;
  padding: var(--space-3) var(--space-4);
  position: sticky;
  top: 12px;
  z-index: 999;
  transition: box-shadow .25s ease;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5))::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(120deg, rgba(59,130,246,0.35), transparent 30%, transparent 70%, rgba(124,58,237,0.22));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="stHorizontalBlock"] {{
  align-items: center !important;
  gap: var(--space-2) !important;
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
  background: linear-gradient(135deg, #3B82F6, #7C3AED);
  padding: 2px;
  box-shadow: 0 0 22px rgba(59,130,246,0.45), var(--shadow-sm);
}}
.hdr-logo-ring img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  border: 2px solid rgba(6,11,22,0.9);
  display: block;
}}
.hdr-brand-text {{
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  min-width: 0;
}}
.hdr-title {{
  font-family: 'Sora', sans-serif;
  font-weight: 800;
  font-size: var(--fs-xl);
  color: #F8FAFC;
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.hdr-title span {{ color: #3B82F6; }}
.hdr-sub {{
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-2xs);
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--txt2);
  margin-top: 3px;
}}

/* Abas (st.radio) estilizadas como pill-tabs dentro do cabeçalho */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  position: static !important;
  padding: 0 !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > label {{ display: none !important; }}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div {{
  display: flex !important;
  flex-direction: row !important;
  justify-content: center !important;
  align-items: center !important;
  gap: 4px !important;
  background: rgba(248,250,252,0.04);
  border: 1px solid var(--bdr);
  border-radius: 14px;
  padding: 4px !important;
  width: fit-content !important;
  margin: 0 auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div > label {{
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 9px 20px !important;
  font-size: var(--fs-xs) !important;
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
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div > label:hover {{
  color: rgba(248,250,252,0.85) !important;
  background: rgba(248,250,252,0.05) !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div > label[data-selected="true"] {{
  color: #fff !important;
  background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
  box-shadow: 0 4px 16px rgba(59,130,246,0.45), 0 1px 3px rgba(0,0,0,0.3) !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div > label > div:first-child {{
  display: none !important;
}}

/* Botões de ação do cabeçalho (tema / notificações / avatar) */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="stPopover"] {{
  display: flex !important;
  justify-content: center !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="stPopover"] > div > button {{
  background: rgba(248,250,252,0.05) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 12px !important;
  color: var(--txt) !important;
  font-size: var(--fs-md) !important;
  padding: 8px 12px !important;
  min-width: 0 !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
}}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) .stButton > button:hover,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="stPopover"] > div > button:hover {{
  background: rgba(248,250,252,0.10) !important;
  border-color: var(--bdr-hover) !important;
  transform: translateY(-2px) !important;
  box-shadow: var(--shadow-md), 0 0 14px rgba(59,130,246,0.20) !important;
}}

/* Avatar circular (5ª coluna do cabeçalho) */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="column"]:nth-of-type(5) [data-testid="stPopover"] > div > button {{
  border-radius: 50% !important;
  width: 42px !important;
  height: 42px !important;
  padding: 0 !important;
  background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
  color: #fff !important;
  font-weight: 800 !important;
  font-size: var(--fs-sm) !important;
  border: 2px solid rgba(248,250,252,0.18) !important;
  box-shadow: 0 0 14px rgba(59,130,246,0.45), var(--shadow-sm) !important;
}}

/* Badge de notificações (4ª coluna do cabeçalho) */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) [data-testid="column"]:nth-of-type(4) {{ position: relative; }}
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
  font-size: var(--fs-xs);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--txt);
  margin-bottom: var(--space-2);
}}
.hdr-notif-item {{
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 7px 0;
  border-bottom: 1px solid var(--bdr);
  font-size: var(--fs-sm);
  color: var(--txt2);
  line-height: 1.45;
}}
.hdr-notif-item:last-child {{ border-bottom: none; }}
.hdr-notif-dot {{
  width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex-shrink: 0;
}}
.hdr-user-name {{ font-size: var(--fs-md); font-weight: 700; color: var(--txt); }}
.hdr-user-mail {{ font-size: var(--fs-xs); color: var(--txt3); margin-bottom: var(--space-3); }}

/* ══════════════════════════════════════════════════════════════════════════
   FILTER BAR PREMIUM — glassmorphism, borda luminosa, hover
   ══════════════════════════════════════════════════════════════════════════ */
.filter-bar {{
  background: var(--glass2);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(248,250,252,0.05);
  margin: var(--space-4) 22px 0;
  padding: var(--space-3) var(--space-4);
  position: relative;
  overflow: hidden;
  transition: box-shadow .3s ease, border-color .3s ease;
}}
.filter-bar::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(120deg, rgba(59,130,246,0.30), transparent 35%, transparent 65%, rgba(124,58,237,0.18));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.filter-bar:hover {{
  border-color: var(--bdr-hover);
  box-shadow: var(--shadow-lg), 0 0 30px rgba(59,130,246,0.12), inset 0 1px 0 rgba(248,250,252,0.06);
}}

/* Inputs de data/texto dentro da filter-bar ganham visual premium */
.filter-bar [data-testid="stDateInput"] input,
.filter-bar [data-testid="stTextInput"] input {{
  background: rgba(248,250,252,0.045) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--txt) !important;
  transition: all .2s cubic-bezier(0.4,0,0.2,1) !important;
  box-shadow: var(--shadow-sm) !important;
}}
.filter-bar [data-testid="stDateInput"] input:focus,
.filter-bar [data-testid="stTextInput"] input:focus {{
  border-color: var(--acc) !important;
  box-shadow: 0 0 0 3px var(--acc-lt), var(--shadow-sm) !important;
}}
.filter-bar label p {{
  font-size: var(--fs-xs) !important;
  font-weight: 600 !important;
  color: var(--txt2) !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   CARDS PREMIUM — glassmorphism, cantos arredondados, sombra suave,
   bordas luminosas, gradientes discretos, hover animado
   ══════════════════════════════════════════════════════════════════════════ */
.card {{
  background: var(--glass);
  backdrop-filter: blur(24px) saturate(170%);
  -webkit-backdrop-filter: blur(24px) saturate(170%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(248,250,252,0.05);
  margin: 0 22px var(--space-4);
  overflow: hidden;
  position: relative;
  isolation: isolate;
  transition: transform .28s cubic-bezier(0.4,0,0.2,1), box-shadow .28s cubic-bezier(0.4,0,0.2,1), border-color .28s ease;
}}
.card::before {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(135deg, rgba(59,130,246,0.30), transparent 40%, transparent 60%, rgba(124,58,237,0.16));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.card:hover {{
  transform: translateY(-3px);
  border-color: var(--bdr-hover);
  box-shadow: var(--shadow-lg), 0 0 34px rgba(59,130,246,0.14), inset 0 1px 0 rgba(248,250,252,0.07);
}}
.card-head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--bdr);
  background: linear-gradient(180deg, rgba(248,250,252,0.035), transparent);
}}
.card-title {{
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  font-size: var(--fs-md);
  color: var(--txt);
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.card-count {{
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-xs);
  font-weight: 700;
  color: var(--txt2);
  background: rgba(248,250,252,0.05);
  border: 1px solid var(--bdr);
  border-radius: 999px;
  padding: 4px 12px;
  white-space: nowrap;
}}
.card-body {{
  padding: var(--space-4);
}}

/* ── KPI cards — dashboard overview ── */
.dash-grid {{
  display: grid;
  gap: var(--space-3);
  margin: var(--space-4) 22px 0;
}}
.kpi-card {{
  position: relative;
  background: var(--glass);
  backdrop-filter: blur(22px) saturate(170%);
  -webkit-backdrop-filter: blur(22px) saturate(170%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(248,250,252,0.05);
  padding: var(--space-4);
  overflow: hidden;
  isolation: isolate;
  transition: transform .28s cubic-bezier(0.4,0,0.2,1), box-shadow .28s cubic-bezier(0.4,0,0.2,1), border-color .28s ease;
}}
.kpi-card::before {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: -2;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(135deg, var(--kpi-glow, rgba(59,130,246,0.32)), transparent 45%, transparent 60%, rgba(248,250,252,0.06));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.kpi-card::after {{
  content: '';
  position: absolute;
  top: -40%;
  right: -30%;
  width: 65%;
  height: 65%;
  border-radius: 50%;
  background: radial-gradient(circle, var(--kpi-glow, rgba(59,130,246,0.22)) 0%, transparent 70%);
  z-index: -1;
  opacity: 0.7;
  transition: opacity .3s ease, transform .3s ease;
}}
.kpi-card:hover {{
  transform: translateY(-4px) scale(1.01);
  border-color: var(--bdr-hover);
  box-shadow: var(--shadow-lg), 0 0 30px var(--kpi-glow, rgba(59,130,246,0.18)), inset 0 1px 0 rgba(248,250,252,0.08);
}}
.kpi-card:hover::after {{
  opacity: 1;
  transform: scale(1.15);
}}
.kpi-card-accent {{ --kpi-glow: rgba(59,130,246,0.32); }}
.kpi-card-green  {{ --kpi-glow: rgba(34,197,94,0.30); }}
.kpi-card-yellow {{ --kpi-glow: rgba(124,58,237,0.30); }}
.kpi-card-red    {{ --kpi-glow: rgba(251,124,143,0.30); }}
.kpi-card-icon {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--kpi-glow, rgba(59,130,246,0.28)), transparent);
  border: 1px solid var(--bdr2);
  font-size: 1.15rem;
  margin-bottom: var(--space-2);
  box-shadow: var(--shadow-sm);
}}
.kpi-card-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-2xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--txt2);
  margin-bottom: 4px;
}}
.kpi-card-value {{
  font-family: 'Sora', sans-serif;
  font-weight: 800;
  font-size: var(--fs-2xl);
  color: var(--txt);
  letter-spacing: -0.02em;
  line-height: 1.15;
}}
.kpi-card-sub {{
  font-size: var(--fs-xs);
  color: var(--txt3);
  margin-top: 5px;
}}

/* ── Chart wrap (containers de gráficos) ── */
.chart-wrap {{
  background: var(--glass);
  backdrop-filter: blur(22px) saturate(170%);
  -webkit-backdrop-filter: blur(22px) saturate(170%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(248,250,252,0.05);
  overflow: hidden;
  position: relative;
  isolation: isolate;
  height: 100%;
  transition: transform .28s cubic-bezier(0.4,0,0.2,1), box-shadow .28s cubic-bezier(0.4,0,0.2,1), border-color .28s ease;
}}
.chart-wrap::before {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(135deg, rgba(59,130,246,0.26), transparent 45%, transparent 60%, rgba(124,58,237,0.16));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.chart-wrap:hover {{
  transform: translateY(-2px);
  border-color: var(--bdr-hover);
  box-shadow: var(--shadow-lg), 0 0 26px rgba(59,130,246,0.12), inset 0 1px 0 rgba(248,250,252,0.06);
}}
.chart-head {{
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--bdr);
  background: linear-gradient(180deg, rgba(248,250,252,0.035), transparent);
  display: flex;
  align-items: center;
}}
.chart-title {{
  font-family: 'Sora', sans-serif;
  font-weight: 700;
  font-size: var(--fs-sm);
  letter-spacing: 0.01em;
  text-transform: uppercase;
}}
.chart-body {{
  padding: var(--space-3) var(--space-4) var(--space-4);
}}

/* ── Divisor de seção (sec-div) ── */
.sec-div {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin: var(--space-4) 22px var(--space-3);
}}
.sec-div-line {{
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--bdr2) 20%, var(--bdr2) 80%, transparent);
}}
.sec-div-txt {{
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-2xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--txt2);
  white-space: nowrap;
  padding: 4px 12px;
  background: rgba(248,250,252,0.04);
  border: 1px solid var(--bdr);
  border-radius: 999px;
}}

/* ── Alertas premium (al-s / al-e / al-w / al-i) ── */
.al-s, .al-e, .al-w, .al-i {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-sm);
  font-weight: 500;
  line-height: 1.5;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow-sm);
  margin: 10px 0;
  transition: transform .2s ease, box-shadow .2s ease;
}}
.al-s:hover, .al-e:hover, .al-w:hover, .al-i:hover {{
  transform: translateX(2px);
}}
.al-s {{ background: var(--grn-lt); border: 1px solid var(--grn-bdr); color: #a7f3d8; }}
.al-e {{ background: var(--red-lt); border: 1px solid var(--red-bdr); color: #fecdd6; }}
.al-w {{ background: var(--ylw-lt); border: 1px solid var(--ylw-bdr); color: #fde9b8; }}
.al-i {{ background: var(--acc-lt); border: 1px solid rgba(59,130,246,0.32); color: #bcd6ff; }}

/* ── page-body wrapper ── */
.page-body {{
  padding-bottom: var(--space-6);
}}

/* ══════════════════════════════════════════════════════════════════════════
   BUSCA PREMIUM — estilo Google Cloud Console (campo grande + ícone + botão)
   ══════════════════════════════════════════════════════════════════════════ */
.search-card {{
  background: var(--glass);
  backdrop-filter: blur(24px) saturate(170%);
  -webkit-backdrop-filter: blur(24px) saturate(170%);
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(248,250,252,0.05);
  padding: var(--space-4) var(--space-4) var(--space-3);
  margin-bottom: var(--space-4);
  position: relative;
  isolation: isolate;
  overflow: hidden;
}}
.search-card::before {{
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: var(--radius-lg);
  padding: 1px;
  background: linear-gradient(135deg, rgba(59,130,246,0.34), transparent 45%, transparent 60%, rgba(124,58,237,0.18));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}}
.search-card-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--txt2);
  margin-bottom: var(--space-3);
  display: flex;
  align-items: center;
  gap: 8px;
}}

/* Campo de busca — maior, com ícone de lupa embutido */
.search-card .st-key-nota_inp input,
.search-card [data-testid="stTextInput"] input[aria-label="Número da Nota Fiscal"] {{
  height: 56px !important;
  font-size: var(--fs-lg) !important;
  font-weight: 500 !important;
  padding: 0 20px 0 52px !important;
  border-radius: 14px !important;
  border: 1.5px solid var(--bdr2) !important;
  background-color: rgba(248,250,252,0.045) !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E") !important;
  background-repeat: no-repeat !important;
  background-position: 18px center !important;
  color: var(--txt) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all .25s cubic-bezier(0.4,0,0.2,1) !important;
}}
.search-card .st-key-nota_inp input::placeholder,
.search-card [data-testid="stTextInput"] input[aria-label="Número da Nota Fiscal"]::placeholder {{
  color: var(--txt3) !important;
  font-weight: 400 !important;
}}
.search-card .st-key-nota_inp input:hover,
.search-card [data-testid="stTextInput"] input[aria-label="Número da Nota Fiscal"]:hover {{
  border-color: var(--bdr-hover) !important;
  background-color: rgba(248,250,252,0.065) !important;
}}
.search-card .st-key-nota_inp input:focus,
.search-card [data-testid="stTextInput"] input[aria-label="Número da Nota Fiscal"]:focus {{
  border-color: var(--acc) !important;
  background-color: rgba(248,250,252,0.075) !important;
  box-shadow: 0 0 0 4px var(--acc-lt), var(--shadow-md) !important;
}}

/* Botão de busca — gradiente azul, sombra e hover elevado (estilo GCP) */
.search-card .st-key-buscar_btn button,
.search-card div[data-testid="stButton"]:has(button[kind="primary"]) button {{
  height: 56px !important;
  min-height: 56px !important;
  border-radius: 14px !important;
  border: none !important;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: var(--fs-md) !important;
  letter-spacing: 0.02em !important;
  box-shadow: 0 6px 22px rgba(37,99,235,0.40), var(--shadow-sm) !important;
  transition: all .25s cubic-bezier(0.4,0,0.2,1) !important;
}}
.search-card .st-key-buscar_btn button:hover {{
  transform: translateY(-2px) !important;
  background: linear-gradient(135deg, #5B9BF8 0%, #3B7CE8 100%) !important;
  box-shadow: 0 10px 30px rgba(37,99,235,0.55), var(--shadow-md) !important;
}}
.search-card .st-key-buscar_btn button:active {{
  transform: translateY(0) !important;
  box-shadow: 0 4px 14px rgba(37,99,235,0.45) !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   DATAGRID PROFISSIONAL — cabeçalho fixo, zebra, hover, chips, paginação
   ══════════════════════════════════════════════════════════════════════════ */
.dg-wrap {{
  border: 1px solid var(--bdr2);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: rgba(248,250,252,0.015);
  box-shadow: var(--shadow-sm);
}}
.dg-scroll {{
  max-height: 520px;
  overflow-y: auto;
  overflow-x: auto;
}}
.dg-scroll::-webkit-scrollbar {{ width: 8px; height: 8px; }}
.dg-scroll::-webkit-scrollbar-thumb {{ background: rgba(248,250,252,0.14); border-radius: 8px; }}
.dg-scroll::-webkit-scrollbar-track {{ background: transparent; }}
.dg-table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-family: 'Sora', sans-serif;
  font-size: var(--fs-sm);
}}
.dg-table thead th {{
  position: sticky;
  top: 0;
  z-index: 5;
  background: rgba(15,23,42,0.97);
  backdrop-filter: blur(8px);
  color: var(--txt2);
  font-family: 'JetBrains Mono', monospace;
  font-size: var(--fs-2xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 13px 16px;
  border-bottom: 1px solid var(--bdr2);
  white-space: nowrap;
}}
.dg-th-left   {{ text-align: left; }}
.dg-th-right  {{ text-align: right; }}
.dg-th-center {{ text-align: center; }}
.dg-table tbody td {{
  padding: 12px 16px;
  color: var(--txt);
  border-bottom: 1px solid rgba(248,250,252,0.045);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
  line-height: 1.4;
}}
.dg-td-left   {{ text-align: left; }}
.dg-td-right  {{ text-align: right; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }}
.dg-td-center {{ text-align: center; }}
.dg-table tbody tr {{ transition: background .15s ease; }}
.dg-table tbody tr:nth-child(even) {{ background: rgba(248,250,252,0.018); }}
.dg-table tbody tr:hover {{ background: var(--acc-lt) !important; }}
.dg-table tbody tr:last-child td {{ border-bottom: none; }}

.dg-chip {{
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: var(--fs-2xs);
  font-weight: 700;
  letter-spacing: 0.03em;
  border: 1px solid;
  white-space: nowrap;
}}

.dg-pageinfo {{
  font-size: var(--fs-sm);
  color: var(--txt2);
  padding-top: 8px;
}}
.dg-pager-marker + div[data-testid="stHorizontalBlock"] {{
  margin-top: var(--space-2);
  align-items: center !important;
}}
.dg-pager-marker + div[data-testid="stHorizontalBlock"] button {{
  height: 34px !important;
  min-height: 34px !important;
  padding: 0 !important;
  border-radius: 8px !important;
  background: rgba(248,250,252,0.045) !important;
  border: 1px solid var(--bdr2) !important;
  color: var(--txt) !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}}
.dg-pager-marker + div[data-testid="stHorizontalBlock"] button:hover:not(:disabled) {{
  background: var(--acc) !important;
  border-color: var(--acc) !important;
  color: #fff !important;
  transform: none !important;
}}
.dg-pager-marker + div[data-testid="stHorizontalBlock"] button:disabled {{
  opacity: 0.3 !important;
}}

/* ══════════════════════════════════════════════════════════════════════════
   MICRO-ANIMAÇÕES — fade-in, hover, glow, elevação (300ms)
   Apenas efeitos de transição/interação — nenhuma alteração de layout.
   ══════════════════════════════════════════════════════════════════════════ */
@keyframes fadeInUp {{
  from {{ opacity: 0; transform: translateY(10px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeIn {{
  from {{ opacity: 0; }}
  to   {{ opacity: 1; }}
}}

/* Fade-in ao carregar: cards, KPIs, gráficos, filtros e busca */
.card, .kpi-card, .chart-wrap, .filter-bar, .search-card {{
  animation: fadeInUp 0.45s cubic-bezier(0.4,0,0.2,1) both;
}}
.dg-wrap, .al-s, .al-e, .al-w, .al-i {{
  animation: fadeIn 0.35s ease both;
}}
/* Pequeno escalonamento visual entre KPIs para um fade-in mais orgânico */
.dash-grid .kpi-card:nth-child(1) {{ animation-delay: 0.02s; }}
.dash-grid .kpi-card:nth-child(2) {{ animation-delay: 0.06s; }}
.dash-grid .kpi-card:nth-child(3) {{ animation-delay: 0.10s; }}
.dash-grid .kpi-card:nth-child(4) {{ animation-delay: 0.14s; }}

/* Todos os botões Streamlit: transição suave + leve elevação + glow no hover */
.stButton > button,
[data-testid="stDownloadButton"] > button,
[data-testid="stPopover"] > div > button {{
  transition: transform 300ms cubic-bezier(0.4,0,0.2,1),
              box-shadow 300ms cubic-bezier(0.4,0,0.2,1),
              background-color 300ms ease,
              border-color 300ms ease,
              filter 300ms ease !important;
  font-weight: 600 !important;
}}
.stButton > button:hover:not(:disabled),
[data-testid="stDownloadButton"] > button:hover:not(:disabled),
[data-testid="stPopover"] > div > button:hover {{
  transform: translateY(-2px);
  filter: brightness(1.06);
  box-shadow: 0 8px 22px rgba(59,130,246,0.30), var(--shadow-md) !important;
}}
.stButton > button:active:not(:disabled),
[data-testid="stDownloadButton"] > button:active:not(:disabled) {{
  transform: translateY(0);
}}

/* Inputs / selects / date pickers: transição suave em foco e hover, altura e raio consistentes */
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stTextArea"] textarea {{
  transition: border-color 300ms ease, box-shadow 300ms ease, background-color 300ms ease !important;
  border-radius: var(--radius-sm) !important;
}}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
[data-testid="stTextInput"] input:hover,
[data-testid="stDateInput"] input:hover {{
  border-color: var(--bdr-hover) !important;
}}
label p, [data-testid="stWidgetLabel"] p {{
  font-size: var(--fs-xs) !important;
  font-weight: 600 !important;
  color: var(--txt2) !important;
  letter-spacing: 0.01em;
}}

/* Chips de status: leve elevação + glow no hover dentro das tabelas */
.dg-chip {{
  transition: transform 300ms cubic-bezier(0.4,0,0.2,1), box-shadow 300ms ease, filter 300ms ease;
}}
.dg-table tbody tr:hover .dg-chip {{
  transform: translateY(-1px) scale(1.03);
  filter: brightness(1.08);
}}

/* Linhas da tabela: transição de 300ms no hover (mantendo o mesmo efeito, apenas suavizado) */
.dg-table tbody tr {{
  transition: background 300ms ease;
}}

/* KPI icon: leve giro/glow no hover do card */
.kpi-card-icon {{
  transition: transform 300ms cubic-bezier(0.4,0,0.2,1), box-shadow 300ms ease;
}}
.kpi-card:hover .kpi-card-icon {{
  transform: scale(1.08);
  box-shadow: 0 0 18px var(--kpi-glow, rgba(59,130,246,0.35)), var(--shadow-sm);
}}

/* Popovers: fade-in suave ao abrir */
div[data-testid="stPopoverBody"] {{
  animation: fadeIn 300ms ease both;
}}

/* Pill-tabs do cabeçalho: transição de 300ms já reforçada aqui */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="column"]:nth-child(5)) div[data-testid="stRadio"] > div > label {{
  transition: all 300ms cubic-bezier(0.4,0,0.2,1) !important;
}}
</style>

<div class="bg-stars-far"></div>
<div class="bg-stars-near"></div>
<div class="bg-earth-wrap">
  <div class="bg-earth-atmo"></div>
  <div class="bg-earth-globe">
    <div class="bg-earth-continent"></div>
    <div class="bg-earth-amazon-glow"></div>
    <div class="bg-earth-clouds"></div>
    <div class="bg-earth-terminator"></div>
  </div>
  <div class="bg-earth-ring"></div>
</div>
<div class="bg-scrim"></div>
""", unsafe_allow_html=True)


# ─── Cabeçalho Premium — logo, título, abas, tema, notificações e avatar ─────
if "_tema_claro" not in st.session_state:
    st.session_state["_tema_claro"] = False
if "_notif_aberta" not in st.session_state:
    st.session_state["_notif_aberta"] = False
if "_user_aberto" not in st.session_state:
    st.session_state["_user_aberto"] = False

_HAS_POPOVER = hasattr(st, "popover")

def _hdr_dropdown(icon_label, state_key, help_txt, render_fn):
    """Usa st.popover quando disponível; caso contrário, cai para um
    botão + painel expansível (compatível com versões mais antigas do Streamlit)."""
    if _HAS_POPOVER:
        with st.popover(icon_label, help=help_txt):
            render_fn()
    else:
        if st.button(icon_label, key=f"btn_{state_key}", help=help_txt):
            st.session_state[state_key] = not st.session_state.get(state_key, False)
        if st.session_state.get(state_key, False):
            with st.container():
                render_fn()

# Registra a atividade do usuário logado (throttlado internamente)
registrar_presenca(st.session_state.get("_usuario_logado", ""))
_lista_ativos = usuarios_ativos(_cache_key=int(datetime.now(ZoneInfo("America/Manaus")).timestamp() // 15))
_n_ativos = len(_lista_ativos)

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
    def _render_ativos():
        st.markdown(
            f'<div class="hdr-pop-title">🟢 {_n_ativos} ativo(s) agora</div>',
            unsafe_allow_html=True,
        )
        if _lista_ativos:
            _itens = "".join(
                f'<div class="hdr-notif-item"><span class="hdr-notif-dot" style="background:#22C55E"></span>'
                f'{u.title()}</div>'
                for u in _lista_ativos
            )
            st.markdown(_itens, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="hdr-notif-item">Nenhum usuário ativo no momento.</div>',
                unsafe_allow_html=True,
            )
        st.caption(f"Considerado ativo quem usou o site nos últimos {JANELA_ATIVO_MIN} min.")

    _hdr_dropdown(f"🟢 {_n_ativos}", "_online_aberto", "Usuários ativos agora", _render_ativos)

with hcol_notif:
    pass

with hcol_user:

    def _render_user():
        _nome_usuario = st.session_state.get("_usuario_logado", "Usuário").title()
        st.markdown(
            f'<div class="hdr-user-name">{_nome_usuario}</div>'
            '<div class="hdr-user-mail">Painel de Transferências · Delly\'s</div>',
            unsafe_allow_html=True,
        )
        if st.button("🚪 Sair", key="btn_logout_header", use_container_width=True):
            st.session_state["_autenticado"] = False
            st.session_state.pop("_usuario_logado", None)
            st.rerun()

    _hdr_dropdown(
        st.session_state.get("_usuario_logado", "N")[:1].upper(),
        "_user_aberto",
        "Minha conta",
        _render_user,
    )

# ══════════════════════════════════════════════════════════════════════════
# DATAGRID PROFISSIONAL — helpers de renderização (chips, células, paginação)
# ══════════════════════════════════════════════════════════════════════════
STATUS_CHIP_STYLES = {
    "roteirizado": ("#22C55E", "rgba(34,197,94,0.14)", "rgba(34,197,94,0.35)", "Roteirizado"),
    "pendente":    ("#fbc245", "rgba(251,194,69,0.14)", "rgba(251,194,69,0.35)", "Pendente"),
    "cancelado":   ("#fb7c8f", "rgba(251,124,143,0.14)", "rgba(251,124,143,0.35)", "Cancelado"),
}

def _status_chip(value):
    v = str(value).strip().lower()
    if v in ("", "nan", "none"):
        v = "pendente"
    color, bg, bdr, label = STATUS_CHIP_STYLES.get(
        v, ("#94A3B8", "rgba(248,250,252,0.06)", "rgba(248,250,252,0.16)", str(value) or "—")
    )
    return f'<span class="dg-chip" style="color:{color};background:{bg};border-color:{bdr}">{label}</span>'

def _fmt_cell(value, col_type="text"):
    s = "" if value is None else str(value).strip()
    if s in ("", "nan", "None", "NaT"):
        return "—"
    if col_type == "currency":
        try:
            return br(float(value))
        except Exception:
            return s
    if col_type == "weight":
        try:
            return f"{float(value):,.3f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kg"
        except Exception:
            return s
    if col_type == "int":
        try:
            return f"{int(float(value)):,}".replace(",", ".")
        except Exception:
            return s
    return s.replace("<", "&lt;").replace(">", "&gt;")

def render_pro_table(df, column_defs, key, page_size=10, status_key=None, empty_msg="Nenhum registro encontrado."):
    """
    Renderiza uma tabela HTML no estilo DataGrid profissional:
    cabeçalho fixo, linhas zebradas, hover, chips de status e paginação.

    column_defs: lista de dicts:
      {"key": "coluna_no_df", "label": "Rótulo", "align": "left"/"right"/"center",
       "type": "text"/"currency"/"weight"/"int"/"status", "width": "160px" (opcional)}
    """
    total = len(df)
    page_key = f"_{key}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    if total == 0:
        st.markdown(f'<div class="al-i" style="margin:.75rem 0">{empty_msg}</div>', unsafe_allow_html=True)
        return

    total_pages = max(1, -(-total // page_size))
    cur_page = min(st.session_state[page_key], total_pages - 1)
    st.session_state[page_key] = cur_page

    start = cur_page * page_size
    end = start + page_size
    page_df = df.iloc[start:end]

    thead = "<tr>"
    for c in column_defs:
        align = c.get("align", "left")
        width = f' style="width:{c["width"]}"' if c.get("width") else ""
        thead += f'<th class="dg-th-{align}"{width}>{c["label"]}</th>'
    thead += "</tr>"

    rows_html = []
    for _, row in page_df.iterrows():
        tds = []
        for c in column_defs:
            align = c.get("align", "left")
            key_c = c["key"]
            raw = row[key_c] if key_c in row.index else ""
            if c.get("type") == "status" or (status_key and key_c == status_key):
                cell = _status_chip(raw)
            else:
                cell = _fmt_cell(raw, c.get("type", "text"))
            tds.append(f'<td class="dg-td-{align}">{cell}</td>')
        rows_html.append(f"<tr>{''.join(tds)}</tr>")

    table_html = (
        '<div class="dg-wrap"><div class="dg-scroll"><table class="dg-table">'
        f'<thead>{thead}</thead><tbody>{"".join(rows_html)}</tbody>'
        '</table></div></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Paginação ──────────────────────────────────────────────────────────
    st.markdown('<div class="dg-pager-marker"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns([2.4, 0.45, 0.45, 1.3, 0.45, 0.45], gap="small")
    with c1:
        st.markdown(
            f'<div class="dg-pageinfo">Mostrando <strong>{start + 1}</strong>–<strong>{min(end, total)}</strong> de <strong>{total}</strong></div>',
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("«", key=f"{key}_first", disabled=cur_page == 0, use_container_width=True):
            st.session_state[page_key] = 0
            st.rerun()
    with c3:
        if st.button("‹", key=f"{key}_prev", disabled=cur_page == 0, use_container_width=True):
            st.session_state[page_key] = cur_page - 1
            st.rerun()
    with c4:
        st.markdown(
            f'<div class="dg-pageinfo" style="text-align:center">Página <strong>{cur_page + 1}</strong> de <strong>{total_pages}</strong></div>',
            unsafe_allow_html=True,
        )
    with c5:
        if st.button("›", key=f"{key}_next", disabled=cur_page >= total_pages - 1, use_container_width=True):
            st.session_state[page_key] = cur_page + 1
            st.rerun()
    with c6:
        if st.button("»", key=f"{key}_last", disabled=cur_page >= total_pages - 1, use_container_width=True):
            st.session_state[page_key] = total_pages - 1
            st.rerun()

# Definições de colunas reutilizadas pelas tabelas de exibição
STD_DG_DEFS = [
    {"key": "data_registro",   "label": "Data Registro", "align": "left"},
    {"key": "placa_road",      "label": "Placa Antiga",  "align": "left"},
    {"key": "motivo",          "label": "Motivo",        "align": "left",  "width": "200px"},
    {"key": "bairro",          "label": "Bairro",        "align": "left",  "width": "180px"},
    {"key": "numnota",         "label": "Nota Fiscal",   "align": "left"},
    {"key": "numped",          "label": "Pedido",        "align": "left"},
    {"key": "codcliente",      "label": "Cód. Cliente",  "align": "left"},
    {"key": "nomecliente",     "label": "Cliente",       "align": "left",  "width": "220px"},
    {"key": "dt_liberado",     "label": "Dt. Liberado",  "align": "left"},
    {"key": "nomevend",        "label": "Vendedor",      "align": "left"},
    {"key": "nomesup",         "label": "Supervisor",    "align": "left"},
    {"key": "pesobrutotot",    "label": "Peso (kg)",     "align": "right", "type": "weight"},
    {"key": "vltotal",         "label": "Valor (R$)",    "align": "right", "type": "currency"},
    {"key": "praca",           "label": "Praça",         "align": "left"},
    {"key": "numcarregamento", "label": "Carregamento",  "align": "left"},
    {"key": "destino",         "label": "Destino",       "align": "left"},
]

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
    st.markdown('<div style="height:29px"></div>', unsafe_allow_html=True)
    _vt_ativo = st.session_state.get("_ver_todas", False)
    _label_toggle = ("✓ Todas as datas") if _vt_ativo else "Todas as datas"
    _bg    = "rgba(59,130,246,0.2)"  if _vt_ativo else "rgba(248,250,252,0.05)"
    _borda = "#3B82F6"               if _vt_ativo else "rgba(248,250,252,0.14)"
    _color = "#93c5fd"               if _vt_ativo else "rgba(248,250,252,0.55)"
    st.markdown(f"""<style>
    div[data-testid="stButton"] button[kind="secondary"]#btn_ver_todas,
    div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] > button {{
        background: {_bg} !important;
        border: 1px solid {_borda} !important;
        color: {_color} !important;
        font-size: var(--fs-xs) !important;
        font-weight: 600 !important;
        padding: 6px 14px !important;
        height: 34px !important;
        min-height: 34px !important;
        border-radius: 8px !important;
        margin-top: 0 !important;
        box-shadow: none !important;
        letter-spacing: .03em !important;
        transition: all .2s cubic-bezier(0.4,0,0.2,1) !important;
    }}
    div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 0 12px rgba(59,130,246,0.25) !important;
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
    "data_registro", "placa_road", "motivo", "bairro",
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
    "bairro":          st.column_config.TextColumn("Bairro",         width="medium"),
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
        return '<div style="padding:.75rem;color:#64748B;font-size:.78rem;text-align:center">Sem dados</div>'
    max_v = max(r[value_key] for r in rows) or 1
    bars = ""
    for i, r in enumerate(rows):
        lbl   = str(r[label_key])[:20] or "—"
        val   = r[value_key]
        pct   = int(val / max_v * 100)
        shown = fmt_val(val) if fmt_val else str(val)
        bars += f'''
        <div style="display:grid;grid-template-columns:140px 1fr 70px;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(248,250,252,0.04)">
          <div style="font-size:.75rem;color:#94A3B8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{lbl}">{lbl}</div>
          <div style="background:rgba(248,250,252,0.05);border-radius:4px;height:8px;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;transition:width .4s ease"></div>
          </div>
          <div style="font-size:.75rem;font-weight:700;color:#F8FAFC;text-align:right;white-space:nowrap">{shown}</div>
        </div>'''
    return bars

# ── Helper: gráfico de colunas verticais em HTML puro ─────────────────────────
def _col_chart_html(rows, label_key, value_key, color, fmt_val=None, height=90):
    if not rows:
        return '<div style="padding:.75rem;color:#64748B;font-size:.78rem;text-align:center">Sem dados</div>'
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
          <div style="font-size:.68rem;font-weight:700;color:#F8FAFC">{shown}</div>
          <div style="width:100%;display:flex;align-items:flex-end;justify-content:center;height:{height}px">
            <div style="width:70%;background:{color};border-radius:4px 4px 0 0;height:{bar_h}px;min-height:4px;box-shadow:0 0 8px {color}55"></div>
          </div>
          <div style="font-size:.62rem;color:#94A3B8;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;padding:0 2px" title="{lbl}">{short}</div>
        </div>'''
    return f'<div style="display:flex;gap:4px;align-items:flex-end;padding:.5rem .25rem 0">{cols_html}</div>'


# ── Helper: gera SVG de colunas verticais 3D (glassmorphism) com linha de qtd ─
def _svg_col_line(rows, label_key, val_key, qtd_key, bar_color_1, bar_color_2, line_color="#3B82F6", fmt_val=None, rotate_labels=False, line_fmt=None):
    """Retorna string SVG: barras verticais extrudadas (3D + glass) + linha com glow."""
    if not rows:
        return '<p style="color:#64748B;font-size:.78rem;text-align:center;padding:1rem">Sem dados</p>'

    n = len(rows)
    max_lbl_len = max(len(str(r[label_key])) for r in rows)

    MIN_SLOT   = 64
    DEPTH_X    = 11    # deslocamento da extrusão 3D (elegante, não exagerado)
    DEPTH_Y    = -9
    TOP_PAD    = 64
    BAR_AREA   = 156
    BOT_PAD    = max(130, int(max_lbl_len * 6 * 0.64) + 20) if rotate_labels else 32
    LEFT_PAD   = max(14, int(max_lbl_len * 6 * 0.77) - 16) if rotate_labels else (DEPTH_X + 6)
    RIGHT_PAD  = DEPTH_X + 12

    SVG_W  = max(560, n * MIN_SLOT) + LEFT_PAD + RIGHT_PAD
    SVG_H  = TOP_PAD + BAR_AREA + BOT_PAD
    slot_w = (SVG_W - LEFT_PAD - RIGHT_PAD) / max(n, 1)
    bar_w  = min(slot_w * 0.5, 60)
    max_val = max(r[val_key] for r in rows) or 1
    base_y  = TOP_PAD + BAR_AREA

    uid = f"g{abs(hash((label_key, val_key))) % 99999}"

    defs = f'''<defs>
      <linearGradient id="{uid}front" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="{bar_color_1}"/>
        <stop offset="100%" stop-color="{bar_color_2}"/>
      </linearGradient>
      <linearGradient id="{uid}top" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#D9FBE3"/>
        <stop offset="100%" stop-color="{bar_color_1}"/>
      </linearGradient>
      <linearGradient id="{uid}side" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="{bar_color_2}"/>
        <stop offset="100%" stop-color="#0F5132"/>
      </linearGradient>
      <linearGradient id="{uid}glass" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.32"/>
        <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
      </linearGradient>
      <radialGradient id="{uid}dot" cx="35%" cy="35%" r="65%">
        <stop offset="0%" stop-color="#EFF6FF"/>
        <stop offset="45%" stop-color="{line_color}"/>
        <stop offset="100%" stop-color="{line_color}" stop-opacity="0"/>
      </radialGradient>
      <filter id="{uid}shadow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="3.4"/>
      </filter>
      <filter id="{uid}glow" x="-90%" y="-90%" width="280%" height="280%">
        <feGaussianBlur stdDeviation="3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <style>
        .{uid}bar {{
          transform-box: fill-box;
          transform-origin: 50% 100%;
          animation: {uid}grow .65s cubic-bezier(.34,1.56,.64,1) both;
          transition: transform .25s cubic-bezier(0.4,0,0.2,1), filter .25s ease;
          cursor: default;
        }}
        .{uid}bar:hover {{
          transform: translateY(-5px);
          filter: brightness(1.12) drop-shadow(0 10px 12px rgba(34,197,94,0.45));
        }}
        @keyframes {uid}grow {{ from {{ transform: scaleY(0.04); opacity:0; }} to {{ transform: scaleY(1); opacity:1; }} }}
        .{uid}line {{
          stroke-dasharray: 2000;
          stroke-dashoffset: 2000;
          animation: {uid}draw 1.2s ease-out .35s forwards;
        }}
        @keyframes {uid}draw {{ to {{ stroke-dashoffset: 0; }} }}
        .{uid}pt {{
          transform-box: fill-box;
          transform-origin: center;
          animation: {uid}pop .45s cubic-bezier(.34,1.56,.64,1) both;
        }}
        @keyframes {uid}pop {{ from {{ transform: scale(0); opacity:0; }} to {{ transform: scale(1); opacity:1; }} }}
      </style>
    </defs>'''

    rects  = ""
    labels = ""
    pts    = []

    for i, r in enumerate(rows):
        lbl   = str(r[label_key])
        short = (lbl[:9] + "…") if (not rotate_labels and len(lbl) > 10) else lbl
        val   = r[val_key]
        bh    = max(6, int(val / max_val * BAR_AREA))
        cx    = LEFT_PAD + slot_w * i + slot_w / 2
        bx    = cx - bar_w / 2
        by    = base_y - bh
        shown = fmt_val(val) if fmt_val else str(int(val))
        delay = round(i * 0.05, 2)

        # sombra suave projetada no "chão" do gráfico
        rects += (
            f'<ellipse cx="{cx:.1f}" cy="{base_y + 6}" rx="{bar_w * 0.62:.1f}" ry="5" '
            f'fill="#020617" opacity="0.40" filter="url(#{uid}shadow)"/>'
        )

        # grupo 3D (lateral + topo + frente + glass) — anima e recebe hover-lift
        rects += f'<g class="{uid}bar" style="animation-delay:{delay}s">'
        rects += (
            f'<polygon points="{bx+bar_w:.1f},{by:.1f} {bx+bar_w+DEPTH_X:.1f},{by+DEPTH_Y:.1f} '
            f'{bx+bar_w+DEPTH_X:.1f},{base_y+DEPTH_Y:.1f} {bx+bar_w:.1f},{base_y:.1f}" '
            f'fill="url(#{uid}side)"/>'
        )
        rects += (
            f'<polygon points="{bx:.1f},{by:.1f} {bx+DEPTH_X:.1f},{by+DEPTH_Y:.1f} '
            f'{bx+bar_w+DEPTH_X:.1f},{by+DEPTH_Y:.1f} {bx+bar_w:.1f},{by:.1f}" '
            f'fill="url(#{uid}top)"/>'
        )
        rects += (
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh}" rx="2.5" '
            f'fill="url(#{uid}front)"/>'
        )
        _gh = max(8, int(bh * 0.4))
        rects += (
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{_gh}" rx="2.5" '
            f'fill="url(#{uid}glass)"/>'
        )
        rects += '</g>'

        val_ty = by + 15 if bh >= 20 else by - 5
        rects += (
            f'<text x="{cx:.1f}" y="{val_ty:.1f}" text-anchor="middle" font-size="11" '
            f'font-weight="800" fill="#FFFFFF" stroke="#064e2f" stroke-width="3" '
            f'stroke-linejoin="round" paint-order="stroke fill">{shown}</text>'
        )

        if rotate_labels:
            labels += (
                f'<text transform="translate({cx:.1f},{base_y + 12}) rotate(-40)" '
                f'text-anchor="end" font-size="11" font-weight="600" fill="#94A3B8">{lbl}</text>'
            )
        else:
            labels += (
                f'<text x="{cx:.1f}" y="{base_y + 16}" text-anchor="middle" font-size="11" '
                f'font-weight="600" fill="#94A3B8">{short}</text>'
            )

        if qtd_key:
            qtd_raw = r[qtd_key]
            dot_y = by - 20
            pts.append((cx, dot_y, qtd_raw, delay))

    poly = ""
    dots = ""
    if pts:
        path_d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
        for k in range(1, len(pts)):
            x0, y0, _, _ = pts[k - 1]
            x1, y1, _, _ = pts[k]
            mx = (x0 + x1) / 2
            path_d += f"Q {x0:.1f} {y0:.1f} {mx:.1f} {(y0 + y1) / 2:.1f} "
        path_d += f"T {pts[-1][0]:.1f} {pts[-1][1]:.1f}"

        poly += (
            f'<path d="{path_d}" fill="none" stroke="{line_color}" stroke-width="7" '
            f'opacity="0.22" filter="url(#{uid}shadow)"/>'
        )
        poly += (
            f'<path class="{uid}line" d="{path_d}" fill="none" stroke="{line_color}" '
            f'stroke-width="2.5" stroke-linecap="round"/>'
        )

        for x, y, q_raw, delay in pts:
            q_shown = line_fmt(q_raw) if line_fmt else str(int(q_raw))
            dots += (
                f'<circle class="{uid}pt" style="animation-delay:{delay + 0.4}s" '
                f'cx="{x:.1f}" cy="{y}" r="9" fill="url(#{uid}dot)"/>'
            )
            dots += (
                f'<circle cx="{x:.1f}" cy="{y}" r="3.4" fill="#FFFFFF" filter="url(#{uid}glow)"/>'
            )
            dots += (
                f'<text x="{x:.1f}" y="{y - 11}" text-anchor="middle" font-size="11" '
                f'font-weight="700" fill="{line_color}">{q_shown}</text>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W:.0f} {SVG_H:.0f}" '
        f'style="width:100%;height:auto;display:block;overflow:visible">'
        f'{defs}{rects}{labels}{poly}{dots}</svg>'
    )


# ── Helper: gera SVG de barras horizontais 3D (glassmorphism) ─────────────────
def _svg_bar_horiz(rows, label_key, val_key, bar_color_1, bar_color_2, fmt_val=None):
    """Retorna string SVG: barras horizontais extrudadas com leve profundidade e glass."""
    if not rows:
        return '<p style="color:#64748B;font-size:.78rem;text-align:center;padding:1rem">Sem dados</p>'
    n        = len(rows)
    LABEL_W  = 74
    BAR_H    = 11
    ROW_H    = 30
    VAL_W    = 58
    DEPTH    = 5
    SVG_W    = 400
    SVG_H    = n * ROW_H + 10
    BAR_AREA = SVG_W - LABEL_W - VAL_W - 10 - DEPTH
    max_val  = max(r[val_key] for r in rows) or 1

    uid = f"h{abs(hash((label_key, val_key))) % 99999}"

    defs = f'''<defs>
      <linearGradient id="{uid}bar" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="{bar_color_1}"/>
        <stop offset="100%" stop-color="{bar_color_2}"/>
      </linearGradient>
      <linearGradient id="{uid}glass" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.30"/>
        <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
      </linearGradient>
      <filter id="{uid}shadow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="2.2"/>
      </filter>
      <style>
        .{uid}row {{
          transform-box: fill-box;
          transform-origin: 0% 50%;
          animation: {uid}grow .55s cubic-bezier(.34,1.56,.64,1) both;
          transition: transform .22s ease, filter .22s ease;
        }}
        .{uid}row:hover {{ transform: translateX(3px); filter: brightness(1.1); }}
        @keyframes {uid}grow {{ from {{ transform: scaleX(0.05); opacity:0; }} to {{ transform: scaleX(1); opacity:1; }} }}
      </style>
    </defs>'''

    els = ""
    for i, r in enumerate(rows):
        lbl   = str(r[label_key])
        short = (lbl[:9] + "…") if len(lbl) > 10 else lbl
        val   = r[val_key]
        bw    = max(4, int(val / max_val * BAR_AREA))
        y_mid = i * ROW_H + ROW_H / 2 + 4
        bar_y = y_mid - BAR_H / 2
        shown = fmt_val(val) if fmt_val else str(int(val))
        delay = round(i * 0.05, 2)

        els += f'<rect x="{LABEL_W}" y="{bar_y:.1f}" width="{BAR_AREA + DEPTH}" height="{BAR_H}" rx="4" fill="rgba(248,250,252,0.05)"/>'
        els += (
            f'<ellipse cx="{LABEL_W}" cy="{y_mid:.1f}" rx="2" ry="{BAR_H/2:.1f}" '
            f'fill="#000" opacity="0.25" filter="url(#{uid}shadow)"/>'
        )
        els += f'<g class="{uid}row" style="animation-delay:{delay}s">'
        # lateral (extrusão inferior, sombra)
        els += f'<rect x="{LABEL_W}" y="{bar_y+2:.1f}" width="{bw}" height="{BAR_H}" rx="4" fill="{bar_color_2}" opacity="0.55"/>'
        # frente
        els += f'<rect x="{LABEL_W}" y="{bar_y:.1f}" width="{bw}" height="{BAR_H}" rx="4" fill="url(#{uid}bar)"/>'
        # glass sheen
        els += f'<rect x="{LABEL_W}" y="{bar_y:.1f}" width="{bw}" height="{BAR_H*0.45:.1f}" rx="4" fill="url(#{uid}glass)"/>'
        els += '</g>'

        els += f'<text x="{LABEL_W - 6}" y="{y_mid:.1f}" text-anchor="end" dominant-baseline="middle" font-size="9" fill="#94A3B8">{short}</text>'
        els += f'<text x="{LABEL_W + BAR_AREA + DEPTH + 6}" y="{y_mid:.1f}" dominant-baseline="middle" font-size="9" font-weight="700" fill="#F8FAFC">{shown}</text>'

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
        st.markdown('<div class="search-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="search-card-label">🔍 Buscar Nota Fiscal</div>',
            unsafe_allow_html=True,
        )

        ca, cb = st.columns([4.2, 1], gap="medium")
        with ca:
            nota_inp = st.text_input(
                "Número da Nota Fiscal",
                placeholder="Pesquisar por número da nota fiscal…",
                key="nota_inp",
                label_visibility="collapsed",
            )
        with cb:
            buscar_btn = st.button("Buscar", use_container_width=True, key="buscar_btn", type="primary")

        st.markdown("</div>", unsafe_allow_html=True)


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
            <div class="sec-div" style="margin:1.25rem 0 .85rem 0">
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
            <div class="sec-div" style="margin:1.25rem 0 .85rem 0">
              <div class="sec-div-line"></div>
              <div class="sec-div-txt">📍 Bairro</div>
              <div class="sec-div-line"></div>
            </div>
            """, unsafe_allow_html=True)
            bairro_sel = st.selectbox(
                "Bairro",
                options=["— Selecione ou digite o bairro —"] + BAIRROS_MANAUS,
                key="bairro_input",
                label_visibility="collapsed",
            )
            bairro_input = bairro_sel.strip() if bairro_sel != "— Selecione ou digite o bairro —" else ""

            st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True, key="confirm_btn"):
                if not motivo_input or motivo_input == "— Selecione um motivo —":
                    if motivo_sel == "✏️ Outro (digitar)":
                        st.markdown('<div class="al-e">❌ Digite o <strong>Motivo</strong> no campo acima antes de confirmar.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="al-e">❌ Selecione um <strong>Motivo</strong> antes de confirmar.</div>', unsafe_allow_html=True)
                elif not bairro_input:
                    st.markdown('<div class="al-e">❌ Selecione um <strong>Bairro</strong> antes de confirmar.</div>', unsafe_allow_html=True)
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
                                "bairro":          bairro_input,
                            })
                        st.success(f"✅ Transferência registrada! Nota {cur['numnota']} aguarda roteirização.")
                        st.session_state.cur = None
                        st.balloons()
                        st.rerun()

            st.markdown("</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="border-style:dashed;border-color:rgba(248,250,252,0.15)">
              <div class="card-body" style="text-align:center;padding:3rem 2rem">
                <div style="font-size:2.5rem;margin-bottom:.75rem;opacity:.85">🧾</div>
                <div style="font-size:var(--fs-md);color:var(--txt2)">Informe o número da nota e clique em <strong style="color:var(--acc)">Buscar</strong></div>
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
        st.markdown('<div class="card-body" style="padding-top:0">', unsafe_allow_html=True)
        _lista_defs = [d for d in STD_DG_DEFS if d["key"] in df_show.columns]
        render_pro_table(df_show, _lista_defs, key="lista_completa", page_size=10)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div style="padding:.85rem 1.5rem;border-top:1px solid var(--bdr)">', unsafe_allow_html=True)
        ids_hj = df_hj["id"].astype(str).tolist()
        cd1, cd2, _ = st.columns([2, 1, 3], gap="medium")
        with cd1:
            del_id = st.selectbox("Excluir por ID", ["—"] + ids_hj, key="del_id", label_visibility="visible")
        with cd2:
            st.markdown('<div style="height:29px"></div>', unsafe_allow_html=True)
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



    st.markdown('<div class="card" style="border-top:3px solid #fb7c8f">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#fb7c8f">⏳ Notas Pendentes</span>
      <span class="card-count">{len(pend)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div style="padding:1.75rem;text-align:center"><span class="al-s" style="justify-content:center;display:inline-flex">✅ Nenhuma nota pendente!</span></div>', unsafe_allow_html=True)
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

        # ── Tabela de exibição (DataGrid com paginação) + painel de roteirização
        PEND_COLS = [c for c in [
            "data_registro", "placa_road", "motivo", "bairro",
            "numnota", "numped", "codcliente", "nomecliente", "dt_liberado",
            "nomevend", "nomesup", "pesobrutotot", "vltotal",
            "praca", "numcarregamento", "destino",
        ] if c in df_p.columns]

        if df_p.empty:
            st.markdown('<div class="al-i" style="margin:1rem 1.5rem">Nenhuma nota pendente nos filtros.</div>', unsafe_allow_html=True)
        else:
            df_p_sorted = df_p.sort_values("dt_liberado", ascending=False).reset_index(drop=True)
            df_p_display = dedup_columns(df_p_sorted[PEND_COLS].copy()) if PEND_COLS else df_p_sorted

            st.markdown('<div class="card-body" style="padding-top:0">', unsafe_allow_html=True)
            _pend_defs = [d for d in STD_DG_DEFS if d["key"] in df_p_display.columns]
            render_pro_table(df_p_display, _pend_defs, key="pend_table", page_size=10)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="sec-div" style="margin-top:.75rem"><div class="sec-div-line"></div><div class="sec-div-txt">🗺️ Roteirizar notas</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)

            # ── Monta tabela de seleção com checkbox ─────────────────────────
            df_sel = df_p_sorted[["numnota", "numped", "nomecliente", "bairro", "numcarregamento", "placa_road", "pesobrutotot", "vltotal", "praca", "id"]].copy()
            df_sel.insert(0, "✓", False)
            df_sel = df_sel.rename(columns={
                "numnota":        "Nota",
                "numped":         "Pedido",
                "nomecliente":    "Cliente",
                "bairro":         "Bairro",
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
                    "Bairro":       st.column_config.TextColumn("Bairro",             width="medium"),
                    "Carregamento": st.column_config.TextColumn("Carregamento",       width="small"),
                    "Placa Antiga": st.column_config.TextColumn("Placa Antiga",       width="small"),
                    "Peso (kg)":    st.column_config.NumberColumn("Peso (kg)",        format="%.0f kg", width="small"),
                    "Valor (R$)":   st.column_config.NumberColumn("Valor (R$)",       format="R$ %.2f", width="small"),
                    "Praça":        st.column_config.TextColumn("Praça",              width="small"),
                    "_id":          st.column_config.TextColumn("ID",                 width="small"),
                },
                disabled=["Nota","Pedido","Cliente","Bairro","Carregamento","Placa Antiga","Peso (kg)","Valor (R$)","Praça","_id"],
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
                <div style="display:flex;gap:.6rem;flex-wrap:wrap;margin:.75rem 0 1rem">
                  <div style="background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.3);border-radius:8px;padding:.45rem 1rem;font-size:.75rem;color:#93c5fd">
                    <span style="font-weight:700;font-size:1rem;color:#F8FAFC">{n_sel}</span> &nbsp;nota(s) selecionada(s)
                  </div>
                  <div style="background:rgba(124,58,237,0.10);border:1px solid rgba(124,58,237,0.30);border-radius:8px;padding:.45rem 1rem;font-size:.75rem;color:#c4b5fd">
                    👤 <span style="font-weight:700;font-size:1rem;color:#F8FAFC">{_n_clientes}</span> &nbsp;cliente(s)
                  </div>
                  <div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.25);border-radius:8px;padding:.45rem 1rem;font-size:.75rem;color:#6ee7b7">
                    ⚖️ <span style="font-weight:700">{_peso_fmt}</span>
                  </div>
                  <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);border-radius:8px;padding:.45rem 1rem;font-size:.75rem;color:#93c5fd">
                    💰 <span style="font-weight:700">{_valor_fmt}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="al-i" style="margin:.5rem 0 1rem">☝️ Marque uma ou mais notas na tabela acima para roteirizar em lote.</div>', unsafe_allow_html=True)

            # ── Placa + Data de saída compartilhadas ─────────────────────────
            c_nova_pl, c_dt_saida, c_btn = st.columns([1.4, 1.1, 0.8], gap="medium")
            with c_nova_pl:
                nova_pl_i = st.text_input("Nova Placa", placeholder="Ex: ABC-1234", key="pl_lote")
            with c_dt_saida:
                dt_saida_i = st.date_input("Data de Saída", value=None, key="dt_lote", format="DD/MM/YYYY")
            with c_btn:
                st.markdown('<div style="height:29px"></div>', unsafe_allow_html=True)
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
    st.markdown('<div class="card" style="border-top:3px solid #22C55E">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#22C55E">✅ Notas Roteirizadas</span>
      <span class="card-count">{len(rote)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if rote.empty:
        st.markdown(f'<div style="padding:1.5rem"><div class="al-i">Nenhuma nota roteirizada em {periodo_txt}.</div></div>', unsafe_allow_html=True)
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
        _rot_front = ["data_registro", "placa_road", "placa_veiculo", "motivo", "bairro", "numcarregamento", "dt_saida"]
        _rot_rest  = [c for c in STD_COLS + ["placa_veiculo", "dt_saida", "motivo", "bairro"] if c not in _rot_front]
        ROT_COLS   = [c for c in _rot_front + _rot_rest if c in df_r.columns]
        ROT_DG_DEFS = [
            {"key": "data_registro",   "label": "Data Registro", "align": "left"},
            {"key": "placa_road",      "label": "Placa Antiga",  "align": "left"},
            {"key": "placa_veiculo",   "label": "Nova Placa",    "align": "left"},
            {"key": "motivo",          "label": "Motivo",        "align": "left",  "width": "180px"},
            {"key": "bairro",          "label": "Bairro",        "align": "left",  "width": "160px"},
            {"key": "numcarregamento", "label": "Carregamento",  "align": "left"},
            {"key": "dt_saida",        "label": "Dt. Saída",     "align": "left"},
        ] + [d for d in STD_DG_DEFS if d["key"] not in (
            "placa_road", "motivo", "bairro", "numcarregamento", "data_registro"
        )]
        df_rd = dedup_columns(df_r[ROT_COLS].copy())
        if "dt_saida" in df_rd.columns:
            df_rd["dt_saida"] = df_rd["dt_saida"].apply(fmt_date)
        # Substitui vazios por traço para exibição limpa
        for _c2 in ["placa_veiculo", "dt_saida"]:
            if _c2 in df_rd.columns:
                df_rd[_c2] = df_rd[_c2].replace({"": "—", "nan": "—", "None": "—"})

        df_rd_sorted = df_rd.sort_values("dt_liberado", ascending=False).reset_index(drop=True) if not df_rd.empty else df_rd
        df_r_sorted  = df_r.sort_values("dt_liberado", ascending=False).reset_index(drop=True) if not df_r.empty else df_r

        # ── DataGrid profissional (paginado) ─────────────────────────────────
        _rote_defs = [d for d in ROT_DG_DEFS if d["key"] in df_rd_sorted.columns]
        render_pro_table(df_rd_sorted, _rote_defs, key="roteirizadas_table", page_size=10)
        st.caption(f"{len(df_r)} nota(s)")

        # ── Lixeira por linha: selectbox de nota + botão devolver ────────────
        if not df_r_sorted.empty:
            st.markdown('<div class="sec-div" style="margin:.85rem 0 .5rem"><div class="sec-div-line"></div><div class="sec-div-txt">↩️ Devolver para pendente</div><div class="sec-div-line"></div></div>', unsafe_allow_html=True)
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
    st.markdown('<div class="card" style="border-top:3px solid #3B82F6">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title" style="color:#60a5fa">📊 Relatório por Placa</span>
      <span class="card-count">{len(rote)} · {periodo_txt}</span>
    </div>
    """, unsafe_allow_html=True)

    if rote.empty:
        st.markdown(f'<div style="padding:1.5rem"><div class="al-i">Nenhum dado roteirizado em {periodo_txt}.</div></div>', unsafe_allow_html=True)
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

        PLACA_DG_DEFS = [
            {"key": "data_registro",  "label": "Data",          "align": "left"},
            {"key": "placa_veiculo",  "label": "Placa",         "align": "left"},
            {"key": "qtd_clientes",   "label": "Qtd. Clientes", "align": "right", "type": "int"},
            {"key": "peso",           "label": "Peso (kg)",     "align": "right", "type": "weight"},
            {"key": "valor",          "label": "Valor (R$)",    "align": "right", "type": "currency"},
        ]

        render_pro_table(df_placa, PLACA_DG_DEFS, key="placa_table", page_size=10)

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
            '<span class="chart-title" style="color:#A78BFA">🚛 Por Veículo</span>'
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
                _tv2 = _tv2.sort_values("qtd", ascending=False)
                _rows_vend2 = _tv2.to_dict("records")

        def _fmt_brl(v):
            s = f"{int(round(v)):,}".replace(",", ".")
            return f"R {s}"

        st.markdown(
            _svg_col_line(
                _rows_vend2,
                label_key="veiculo", val_key="qtd", qtd_key="valor",
                bar_color_1="#86EFAC", bar_color_2="#22C55E",
                line_color="#FACC15",
                fmt_val=None,
                line_fmt=_fmt_brl,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-top:8px;padding:0 .25rem">'
            '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#FACC15" stroke-width="2"/>'
            '<circle cx="18" cy="5" r="3.5" fill="#FACC15"/></svg>'
            '<span style="font-size:.68rem;color:#94A3B8">Linha = valor (R$)</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)

    # — Gráfico Motivo —
    with _col_mot:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-head">'
            '<span class="chart-title" style="color:#A78BFA">📋 Por Motivos</span>'
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
                _mot_qtd = _df_mot.groupby("motivo")["numnota"].count().reset_index()
                _mot_qtd.columns = ["motivo", "qtd"]
                _mot_val = _df_mot.groupby("motivo")["vltotal"].sum().reset_index()
                _mot_val.columns = ["motivo", "valor"]
                _top_mot = _mot_qtd.merge(_mot_val, on="motivo", how="left").fillna(0)
                _top_mot = _top_mot.sort_values("qtd", ascending=False)
                _rows_motivo = _top_mot.to_dict("records")

        def _fmt_brl_mot(v):
            s = f"{int(round(v)):,}".replace(",", ".")
            return f"R {s}"

        if _rows_motivo:
            st.markdown(
                _svg_col_line(
                    _rows_motivo,
                    label_key="motivo", val_key="qtd", qtd_key="valor",
                    bar_color_1="#86EFAC", bar_color_2="#22C55E",
                    line_color="#FACC15",
                    fmt_val=None,
                    line_fmt=_fmt_brl_mot,
                    rotate_labels=True,
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="display:flex;align-items:center;gap:6px;margin-top:8px;padding:0 .25rem">'
                '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#FACC15" stroke-width="2"/>'
                '<circle cx="18" cy="5" r="3.5" fill="#FACC15"/></svg>'
                '<span style="font-size:.68rem;color:#94A3B8">Linha = valor (R$)</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="color:#64748B;font-size:.78rem;text-align:center;padding:1.5rem 0">'
                'Nenhum motivo registrado no período.</p>',
                unsafe_allow_html=True,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

    # — Gráfico Bairro —
    st.markdown('<div style="height:var(--space-4)"></div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="chart-head">'
        '<span class="chart-title" style="color:#A78BFA">📍 Por Bairro</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="chart-body">', unsafe_allow_html=True)

    _rows_bairro = []
    if not df.empty and "bairro" in df.columns:
        _df_bai = df[
            df["bairro"].notna() &
            (df["bairro"].astype(str).str.strip() != "") &
            (df["bairro"].astype(str).str.strip() != "— Selecione ou digite o bairro —")
        ]
        if not _df_bai.empty:
            _bai_qtd = _df_bai.groupby("bairro")["numnota"].count().reset_index()
            _bai_qtd.columns = ["bairro", "qtd"]
            _bai_val = _df_bai.groupby("bairro")["vltotal"].sum().reset_index()
            _bai_val.columns = ["bairro", "valor"]
            _top_bai = _bai_qtd.merge(_bai_val, on="bairro", how="left").fillna(0)
            _top_bai = _top_bai.sort_values("qtd", ascending=False)
            _rows_bairro = _top_bai.to_dict("records")

    def _fmt_brl_bai(v):
        s = f"{int(round(v)):,}".replace(",", ".")
        return f"R {s}"

    if _rows_bairro:
        st.markdown(
            _svg_col_line(
                _rows_bairro,
                label_key="bairro", val_key="qtd", qtd_key="valor",
                bar_color_1="#86EFAC", bar_color_2="#22C55E",
                line_color="#FACC15",
                fmt_val=None,
                line_fmt=_fmt_brl_bai,
                rotate_labels=True,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-top:8px;padding:0 .25rem">'
            '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#FACC15" stroke-width="2"/>'
            '<circle cx="18" cy="5" r="3.5" fill="#FACC15"/></svg>'
            '<span style="font-size:.68rem;color:#94A3B8">Linha = valor (R$)</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color:#64748B;font-size:.78rem;text-align:center;padding:1.5rem 0">'
            'Nenhum bairro registrado no período.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div style="margin-top:20px"></div>', unsafe_allow_html=True)
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
        '<div style="margin-top:14px;margin-bottom:4px;display:flex;align-items:center;gap:8px">'
        '<span style="font-size:.68rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">&#128197; Filtrar por Data de Sa&#237;da</span>'
        '<div style="flex:1;height:1px;background:rgba(248,250,252,0.07)"></div>'
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

    _hist_front = ["data_registro", "placa_road", "placa_veiculo", "motivo", "bairro", "numcarregamento"]
    _hist_rest  = [c for c in STD_COLS + ["dt_saida", "status", "motivo", "bairro"] if c not in _hist_front]
    HIST_COLS = [c for c in _hist_front + _hist_rest + ["status"] if c in df_h.columns]
    HIST_DG_DEFS = [
        {"key": "data_registro",   "label": "Data Registro", "align": "left"},
        {"key": "placa_road",      "label": "Placa Antiga",  "align": "left"},
        {"key": "placa_veiculo",   "label": "Nova Placa",    "align": "left"},
        {"key": "motivo",          "label": "Motivo",        "align": "left",  "width": "180px"},
        {"key": "bairro",          "label": "Bairro",        "align": "left",  "width": "160px"},
        {"key": "numcarregamento", "label": "Carregamento",  "align": "left"},
        {"key": "status",          "label": "Status",        "align": "center", "type": "status"},
    ] + [d for d in STD_DG_DEFS if d["key"] not in (
        "placa_road", "motivo", "bairro", "numcarregamento", "data_registro"
    )] + [{"key": "dt_saida", "label": "Dt. Saída", "align": "left"}]

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
        df_hd_sorted = df_hd.sort_values("numnota", ascending=False).reset_index(drop=True)
        st.markdown('<div class="card-body" style="padding-top:0">', unsafe_allow_html=True)
        _hist_defs = [d for d in HIST_DG_DEFS if d["key"] in df_hd_sorted.columns]
        render_pro_table(df_hd_sorted, _hist_defs, key="historico_table", page_size=15, status_key="status")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
