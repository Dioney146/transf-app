import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime
import io

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
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg:#080a0e; --sur:#0e1117; --sur2:#161b25; --sur3:#1e2535;
  --bdr:#1e2535; --bdr2:#2a3347;
  --acc:#f97316; --acc2:#fb923c; --acc3:#fed7aa;
  --grn:#10b981; --grn2:#34d399;
  --blu:#3b82f6; --blu2:#60a5fa;
  --pur:#8b5cf6; --yel:#f59e0b;
  --red:#ef4444; --red2:#fca5a5;
  --txt:#f1f5f9; --txt2:#94a3b8; --mut:#475569;
}
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"],.stApp{
  font-family:'Inter',sans-serif!important;
  background-color:var(--bg)!important;
  color:var(--txt)!important;
}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--sur)}
::-webkit-scrollbar-thumb{background:var(--bdr2);border-radius:99px}
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0a0d14 0%,#0e1117 100%)!important;
  border-right:1px solid var(--bdr)!important;
}
section[data-testid="stSidebar"]>div{padding-top:1.5rem!important}
.main .block-container{padding:1.5rem 2rem!important;max-width:1600px!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stDecoration"]{display:none}

/* HERO */
.hero{
  position:relative;border-radius:20px;padding:2.5rem 2.5rem 2rem;
  margin-bottom:2rem;overflow:hidden;border:1px solid var(--bdr2);
}
.hero-bg{
  position:absolute;inset:0;border-radius:20px;z-index:0;
  display:flex;align-items:center;justify-content:flex-end;
  padding-right:3rem;pointer-events:none;overflow:hidden;
}
.hero-bg-text{
  font-size:18rem;opacity:0.025;line-height:1;
  filter:blur(1px);user-select:none;
}
.hero-fat{background:linear-gradient(135deg,#0e1117 0%,#1a0d05 60%,#0e1117 100%)}
.hero-dash{background:linear-gradient(135deg,#0e1117 0%,#05101a 60%,#0e1117 100%)}
.hero-rot{background:linear-gradient(135deg,#0e1117 0%,#051a0e 60%,#0e1117 100%)}
.hero-content{position:relative;z-index:1}
.hero-tag{
  display:inline-flex;align-items:center;gap:6px;
  padding:4px 14px;border-radius:99px;font-size:.62rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.12em;margin-bottom:.75rem;
  font-family:'JetBrains Mono',monospace;
}
.tag-fat{background:rgba(249,115,22,.15);color:var(--acc2);border:1px solid rgba(249,115,22,.3)}
.tag-rot{background:rgba(16,185,129,.15);color:var(--grn2);border:1px solid rgba(16,185,129,.3)}
.tag-dash{background:rgba(59,130,246,.15);color:var(--blu2);border:1px solid rgba(59,130,246,.3)}
.hero-h1{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;line-height:1.1;color:var(--txt);margin:0 0 .5rem}
.hero-sub{font-size:.88rem;color:var(--txt2)}

/* KPI */
.kpi{
  background:var(--sur);border:1px solid var(--bdr);border-radius:16px;
  padding:1.4rem 1.6rem;position:relative;overflow:hidden;
  transition:border-color .2s,transform .2s;margin-bottom:.5rem;
}
.kpi:hover{border-color:var(--bdr2);transform:translateY(-2px)}
.kpi-glow{position:absolute;top:-30px;right:-30px;width:100px;height:100px;border-radius:50%;opacity:.07;filter:blur(20px)}
.kpi-icon{font-size:1.4rem;margin-bottom:.5rem}
.kpi-lbl{font-size:.63rem;font-weight:600;text-transform:uppercase;letter-spacing:.1em;color:var(--mut);margin-bottom:.35rem;font-family:'JetBrains Mono',monospace}
.kpi-val{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;line-height:1;color:var(--txt)}
.kpi-sub{font-size:.72rem;color:var(--txt2);margin-top:.3rem}
.kpi-bar{position:absolute;bottom:0;left:0;right:0;height:3px;border-radius:0 0 16px 16px}

/* CHART CARD */
.cc{background:var(--sur);border:1px solid var(--bdr);border-radius:16px;padding:1.4rem;margin-bottom:1rem}
.cc-title{font-family:'Syne',sans-serif;font-size:.82rem;font-weight:700;color:var(--txt2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:1rem}

/* TABLE */
.tbl-wrap{background:var(--sur);border:1px solid var(--bdr);border-radius:16px;overflow:hidden;margin-bottom:1.5rem}
.tbl-hd{padding:1rem 1.5rem;border-bottom:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;background:linear-gradient(90deg,var(--sur) 0%,var(--sur2) 100%)}
.tbl-title{font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;color:var(--txt)}
.tbl-badge{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--mut);background:var(--sur3);border-radius:99px;padding:3px 10px;border:1px solid var(--bdr2)}

/* SECTION DIV */
.sdiv{display:flex;align-items:center;gap:.75rem;margin:1.5rem 0 1rem}
.sdiv-line{flex:1;height:1px;background:var(--bdr)}
.sdiv-txt{font-family:'JetBrains Mono',monospace;font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--mut);white-space:nowrap}

/* ALERTS */
.al-s{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);color:var(--grn2);border-radius:10px;padding:.7rem 1rem;font-size:.83rem;margin:.5rem 0}
.al-e{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:var(--red2);border-radius:10px;padding:.7rem 1rem;font-size:.83rem;margin:.5rem 0}
.al-i{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.3);color:var(--blu2);border-radius:10px;padding:.7rem 1rem;font-size:.83rem;margin:.5rem 0}
.al-w{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:#fcd34d;border-radius:10px;padding:.7rem 1rem;font-size:.83rem;margin:.5rem 0}

/* ROAD BOX */
.road-box{background:linear-gradient(135deg,var(--sur2) 0%,#1a1205 100%);border:1px solid rgba(249,115,22,.25);border-left:3px solid var(--acc);border-radius:12px;padding:1.25rem;margin:.75rem 0}
.road-tit{font-family:'JetBrains Mono',monospace;font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--acc2);margin-bottom:.9rem}

/* NOTA CARD */
.nota-card{background:var(--sur2);border:1px solid var(--bdr);border-radius:10px;padding:.75rem 1rem;margin-bottom:.5rem;transition:border-color .15s}
.nota-card:hover{border-color:var(--bdr2)}
.placa-chip{display:inline-flex;align-items:center;gap:5px;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:8px;padding:3px 9px;font-family:'JetBrains Mono',monospace;font-size:.8rem;font-weight:700;color:#fcd34d;letter-spacing:.05em}

/* INPUTS */
.stTextInput>div>div>input,.stDateInput>div>div>input{
  background-color:var(--sur2)!important;color:var(--txt)!important;
  border:1px solid var(--bdr2)!important;border-radius:10px!important;
  font-family:'Inter',sans-serif!important;
}
.stTextInput>div>div>input:focus{border-color:var(--acc)!important;box-shadow:0 0 0 3px rgba(249,115,22,.1)!important}
.stSelectbox>div>div{background-color:var(--sur2)!important;border:1px solid var(--bdr2)!important;border-radius:10px!important}
.stTextArea textarea{background-color:var(--sur2)!important;color:var(--txt)!important;border:1px solid var(--bdr2)!important;border-radius:10px!important}
.stTextInput label,.stDateInput label,.stSelectbox label,.stTextArea label{color:var(--txt2)!important;font-size:.75rem!important;font-weight:600!important;text-transform:uppercase!important;letter-spacing:.07em!important}

/* BUTTONS */
.stButton>button{
  background:linear-gradient(135deg,var(--acc),#ea580c)!important;
  color:white!important;border:none!important;border-radius:10px!important;
  font-weight:700!important;font-family:'Inter',sans-serif!important;
  transition:all .2s!important;box-shadow:0 4px 15px rgba(249,115,22,.3)!important;
}
.stButton>button:hover{transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(249,115,22,.4)!important}
.stDownloadButton>button{background:var(--sur2)!important;color:var(--txt2)!important;border:1px solid var(--bdr2)!important;border-radius:10px!important;font-weight:600!important;box-shadow:none!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════════
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_client():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    return get_client().open_by_key(st.secrets["spreadsheet_id"])

def get_sheet(name):
    ss = get_spreadsheet()
    try:
        return ss.worksheet(name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=name, rows=5000, cols=20)

TCOLS = ["id","dt_transferencia","numped","numnota","nomecliente","nomesup",
         "praca","pesobrutotot","numcarregamento","vltotal","destino","obs",
         "placa_veiculo","placa_road","dt_roteirizacao","status","criado_em"]

def ensure_header():
    ws = get_sheet("transferencias")
    if not ws.row_values(1):
        ws.update("A1", [TCOLS])
    return ws

@st.cache_data(ttl=15, show_spinner=False)
def load_transferencias():
    ws = ensure_header()
    data = ws.get_all_records()
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
    row["criado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row.setdefault("status","pendente")
    row.setdefault("placa_veiculo","")
    row.setdefault("placa_road","")
    row.setdefault("dt_roteirizacao","")
    ws.append_row([str(row.get(c,"")) for c in TCOLS], value_input_option="USER_ENTERED")
    load_transferencias.clear()

def update_transf(tid, updates):
    ws = ensure_header()
    data = ws.get_all_values()
    if not data: return
    hdr = data[0]
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
    try:
        ws = get_sheet("ROAD")
        data = ws.get_all_records()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        df.columns = [str(c).upper().strip() for c in df.columns]
        for c in ["NUMNOTA","NUMPED"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.split(".").str[0].str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()

def buscar_nota(numnota):
    df = load_road()
    if df.empty: return None
    row = df[df["NUMNOTA"].astype(str)==numnota.strip()]
    if row.empty: return None
    r = row.iloc[0]
    def safe(col):
        v = r.get(col,"")
        if str(v) in ("nan","None","",None): return ""
        v = str(v)
        return v[:-2] if v.endswith(".0") else v
    try: peso = float(str(r.get("PESOBRUTOTOT","0")).replace(",","."))
    except: peso = 0.0
    try: vl = float(str(r.get("VLTOTAL","0")).replace(",","."))
    except: vl = 0.0
    praca = safe("PRAÇA") or safe("PRACA") or safe("PRAA") or safe("PRAÃ‡A")
    placa_road = safe("PLACA") or safe("PLACA_ROAD") or ""
    return {
        "numped": safe("NUMPED"), "numnota": safe("NUMNOTA"),
        "nomecliente": safe("NOMECLIENTE"), "nomesup": safe("NOMESUP"),
        "praca": praca, "pesobrutotot": peso,
        "numcarregamento": safe("NUMCARREGAMENTO"),
        "vltotal": vl, "destino": safe("DESTINO"),
        "placa_road": placa_road,
    }

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def br(v):
    try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

def fmt_date(s):
    if not s or str(s) in ("","nan","None"): return "—"
    try:
        p = str(s).split("-")
        if len(p)==3: return f"{p[2]}/{p[1]}/{p[0]}"
    except: pass
    return str(s)

def fmt_col(df, col="dt_transferencia"):
    df = df.copy()
    if col in df.columns:
        df[col] = df[col].apply(fmt_date)
    return df

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:0 .5rem 1.5rem">
      <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;
        background:linear-gradient(135deg,#f97316,#fb923c);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-.02em">
        🚛 TRANSF
      </div>
      <div style="font-size:.7rem;color:#475569;font-family:'JetBrains Mono',monospace;margin-top:2px">
        Sistema de Transferências
      </div>
    </div>
    """, unsafe_allow_html=True)

    pagina = st.radio("Nav", [
        "📊  Dashboard",
        "➕  Nova Transferência",
        "📋  Histórico",
        "🗺️  Roteirização",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div style="font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#475569;margin-bottom:.5rem">📅 Filtrar por Data</div>', unsafe_allow_html=True)

    data_filtro = st.date_input("Data", value=date.today(), label_visibility="collapsed", key="data_global")
    data_str = data_filtro.isoformat()

    ver_todas = st.checkbox("📋 Ver todas as datas", key="ver_todas")

    st.markdown("---")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        load_transferencias.clear()
        load_road.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(f'<div style="font-size:.7rem;color:#475569;line-height:2;font-family:JetBrains Mono,monospace">🟢 Online<br>📅 {date.today().strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DADOS
# ══════════════════════════════════════════════════════════════════════════════
df_all = load_transferencias()
df = df_all.copy() if ver_todas else (df_all[df_all["dt_transferencia"]==data_str].copy() if not df_all.empty else pd.DataFrame(columns=TCOLS))
periodo_txt = "Todas as datas" if ver_todas else fmt_date(data_str)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "📊  Dashboard":
    st.markdown(f"""
    <div class="hero hero-dash">
      <div class="hero-bg"><div class="hero-bg-text">📊</div></div>
      <div class="hero-content">
        <div class="hero-tag tag-dash">📊 Visão Geral</div>
        <div class="hero-h1">Dashboard</div>
        <div class="hero-sub">Período: <strong style="color:#60a5fa">{periodo_txt}</strong></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    n  = len(df)
    vt = df["vltotal"].sum() if not df.empty else 0
    pt = df["pesobrutotot"].sum() if not df.empty else 0
    nd = df["nomecliente"].nunique() if not df.empty else 0
    np = int((df["status"]=="pendente").sum()) if not df.empty else 0
    nr = int((df["status"]=="roteirizado").sum()) if not df.empty else 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col,icon,lbl,val,sub,clr in [
        (c1,"📦","Notas",str(n),"transferências","#f97316"),
        (c2,"💰","Valor Total",br(vt),"período","#3b82f6"),
        (c3,"⚖️","Peso",f"{pt:,.0f} kg","bruto","#8b5cf6"),
        (c4,"🏪","Clientes",str(nd),"distintos","#10b981"),
        (c5,"⏳","Pendentes",str(np),"sem placa","#ef4444"),
        (c6,"✅","Roteiriz.",str(nr),"com placa","#10b981"),
    ]:
        with col:
            st.markdown(f"""<div class="kpi">
              <div class="kpi-glow" style="background:{clr}"></div>
              <div class="kpi-icon">{icon}</div>
              <div class="kpi-lbl">{lbl}</div>
              <div class="kpi-val">{val}</div>
              <div class="kpi-sub">{sub}</div>
              <div class="kpi-bar" style="background:linear-gradient(90deg,{clr}88,{clr}22)"></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df.empty:
        try:
            import plotly.graph_objects as go
            T = dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(color="#94a3b8",family="Inter"),
                     margin=dict(l=10,r=10,t=30,b=10))
            GC = "#1e2535"

            # Row 1
            r1a, r1b = st.columns([3,2])
            with r1a:
                st.markdown('<div class="cc"><div class="cc-title">📅 Valor por Data de Transferência</div>', unsafe_allow_html=True)
                if ver_todas and not df.empty:
                    pd_ = df.groupby("dt_transferencia").agg(valor=("vltotal","sum")).reset_index().sort_values("dt_transferencia").tail(30)
                    pd_["dt_f"] = pd_["dt_transferencia"].apply(fmt_date)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=pd_["dt_f"],y=pd_["valor"],
                        marker=dict(color=pd_["valor"],colorscale=[[0,"#7c2d12"],[0.5,"#f97316"],[1,"#fed7aa"]],showscale=False),
                        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>"))
                    fig.add_trace(go.Scatter(x=pd_["dt_f"],y=pd_["valor"],mode="lines",
                        line=dict(color="#fb923c",width=2,dash="dot"),showlegend=False))
                    fig.update_layout(**T,height=260,xaxis=dict(gridcolor=GC),yaxis=dict(gridcolor=GC,tickformat=",.0f"))
                    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
                else:
                    st.markdown(f'<div class="al-i">Data selecionada: <strong>{fmt_date(data_str)}</strong> — {n} nota(s) — {br(vt)}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with r1b:
                st.markdown('<div class="cc"><div class="cc-title">🔄 Status das Notas</div>', unsafe_allow_html=True)
                if n > 0:
                    fig2 = go.Figure(go.Pie(
                        labels=["⏳ Pendentes","✅ Roteirizadas"],
                        values=[np,nr],hole=0.6,
                        marker=dict(colors=["#ef4444","#10b981"],line=dict(color="#0e1117",width=3)),
                        textinfo="percent+value",
                        hovertemplate="<b>%{label}</b><br>%{value} notas<extra></extra>"))
                    fig2.update_layout(**T,height=260,
                        legend=dict(orientation="h",yanchor="bottom",y=-0.2,xanchor="center",x=0.5))
                    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
                else:
                    st.markdown('<div class="al-i">Sem dados.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Row 2
            r2a, r2b = st.columns(2)
            with r2a:
                st.markdown('<div class="cc"><div class="cc-title">🏆 Top Clientes por Valor</div>', unsafe_allow_html=True)
                cli = df.groupby("nomecliente")["vltotal"].sum().sort_values(ascending=True).tail(8).reset_index()
                if not cli.empty:
                    fig3 = go.Figure(go.Bar(
                        x=cli["vltotal"],y=cli["nomecliente"],orientation="h",
                        marker=dict(color=cli["vltotal"],colorscale=[[0,"#1e3a5f"],[0.5,"#3b82f6"],[1,"#bfdbfe"]],showscale=False),
                        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"))
                    fig3.update_layout(**T,height=260,xaxis=dict(gridcolor=GC,tickformat=",.0f"),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig3,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            with r2b:
                st.markdown('<div class="cc"><div class="cc-title">👤 Valor por Supervisor</div>', unsafe_allow_html=True)
                sup = df.groupby("nomesup")["vltotal"].sum().sort_values(ascending=False).reset_index()
                if not sup.empty:
                    COLS_P = ["#8b5cf6","#a78bfa","#c4b5fd","#7c3aed","#6d28d9","#5b21b6"]
                    fig4 = go.Figure(go.Pie(
                        labels=sup["nomesup"],values=sup["vltotal"],hole=0.45,
                        marker=dict(colors=COLS_P[:len(sup)],line=dict(color="#0e1117",width=2)),
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"))
                    fig4.update_layout(**T,height=260,
                        legend=dict(orientation="h",yanchor="bottom",y=-0.25,xanchor="center",x=0.5))
                    st.plotly_chart(fig4,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            # Row 3
            r3a, r3b = st.columns([2,1])
            with r3a:
                st.markdown('<div class="cc"><div class="cc-title">📍 Top Destinos por Valor</div>', unsafe_allow_html=True)
                dest = df.groupby("destino")["vltotal"].sum().sort_values(ascending=True).tail(10).reset_index()
                if not dest.empty:
                    fig5 = go.Figure(go.Bar(
                        x=dest["vltotal"],y=dest["destino"],orientation="h",
                        marker=dict(color=dest["vltotal"],colorscale=[[0,"#064e3b"],[0.5,"#10b981"],[1,"#a7f3d0"]],showscale=False),
                        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"))
                    fig5.update_layout(**T,height=260,xaxis=dict(gridcolor=GC,tickformat=",.0f"),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig5,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            with r3b:
                st.markdown('<div class="cc"><div class="cc-title">🏙️ Por Praça</div>', unsafe_allow_html=True)
                praca = df.groupby("praca")["vltotal"].sum().sort_values(ascending=False).head(8).reset_index()
                if not praca.empty:
                    COLS_O = ["#f97316","#fb923c","#fdba74","#fed7aa","#ea580c","#c2410c","#9a3412","#7c2d12"]
                    fig6 = go.Figure(go.Pie(
                        labels=praca["praca"],values=praca["vltotal"],hole=0.45,
                        marker=dict(colors=COLS_O[:len(praca)],line=dict(color="#0e1117",width=2)),
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"))
                    fig6.update_layout(**T,height=260,
                        legend=dict(orientation="h",yanchor="bottom",y=-0.3,xanchor="center",x=0.5))
                    st.plotly_chart(fig6,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

            # Row 4 — peso por data
            if ver_todas:
                st.markdown('<div class="cc"><div class="cc-title">⚖️ Peso Total por Data (kg)</div>', unsafe_allow_html=True)
                pp = df.groupby("dt_transferencia").agg(peso=("pesobrutotot","sum"),qtd=("id","count")).reset_index().sort_values("dt_transferencia").tail(30)
                pp["dt_f"] = pp["dt_transferencia"].apply(fmt_date)
                fig7 = go.Figure()
                fig7.add_trace(go.Bar(x=pp["dt_f"],y=pp["qtd"],name="Qtd Notas",yaxis="y2",
                    marker=dict(color="rgba(59,130,246,0.3)"),hovertemplate="<b>%{x}</b><br>%{y} notas<extra></extra>"))
                fig7.add_trace(go.Scatter(x=pp["dt_f"],y=pp["peso"],name="Peso kg",
                    line=dict(color="#10b981",width=2.5),fill="tozeroy",fillcolor="rgba(16,185,129,0.08)",
                    hovertemplate="<b>%{x}</b><br>%{y:,.0f} kg<extra></extra>"))
                fig7.update_layout(**T,height=220,
                    xaxis=dict(gridcolor=GC),
                    yaxis=dict(gridcolor=GC,title="Peso (kg)"),
                    yaxis2=dict(overlaying="y",side="right",showgrid=False,title="Qtd"),
                    legend=dict(orientation="h",yanchor="bottom",y=1,xanchor="right",x=1))
                st.plotly_chart(fig7,use_container_width=True,config={"displayModeBar":False})
                st.markdown('</div>', unsafe_allow_html=True)

        except ImportError:
            st.info("Adicione `plotly` ao requirements.txt para ativar os gráficos.")

    # TABELA
    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📋 Registro de Transferências</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

    cf1,cf2 = st.columns([3,1])
    with cf1: busca = st.text_input("🔍 Buscar...", key="db", label_visibility="collapsed", placeholder="Nota, cliente, destino, placa...")
    with cf2: fst = st.selectbox("Status",["Todos","pendente","roteirizado"],key="dst",label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst!="Todos": df_s=df_s[df_s["status"]==fst]
        if busca:
            m = df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_s = df_s[m]

    if not df_s.empty:
        out=io.BytesIO()
        with pd.ExcelWriter(out,engine="openpyxl") as w: df_s.to_excel(w,index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel",out,file_name=f"transf_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    df_d = fmt_col(df_s)
    if "dt_roteirizacao" in df_d.columns: df_d=fmt_col(df_d,"dt_roteirizacao")

    SHOW_COLS = [c for c in ["dt_transferencia","numnota","numped","nomecliente","nomesup",
                              "praca","destino","pesobrutotot","vltotal","placa_veiculo","placa_road","status"] if c in df_d.columns]

    st.markdown(f"""<div class="tbl-wrap">
      <div class="tbl-hd"><span class="tbl-title">Transferências</span><span class="tbl-badge">{len(df_s)} reg.</span></div>
    </div>""", unsafe_allow_html=True)

    st.dataframe(df_d[SHOW_COLS].sort_values("dt_transferencia",ascending=False) if not df_d.empty else df_d,
        use_container_width=True, hide_index=True,
        column_config={
            "dt_transferencia": st.column_config.TextColumn("📅 Data",width=95),
            "numnota":          st.column_config.TextColumn("🧾 Nota",width=90),
            "numped":           st.column_config.TextColumn("📋 Pedido",width=90),
            "nomecliente":      st.column_config.TextColumn("👤 Cliente",width=200),
            "nomesup":          st.column_config.TextColumn("👔 Supervisor",width=130),
            "praca":            st.column_config.TextColumn("🏙️ Praça",width=90),
            "destino":          st.column_config.TextColumn("📍 Destino",width=130),
            "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso kg",format="%.3f",width=95),
            "vltotal":          st.column_config.NumberColumn("💰 Valor R$",format="R$ %.2f",width=120),
            "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.",width=110),
            "placa_road":       st.column_config.TextColumn("📋 Placa ROAD",width=110),
            "status":           st.column_config.TextColumn("📌 Status",width=100),
        })

    if not df.empty:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🗑️ Excluir</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        ids = df["id"].astype(str).tolist()
        cd1,cd2 = st.columns([3,1])
        with cd1: del_id = st.selectbox("ID",["—"]+ids,label_visibility="collapsed")
        with cd2:
            if del_id!="—" and st.button("🗑️ Excluir",type="secondary"):
                delete_transf(int(del_id)); st.success("✅ Excluído!"); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# NOVA TRANSFERÊNCIA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "➕  Nova Transferência":
    st.markdown(f"""
    <div class="hero hero-fat">
      <div class="hero-bg"><div class="hero-bg-text">🧾</div></div>
      <div class="hero-content">
        <div class="hero-tag tag-fat">🧾 Faturamento</div>
        <div class="hero-h1">Nova Transferência</div>
        <div class="hero-sub">Registre a nota — data: <strong style="color:#fb923c">{fmt_date(data_str)}</strong></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_f, col_s = st.columns([1.3,0.7])

    with col_f:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📅 Data & Nota</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        cd,cn,cb = st.columns([1,2,1])
        with cd: dt_t = st.date_input("Data",value=data_filtro,label_visibility="visible")
        with cn: nota_inp = st.text_input("Número da Nota",placeholder="Ex: 398234",key="nn")
        with cb:
            st.markdown("<br>",unsafe_allow_html=True)
            buscar_btn = st.button("🔍 Buscar",use_container_width=True)

        if "cur" not in st.session_state: st.session_state.cur = None

        if buscar_btn and nota_inp.strip():
            with st.spinner("Consultando ROAD..."):
                r = buscar_nota(nota_inp.strip())
            if r:
                st.session_state.cur = r
                st.markdown('<div class="al-s">✅ Nota encontrada! Dados preenchidos automaticamente.</div>',unsafe_allow_html=True)
            else:
                st.session_state.cur = None
                st.markdown(f'<div class="al-e">❌ Nota "{nota_inp.strip()}" não encontrada na base ROAD.</div>',unsafe_allow_html=True)

        cur = st.session_state.cur
        if cur:
            st.markdown('<div class="road-box"><div class="road-tit">✅ Dados da Base ROAD</div></div>',unsafe_allow_html=True)
            a,b,c_ = st.columns(3)
            with a: st.text_input("📋 Pedido",value=cur["numped"] or "—",disabled=True)
            with b: st.text_input("🧾 Nota Fiscal",value=cur["numnota"],disabled=True)
            with c_: st.text_input("📦 Carregamento",value=cur["numcarregamento"],disabled=True)
            a2,b2,c2 = st.columns(3)
            with a2: st.text_input("👤 Cliente",value=cur["nomecliente"],disabled=True)
            with b2: st.text_input("👔 Supervisor",value=cur["nomesup"],disabled=True)
            with c2: st.text_input("🏙️ Praça",value=cur["praca"] or "—",disabled=True)
            a3,b3,c3 = st.columns(3)
            with a3: st.text_input("📍 Destino",value=cur["destino"],disabled=True)
            with b3: st.text_input("⚖️ Peso (kg)",value=f"{cur['pesobrutotot']:.3f}".replace(".",","),disabled=True)
            with c3: st.text_input("💰 Valor Total",value=br(cur["vltotal"]),disabled=True)
            if cur.get("placa_road"):
                st.markdown(f'<div class="al-w">🚗 Placa ROAD registrada: <strong>{cur["placa_road"]}</strong></div>',unsafe_allow_html=True)
            obs = st.text_area("💬 Observação (opcional)",placeholder="Observação adicional...",key="obs")
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência",type="primary",use_container_width=True):
                dt_s = dt_t.isoformat()
                if check_dup(cur["numnota"],dt_s):
                    st.markdown(f'<div class="al-e">❌ Nota {cur["numnota"]} já registrada em {fmt_date(dt_s)}.</div>',unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        append_transf({
                            "dt_transferencia":dt_s,"numped":cur["numped"],"numnota":cur["numnota"],
                            "nomecliente":cur["nomecliente"],"nomesup":cur["nomesup"],"praca":cur["praca"],
                            "pesobrutotot":cur["pesobrutotot"],"numcarregamento":cur["numcarregamento"],
                            "vltotal":cur["vltotal"],"destino":cur["destino"],
                            "placa_road":cur.get("placa_road",""),"obs":obs,
                        })
                    st.success(f"✅ Transferência registrada! Nota **{cur['numnota']}** pendente.")
                    st.session_state.cur = None; st.balloons(); st.rerun()

    with col_s:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📅 Notas do Dia</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        dt_show = (st.session_state.get("cur") and data_str) or data_str
        df_hj = df_all[df_all["dt_transferencia"]==data_str] if not df_all.empty else pd.DataFrame()
        if df_hj.empty:
            st.markdown('<div class="al-i">📭 Nenhuma nota nesta data.</div>',unsafe_allow_html=True)
        else:
            tv = df_hj["vltotal"].sum()
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:.4rem 0;margin-bottom:.5rem;border-bottom:1px solid #1e2535"><span style="color:#94a3b8;font-size:.78rem">{len(df_hj)} notas</span><span style="color:#fb923c;font-weight:700;font-size:.85rem">{br(tv)}</span></div>', unsafe_allow_html=True)
            for _,row in df_hj.iterrows():
                pl = row.get("placa_veiculo","")
                pl_h = f'<span class="placa-chip">🚗 {pl}</span>' if pl else '<span style="color:#ef4444;font-size:.72rem">⏳ Pendente</span>'
                st.markdown(f"""<div class="nota-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f1f5f9;font-size:.88rem">{row['numnota']}</div>
                      <div style="color:#94a3b8;font-size:.76rem;margin-top:2px">{str(row.get('nomecliente',''))[:28]}</div>
                    </div>
                    <div style="text-align:right">
                      <div style="color:#fb923c;font-weight:700;font-size:.82rem">{br(row['vltotal'])}</div>
                      {pl_h}
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:var(--sur2);border:1px solid var(--bdr);border-radius:12px;padding:1rem;margin-top:1rem">
          <div style="font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:#475569;margin-bottom:.6rem;font-family:'JetBrains Mono',monospace">💡 Como usar</div>
          <ol style="font-size:.81rem;color:#94a3b8;padding-left:1.1rem;line-height:2.3">
            <li>Selecione a <strong style="color:#f1f5f9">data</strong></li>
            <li>Digite o <strong style="color:#f1f5f9">número da nota</strong></li>
            <li>Clique <strong style="color:#f97316">Buscar</strong></li>
            <li>Dados preenchidos <strong style="color:#f97316">automaticamente</strong></li>
            <li>Clique <strong style="color:#f1f5f9">Confirmar Transferência</strong></li>
          </ol>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":
    st.markdown(f"""
    <div class="hero hero-fat">
      <div class="hero-bg"><div class="hero-bg-text">📋</div></div>
      <div class="hero-content">
        <div class="hero-tag tag-fat">🧾 Faturamento</div>
        <div class="hero-h1">Histórico</div>
        <div class="hero-sub">Período: <strong style="color:#fb923c">{periodo_txt}</strong> — {len(df)} registro(s)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cf1,cf2,cf3 = st.columns([3,1,1])
    with cf1: busca = st.text_input("🔍 Buscar...",key="hb",label_visibility="collapsed",placeholder="Nota, cliente, placa...")
    with cf2: fst = st.selectbox("Status",["Todos","pendente","roteirizado"],key="hst",label_visibility="collapsed")
    with cf3:
        sups = ["Todos"]+(sorted(df["nomesup"].dropna().unique().tolist()) if not df.empty else [])
        fsup = st.selectbox("Supervisor",sups,key="hsup",label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst!="Todos": df_s=df_s[df_s["status"]==fst]
        if fsup!="Todos": df_s=df_s[df_s["nomesup"]==fsup]
        if busca:
            m=df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(),axis=1)
            df_s=df_s[m]

    if not df_s.empty:
        out=io.BytesIO()
        with pd.ExcelWriter(out,engine="openpyxl") as w: df_s.to_excel(w,index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel",out,file_name=f"historico_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    df_d = fmt_col(df_s)
    if "dt_roteirizacao" in df_d.columns: df_d=fmt_col(df_d,"dt_roteirizacao")
    HCOLS = [c for c in ["dt_transferencia","numnota","numped","nomecliente","nomesup","praca",
                          "destino","pesobrutotot","vltotal","placa_veiculo","placa_road",
                          "status","obs","dt_roteirizacao"] if c in df_d.columns]
    st.markdown(f"""<div class="tbl-wrap">
      <div class="tbl-hd"><span class="tbl-title">📋 Todas as Transferências</span><span class="tbl-badge">{len(df_s)} reg.</span></div>
    </div>""", unsafe_allow_html=True)
    st.dataframe(df_d[HCOLS].sort_values("dt_transferencia",ascending=False) if not df_d.empty else df_d,
        use_container_width=True,hide_index=True,
        column_config={
            "dt_transferencia": st.column_config.TextColumn("📅 Data",width=95),
            "numnota":          st.column_config.TextColumn("🧾 Nota",width=90),
            "numped":           st.column_config.TextColumn("📋 Pedido",width=90),
            "nomecliente":      st.column_config.TextColumn("👤 Cliente",width=190),
            "nomesup":          st.column_config.TextColumn("👔 Supervisor",width=120),
            "praca":            st.column_config.TextColumn("🏙️ Praça",width=90),
            "destino":          st.column_config.TextColumn("📍 Destino",width=130),
            "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso kg",format="%.3f",width=95),
            "vltotal":          st.column_config.NumberColumn("💰 Valor R$",format="R$ %.2f",width=120),
            "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.",width=110),
            "placa_road":       st.column_config.TextColumn("📋 Placa ROAD",width=110),
            "status":           st.column_config.TextColumn("📌 Status",width=100),
            "obs":              st.column_config.TextColumn("💬 Obs",width=150),
            "dt_roteirizacao":  st.column_config.TextColumn("🗺️ Dt. Roteiriz.",width=110),
        })

# ══════════════════════════════════════════════════════════════════════════════
# ROTEIRIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗺️  Roteirização":
    st.markdown(f"""
    <div class="hero hero-rot">
      <div class="hero-bg"><div class="hero-bg-text">🗺️</div></div>
      <div class="hero-content">
        <div class="hero-tag tag-rot">🗺️ Roteirização</div>
        <div class="hero-h1">Roteirizar Notas</div>
        <div class="hero-sub">Período: <strong style="color:#34d399">{periodo_txt}</strong></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pend = df[df["status"]=="pendente"] if not df.empty else pd.DataFrame()
    rote = df[df["status"]=="roteirizado"] if not df.empty else pd.DataFrame()

    c1,c2,c3,c4 = st.columns(4)
    for col,icon,lbl,val,sub,clr in [
        (c1,"⏳","Pendentes",len(pend),br(pend["vltotal"].sum()) if not pend.empty else "R$ 0,00","#ef4444"),
        (c2,"✅","Roteirizadas",len(rote),br(rote["vltotal"].sum()) if not rote.empty else "R$ 0,00","#10b981"),
        (c3,"⚖️","Peso Pend.",f"{pend['pesobrutotot'].sum():.0f} kg" if not pend.empty else "0 kg","peso","#f59e0b"),
        (c4,"⚖️","Peso Rot.",f"{rote['pesobrutotot'].sum():.0f} kg" if not rote.empty else "0 kg","peso","#8b5cf6"),
    ]:
        with col:
            st.markdown(f"""<div class="kpi">
              <div class="kpi-glow" style="background:{clr}"></div>
              <div class="kpi-icon">{icon}</div>
              <div class="kpi-lbl">{lbl}</div>
              <div class="kpi-val" style="color:{clr}">{val}</div>
              <div class="kpi-sub">{sub}</div>
              <div class="kpi-bar" style="background:linear-gradient(90deg,{clr}88,{clr}22)"></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # PENDENTES
    st.markdown(f"""<div class="tbl-wrap" style="border-color:rgba(239,68,68,.25)">
      <div class="tbl-hd" style="border-bottom-color:rgba(239,68,68,.2)">
        <span class="tbl-title" style="color:#fca5a5">⏳ Pendentes</span>
        <span class="tbl-badge">{len(pend)}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div class="al-s">✅ Nenhuma nota pendente!</div>',unsafe_allow_html=True)
    else:
        pb1,pb2 = st.columns([3,1])
        with pb1: bp = st.text_input("🔍 Buscar pendentes...",key="rbp",label_visibility="collapsed")
        with pb2:
            dp_opts = ["Todas"]+sorted(pend["dt_transferencia"].unique().tolist(),reverse=True)
            fdp = st.selectbox("Data",dp_opts,key="rdp",label_visibility="collapsed")
        df_p = pend.copy()
        if fdp!="Todas": df_p=df_p[df_p["dt_transferencia"]==fdp]
        if bp:
            m=df_p.apply(lambda r: bp.lower() in " ".join(str(v) for v in r).lower(),axis=1)
            df_p=df_p[m]
        PCOLS=[c for c in ["id","dt_transferencia","numnota","numped","nomecliente","nomesup","praca","destino","pesobrutotot","vltotal","placa_road"] if c in df_p.columns]
        df_pd=fmt_col(df_p)
        st.dataframe(df_pd[PCOLS].sort_values("dt_transferencia",ascending=False),
            use_container_width=True,hide_index=True,
            column_config={
                "id":               st.column_config.NumberColumn("ID",width=55),
                "dt_transferencia": st.column_config.TextColumn("📅 Data",width=95),
                "numnota":          st.column_config.TextColumn("🧾 Nota",width=90),
                "numped":           st.column_config.TextColumn("📋 Pedido",width=90),
                "nomecliente":      st.column_config.TextColumn("👤 Cliente",width=190),
                "nomesup":          st.column_config.TextColumn("👔 Supervisor",width=120),
                "praca":            st.column_config.TextColumn("🏙️ Praça",width=90),
                "destino":          st.column_config.TextColumn("📍 Destino",width=130),
                "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso kg",format="%.3f",width=95),
                "vltotal":          st.column_config.NumberColumn("💰 Valor R$",format="R$ %.2f",width=120),
                "placa_road":       st.column_config.TextColumn("📋 Placa ROAD",width=110),
            })
        st.caption(f"{len(df_p)} pendente(s)")

        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🚗 Informar Placa</div><div class="sdiv-line"></div></div>',unsafe_allow_html=True)
        ids_p = df_p["id"].astype(str).tolist()
        if ids_p:
            cs,cp,cok = st.columns([1.5,2,1])
            with cs: sel = st.selectbox("Nota (ID)",ids_p,label_visibility="visible")
            with cp: nova_pl = st.text_input("Placa do Veículo",placeholder="Ex: ABC-1234",key="rpl").upper()
            with cok:
                st.markdown("<br>",unsafe_allow_html=True)
                conf = st.button("✅ Confirmar",use_container_width=True)
            if sel:
                rs = df_p[df_p["id"].astype(str)==sel]
                if not rs.empty:
                    r=rs.iloc[0]
                    pr=r.get("placa_road","")
                    pr_h=f'&nbsp;·&nbsp;<span class="placa-chip">📋 ROAD: {pr}</span>' if pr else ""
                    st.markdown(f"""<div style="background:var(--sur2);border:1px solid var(--bdr);border-radius:10px;padding:.7rem 1rem;font-size:.82rem;display:flex;align-items:center;gap:.75rem;margin:.4rem 0">
                      <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f1f5f9">{r['numnota']}</span>
                      <span style="color:#94a3b8">{r.get('nomecliente','')}</span>
                      <span style="color:#fb923c;font-weight:700">{br(r['vltotal'])}</span>
                      <span style="color:#94a3b8">📍 {r.get('destino','—')}</span>{pr_h}
                    </div>""",unsafe_allow_html=True)
            if conf:
                if not nova_pl.strip():
                    st.markdown('<div class="al-e">⚠️ Informe a placa!</div>',unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        update_transf(int(sel),{"placa_veiculo":nova_pl.strip(),"dt_roteirizacao":date.today().isoformat(),"status":"roteirizado"})
                    st.success(f"🚗 Placa **{nova_pl.strip()}** registrada!"); st.rerun()

    # ROTEIRIZADAS
    st.markdown(f"""<div class="tbl-wrap" style="margin-top:1.5rem;border-color:rgba(16,185,129,.25)">
      <div class="tbl-hd" style="border-bottom-color:rgba(16,185,129,.2)">
        <span class="tbl-title" style="color:#34d399">✅ Roteirizadas</span>
        <span class="tbl-badge">{len(rote)}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if rote.empty:
        st.markdown('<div class="al-i">📋 Nenhuma nota roteirizada neste período.</div>',unsafe_allow_html=True)
    else:
        br_ = st.text_input("🔍 Buscar roteirizadas...",key="rbr",label_visibility="collapsed")
        df_r = rote.copy()
        if br_:
            m=df_r.apply(lambda r: br_.lower() in " ".join(str(v) for v in r).lower(),axis=1)
            df_r=df_r[m]
        RCOLS=[c for c in ["id","dt_transferencia","numnota","numped","nomecliente","nomesup","praca","destino","pesobrutotot","vltotal","placa_veiculo","placa_road","dt_roteirizacao"] if c in df_r.columns]
        df_rd=fmt_col(df_r)
        if "dt_roteirizacao" in df_rd.columns: df_rd=fmt_col(df_rd,"dt_roteirizacao")
        st.dataframe(df_rd[RCOLS].sort_values("dt_transferencia",ascending=False),
            use_container_width=True,hide_index=True,
            column_config={
                "id":               st.column_config.NumberColumn("ID",width=55),
                "dt_transferencia": st.column_config.TextColumn("📅 Data",width=95),
                "numnota":          st.column_config.TextColumn("🧾 Nota",width=90),
                "numped":           st.column_config.TextColumn("📋 Pedido",width=90),
                "nomecliente":      st.column_config.TextColumn("👤 Cliente",width=190),
                "nomesup":          st.column_config.TextColumn("👔 Supervisor",width=120),
                "praca":            st.column_config.TextColumn("🏙️ Praça",width=90),
                "destino":          st.column_config.TextColumn("📍 Destino",width=130),
                "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso kg",format="%.3f",width=95),
                "vltotal":          st.column_config.NumberColumn("💰 Valor R$",format="R$ %.2f",width=120),
                "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.",width=110),
                "placa_road":       st.column_config.TextColumn("📋 Placa ROAD",width=110),
                "dt_roteirizacao":  st.column_config.TextColumn("🗺️ Dt. Roteiriz.",width=110),
            })
        st.caption(f"{len(df_r)} roteirizada(s)")
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">↩️ Devolver para Pendente</div><div class="sdiv-line"></div></div>',unsafe_allow_html=True)
        ids_r=df_r["id"].astype(str).tolist()
        if ids_r:
            cd1,cd2=st.columns([3,1])
            with cd1: dvid=st.selectbox("ID",ids_r,key="rdv",label_visibility="collapsed")
            with cd2:
                if st.button("↩️ Devolver",use_container_width=True):
                    update_transf(int(dvid),{"placa_veiculo":"","dt_roteirizacao":"","status":"pendente"})
                    st.success("↩️ Devolvida para pendentes!"); st.rerun()
