import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import json
import io

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TRANSF — Sistema de Transferências",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --bg:#0a0c10; --sur:#111318; --sur2:#1a1d24; --sur3:#22262f;
  --bdr:#2a2f3a; --bdr2:#353b47;
  --acc:#ff6b2b; --acc2:#ff8f5e;
  --grn:#22c55e; --grn2:#4ade80;
  --blu:#3b82f6; --blu2:#60a5fa;
  --pur:#a855f7; --yel:#eab308; --red:#ef4444;
  --txt:#e8ecf3; --txt2:#a0aab8; --mut:#6b7585;
}

html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--txt) !important;
}

.stApp { background-color: var(--bg) !important; }

section[data-testid="stSidebar"] {
  background-color: var(--sur) !important;
  border-right: 1px solid var(--bdr) !important;
}

.metric-card {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 1.25rem 1.4rem;
  position: relative;
  overflow: hidden;
  margin-bottom: 0.5rem;
}
.metric-bar {
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  border-radius: 12px 12px 0 0;
}
.metric-lbl {
  font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--mut); margin-bottom: 0.4rem;
}
.metric-val {
  font-size: 1.9rem; font-weight: 800; line-height: 1;
  font-family: 'JetBrains Mono', monospace;
}
.metric-sub { font-size: 0.73rem; color: var(--txt2); margin-top: 0.3rem; }

.page-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--bdr);
}
.page-tag {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.15rem 0.6rem; border-radius: 99px;
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; margin-bottom: 0.5rem;
}
.tag-fat { background: rgba(255,107,43,0.15); color: var(--acc2); border: 1px solid rgba(255,107,43,0.25); }
.tag-rot { background: rgba(34,197,94,0.15); color: var(--grn2); border: 1px solid rgba(34,197,94,0.25); }
.tag-dash { background: rgba(59,130,246,0.15); color: var(--blu2); border: 1px solid rgba(59,130,246,0.25); }
.page-h1 { font-size: 1.6rem; font-weight: 800; line-height: 1.2; color: var(--txt); }
.page-sub { font-size: 0.82rem; color: var(--txt2); margin-top: 0.3rem; }

.road-box {
  background: var(--sur2);
  border: 1px solid rgba(255,107,43,0.2);
  border-radius: 12px;
  padding: 1.25rem;
  margin: 0.75rem 0;
}
.road-box-tit {
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--acc2); margin-bottom: 0.75rem;
}

.badge {
  display: inline-flex; align-items: center;
  padding: 0.15rem 0.55rem; border-radius: 99px;
  font-size: 0.67rem; font-weight: 700; white-space: nowrap;
}
.badge-grn { background: rgba(34,197,94,0.15); color: var(--grn2); }
.badge-red { background: rgba(239,68,68,0.15); color: #f87171; }
.badge-yel { background: rgba(234,179,8,0.15); color: #fbbf24; }
.badge-acc { background: rgba(255,107,43,0.15); color: var(--acc2); }
.badge-blu { background: rgba(59,130,246,0.15); color: var(--blu2); }

.alert-success {
  background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3);
  color: var(--grn2); border-radius: 8px; padding: 0.65rem 0.95rem;
  font-size: 0.85rem; margin: 0.5rem 0;
}
.alert-error {
  background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3);
  color: #f87171; border-radius: 8px; padding: 0.65rem 0.95rem;
  font-size: 0.85rem; margin: 0.5rem 0;
}
.alert-info {
  background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.3);
  color: var(--blu2); border-radius: 8px; padding: 0.65rem 0.95rem;
  font-size: 0.85rem; margin: 0.5rem 0;
}

div[data-testid="stDataFrameContainer"] {
  background: var(--sur) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: 12px !important;
}

.stButton > button {
  background-color: var(--acc) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  font-family: 'DM Sans', sans-serif !important;
}
.stButton > button:hover {
  background-color: var(--acc2) !important;
}

.stTextInput > div > input,
.stDateInput > div > input,
.stSelectbox > div > div {
  background-color: var(--sur2) !important;
  color: var(--txt) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: 8px !important;
}
.stTextArea > div > textarea {
  background-color: var(--sur2) !important;
  color: var(--txt) !important;
  border: 1px solid var(--bdr) !important;
}

