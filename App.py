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
# CSS — REDESIGN COMPLETO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ── VARIÁVEIS ── */
:root {
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
}

/* ── BASE ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
  font-family: 'Outfit', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--txt) !important;
}

/* ── BACKGROUND PATTERN (caminhões e rotas) ── */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    radial-gradient(ellipse 80% 40% at 20% 10%, rgba(249,115,22,0.06) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 80% 80%, rgba(59,130,246,0.05) 0%, transparent 60%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' opacity='0.018'%3E%3Ctext x='10' y='40' font-size='28' fill='%23ffffff'%3E🚛%3C/text%3E%3Ctext x='65' y='90' font-size='18' fill='%23ffffff'%3E📦%3C/text%3E%3Ctext x='5' y='110' font-size='16' fill='%23ffffff'%3E🛣️%3C/text%3E%3C/svg%3E");
  background-size: auto, auto, 120px 120px;
}

/* Grid de estradas no fundo */
.stApp::after {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(249,115,22,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(249,115,22,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black 30%, transparent 80%);
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(249,115,22,0.3); border-radius: 99px; }

/* ── HIDE STREAMLIT DEFAULT ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
section[data-testid="stSidebar"] { display: none !important; }

/* ── MAIN CONTAINER ── */
.main .block-container {
  padding: 0 !important;
  max-width: 100% !important;
  position: relative;
  z-index: 1;
}

/* ══════════════════════════════════
   TOP NAV BAR
══════════════════════════════════ */
.topnav {
  position: sticky;
  top: 0;
  z-index: 999;
  background: rgba(11, 15, 26, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--bdr2);
  padding: 0 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}

.topnav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.topnav-logo {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #f97316, #ea580c);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  box-shadow: 0 4px 16px rgba(249,115,22,0.4);
  flex-shrink: 0;
}

.topnav-name {
  font-family: 'Outfit', sans-serif;
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #f97316, #fb923c);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.topnav-sub {
  font-size: 0.65rem;
  color: var(--mut);
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  line-height: 1;
  margin-top: 1px;
}

.topnav-links {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--txt2);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  font-family: 'Outfit', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.nav-item:hover {
  color: var(--txt);
  background: rgba(255,255,255,0.05);
  border-color: var(--bdr2);
}

.nav-item.active {
  color: var(--acc2);
  background: rgba(249,115,22,0.1);
  border-color: rgba(249,115,22,0.25);
}

.topnav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-date {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--txt2);
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 6px 12px;
}

.nav-status {
  width: 8px; height: 8px;
  background: var(--grn);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--grn);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ══════════════════════════════════
   PAGE CONTENT WRAPPER
══════════════════════════════════ */
.page-wrap {
  padding: 2rem 2.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

/* ══════════════════════════════════
   PAGE HEADER
══════════════════════════════════ */
.page-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--acc2);
  margin-bottom: 0.4rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-eyebrow::before {
  content: '';
  display: inline-block;
  width: 20px;
  height: 2px;
  background: var(--acc);
  border-radius: 99px;
}

.page-title {
  font-family: 'Outfit', sans-serif;
  font-size: 2.4rem;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: var(--txt);
  line-height: 1;
}

.page-period {
  font-size: 0.82rem;
  color: var(--txt2);
  margin-top: 0.4rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.period-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(59,130,246,0.1);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 99px;
  padding: 3px 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--blu2);
}

/* ══════════════════════════════════
   KPI CARDS — DASHBOARD
══════════════════════════════════ */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 2rem;
}

.kpi-card {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 16px;
  padding: 1.4rem 1.6rem 1.2rem;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-3px);
  border-color: var(--bdr2);
  box-shadow: 0 12px 32px rgba(0,0,0,0.3);
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: 16px 16px 0 0;
}

.kpi-card.orange::before { background: linear-gradient(90deg, #f97316, #fb923c); }
.kpi-card.blue::before   { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.kpi-card.purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.kpi-card.green::before  { background: linear-gradient(90deg, #10b981, #34d399); }

.kpi-card-bg {
  position: absolute;
  bottom: -20px; right: -20px;
  font-size: 5rem;
  opacity: 0.04;
  pointer-events: none;
  filter: blur(1px);
}

.kpi-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--mut);
  margin-bottom: 0.75rem;
}

.kpi-value {
  font-family: 'Outfit', sans-serif;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--txt);
  line-height: 1;
  margin-bottom: 0.35rem;
}

.kpi-value.sm {
  font-size: 1.4rem;
}

.kpi-sub {
  font-size: 0.72rem;
  color: var(--txt2);
}

.kpi-icon {
  position: absolute;
  top: 1.2rem; right: 1.2rem;
  width: 36px; height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.kpi-icon.orange { background: rgba(249,115,22,0.12); }
.kpi-icon.blue   { background: rgba(59,130,246,0.12); }
.kpi-icon.purple { background: rgba(139,92,246,0.12); }
.kpi-icon.green  { background: rgba(16,185,129,0.12); }

/* ══════════════════════════════════
   CHART CARDS
══════════════════════════════════ */
.chart-card {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 16px;
  padding: 1.4rem 1.6rem;
  margin-bottom: 1rem;
}

.chart-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--txt2);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chart-title::before {
  content: '';
  display: inline-block;
  width: 3px; height: 14px;
  background: var(--acc);
  border-radius: 99px;
}

/* ══════════════════════════════════
   TABELA
══════════════════════════════════ */
.table-wrap {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.table-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(90deg, var(--sur) 0%, var(--sur2) 100%);
}

.table-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--mut);
  background: var(--sur3);
  border: 1px solid var(--bdr2);
  border-radius: 99px;
  padding: 3px 12px;
}

/* ══════════════════════════════════
   SECTION DIVIDER
══════════════════════════════════ */
.sdiv {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 1.75rem 0 1.25rem;
}

.sdiv-line {
  flex: 1;
  height: 1px;
  background: var(--bdr);
}