div[data-testid="metric-container"] {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 1rem;
}

.sidebar-logo {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.3rem; font-weight: 800;
  color: var(--acc);
  padding: 0.5rem 0 1.5rem 0;
  display: flex; align-items: center; gap: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS — CONEXÃO
# ══════════════════════════════════════════════════════════════════════════════
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Conecta ao Google Sheets via service account dos secrets."""
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_gspread_client()
    return client.open_by_key(st.secrets["spreadsheet_id"])

def get_sheet(name: str):
    """Retorna aba pelo nome, criando se não existir."""
    ss = get_spreadsheet()
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=name, rows=5000, cols=20)
        return ws

# ── ABA TRANSFERENCIAS ────────────────────────────────────────────────────────
TRANSF_COLS = [
    "id", "dt_transferencia", "numped", "numnota", "nomecliente",
    "nomesup", "praca", "pesobrutotot", "numcarregamento", "vltotal",
    "destino", "obs", "placa", "dt_roteirizacao", "status", "criado_em"
]

def ensure_transf_header():
    ws = get_sheet("transferencias")
    header = ws.row_values(1)
    if not header:
        ws.update("A1", [TRANSF_COLS])
    return ws

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias() -> pd.DataFrame:
    ws = ensure_transf_header()
    data = ws.get_all_records(expected_headers=TRANSF_COLS)
    if not data:
        return pd.DataFrame(columns=TRANSF_COLS)
    df = pd.DataFrame(data)
    for col in ["pesobrutotot", "vltotal"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df

def next_id(df: pd.DataFrame) -> int:
    if df.empty or "id" not in df.columns or df["id"].eq("").all():
        return 1
    return int(pd.to_numeric(df["id"], errors="coerce").max() + 1)

def append_transferencia(row: dict):
    ws = ensure_transf_header()
    df = load_transferencias()
    row["id"] = next_id(df)
    row["criado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row["status"] = "pendente"
    row["placa"] = ""
    row["dt_roteirizacao"] = ""
    values = [str(row.get(c, "")) for c in TRANSF_COLS]
    ws.append_row(values, value_input_option="USER_ENTERED")
    load_transferencias.clear()

def update_transferencia(tid: int, updates: dict):
    ws = ensure_transf_header()
    data = ws.get_all_values()
    header = data[0]
    for i, row in enumerate(data[1:], start=2):
        row_dict = dict(zip(header, row))
        if str(row_dict.get("id", "")) == str(tid):
            for col, val in updates.items():
                if col in header:
                    col_idx = header.index(col) + 1
                    ws.update_cell(i, col_idx, str(val))
            break
    load_transferencias.clear()

def delete_transferencia(tid: int):
    ws = ensure_transf_header()
    data = ws.get_all_values()
    header = data[0]
    for i, row in enumerate(data[1:], start=2):
        row_dict = dict(zip(header, row))
        if str(row_dict.get("id", "")) == str(tid):
            ws.delete_rows(i)
            break
    load_transferencias.clear()

def check_duplicate(numnota: str, dt: str) -> bool:
    df = load_transferencias()
    if df.empty:
        return False
    mask = (df["numnota"].astype(str) == str(numnota)) & (df["dt_transferencia"].astype(str) == str(dt))
    return bool(mask.any())

# ── ABA ROAD ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_road() -> pd.DataFrame:
    """Carrega a aba ROAD do Google Sheets (mesmo arquivo ou arquivo separado)."""
    try:
        # Tenta ler a aba "ROAD" no mesmo arquivo
        ws = get_sheet("ROAD")
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df.columns = [str(c).upper().strip() for c in df.columns]
        for col in ["NUMNOTA", "NUMPED"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.split(".").str[0].str.strip()
        return df
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar ROAD: {e}")
        return pd.DataFrame()

def buscar_nota(numnota: str) -> dict | None:
    df = load_road()
    if df.empty:
        return None
    mask = df["NUMNOTA"].astype(str) == numnota.strip()
    row = df[mask]
    if row.empty:
        return None
    r = row.iloc[0]

    def safe(col):
        v = r.get(col, "")
        if str(v) in ("nan", "None", "", None): return ""
        v = str(v)
        if v.endswith(".0"): return v[:-2]
        return v

    try: peso = float(str(r.get("PESOBRUTOTOT", "0")).replace(",", "."))
    except: peso = 0.0
    try: vl = float(str(r.get("VLTOTAL", "0")).replace(",", "."))
    except: vl = 0.0

    praca = safe("PRAÇA") or safe("PRACA") or safe("PRAA") or safe("PRAÃ‡A")

    return {
        "numped":          safe("NUMPED"),
        "numnota":         safe("NUMNOTA"),
        "nomecliente":     safe("NOMECLIENTE"),
        "nomesup":         safe("NOMESUP"),
        "praca":           praca,
        "pesobrutotot":    peso,
        "numcarregamento": safe("NUMCARREGAMENTO"),
        "vltotal":         vl,
        "destino":         safe("DESTINO"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def br(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def kg(v):
    try:
        return f"{float(v):,.3f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kg"
    except:
        return "0,000 kg"

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🚛 TRANSF</div>', unsafe_allow_html=True)
    st.markdown("---")

    pagina = st.radio(
        "Navegação",
        ["📊 Dashboard", "➕ Nova Transferência", "📋 Histórico", "🗺️ Roteirização"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.72rem;color:#6b7585;line-height:1.8">'
        '🟢 Sistema ativo<br>'
        f'📅 {date.today().strftime("%d/%m/%Y")}'
        '</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "📊 Dashboard":
    st.markdown("""
    <div class="page-header">
      <div class="page-tag tag-dash">📊 Visão Geral</div>
      <div class="page-h1">Dashboard</div>
      <div class="page-sub">Acompanhe todas as transferências em tempo real</div>
    </div>
    """, unsafe_allow_html=True)

    df = load_transferencias()

    hoje = date.today().isoformat()
    total_notas    = len(df)
    total_valor    = df["vltotal"].sum() if not df.empty else 0
    total_peso     = df["pesobrutotot"].sum() if not df.empty else 0
    total_pendente = int((df["status"] == "pendente").sum()) if not df.empty else 0
    total_rot      = int((df["status"] == "roteirizado").sum()) if not df.empty else 0
    hoje_df        = df[df["dt_transferencia"] == hoje] if not df.empty else pd.DataFrame()
    hoje_n         = len(hoje_df)
    hoje_v         = hoje_df["vltotal"].sum() if not hoje_df.empty else 0

    # KPIs
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#ff6b2b,#ff8f5e)"></div>
          <div class="metric-lbl">Total de Notas</div>
          <div class="metric-val">{total_notas}</div>
          <div class="metric-sub">transferências</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#ff6b2b,#ff8f5e)"></div>
          <div class="metric-lbl">Valor Total</div>
          <div class="metric-val" style="font-size:1.2rem">{br(total_valor)}</div>
          <div class="metric-sub">soma de todas</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#ff6b2b,#ff8f5e)"></div>
          <div class="metric-lbl">Peso Total</div>
          <div class="metric-val" style="font-size:1.2rem">{kg(total_peso)}</div>
          <div class="metric-sub">peso bruto</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#3b82f6,#60a5fa)"></div>
          <div class="metric-lbl">Hoje</div>
          <div class="metric-val">{hoje_n}</div>
          <div class="metric-sub">{br(hoje_v)}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#ef4444,#f87171)"></div>
          <div class="metric-lbl">⏳ Pendentes</div>
          <div class="metric-val" style="color:#ef4444">{total_pendente}</div>
          <div class="metric-sub">aguardando placa</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#22c55e,#4ade80)"></div>
          <div class="metric-lbl">✅ Roteirizadas</div>
          <div class="metric-val" style="color:#22c55e">{total_rot}</div>
          <div class="metric-sub">placa definida</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df.empty:
        # Gráficos
        por_data = df.groupby("dt_transferencia").agg(
            valor=("vltotal", "sum"),
            qtd=("id", "count"),
            peso=("pesobrutotot", "sum")
        ).reset_index().sort_values("dt_transferencia").tail(30)

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**📅 Valor por Data**")
            st.area_chart(por_data.set_index("dt_transferencia")["valor"], color="#ff6b2b")
        with col_r:
            st.markdown("**📦 Quantidade de Notas por Data**")
            st.bar_chart(por_data.set_index("dt_transferencia")["qtd"], color="#3b82f6")

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**🏆 Top Clientes por Valor**")
            top_cli = df.groupby("nomecliente")["vltotal"].sum().sort_values(ascending=False).head(8)
            st.bar_chart(top_cli, color="#a855f7")
        with col4:
            st.markdown("**👤 Valor por Supervisor**")
            sup = df.groupby("nomesup")["vltotal"].sum().sort_values(ascending=False)
            st.bar_chart(sup, color="#22c55e")

    st.markdown("---")

    # Filtros e tabela
    st.markdown("**📋 Registro de Transferências**")
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        busca = st.text_input("🔍 Buscar...", key="dash_busca", label_visibility="collapsed")
    with col_f2:
        datas = ["Todas as datas"] + (sorted(df["dt_transferencia"].unique().tolist(), reverse=True) if not df.empty else [])
        filtro_data = st.selectbox("Data", datas, label_visibility="collapsed")
    with col_f3:
        filtro_st = st.selectbox("Status", ["Todos", "pendente", "roteirizado"], label_visibility="collapsed")

    df_show = df.copy() if not df.empty else pd.DataFrame(columns=TRANSF_COLS)
    if not df_show.empty:
        if filtro_data != "Todas as datas":
            df_show = df_show[df_show["dt_transferencia"] == filtro_data]
        if filtro_st != "Todos":
            df_show = df_show[df_show["status"] == filtro_st]
        if busca:
            mask = df_show.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_show = df_show[mask]

    # Botão exportar
    if not df_show.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            df_show.to_excel(w, index=False, sheet_name="Transferencias")
        out.seek(0)
        st.download_button(
            "⬇️ Exportar Excel",
            out,
            file_name=f"transferencias_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    cols_show = ["dt_transferencia", "numnota", "numped", "nomecliente",
                 "nomesup", "praca", "destino", "pesobrutotot", "vltotal", "placa", "status"]
    cols_show = [c for c in cols_show if c in df_show.columns]
    st.dataframe(
        df_show[cols_show].sort_values("dt_transferencia", ascending=False) if not df_show.empty else df_show,
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(df_show)} registro(s)")

    # Excluir
    if not df.empty:
        st.markdown("---")
        st.markdown("**🗑️ Excluir Transferência**")
        ids = df["id"].astype(str).tolist()
        del_id = st.selectbox("ID para excluir", ["—"] + ids, label_visibility="collapsed")
        if del_id != "—":
            row_info = df[df["id"].astype(str) == del_id].iloc[0]
            st.warning(f"Nota: **{row_info['numnota']}** — {row_info['nomecliente']} — {br(row_info['vltotal'])}")
            if st.button("🗑️ Confirmar Exclusão", type="secondary"):
                delete_transferencia(int(del_id))
                st.success("✅ Excluído com sucesso!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: NOVA TRANSFERÊNCIA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "➕ Nova Transferência":
    st.markdown("""
    <div class="page-header">
      <div class="page-tag tag-fat">🧾 Faturamento</div>
      <div class="page-h1">Nova Transferência</div>
      <div class="page-sub">Registre a transferência de nota para a Roteirização</div>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_side = st.columns([1.2, 0.8])

    with col_form:
        st.markdown("**📅 Data da Transferência**")
        dt_transf = st.date_input("Data", value=date.today(), label_visibility="collapsed")

        st.markdown("**🔍 Número da Nota (NUMNOTA)**")
        col_nota, col_btn = st.columns([3, 1])
        with col_nota:
            nota_input = st.text_input("Nota", placeholder="Ex: 398234", label_visibility="collapsed",
                                       key="nova_nota")
        with col_btn:
            buscar_btn = st.button("🔍 Buscar", use_container_width=True)

        if "nota_encontrada" not in st.session_state:
            st.session_state.nota_encontrada = None
        if "ultima_nota_buscada" not in st.session_state:
            st.session_state.ultima_nota_buscada = ""

        if buscar_btn and nota_input.strip():
            with st.spinner("Buscando na base ROAD..."):
                resultado = buscar_nota(nota_input.strip())
            if resultado:
                st.session_state.nota_encontrada = resultado
                st.session_state.ultima_nota_buscada = nota_input.strip()
                st.markdown('<div class="alert-success">✅ Nota encontrada! Dados preenchidos automaticamente.</div>',
                            unsafe_allow_html=True)
            else:
                st.session_state.nota_encontrada = None
                st.markdown(f'<div class="alert-error">❌ Nota "{nota_input.strip()}" não encontrada na base ROAD.</div>',
                            unsafe_allow_html=True)

        cur = st.session_state.nota_encontrada

        if cur:
            st.markdown(f"""
            <div class="road-box">
              <div class="road-box-tit">✅ DADOS ENCONTRADOS NA BASE ROAD</div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Pedido", value=cur["numped"] or "—", disabled=True)
                st.text_input("Cliente", value=cur["nomecliente"], disabled=True)
                st.text_input("Carregamento", value=cur["numcarregamento"], disabled=True)
                st.text_input("Peso Bruto (kg)", value=f"{cur['pesobrutotot']:.3f}".replace(".", ","), disabled=True)
            with c2:
                st.text_input("Nota Fiscal", value=cur["numnota"], disabled=True)
                st.text_input("Supervisor", value=cur["nomesup"], disabled=True)
                st.text_input("Praça", value=cur["praca"] or "—", disabled=True)
                st.text_input("Destino", value=cur["destino"], disabled=True)

            st.text_input("Valor Total", value=br(cur["vltotal"]), disabled=True)

            obs = st.text_area("💬 Observação (opcional)", placeholder="Alguma observação adicional...",
                               key="nova_obs")

            st.markdown("<br>", unsafe_allow_html=True)
            confirmar = st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True)

            if confirmar:
                dt_str = dt_transf.isoformat()
                if check_duplicate(cur["numnota"], dt_str):
                    st.markdown(f'<div class="alert-error">❌ Nota {cur["numnota"]} já registrada nesta data.</div>',
                                unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        append_transferencia({
                            "dt_transferencia":  dt_str,
                            "numped":            cur["numped"],
                            "numnota":           cur["numnota"],
                            "nomecliente":       cur["nomecliente"],
                            "nomesup":           cur["nomesup"],
                            "praca":             cur["praca"],
                            "pesobrutotot":      cur["pesobrutotot"],
                            "numcarregamento":   cur["numcarregamento"],
                            "vltotal":           cur["vltotal"],
                            "destino":           cur["destino"],
                            "obs":               obs,
                        })
                    st.success("✅ Transferência registrada! Nota fica pendente até a Roteirização informar a placa.")
                    st.session_state.nota_encontrada = None
                    st.balloons()
                    st.rerun()

    with col_side:
        st.markdown("**📅 Transferidas Hoje**")
        df_all = load_transferencias()
        hoje = date.today().isoformat()
        df_hoje = df_all[df_all["dt_transferencia"] == hoje] if not df_all.empty else pd.DataFrame()

        if df_hoje.empty:
            st.markdown('<div class="alert-info">📭 Nenhuma transferência hoje ainda.</div>', unsafe_allow_html=True)
        else:
            for _, row in df_hoje.iterrows():
                st_icon = "✅" if row.get("status") == "roteirizado" else "⏳"
                placa_info = f" · 🚗 {row['placa']}" if row.get("placa") else " · Pendente"
                st.markdown(f"""
                <div style="padding:.5rem 0;border-bottom:1px solid #2a2f3a;font-size:.83rem">
                  <span style="font-family:JetBrains Mono,monospace;font-weight:700">{row['numnota']}</span>
                  <span style="color:#a0aab8;margin-left:.5rem">{str(row['nomecliente'])[:25]}</span><br>
                  <span style="color:#ff8f5e;font-weight:700">{br(row['vltotal'])}</span>
                  <span style="color:#6b7585">{st_icon}{placa_info}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown(
                f"**Total hoje:** {len(df_hoje)} notas · {br(df_hoje['vltotal'].sum())}",
                unsafe_allow_html=False
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1a1d24;border:1px solid #2a2f3a;border-radius:12px;padding:1rem;font-size:.83rem;color:#a0aab8">
          <strong style="color:#e8ecf3;display:block;margin-bottom:.5rem">💡 Como usar</strong>
          1. Selecione a <strong style="color:#e8ecf3">data</strong><br>
          2. Digite o <strong style="color:#e8ecf3">número da nota</strong> e clique <strong style="color:#ff6b2b">Buscar</strong><br>
          3. Dados preenchidos <strong style="color:#ff6b2b">automaticamente</strong><br>
          4. Clique em <strong style="color:#e8ecf3">Confirmar Transferência</strong><br><br>
          <div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:8px;padding:.6rem;color:#4ade80">
            🗺️ Após registrar, a nota ficará <strong>pendente</strong> até a Roteirização informar a placa.
          </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋 Histórico":
    st.markdown("""
    <div class="page-header">
      <div class="page-tag tag-fat">🧾 Faturamento</div>
      <div class="page-h1">Histórico de Transferências</div>
      <div class="page-sub">Todas as notas registradas</div>
    </div>
    """, unsafe_allow_html=True)

    df = load_transferencias()

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        busca = st.text_input("🔍 Buscar...", key="hist_busca", label_visibility="collapsed")
    with col_f2:
        datas = ["Todas as datas"] + (sorted(df["dt_transferencia"].unique().tolist(), reverse=True) if not df.empty else [])
        filtro_data = st.selectbox("Data", datas, key="hist_data", label_visibility="collapsed")
    with col_f3:
        filtro_st = st.selectbox("Status", ["Todos", "pendente", "roteirizado"], key="hist_st", label_visibility="collapsed")

    df_show = df.copy() if not df.empty else pd.DataFrame(columns=TRANSF_COLS)
    if not df_show.empty:
        if filtro_data != "Todas as datas":
            df_show = df_show[df_show["dt_transferencia"] == filtro_data]
        if filtro_st != "Todos":
            df_show = df_show[df_show["status"] == filtro_st]
        if busca:
            mask = df_show.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_show = df_show[mask]

    if not df_show.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            df_show.to_excel(w, index=False, sheet_name="Transferencias")
        out.seek(0)
        st.download_button("⬇️ Exportar Excel", out,
                           file_name=f"transferencias_{date.today().isoformat()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.dataframe(
        df_show.sort_values("dt_transferencia", ascending=False) if not df_show.empty else df_show,
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(df_show)} registro(s)")

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: ROTEIRIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗺️ Roteirização":
    st.markdown("""
    <div class="page-header">
      <div class="page-tag tag-rot">🗺️ Roteirização</div>
      <div class="page-h1">Roteirizar Notas</div>
      <div class="page-sub">Informe a placa do veículo para cada nota transferida</div>
    </div>
    """, unsafe_allow_html=True)

    df = load_transferencias()

    pendentes  = df[df["status"] == "pendente"] if not df.empty else pd.DataFrame()
    roteiriz   = df[df["status"] == "roteirizado"] if not df.empty else pd.DataFrame()

    # KPIs rápidos
    c1, c2 = st.columns(2)
    with c1:
        n = len(pendentes)
        v = pendentes["vltotal"].sum() if not pendentes.empty else 0
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#ef4444,#f87171)"></div>
          <div class="metric-lbl">⏳ Pendentes</div>
          <div class="metric-val" style="color:#ef4444">{n}</div>
          <div class="metric-sub">{br(v)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        n2 = len(roteiriz)
        v2 = roteiriz["vltotal"].sum() if not roteiriz.empty else 0
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-bar" style="background:linear-gradient(90deg,#22c55e,#4ade80)"></div>
          <div class="metric-lbl">✅ Roteirizadas</div>
          <div class="metric-val" style="color:#22c55e">{n2}</div>
          <div class="metric-sub">{br(v2)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PENDENTES ──
    st.markdown("### ⏳ Notas Pendentes de Roteirização")
    if pendentes.empty:
        st.markdown('<div class="alert-success">✅ Nenhuma nota pendente! Tudo roteirizado.</div>', unsafe_allow_html=True)
    else:
        col_bp1, col_bp2 = st.columns([2, 1])
        with col_bp1:
            busca_p = st.text_input("🔍 Buscar pendentes...", key="rot_busca_p", label_visibility="collapsed")
        with col_bp2:
            datas_p = ["Todas as datas"] + sorted(pendentes["dt_transferencia"].unique().tolist(), reverse=True)
            fd_p = st.selectbox("Data", datas_p, key="rot_data_p", label_visibility="collapsed")

        df_p = pendentes.copy()
        if fd_p != "Todas as datas":
            df_p = df_p[df_p["dt_transferencia"] == fd_p]
        if busca_p:
            mask = df_p.apply(lambda r: busca_p.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_p = df_p[mask]

        cols_p = ["id", "dt_transferencia", "numnota", "numped", "nomecliente",
                  "nomesup", "praca", "destino", "pesobrutotot", "vltotal"]
        cols_p = [c for c in cols_p if c in df_p.columns]
        st.dataframe(df_p[cols_p], use_container_width=True, hide_index=True)
        st.caption(f"{len(df_p)} pendente(s)")

        # Formulário para informar placa
        st.markdown("---")
        st.markdown("**🚗 Informar Placa**")

        ids_p = df_p["id"].astype(str).tolist() if not df_p.empty else []
        if ids_p:
            col_sel, col_placa, col_ok = st.columns([1, 2, 1])
            with col_sel:
                sel_id = st.selectbox("Nota (ID)", ids_p, label_visibility="collapsed")
            with col_placa:
                nova_placa = st.text_input("Placa", placeholder="Ex: ABC-1234",
                                           key="rot_placa_input", label_visibility="collapsed").upper()
            with col_ok:
                confirmar_placa = st.button("✅ Confirmar", use_container_width=True)

            if sel_id:
                row_sel = df_p[df_p["id"].astype(str) == sel_id]
                if not row_sel.empty:
                    r = row_sel.iloc[0]
                    st.markdown(f"""
                    <div style="background:#1a1d24;border:1px solid #2a2f3a;border-radius:10px;
                                padding:.75rem 1rem;font-size:.83rem;color:#a0aab8;margin:.5rem 0">
                      📋 <strong style="color:#e8ecf3">{r['numnota']}</strong> ·
                      {r['nomecliente']} ·
                      <span style="color:#ff8f5e">{br(r['vltotal'])}</span> ·
                      Destino: {r.get('destino','—')}
                    </div>""", unsafe_allow_html=True)

            if confirmar_placa:
                if not nova_placa.strip():
                    st.error("⚠️ Informe a placa!")
                else:
                    with st.spinner("Salvando..."):
                        update_transferencia(int(sel_id), {
                            "placa":           nova_placa.strip(),
                            "dt_roteirizacao": date.today().isoformat(),
                            "status":          "roteirizado",
                        })
                    st.success(f"🚗 Placa **{nova_placa.strip()}** registrada!")
                    st.rerun()

    # ── ROTEIRIZADAS ──
    st.markdown("---")
    st.markdown("### ✅ Notas Roteirizadas")
    if roteiriz.empty:
        st.markdown('<div class="alert-info">📋 Nenhuma nota roteirizada ainda.</div>', unsafe_allow_html=True)
    else:
        busca_r = st.text_input("🔍 Buscar roteirizadas...", key="rot_busca_r", label_visibility="collapsed")
        df_r = roteiriz.copy()
        if busca_r:
            mask = df_r.apply(lambda r: busca_r.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_r = df_r[mask]

        cols_r = ["id", "dt_transferencia", "numnota", "numped", "nomecliente",
                  "nomesup", "praca", "destino", "pesobrutotot", "vltotal", "placa", "dt_roteirizacao"]
        cols_r = [c for c in cols_r if c in df_r.columns]
        st.dataframe(df_r[cols_r], use_container_width=True, hide_index=True)
        st.caption(f"{len(df_r)} roteirizada(s)")

        st.markdown("---")
        st.markdown("**↩️ Devolver para Pendente**")
        ids_r = df_r["id"].astype(str).tolist()
        if ids_r:
            col_dr, col_dbtn = st.columns([3, 1])
            with col_dr:
                del_rot_id = st.selectbox("ID para devolver", ids_r, key="rot_del", label_visibility="collapsed")
            with col_dbtn:
                if st.button("↩️ Devolver", use_container_width=True):
                    update_transferencia(int(del_rot_id), {
                        "placa": "", "dt_roteirizacao": "", "status": "pendente"
                    })
                    st.success("↩️ Nota devolvida para pendentes!")
                    st.rerun()