.sdiv-txt {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--mut);
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 5px;
}

/* ══════════════════════════════════
   ALERTS
══════════════════════════════════ */
.al-s { background: rgba(16,185,129,.08); border: 1px solid rgba(16,185,129,.2); color: var(--grn2); border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }
.al-e { background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); color: #fca5a5; border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }
.al-i { background: rgba(59,130,246,.08); border: 1px solid rgba(59,130,246,.2); color: var(--blu2); border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }
.al-w { background: rgba(245,158,11,.08); border: 1px solid rgba(245,158,11,.2); color: #fcd34d; border-radius: 10px; padding: .7rem 1rem; font-size: .82rem; margin: .5rem 0; display: flex; align-items: center; gap: 8px; }

/* ══════════════════════════════════
   ROAD INFO BOX
══════════════════════════════════ */
.road-box {
  background: linear-gradient(135deg, var(--sur2) 0%, rgba(26,18,5,0.8) 100%);
  border: 1px solid rgba(249,115,22,0.2);
  border-left: 3px solid var(--acc);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin: .75rem 0;
}

.road-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--acc2);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ══════════════════════════════════
   NOTA CARD (sidebar notas do dia)
══════════════════════════════════ */
.nota-card {
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-radius: 10px;
  padding: .75rem 1rem;
  margin-bottom: 0.4rem;
  transition: border-color 0.15s, transform 0.15s;
}

.nota-card:hover {
  border-color: var(--bdr2);
  transform: translateX(2px);
}

.placa-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(245,158,11,0.1);
  border: 1px solid rgba(245,158,11,0.25);
  border-radius: 7px;
  padding: 2px 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  font-weight: 700;
  color: #fcd34d;
  letter-spacing: 0.04em;
}

/* ══════════════════════════════════
   FORM INPUTS
══════════════════════════════════ */
.stTextInput > div > div > input,
.stDateInput > div > div > input {
  background-color: var(--sur2) !important;
  color: var(--txt) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 10px !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: 0.88rem !important;
  padding: 0.55rem 0.9rem !important;
}

.stTextInput > div > div > input:focus {
  border-color: var(--acc) !important;
  box-shadow: 0 0 0 3px rgba(249,115,22,0.1) !important;
}

.stSelectbox > div > div {
  background-color: var(--sur2) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 10px !important;
  color: var(--txt) !important;
}

.stTextArea textarea {
  background-color: var(--sur2) !important;
  color: var(--txt) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 10px !important;
  font-family: 'Outfit', sans-serif !important;
}

.stTextInput label, .stDateInput label, .stSelectbox label, .stTextArea label, .stNumberInput label {
  color: var(--txt2) !important;
  font-size: 0.7rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  font-family: 'Outfit', sans-serif !important;
}

/* ══════════════════════════════════
   BUTTONS
══════════════════════════════════ */
.stButton > button {
  background: linear-gradient(135deg, var(--acc), #ea580c) !important;
  color: white !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: 0.84rem !important;
  transition: all 0.2s !important;
  box-shadow: 0 4px 16px rgba(249,115,22,0.25) !important;
  letter-spacing: 0.02em !important;
}

.stButton > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 24px rgba(249,115,22,0.4) !important;
}

.stDownloadButton > button {
  background: var(--sur2) !important;
  color: var(--txt2) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  box-shadow: none !important;
  font-family: 'Outfit', sans-serif !important;
}

.stDownloadButton > button:hover {
  color: var(--txt) !important;
  border-color: var(--bdr2) !important;
  transform: none !important;
}

/* ══════════════════════════════════
   DATAFRAME STYLING
══════════════════════════════════ */
.stDataFrame {
  border-radius: 0 0 16px 16px !important;
  overflow: hidden !important;
}

.stDataFrame [data-testid="stDataFrame"] {
  background: var(--sur) !important;
}

/* Row zebra and header */
.stDataFrame thead tr th {
  background: var(--sur2) !important;
  color: var(--txt2) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.62rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  border-bottom: 1px solid var(--bdr2) !important;
  padding: 10px 12px !important;
}

.stDataFrame tbody tr:nth-child(even) td {
  background: rgba(255,255,255,0.015) !important;
}

.stDataFrame tbody tr:hover td {
  background: rgba(249,115,22,0.04) !important;
}

.stDataFrame tbody td {
  font-family: 'Outfit', sans-serif !important;
  font-size: 0.82rem !important;
  border-bottom: 1px solid rgba(255,255,255,0.03) !important;
  color: var(--txt) !important;
  padding: 9px 12px !important;
}

/* ══════════════════════════════════
   CHECKBOX & RADIO
══════════════════════════════════ */
.stCheckbox label, .stRadio label span {
  color: var(--txt2) !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: 0.84rem !important;
}

/* ══════════════════════════════════
   FILTER BAR
══════════════════════════════════ */
.filter-bar {
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 0.9rem 1.2rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

/* ══════════════════════════════════
   INFO PANEL (como usar)
══════════════════════════════════ */
.info-panel {
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 1.1rem 1.3rem;
  margin-top: 1rem;
}

.info-panel-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--mut);
  margin-bottom: 0.7rem;
}

.info-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 0.55rem;
  font-size: 0.8rem;
  color: var(--txt2);
  line-height: 1.5;
}

.info-step-num {
  min-width: 20px; height: 20px;
  background: rgba(249,115,22,0.12);
  border: 1px solid rgba(249,115,22,0.25);
  border-radius: 50%;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--acc2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  flex-shrink: 0;
}

/* ══════════════════════════════════
   CAPTION / HELPER TEXT
══════════════════════════════════ */
.stCaption {
  color: var(--mut) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.65rem !important;
}

/* ══════════════════════════════════
   METRIC OVERRIDE
══════════════════════════════════ */
[data-testid="metric-container"] {
  background: var(--sur) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: 12px !important;
  padding: 1rem !important;
}

/* date input format */
input[type="date"] {
  color-scheme: dark !important;
}
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
    row["criado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
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
    """Converte yyyy-mm-dd → dd/mm/yyyy. Aceita qualquer formato."""
    if not s or str(s) in ("","nan","None","—"): return "—"
    s = str(s).strip()
    # já está no formato dd/mm/yyyy
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s
    # formato ISO yyyy-mm-dd
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        parts = s[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s

def fmt_col(df, col="dt_transferencia"):
    df = df.copy()
    if col in df.columns:
        df[col] = df[col].apply(fmt_date)
    return df

def to_iso(dt_str):
    """Converte dd/mm/yyyy → yyyy-mm-dd para filtros internos."""
    if not dt_str or dt_str == "—": return dt_str
    dt_str = str(dt_str).strip()
    if len(dt_str) == 10 and dt_str[2] == "/" and dt_str[5] == "/":
        p = dt_str.split("/")
        return f"{p[2]}-{p[1]}-{p[0]}"
    return dt_str

# ══════════════════════════════════════════════════════════════════════════════
# NAVEGAÇÃO — TOP BAR com st.radio disfarçado
# ══════════════════════════════════════════════════════════════════════════════

# Esconder sidebar completamente
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
.main .block-container { padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

today_str = date.today().strftime("%d/%m/%Y")
today_iso = date.today().isoformat()

# Top nav HTML
st.markdown(f"""
<div class="topnav">
  <div class="topnav-brand">
    <div class="topnav-logo">🚛</div>
    <div>
      <div class="topnav-name">TRANSF</div>
      <div class="topnav-sub">Sistema de Transferências</div>
    </div>
  </div>
  <div class="topnav-right">
    <div class="nav-date">📅 {today_str}</div>
    <div class="nav-status"></div>
  </div>
</div>
""", unsafe_allow_html=True)

# Nav abas via selectbox invisível
col_nav = st.columns([1,1,1,1,4])
with col_nav[0]:
    st.markdown('<div style="padding-top:0.6rem"></div>', unsafe_allow_html=True)
with col_nav[4]:
    st.markdown("", unsafe_allow_html=True)

# Usar radio horizontal como nav
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:first-child {
  padding: 0 2.5rem;
  background: rgba(11,15,26,0.7);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
/* Radio horizontal nav */
.nav-radio div[data-testid="stRadio"] > label { display: none; }
.nav-radio div[data-testid="stRadio"] > div {
  display: flex !important;
  flex-direction: row !important;
  gap: 4px !important;
  padding: 10px 2.5rem !important;
  background: rgba(11,15,26,0.85) !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important;
  backdrop-filter: blur(12px) !important;
}
.nav-radio div[data-testid="stRadio"] > div > label {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 8px 18px !important;
  border-radius: 10px !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  border: 1px solid transparent !important;
  color: #8899aa !important;
  font-family: 'Outfit', sans-serif !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  transition: all 0.2s !important;
}
.nav-radio div[data-testid="stRadio"] > div > label:hover {
  color: #f0f4ff !important;
  background: rgba(255,255,255,0.05) !important;
  border-color: rgba(255,255,255,0.1) !important;
}
.nav-radio div[data-testid="stRadio"] > div > label[data-selected="true"],
.nav-radio div[data-testid="stRadio"] > div > label input:checked + div {
  color: #fb923c !important;
  background: rgba(249,115,22,0.1) !important;
  border-color: rgba(249,115,22,0.25) !important;
}
/* Hide radio circle */
.nav-radio div[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="nav-radio">', unsafe_allow_html=True)
pagina = st.radio(
    "nav",
    ["📊  Dashboard", "➕  Nova Transferência", "📋  Histórico", "🗺️  Roteirização"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_main"
)
st.markdown('</div>', unsafe_allow_html=True)

# ── Filtros globais (abaixo da nav) ──
with st.expander("⚙️ Filtros e Configurações", expanded=False):
    fc1, fc2, fc3 = st.columns([2,2,4])
    with fc1:
        data_filtro = st.date_input("📅 Data", value=date.today(), key="data_global",
                                     format="DD/MM/YYYY")
    with fc2:
        ver_todas = st.checkbox("📋 Ver todas as datas", key="ver_todas")
    with fc3:
        if st.button("🔄 Atualizar Dados", key="refresh_btn"):
            load_transferencias.clear()
            load_road.clear()
            st.rerun()

data_str = data_filtro.isoformat()  # ISO interno
data_display = data_filtro.strftime("%d/%m/%Y")  # exibição

# ── Dados ──
df_all = load_transferencias()
df = df_all.copy() if ver_todas else (
    df_all[df_all["dt_transferencia"]==data_str].copy()
    if not df_all.empty else pd.DataFrame(columns=TCOLS)
)
periodo_txt = "Todas as datas" if ver_todas else data_display

# ══════════════════════════════════════════════════════════════════════════════
# WRAPPER DE CONTEÚDO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div style="padding: 1.5rem 2.5rem; max-width: 1600px; margin: 0 auto;">', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "📊  Dashboard":
    # Page header
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Visão Geral</div>
        <div class="page-title">Dashboard</div>
        <div class="page-period">Período: <span class="period-pill">📅 {periodo_txt}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    n  = len(df)
    vt = df["vltotal"].sum() if not df.empty else 0
    pt = df["pesobrutotot"].sum() if not df.empty else 0
    nd = df["nomecliente"].nunique() if not df.empty else 0

    # 4 KPI cards
    k1, k2, k3, k4 = st.columns(4)
    for col, klass, icon, label, value, sub in [
        (k1, "orange", "📦", "Notas", str(n), "transferências no período"),
        (k2, "blue",   "💰", "Valor Total", br(vt), "valor acumulado"),
        (k3, "purple", "⚖️", "Peso Bruto", f"{pt:,.0f} kg", "total em kg"),
        (k4, "green",  "🏪", "Clientes", str(nd), "clientes distintos"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-card {klass}">
              <div class="kpi-card-bg">{icon}</div>
              <div class="kpi-icon {klass}">{icon}</div>
              <div class="kpi-label">{label}</div>
              <div class="kpi-value {'sm' if len(value) > 8 else ''}">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df.empty:
        try:
            import plotly.graph_objects as go
            T = dict(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8899aa", family="Outfit"),
                margin=dict(l=10, r=10, t=32, b=10)
            )
            GC = "rgba(255,255,255,0.05)"

            r1a, r1b = st.columns([3, 2])

            with r1a:
                st.markdown('<div class="chart-card"><div class="chart-title">Valor por Data de Transferência</div>', unsafe_allow_html=True)
                if ver_todas and not df.empty:
                    pd_ = df.groupby("dt_transferencia").agg(valor=("vltotal","sum")).reset_index().sort_values("dt_transferencia").tail(30)
                    pd_["dt_f"] = pd_["dt_transferencia"].apply(fmt_date)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=pd_["dt_f"], y=pd_["valor"],
                        marker=dict(color=pd_["valor"], colorscale=[[0,"#7c2d12"],[0.5,"#f97316"],[1,"#fed7aa"]], showscale=False),
                        hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>"
                    ))
                    fig.add_trace(go.Scatter(
                        x=pd_["dt_f"], y=pd_["valor"], mode="lines",
                        line=dict(color="#fb923c", width=2, dash="dot"), showlegend=False
                    ))
                    fig.update_layout(**T, height=260,
                        xaxis=dict(gridcolor=GC, tickfont=dict(size=10)),
                        yaxis=dict(gridcolor=GC, tickformat=",.0f", tickfont=dict(size=10)))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.markdown(f'<div class="al-i">📅 Data selecionada: <strong>{data_display}</strong> — {n} nota(s) — {br(vt)}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with r1b:
                st.markdown('<div class="chart-card"><div class="chart-title">Status das Notas</div>', unsafe_allow_html=True)
                np_ = int((df["status"]=="pendente").sum()) if not df.empty else 0
                nr_ = int((df["status"]=="roteirizado").sum()) if not df.empty else 0
                if n > 0:
                    fig2 = go.Figure(go.Pie(
                        labels=["⏳ Pendentes", "✅ Roteirizadas"],
                        values=[np_, nr_], hole=0.62,
                        marker=dict(colors=["#ef4444","#10b981"], line=dict(color="#0b0f1a", width=3)),
                        textinfo="percent+value",
                        hovertemplate="<b>%{label}</b><br>%{value} notas<extra></extra>"
                    ))
                    fig2.update_layout(**T, height=260,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=11)))
                    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.markdown('<div class="al-i">Sem dados para o período.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            r2a, r2b = st.columns(2)

            with r2a:
                st.markdown('<div class="chart-card"><div class="chart-title">Top Clientes por Valor</div>', unsafe_allow_html=True)
                cli = df.groupby("nomecliente")["vltotal"].sum().sort_values(ascending=True).tail(8).reset_index()
                if not cli.empty:
                    fig3 = go.Figure(go.Bar(
                        x=cli["vltotal"], y=cli["nomecliente"], orientation="h",
                        marker=dict(color=cli["vltotal"], colorscale=[[0,"#1e3a5f"],[0.5,"#3b82f6"],[1,"#bfdbfe"]], showscale=False),
                        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"
                    ))
                    fig3.update_layout(**T, height=260,
                        xaxis=dict(gridcolor=GC, tickformat=",.0f"),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)))
                    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            with r2b:
                st.markdown('<div class="chart-card"><div class="chart-title">Valor por Supervisor</div>', unsafe_allow_html=True)
                sup = df.groupby("nomesup")["vltotal"].sum().sort_values(ascending=False).reset_index()
                if not sup.empty:
                    COLS_P = ["#8b5cf6","#a78bfa","#c4b5fd","#7c3aed","#6d28d9","#5b21b6"]
                    fig4 = go.Figure(go.Pie(
                        labels=sup["nomesup"], values=sup["vltotal"], hole=0.5,
                        marker=dict(colors=COLS_P[:len(sup)], line=dict(color="#0b0f1a", width=2)),
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"
                    ))
                    fig4.update_layout(**T, height=260,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=10)))
                    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            r3a, r3b = st.columns([2,1])

            with r3a:
                st.markdown('<div class="chart-card"><div class="chart-title">Top Destinos por Valor</div>', unsafe_allow_html=True)
                dest = df.groupby("destino")["vltotal"].sum().sort_values(ascending=True).tail(10).reset_index()
                if not dest.empty:
                    fig5 = go.Figure(go.Bar(
                        x=dest["vltotal"], y=dest["destino"], orientation="h",
                        marker=dict(color=dest["vltotal"], colorscale=[[0,"#064e3b"],[0.5,"#10b981"],[1,"#a7f3d0"]], showscale=False),
                        hovertemplate="<b>%{y}</b><br>R$ %{x:,.2f}<extra></extra>"
                    ))
                    fig5.update_layout(**T, height=260,
                        xaxis=dict(gridcolor=GC, tickformat=",.0f"),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)))
                    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            with r3b:
                st.markdown('<div class="chart-card"><div class="chart-title">Por Praça</div>', unsafe_allow_html=True)
                praca = df.groupby("praca")["vltotal"].sum().sort_values(ascending=False).head(8).reset_index()
                if not praca.empty:
                    COLS_O = ["#f97316","#fb923c","#fdba74","#fed7aa","#ea580c","#c2410c","#9a3412","#7c2d12"]
                    fig6 = go.Figure(go.Pie(
                        labels=praca["praca"], values=praca["vltotal"], hole=0.5,
                        marker=dict(colors=COLS_O[:len(praca)], line=dict(color="#0b0f1a", width=2)),
                        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<extra></extra>"
                    ))
                    fig6.update_layout(**T, height=260,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=10)))
                    st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            if ver_todas:
                st.markdown('<div class="chart-card"><div class="chart-title">Peso Total por Data (kg)</div>', unsafe_allow_html=True)
                pp = df.groupby("dt_transferencia").agg(peso=("pesobrutotot","sum"), qtd=("id","count")).reset_index().sort_values("dt_transferencia").tail(30)
                pp["dt_f"] = pp["dt_transferencia"].apply(fmt_date)
                fig7 = go.Figure()
                fig7.add_trace(go.Bar(x=pp["dt_f"], y=pp["qtd"], name="Qtd Notas", yaxis="y2",
                    marker=dict(color="rgba(59,130,246,0.25)"),
                    hovertemplate="<b>%{x}</b><br>%{y} notas<extra></extra>"))
                fig7.add_trace(go.Scatter(x=pp["dt_f"], y=pp["peso"], name="Peso kg",
                    line=dict(color="#10b981", width=2.5),
                    fill="tozeroy", fillcolor="rgba(16,185,129,0.07)",
                    hovertemplate="<b>%{x}</b><br>%{y:,.0f} kg<extra></extra>"))
                fig7.update_layout(**T, height=220,
                    xaxis=dict(gridcolor=GC),
                    yaxis=dict(gridcolor=GC, title="Peso (kg)"),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Qtd"),
                    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1, font=dict(size=11)))
                st.plotly_chart(fig7, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

        except ImportError:
            st.info("Adicione `plotly` ao requirements.txt para ativar os gráficos.")

    # ── Tabela de registros ──
    st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📋 Registro de Transferências</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

    cf1, cf2 = st.columns([3, 1])
    with cf1:
        busca = st.text_input("Buscar", key="db", label_visibility="collapsed", placeholder="🔍  Nota, cliente, destino, placa...")
    with cf2:
        fst = st.selectbox("Status", ["Todos","pendente","roteirizado"], key="dst", label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst != "Todos": df_s = df_s[df_s["status"]==fst]
        if busca:
            m = df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_s = df_s[m]

    if not df_s.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            df_s.to_excel(w, index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel", out, file_name=f"transf_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    df_d = fmt_col(df_s)
    if "dt_roteirizacao" in df_d.columns:
        df_d = fmt_col(df_d, "dt_roteirizacao")

    SHOW_COLS = [c for c in ["dt_transferencia","numnota","numped","nomecliente","nomesup",
                              "praca","destino","pesobrutotot","vltotal","placa_veiculo","placa_road","status"] if c in df_d.columns]

    st.markdown(f"""
    <div class="table-wrap">
      <div class="table-header">
        <span class="table-title">📋 Transferências</span>
        <span class="table-count">{len(df_s)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_d[SHOW_COLS].sort_values("dt_transferencia", ascending=False) if not df_d.empty else df_d,
        use_container_width=True, hide_index=True,
        column_config={
            "dt_transferencia": st.column_config.TextColumn("📅 Data", width=100),
            "numnota":          st.column_config.TextColumn("🧾 Nota", width=90),
            "numped":           st.column_config.TextColumn("📋 Pedido", width=90),
            "nomecliente":      st.column_config.TextColumn("👤 Cliente", width=200),
            "nomesup":          st.column_config.TextColumn("👔 Supervisor", width=130),
            "praca":            st.column_config.TextColumn("🏙️ Praça", width=90),
            "destino":          st.column_config.TextColumn("📍 Destino", width=130),
            "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso (kg)", format="%.3f", width=100),
            "vltotal":          st.column_config.NumberColumn("💰 Valor (R$)", format="R$ %.2f", width=125),
            "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.", width=115),
            "placa_road":       st.column_config.TextColumn("📋 Placa ROAD", width=115),
            "status":           st.column_config.TextColumn("📌 Status", width=100),
        }
    )

    if not df.empty:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🗑️ Excluir Registro</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        ids = df["id"].astype(str).tolist()
        cd1, cd2 = st.columns([3, 1])
        with cd1:
            del_id = st.selectbox("Selecionar ID", ["—"] + ids, label_visibility="collapsed")
        with cd2:
            if del_id != "—" and st.button("🗑️ Excluir", type="secondary"):
                delete_transf(int(del_id))
                st.success("✅ Registro excluído!")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# NOVA TRANSFERÊNCIA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "➕  Nova Transferência":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Faturamento</div>
        <div class="page-title">Nova Transferência</div>
        <div class="page-period">Registre notas fiscais — data selecionada: <span class="period-pill">📅 {data_display}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_f, col_s = st.columns([1.4, 0.6])

    with col_f:
        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">📅 Data e Nota Fiscal</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

        cd, cn, cb = st.columns([1.2, 2, 1])
        with cd:
            dt_t = st.date_input("Data da Transferência", value=data_filtro,
                                  label_visibility="visible", format="DD/MM/YYYY")
        with cn:
            nota_inp = st.text_input("Número da Nota Fiscal", placeholder="Ex: 398234", key="nn")
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            buscar_btn = st.button("🔍 Buscar", use_container_width=True)

        if "cur" not in st.session_state:
            st.session_state.cur = None

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
            st.markdown('<div class="road-box"><div class="road-title">✅ Dados da Base ROAD</div></div>', unsafe_allow_html=True)
            a, b, c_ = st.columns(3)
            with a: st.text_input("📋 Nº Pedido", value=cur["numped"] or "—", disabled=True)
            with b: st.text_input("🧾 Nota Fiscal", value=cur["numnota"], disabled=True)
            with c_: st.text_input("📦 Nº Carregamento", value=cur["numcarregamento"], disabled=True)
            a2, b2, c2 = st.columns(3)
            with a2: st.text_input("👤 Cliente", value=cur["nomecliente"], disabled=True)
            with b2: st.text_input("👔 Supervisor", value=cur["nomesup"], disabled=True)
            with c2: st.text_input("🏙️ Praça", value=cur["praca"] or "—", disabled=True)
            a3, b3, c3 = st.columns(3)
            with a3: st.text_input("📍 Destino", value=cur["destino"], disabled=True)
            with b3: st.text_input("⚖️ Peso Bruto (kg)", value=f"{cur['pesobrutotot']:.3f}".replace(".",","), disabled=True)
            with c3: st.text_input("💰 Valor Total", value=br(cur["vltotal"]), disabled=True)
            if cur.get("placa_road"):
                st.markdown(f'<div class="al-w">🚗 Placa ROAD registrada: <strong>{cur["placa_road"]}</strong></div>', unsafe_allow_html=True)
            obs = st.text_area("💬 Observação (opcional)", placeholder="Observação adicional...", key="obs")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚛 Confirmar Transferência", type="primary", use_container_width=True):
                dt_s = dt_t.isoformat()
                if check_dup(cur["numnota"], dt_s):
                    st.markdown(f'<div class="al-e">❌ Nota {cur["numnota"]} já registrada em {fmt_date(dt_s)}.</div>', unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        append_transf({
                            "dt_transferencia": dt_s,
                            "numped": cur["numped"], "numnota": cur["numnota"],
                            "nomecliente": cur["nomecliente"], "nomesup": cur["nomesup"],
                            "praca": cur["praca"], "pesobrutotot": cur["pesobrutotot"],
                            "numcarregamento": cur["numcarregamento"], "vltotal": cur["vltotal"],
                            "destino": cur["destino"], "placa_road": cur.get("placa_road",""), "obs": obs,
                        })
                    st.success(f"✅ Transferência registrada! Nota **{cur['numnota']}** está pendente de roteirização.")
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
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:.5rem 0;margin-bottom:.6rem;border-bottom:1px solid rgba(255,255,255,0.06)">
              <span style="color:#8899aa;font-size:.76rem;font-family:'JetBrains Mono',monospace">
                {len(df_hj)} nota(s)
              </span>
              <span style="color:#fb923c;font-weight:700;font-size:.88rem;font-family:'Outfit',sans-serif">
                {br(tv)}
              </span>
            </div>
            """, unsafe_allow_html=True)

            for _, row in df_hj.iterrows():
                pl = row.get("placa_veiculo", "")
                pl_h = f'<span class="placa-chip">🚗 {pl}</span>' if pl else '<span style="color:#ef4444;font-size:.7rem;font-family:JetBrains Mono,monospace">⏳ Pendente</span>'
                st.markdown(f"""
                <div class="nota-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                        color:#f0f4ff;font-size:.88rem">{row['numnota']}</div>
                      <div style="color:#8899aa;font-size:.73rem;margin-top:2px">
                        {str(row.get('nomecliente',''))[:26]}
                      </div>
                    </div>
                    <div style="text-align:right">
                      <div style="color:#fb923c;font-weight:700;font-size:.8rem;margin-bottom:4px">
                        {br(row['vltotal'])}
                      </div>
                      {pl_h}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
        <div class="info-panel">
          <div class="info-panel-title">💡 Como registrar</div>
          <div class="info-step"><div class="info-step-num">1</div><span>Selecione a <strong style="color:#f0f4ff">data</strong> da transferência</span></div>
          <div class="info-step"><div class="info-step-num">2</div><span>Digite o <strong style="color:#f0f4ff">número da nota</strong> fiscal</span></div>
          <div class="info-step"><div class="info-step-num">3</div><span>Clique <strong style="color:#fb923c">Buscar</strong> para carregar os dados</span></div>
          <div class="info-step"><div class="info-step-num">4</div><span>Verifique os dados preenchidos <strong style="color:#fb923c">automaticamente</strong></span></div>
          <div class="info-step"><div class="info-step-num">5</div><span>Clique <strong style="color:#f0f4ff">Confirmar Transferência</strong></span></div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Faturamento</div>
        <div class="page-title">Histórico</div>
        <div class="page-period">Período: <span class="period-pill">📅 {periodo_txt}</span> — {len(df)} registro(s)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    cf1, cf2, cf3 = st.columns([3, 1, 1])
    with cf1:
        busca = st.text_input("Buscar", key="hb", label_visibility="collapsed",
                               placeholder="🔍  Nota, cliente, placa, destino...")
    with cf2:
        fst = st.selectbox("Status", ["Todos","pendente","roteirizado"], key="hst", label_visibility="collapsed")
    with cf3:
        sups = ["Todos"] + (sorted(df["nomesup"].dropna().unique().tolist()) if not df.empty else [])
        fsup = st.selectbox("Supervisor", sups, key="hsup", label_visibility="collapsed")

    df_s = df.copy()
    if not df_s.empty:
        if fst != "Todos": df_s = df_s[df_s["status"]==fst]
        if fsup != "Todos": df_s = df_s[df_s["nomesup"]==fsup]
        if busca:
            m = df_s.apply(lambda r: busca.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_s = df_s[m]

    if not df_s.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            df_s.to_excel(w, index=False)
        out.seek(0)
        st.download_button("⬇️ Exportar Excel", out, file_name=f"historico_{data_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    df_d = fmt_col(df_s)
    if "dt_roteirizacao" in df_d.columns:
        df_d = fmt_col(df_d, "dt_roteirizacao")

    HCOLS = [c for c in ["dt_transferencia","numnota","numped","nomecliente","nomesup","praca",
                          "destino","pesobrutotot","vltotal","placa_veiculo","placa_road",
                          "status","obs","dt_roteirizacao"] if c in df_d.columns]

    st.markdown(f"""
    <div class="table-wrap">
      <div class="table-header">
        <span class="table-title">📋 Todas as Transferências</span>
        <span class="table-count">{len(df_s)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        df_d[HCOLS].sort_values("dt_transferencia", ascending=False) if not df_d.empty else df_d,
        use_container_width=True, hide_index=True,
        column_config={
            "dt_transferencia": st.column_config.TextColumn("📅 Data", width=100),
            "numnota":          st.column_config.TextColumn("🧾 Nota", width=90),
            "numped":           st.column_config.TextColumn("📋 Pedido", width=90),
            "nomecliente":      st.column_config.TextColumn("👤 Cliente", width=190),
            "nomesup":          st.column_config.TextColumn("👔 Supervisor", width=125),
            "praca":            st.column_config.TextColumn("🏙️ Praça", width=90),
            "destino":          st.column_config.TextColumn("📍 Destino", width=130),
            "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso (kg)", format="%.3f", width=100),
            "vltotal":          st.column_config.NumberColumn("💰 Valor (R$)", format="R$ %.2f", width=125),
            "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.", width=115),
            "placa_road":       st.column_config.TextColumn("📋 Placa ROAD", width=115),
            "status":           st.column_config.TextColumn("📌 Status", width=105),
            "obs":              st.column_config.TextColumn("💬 Obs", width=150),
            "dt_roteirizacao":  st.column_config.TextColumn("🗺️ Dt. Roteiriz.", width=115),
        }
    )

# ══════════════════════════════════════════════════════════════════════════════
# ROTEIRIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗺️  Roteirização":
    st.markdown(f"""
    <div class="page-header">
      <div>
        <div class="page-eyebrow">Roteirização</div>
        <div class="page-title">Roteirizar Notas</div>
        <div class="page-period">Período: <span class="period-pill" style="background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.2);color:#34d399">📅 {periodo_txt}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pend = df[df["status"]=="pendente"] if not df.empty else pd.DataFrame()
    rote = df[df["status"]=="roteirizado"] if not df.empty else pd.DataFrame()

    # KPIs de roteirização
    c1, c2, c3, c4 = st.columns(4)
    for col, klass, icon, label, value, sub in [
        (c1, "red",    "⏳", "Pendentes",   str(len(pend)),  br(pend["vltotal"].sum()) if not pend.empty else "R$ 0,00"),
        (c2, "green",  "✅", "Roteirizadas", str(len(rote)),  br(rote["vltotal"].sum()) if not rote.empty else "R$ 0,00"),
        (c3, "orange", "⚖️", "Peso Pend.",  f"{pend['pesobrutotot'].sum():.0f} kg" if not pend.empty else "0 kg", "peso pendente"),
        (c4, "purple", "⚖️", "Peso Rot.",   f"{rote['pesobrutotot'].sum():.0f} kg" if not rote.empty else "0 kg", "peso roteirizado"),
    ]:
        with col:
            # Mapear 'red' para card vermelho
            bar_color = {"orange":"#f97316","blue":"#3b82f6","purple":"#8b5cf6","green":"#10b981","red":"#ef4444"}.get(klass,"#f97316")
            st.markdown(f"""
            <div class="kpi-card" style="border-top: 3px solid {bar_color}22; position:relative; overflow:hidden;
              background:var(--sur); border: 1px solid var(--bdr); border-radius:16px; padding:1.4rem 1.6rem 1.2rem;
              transition: transform .2s, border-color .2s;">
              <div style="position:absolute;top:0;left:0;right:0;height:3px;
                background:linear-gradient(90deg,{bar_color},{bar_color}88);border-radius:16px 16px 0 0;"></div>
              <div style="position:absolute;bottom:-20px;right:-20px;font-size:5rem;opacity:.04;filter:blur(1px)">{icon}</div>
              <div style="width:36px;height:36px;border-radius:9px;display:flex;align-items:center;justify-content:center;
                font-size:1rem;background:{bar_color}18;position:absolute;top:1.2rem;right:1.2rem">{icon}</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:.6rem;font-weight:700;
                text-transform:uppercase;letter-spacing:.12em;color:var(--mut);margin-bottom:.75rem">{label}</div>
              <div style="font-family:'Outfit',sans-serif;font-size:{'1.5rem' if len(value)>8 else '2rem'};font-weight:800;
                letter-spacing:-.03em;color:{bar_color};line-height:1;margin-bottom:.35rem">{value}</div>
              <div style="font-size:.72rem;color:var(--txt2)">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PENDENTES ──
    st.markdown(f"""
    <div class="table-wrap" style="border-color:rgba(239,68,68,.2)">
      <div class="table-header" style="border-bottom-color:rgba(239,68,68,.15)">
        <span class="table-title" style="color:#fca5a5">⏳ Notas Pendentes</span>
        <span class="table-count">{len(pend)} registros</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if pend.empty:
        st.markdown('<div class="al-s">✅ Nenhuma nota pendente para o período selecionado!</div>', unsafe_allow_html=True)
    else:
        pb1, pb2 = st.columns([3, 1])
        with pb1:
            bp = st.text_input("Buscar pendentes", key="rbp", label_visibility="collapsed",
                                placeholder="🔍  Nota, cliente, praça...")
        with pb2:
            dp_opts = ["Todas"] + sorted(pend["dt_transferencia"].unique().tolist(), reverse=True)
            dp_opts_fmt = ["Todas"] + [fmt_date(d) for d in dp_opts[1:]]
            fdp_fmt = st.selectbox("Data", dp_opts_fmt, key="rdp", label_visibility="collapsed")
            fdp = to_iso(fdp_fmt) if fdp_fmt != "Todas" else "Todas"

        df_p = pend.copy()
        if fdp != "Todas": df_p = df_p[df_p["dt_transferencia"]==fdp]
        if bp:
            m = df_p.apply(lambda r: bp.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_p = df_p[m]

        PCOLS = [c for c in ["id","dt_transferencia","numnota","numped","nomecliente","nomesup",
                               "praca","destino","pesobrutotot","vltotal","placa_road"] if c in df_p.columns]
        df_pd = fmt_col(df_p)
        st.dataframe(
            df_pd[PCOLS].sort_values("dt_transferencia", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "id":               st.column_config.NumberColumn("ID", width=55),
                "dt_transferencia": st.column_config.TextColumn("📅 Data", width=100),
                "numnota":          st.column_config.TextColumn("🧾 Nota", width=90),
                "numped":           st.column_config.TextColumn("📋 Pedido", width=90),
                "nomecliente":      st.column_config.TextColumn("👤 Cliente", width=190),
                "nomesup":          st.column_config.TextColumn("👔 Supervisor", width=125),
                "praca":            st.column_config.TextColumn("🏙️ Praça", width=90),
                "destino":          st.column_config.TextColumn("📍 Destino", width=130),
                "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso (kg)", format="%.3f", width=100),
                "vltotal":          st.column_config.NumberColumn("💰 Valor (R$)", format="R$ %.2f", width=125),
                "placa_road":       st.column_config.TextColumn("📋 Placa ROAD", width=115),
            }
        )
        st.caption(f"{len(df_p)} nota(s) pendente(s)")

        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">🚗 Informar Placa do Veículo</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)

        ids_p = df_p["id"].astype(str).tolist()
        if ids_p:
            cs, cp, cok = st.columns([1.5, 2, 1])
            with cs:
                sel = st.selectbox("Nota (ID)", ids_p, label_visibility="visible")
            with cp:
                nova_pl = st.text_input("Placa do Veículo", placeholder="Ex: ABC-1234", key="rpl").upper()
            with cok:
                st.markdown("<br>", unsafe_allow_html=True)
                conf = st.button("✅ Confirmar", use_container_width=True)

            if sel:
                rs = df_p[df_p["id"].astype(str)==sel]
                if not rs.empty:
                    r = rs.iloc[0]
                    pr = r.get("placa_road","")
                    pr_h = f'&nbsp;·&nbsp;<span class="placa-chip">📋 ROAD: {pr}</span>' if pr else ""
                    st.markdown(f"""
                    <div style="background:var(--sur2);border:1px solid var(--bdr);border-radius:10px;
                      padding:.7rem 1.1rem;font-size:.82rem;display:flex;align-items:center;
                      gap:.75rem;margin:.4rem 0;flex-wrap:wrap">
                      <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f0f4ff">{r['numnota']}</span>
                      <span style="color:#8899aa">{r.get('nomecliente','')}</span>
                      <span style="color:#fb923c;font-weight:700">{br(r['vltotal'])}</span>
                      <span style="color:#8899aa">📍 {r.get('destino','—')}</span>{pr_h}
                    </div>
                    """, unsafe_allow_html=True)

            if conf:
                if not nova_pl.strip():
                    st.markdown('<div class="al-e">⚠️ Por favor, informe a placa do veículo!</div>', unsafe_allow_html=True)
                else:
                    with st.spinner("Salvando..."):
                        update_transf(int(sel), {
                            "placa_veiculo": nova_pl.strip(),
                            "dt_roteirizacao": date.today().strftime("%d/%m/%Y"),
                            "status": "roteirizado"
                        })
                    st.success(f"🚗 Placa **{nova_pl.strip()}** registrada com sucesso!")
                    st.rerun()

    # ── ROTEIRIZADAS ──
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
        br_ = st.text_input("Buscar roteirizadas", key="rbr", label_visibility="collapsed",
                              placeholder="🔍  Nota, cliente, placa...")
        df_r = rote.copy()
        if br_:
            m = df_r.apply(lambda r: br_.lower() in " ".join(str(v) for v in r).lower(), axis=1)
            df_r = df_r[m]

        RCOLS = [c for c in ["id","dt_transferencia","numnota","numped","nomecliente","nomesup",
                               "praca","destino","pesobrutotot","vltotal","placa_veiculo",
                               "placa_road","dt_roteirizacao"] if c in df_r.columns]
        df_rd = fmt_col(df_r)
        if "dt_roteirizacao" in df_rd.columns:
            df_rd = fmt_col(df_rd, "dt_roteirizacao")

        st.dataframe(
            df_rd[RCOLS].sort_values("dt_transferencia", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "id":               st.column_config.NumberColumn("ID", width=55),
                "dt_transferencia": st.column_config.TextColumn("📅 Data", width=100),
                "numnota":          st.column_config.TextColumn("🧾 Nota", width=90),
                "numped":           st.column_config.TextColumn("📋 Pedido", width=90),
                "nomecliente":      st.column_config.TextColumn("👤 Cliente", width=190),
                "nomesup":          st.column_config.TextColumn("👔 Supervisor", width=125),
                "praca":            st.column_config.TextColumn("🏙️ Praça", width=90),
                "destino":          st.column_config.TextColumn("📍 Destino", width=130),
                "pesobrutotot":     st.column_config.NumberColumn("⚖️ Peso (kg)", format="%.3f", width=100),
                "vltotal":          st.column_config.NumberColumn("💰 Valor (R$)", format="R$ %.2f", width=125),
                "placa_veiculo":    st.column_config.TextColumn("🚗 Placa Veíc.", width=115),
                "placa_road":       st.column_config.TextColumn("📋 Placa ROAD", width=115),
                "dt_roteirizacao":  st.column_config.TextColumn("🗺️ Dt. Roteiriz.", width=115),
            }
        )
        st.caption(f"{len(df_r)} nota(s) roteirizada(s)")

        st.markdown('<div class="sdiv"><div class="sdiv-line"></div><div class="sdiv-txt">↩️ Devolver para Pendente</div><div class="sdiv-line"></div></div>', unsafe_allow_html=True)
        ids_r = df_r["id"].astype(str).tolist()
        if ids_r:
            cd1, cd2 = st.columns([3, 1])
            with cd1:
                dvid = st.selectbox("ID a devolver", ids_r, key="rdv", label_visibility="collapsed")
            with cd2:
                if st.button("↩️ Devolver", use_container_width=True):
                    update_transf(int(dvid), {"placa_veiculo":"","dt_roteirizacao":"","status":"pendente"})
                    st.success("↩️ Nota devolvida para pendentes!")
                    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
