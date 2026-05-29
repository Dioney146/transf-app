import os, json, sqlite3, subprocess, sys
from datetime import date, datetime
from flask import Flask, request, jsonify, redirect, Response, send_file
import pandas as pd

# ── AUTO-INSTALA DEPENDÊNCIAS ─────────────────────────────────────────────────
for pkg in ["waitress", "openpyxl", "xlrd"]:
    try:
        __import__(pkg)
    except ImportError:
        print(f"  Instalando {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

app = Flask(__name__, template_folder=None)
app.secret_key = "transf_road_2025"

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "transferencias.db")
ROAD_PATH = os.path.join(BASE_DIR, "ROAD.xls")

# ── BANCO ─────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transferencias (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                dt_transferencia TEXT NOT NULL,
                numped           TEXT,
                numnota          TEXT NOT NULL,
                nomecliente      TEXT,
                nomesup          TEXT,
                praca            TEXT,
                pesobrutotot     REAL,
                numcarregamento  TEXT,
                vltotal          REAL,
                destino          TEXT,
                obs              TEXT,
                placa            TEXT,
                dt_roteirizacao  TEXT,
                status           TEXT DEFAULT 'pendente',
                criado_em        TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col, defn in [
            ("placa",           "TEXT"),
            ("dt_roteirizacao", "TEXT"),
            ("status",          "TEXT DEFAULT 'pendente'"),
            ("praca",           "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE transferencias ADD COLUMN {col} {defn}")
            except Exception:
                pass
        conn.commit()

# ── ROAD ──────────────────────────────────────────────────────────────────────
def load_road():
    for ext in ["xls", "xlsx"]:
        path = os.path.join(BASE_DIR, f"ROAD.{ext}")
        if os.path.exists(path):
            try:
                engine = "xlrd" if ext == "xls" else "openpyxl"
                df = pd.read_excel(path, engine=engine, dtype=str)
                for c in df.columns:
                    df[c] = df[c].astype(str).str.strip()
                df.columns = [c.upper().strip() for c in df.columns]
                if "NUMNOTA" in df.columns:
                    df["NUMNOTA"] = df["NUMNOTA"].str.split(".").str[0]
                if "NUMPED" in df.columns:
                    df["NUMPED"] = df["NUMPED"].str.split(".").str[0]
                return df
            except Exception as e:
                print(f"Erro ao ler ROAD.{ext}: {e}")
    return pd.DataFrame()

def buscar_nota(numnota):
    df = load_road()
    if df.empty: return None
    row = df[df["NUMNOTA"] == numnota.strip()]
    if row.empty: return None
    r = row.iloc[0]
    def safe(col):
        v = r.get(col, "")
        if v in ("nan", "None", "", None): return ""
        v = str(v)
        if v.endswith(".0"): return v[:-2]
        return v
    try: peso = float(str(r.get("PESOBRUTOTOT","0")).replace(",","."))
    except: peso = 0.0
    try: vl = float(str(r.get("VLTOTAL","0")).replace(",","."))
    except: vl = 0.0
    return {
        "numped":         safe("NUMPED"),
        "numnota":        safe("NUMNOTA"),
        "nomecliente":    safe("NOMECLIENTE"),
        "nomesup":        safe("NOMESUP"),
        "praca":          safe("PRAÇA") or safe("PRACA") or safe("PRAA"),
        "pesobrutotot":   peso,
        "numcarregamento":safe("NUMCARREGAMENTO"),
        "vltotal":        vl,
        "destino":        safe("DESTINO"),
    }

# ══════════════════════════════════════════════════════════════════════════════
# ESTILOS
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
  --bg:     #0a0c10;
  --sur:    #111318;
  --sur2:   #1a1d24;
  --sur3:   #22262f;
  --bdr:    #2a2f3a;
  --bdr2:   #353b47;
  --acc:    #ff6b2b;
  --acc2:   #ff8f5e;
  --grn:    #22c55e;
  --grn2:   #4ade80;
  --blu:    #3b82f6;
  --blu2:   #60a5fa;
  --pur:    #a855f7;
  --yel:    #eab308;
  --red:    #ef4444;
  --txt:    #e8ecf3;
  --txt2:   #a0aab8;
  --mut:    #6b7585;
  --nav-h:  64px;
  --rad:    12px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--txt);
  font-family: 'DM Sans', sans-serif;
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--sur); }
::-webkit-scrollbar-thumb { background: var(--bdr2); border-radius: 99px; }

/* ── NAV ── */
nav {
  background: var(--sur);
  border-bottom: 1px solid var(--bdr);
  height: var(--nav-h);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 0.5rem;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 0 var(--bdr), 0 4px 24px rgba(0,0,0,0.4);
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--acc);
  text-decoration: none;
  margin-right: 0.5rem;
  flex-shrink: 0;
}
.brand-dot { width: 8px; height: 8px; background: var(--acc); border-radius: 50%; animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.8)} }
.nav-div { width: 1px; height: 24px; background: var(--bdr); margin: 0 0.5rem; flex-shrink: 0; }
.nav-group { display: flex; align-items: center; gap: 0.25rem; }
.nav-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--mut); padding: 0 0.5rem; white-space: nowrap; }
.nav-a {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--txt2);
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}
.nav-a:hover { background: var(--sur2); color: var(--txt); }
.nav-a.dash { color: var(--blu); }
.nav-a.fat  { color: var(--acc); }
.nav-a.rot  { color: var(--grn); }
.nav-a.active { font-weight: 700; }
.nav-a.active.dash { background: rgba(59,130,246,0.15); }
.nav-a.active.fat  { background: rgba(255,107,43,0.15); }
.nav-a.active.rot  { background: rgba(34,197,94,0.15); }
.nav-spacer { flex: 1; }
.nav-status {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.75rem; color: var(--mut);
  padding: 0.35rem 0.85rem;
  background: var(--sur2);
  border: 1px solid var(--bdr);
  border-radius: 99px;
}
.ns-dot { width: 6px; height: 6px; background: var(--grn); border-radius: 50%; animation: pulse 2s ease infinite; }

/* ── MAIN ── */
main { max-width: 1440px; margin: 0 auto; padding: 2rem 1.5rem; }

/* ── PAGE HEADER ── */
.ph { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 2rem; gap: 1rem; flex-wrap: wrap; }
.ph-left {}
.ph-tag { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.2rem 0.65rem; border-radius: 99px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.5rem; }
.ph-tag.dash { background: rgba(59,130,246,0.15); color: var(--blu2); border: 1px solid rgba(59,130,246,0.25); }
.ph-tag.fat  { background: rgba(255,107,43,0.15); color: var(--acc2); border: 1px solid rgba(255,107,43,0.25); }
.ph-tag.rot  { background: rgba(34,197,94,0.15); color: var(--grn2); border: 1px solid rgba(34,197,94,0.25); }
.ph h1 { font-size: 1.6rem; font-weight: 800; line-height: 1.2; }
.ph-sub { font-size: 0.82rem; color: var(--txt2); margin-top: 0.35rem; }
.ph-acts { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }

/* ── KPI GRID ── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.kpi {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: var(--rad);
  padding: 1.25rem 1.4rem;
  position: relative;
  overflow: hidden;
  transition: border-color 0.2s;
}
.kpi:hover { border-color: var(--bdr2); }
.kpi::after { content: ""; position: absolute; inset: 0; background: linear-gradient(135deg, rgba(255,255,255,0.02), transparent); pointer-events: none; }
.kpi-bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
.kpi-lbl { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: var(--mut); margin-bottom: 0.6rem; }
.kpi-val { font-size: 1.9rem; font-weight: 800; line-height: 1; font-family: 'JetBrains Mono', monospace; }
.kpi-sub { font-size: 0.73rem; color: var(--txt2); margin-top: 0.4rem; }

/* ── CHART GRID ── */
.cgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
.cc { background: var(--sur); border: 1px solid var(--bdr); border-radius: var(--rad); padding: 1.4rem; }
.cc.full { grid-column: 1/-1; }
.cc.third { grid-column: span 1; }
.cc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; }
.cc-tit { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: var(--txt2); }
.cc-wrap { position: relative; height: 240px; }

/* ── TABLE CONTAINER ── */
.tc { background: var(--sur); border: 1px solid var(--bdr); border-radius: var(--rad); overflow: hidden; margin-bottom: 1.5rem; }
.tc-head { padding: 1rem 1.4rem; border-bottom: 1px solid var(--bdr); display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.tc-tit { font-weight: 700; font-size: 0.92rem; flex: 1; min-width: 140px; }
.tc-filters { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.tc-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
thead th {
  background: var(--sur2);
  padding: 0.65rem 1rem;
  text-align: left;
  font-size: 0.67rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--mut);
  border-bottom: 1px solid var(--bdr);
  white-space: nowrap;
  position: sticky;
  top: 0;
}
tbody tr { border-bottom: 1px solid var(--bdr); transition: background 0.1s; }
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--sur2); }
tbody td { padding: 0.6rem 1rem; vertical-align: middle; }
.tc-foot { padding: 0.65rem 1.4rem; color: var(--mut); font-size: 0.75rem; border-top: 1px solid var(--bdr); display: flex; align-items: center; justify-content: space-between; }

/* ── ROW STYLES ── */
tr.row-pend { background: rgba(239,68,68,0.03); }
tr.row-pend:hover { background: rgba(239,68,68,0.07) !important; }
tr.row-done { background: rgba(34,197,94,0.03); }
tr.row-done:hover { background: rgba(34,197,94,0.06) !important; }

/* ── INPUTS ── */
.si {
  background: var(--sur2);
  border: 1px solid var(--bdr);
  color: var(--txt);
  border-radius: 8px;
  padding: 0.4rem 0.85rem;
  font-size: 0.82rem;
  font-family: 'DM Sans', sans-serif;
  outline: none;
  transition: border-color 0.15s;
}
.si:focus { border-color: var(--acc); }
.si::placeholder { color: var(--mut); }

.fi {
  width: 100%;
  background: var(--sur2);
  border: 1px solid var(--bdr);
  color: var(--txt);
  border-radius: 9px;
  padding: 0.6rem 0.95rem;
  font-size: 0.88rem;
  font-family: 'DM Sans', sans-serif;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.fi:focus { border-color: var(--acc); box-shadow: 0 0 0 3px rgba(255,107,43,0.1); }
.fi::placeholder { color: var(--mut); }
.fi[readonly] { opacity: 0.6; cursor: default; }
textarea.fi { resize: vertical; min-height: 60px; }

/* ── BUTTONS ── */
.btn {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1.1rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  border: none;
  text-decoration: none;
  transition: all 0.15s;
  font-family: 'DM Sans', sans-serif;
  white-space: nowrap;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-acc { background: var(--acc); color: #fff; }
.btn-acc:hover:not(:disabled) { background: var(--acc2); }
.btn-grn { background: var(--grn); color: #000; }
.btn-grn:hover:not(:disabled) { background: var(--grn2); }
.btn-blu { background: var(--blu); color: #fff; }
.btn-blu:hover:not(:disabled) { background: var(--blu2); }
.btn-red { background: var(--red); color: #fff; }
.btn-red:hover:not(:disabled) { filter: brightness(1.1); }
.btn-ghost { background: var(--sur2); color: var(--txt2); border: 1px solid var(--bdr); }
.btn-ghost:hover:not(:disabled) { border-color: var(--bdr2); color: var(--txt); }
.btn-sm { padding: 0.3rem 0.7rem; font-size: 0.75rem; }

/* ── BADGES ── */
.badge {
  display: inline-flex; align-items: center; gap: 0.25rem;
  padding: 0.15rem 0.55rem;
  border-radius: 99px;
  font-size: 0.67rem;
  font-weight: 700;
  white-space: nowrap;
}
.badge-acc   { background: rgba(255,107,43,0.15); color: var(--acc2); }
.badge-grn   { background: rgba(34,197,94,0.15); color: var(--grn2); }
.badge-blu   { background: rgba(59,130,246,0.15); color: var(--blu2); }
.badge-red   { background: rgba(239,68,68,0.15); color: #f87171; }
.badge-yel   { background: rgba(234,179,8,0.15); color: #fbbf24; }
.badge-mut   { background: var(--sur3); color: var(--txt2); }

/* ── FORM CARD ── */
.form-card { background: var(--sur); border: 1px solid var(--bdr); border-radius: 16px; padding: 1.75rem; }
.form-sec { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: var(--mut); margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem; }
.form-sec::after { content: ""; flex: 1; height: 1px; background: var(--bdr); }
.form-g { margin-bottom: 1rem; }
.form-g label { display: block; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--txt2); margin-bottom: 0.35rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
.form-row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.85rem; }

.road-box {
  background: var(--sur2);
  border: 1px solid rgba(255,107,43,0.2);
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.25rem;
}
.road-box-tit { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: var(--acc2); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.4rem; }

.alert { padding: 0.65rem 0.95rem; border-radius: 8px; font-size: 0.82rem; margin-top: 0.5rem; }
.alert-e { background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3); color: #f87171; }
.alert-s { background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3); color: var(--grn2); }
.alert-i { background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.3); color: var(--blu2); }

/* ── SIDE CARD ── */
.side-card { background: var(--sur); border: 1px solid var(--bdr); border-radius: 16px; padding: 1.5rem; }
.info-item { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--bdr); font-size: 0.82rem; }
.info-item:last-child { border-bottom: none; }
.info-lbl { color: var(--txt2); font-size: 0.75rem; }
.info-val { font-weight: 700; }

/* ── TWO COLUMN LAYOUT ── */
.two-col { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 1.5rem; align-items: start; }

/* ── MODAL ── */
.modal-bg {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.75);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none;
  transition: opacity 0.2s;
}
.modal-bg.open { opacity: 1; pointer-events: all; }
.modal {
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-top: 2px solid var(--grn);
  border-radius: 18px;
  padding: 2rem;
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  transform: translateY(16px) scale(0.98);
  transition: transform 0.2s;
}
.modal-bg.open .modal { transform: translateY(0) scale(1); }
.modal-tit { font-size: 1.1rem; font-weight: 800; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }
.modal-info { background: var(--sur2); border-radius: 10px; padding: 1rem; margin-bottom: 1.25rem; }

/* ── TOAST ── */
#toast {
  position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
  background: var(--sur);
  border: 1px solid var(--bdr);
  border-radius: 12px;
  padding: 0.85rem 1.25rem;
  font-size: 0.85rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  opacity: 0; transform: translateY(8px);
  transition: all 0.25s;
  pointer-events: none;
  max-width: 320px;
  display: flex; align-items: center; gap: 0.5rem;
}
#toast.show { opacity: 1; transform: translateY(0); }
#toast.ts { border-color: var(--grn); }
#toast.te { border-color: var(--red); }
#toast.ti { border-color: var(--blu); }

/* ── LOADER ── */
.spin { display: inline-block; width: 13px; height: 13px; border: 2px solid rgba(255,255,255,0.25); border-top-color: currentColor; border-radius: 50%; animation: sp 0.6s linear infinite; }
@keyframes sp { to { transform: rotate(360deg); } }

/* ── EMPTY ── */
.empty { text-align: center; padding: 3.5rem 2rem; color: var(--mut); }
.empty-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
.empty-txt { font-size: 0.88rem; }

/* ── MONO ── */
.mono { font-family: 'JetBrains Mono', monospace; }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .cgrid, .two-col { grid-template-columns: 1fr; }
  .cc.full { grid-column: 1; }
  .form-row, .form-row3 { grid-template-columns: 1fr; }
  nav { padding: 0 1rem; gap: 0.25rem; }
  .nav-lbl { display: none; }
}
@media (max-width: 600px) {
  main { padding: 1rem; }
  .kpi-val { font-size: 1.5rem; }
}
"""

JS_BASE = """
function toast(msg, type='ts') {
  const t = document.getElementById('toast');
  t.innerHTML = msg;
  t.className = 'show ' + type;
  clearTimeout(t._t);
  t._t = setTimeout(() => t.className = '', 3500);
}
function fmt(v) {
  return 'R$ ' + Number(v||0).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
}
function fmtPeso(v) {
  return Number(v||0).toLocaleString('pt-BR', {minimumFractionDigits:3, maximumFractionDigits:3}) + ' kg';
}
function fmtDate(s) {
  if (!s) return '—';
  const [y,m,d] = s.split('-');
  return d+'/'+m+'/'+y;
}
"""

def page(title, body, scripts="", active=""):
    a_dash = 'active' if active=='dash' else ''
    a_fat  = 'active' if active=='fat'  else ''
    a_rot  = 'active' if active=='rot'  else ''
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title} — TRANSF</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<nav>
  <a href="/dashboard" class="brand">
    <div class="brand-dot"></div>
    TRANSF
  </a>
  <div class="nav-div"></div>
  <div class="nav-group">
    <span class="nav-lbl">Geral</span>
    <a href="/dashboard" class="nav-a dash {a_dash}">📊 Dashboard</a>
  </div>
  <div class="nav-div"></div>
  <div class="nav-group">
    <span class="nav-lbl">Faturamento</span>
    <a href="/nova" class="nav-a fat {a_fat}">➕ Nova Transferência</a>
    <a href="/lista-fat" class="nav-a fat">📋 Histórico</a>
  </div>
  <div class="nav-div"></div>
  <div class="nav-group">
    <span class="nav-lbl">Roteirização</span>
    <a href="/roteirizacao" class="nav-a rot {a_rot}">🗺️ Roteirizar Notas</a>
  </div>
  <div class="nav-spacer"></div>
  <div class="nav-status">
    <div class="ns-dot"></div>
    Sistema ativo
  </div>
</nav>
<main>{body}</main>
<div id="toast"></div>
<script>{JS_BASE}</script>
<script>{scripts}</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
# ROTAS
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index(): return redirect("/dashboard")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM transferencias ORDER BY dt_transferencia DESC, id DESC").fetchall()
    trans = [dict(r) for r in rows]

    total_notas    = len(trans)
    total_valor    = sum(t["vltotal"] or 0 for t in trans)
    total_peso     = sum(t["pesobrutotot"] or 0 for t in trans)
    total_pendente = sum(1 for t in trans if (t.get("status") or "pendente") == "pendente")
    total_roteiriz = sum(1 for t in trans if (t.get("status") or "pendente") == "roteirizado")

    hoje = date.today().isoformat()
    hoje_n = sum(1 for t in trans if t["dt_transferencia"] == hoje)
    hoje_v = sum(t["vltotal"] or 0 for t in trans if t["dt_transferencia"] == hoje)

    por_data = {}
    for t in trans:
        d = t["dt_transferencia"]
        if d not in por_data: por_data[d] = {"n":0,"v":0,"p":0}
        por_data[d]["n"] += 1
        por_data[d]["v"] += t["vltotal"] or 0
        por_data[d]["p"] += t["pesobrutotot"] or 0
    ds = sorted(por_data)[-30:]  # últimos 30 dias com dados

    clientes = {}
    for t in trans:
        c = t["nomecliente"] or "N/A"
        clientes[c] = clientes.get(c, 0) + (t["vltotal"] or 0)
    top_cli = sorted(clientes.items(), key=lambda x:x[1], reverse=True)[:8]

    sups = {}
    for t in trans:
        s = t["nomesup"] or "N/A"
        sups[s] = sups.get(s, 0) + (t["vltotal"] or 0)

    dests = {}
    for t in trans:
        d = t["destino"] or "N/A"
        dests[d] = dests.get(d, 0) + 1
    top_dest = sorted(dests.items(), key=lambda x:x[1], reverse=True)[:10]

    pracas = {}
    for t in trans:
        p = t.get("praca") or "N/A"
        pracas[p] = pracas.get(p, 0) + (t["vltotal"] or 0)

    def br(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    def kg(v): return f"{v:,.3f}".replace(",","X").replace(".",",").replace("X",".")+" kg"

    # Tabela — últimas 50
    rows_html = ""
    if not trans:
        rows_html = '<tr><td colspan="12"><div class="empty"><div class="empty-icon">🚛</div><div class="empty-txt">Nenhuma transferência registrada ainda.</div></div></td></tr>'
    for t in trans[:200]:
        st = t.get("status") or "pendente"
        row_cls = "row-done" if st == "roteirizado" else "row-pend"
        st_badge = (f'<span class="badge badge-grn">✅ Roteirizado</span>' if st == "roteirizado"
                    else f'<span class="badge badge-red">⏳ Pendente</span>')
        placa_txt = (f'<span class="mono" style="color:var(--yel);font-weight:700">{t["placa"]}</span>'
                     if t.get("placa") else '<span style="color:var(--mut)">—</span>')
        praca_txt = t.get("praca") or "—"
        rows_html += f"""<tr class="{row_cls}" data-id="{t['id']}" data-dt="{t['dt_transferencia']}" data-status="{st}">
<td><span class="badge badge-acc mono">{t['dt_transferencia']}</span></td>
<td class="mono" style="font-weight:700">{t['numnota']}</td>
<td class="mono">{t.get('numped','') or '—'}</td>
<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{t['nomecliente'] or '—'}</td>
<td><span class="badge badge-blu">{t['nomesup'] or '—'}</span></td>
<td><span class="badge badge-mut">{praca_txt}</span></td>
<td style="color:var(--txt2)">{t['numcarregamento'] or '—'}</td>
<td style="color:var(--txt2);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{t['destino'] or '—'}</td>
<td class="mono" style="color:var(--txt2)">{(t['pesobrutotot'] or 0):.3f}</td>
<td class="mono" style="font-weight:700">{br(t['vltotal'] or 0)}</td>
<td>{placa_txt}</td>
<td>{st_badge}</td>
<td><button class="btn btn-red btn-sm" onclick="excluir({t['id']})">🗑</button></td>
</tr>"""

    filter_datas_html = "".join(f'<option value="{d}">{d}</option>' for d in sorted(por_data, reverse=True))

    body = f"""
<div class="ph">
  <div class="ph-left">
    <div class="ph-tag dash">📊 Visão Geral</div>
    <h1>Dashboard</h1>
    <div class="ph-sub">Acompanhe todas as transferências em tempo real</div>
  </div>
  <div class="ph-acts">
    <a href="/exportar" class="btn btn-ghost">⬇️ Exportar Excel</a>
    <a href="/nova" class="btn btn-acc">➕ Nova Transferência</a>
    <a href="/roteirizacao" class="btn btn-grn">🗺️ Roteirizar</a>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--acc),var(--acc2))"></div>
    <div class="kpi-lbl">Total de Notas</div>
    <div class="kpi-val">{total_notas}</div>
    <div class="kpi-sub">transferências registradas</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--acc),var(--acc2))"></div>
    <div class="kpi-lbl">Valor Total</div>
    <div class="kpi-val" style="font-size:1.35rem">{br(total_valor)}</div>
    <div class="kpi-sub">soma de todas</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--acc),var(--acc2))"></div>
    <div class="kpi-lbl">Peso Total</div>
    <div class="kpi-val" style="font-size:1.35rem">{kg(total_peso)}</div>
    <div class="kpi-sub">peso bruto</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--blu),var(--blu2))"></div>
    <div class="kpi-lbl">Hoje ({hoje})</div>
    <div class="kpi-val">{hoje_n}</div>
    <div class="kpi-sub">{br(hoje_v)}</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--red),#f87171)"></div>
    <div class="kpi-lbl">⏳ Pendentes</div>
    <div class="kpi-val" style="color:var(--red)">{total_pendente}</div>
    <div class="kpi-sub">aguardando placa</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--grn),var(--grn2))"></div>
    <div class="kpi-lbl">✅ Roteirizadas</div>
    <div class="kpi-val" style="color:var(--grn)">{total_roteiriz}</div>
    <div class="kpi-sub">placa definida</div>
  </div>
</div>

<div class="cgrid">
  <div class="cc full">
    <div class="cc-head"><span class="cc-tit">📅 Valor por Data de Transferência</span></div>
    <div class="cc-wrap"><canvas id="cV"></canvas></div>
  </div>
  <div class="cc">
    <div class="cc-head"><span class="cc-tit">📦 Quantidade de Notas por Data</span></div>
    <div class="cc-wrap"><canvas id="cN"></canvas></div>
  </div>
  <div class="cc">
    <div class="cc-head"><span class="cc-tit">⚖️ Peso Total por Data (kg)</span></div>
    <div class="cc-wrap"><canvas id="cP"></canvas></div>
  </div>
  <div class="cc">
    <div class="cc-head"><span class="cc-tit">🏆 Top Clientes por Valor</span></div>
    <div class="cc-wrap"><canvas id="cC"></canvas></div>
  </div>
  <div class="cc">
    <div class="cc-head"><span class="cc-tit">👤 Valor por Supervisor</span></div>
    <div class="cc-wrap"><canvas id="cS"></canvas></div>
  </div>
  <div class="cc">
    <div class="cc-head"><span class="cc-tit">📍 Top Destinos (Qtd)</span></div>
    <div class="cc-wrap"><canvas id="cD"></canvas></div>
  </div>
</div>

<div class="tc">
  <div class="tc-head">
    <span class="tc-tit">📋 Registro de Transferências</span>
    <div class="tc-filters">
      <input class="si" type="text" id="busca" placeholder="🔍 Buscar..." style="width:175px" oninput="filtrar()"/>
      <select class="si" id="fdData" onchange="filtrar()">
        <option value="">Todas as datas</option>
        {filter_datas_html}
      </select>
      <select class="si" id="fdStatus" onchange="filtrar()">
        <option value="">Todos os status</option>
        <option value="pendente">⏳ Pendentes</option>
        <option value="roteirizado">✅ Roteirizadas</option>
      </select>
    </div>
  </div>
  <div class="tc-wrap">
    <table>
      <thead>
        <tr>
          <th>Data</th><th>Nota</th><th>Pedido</th><th>Cliente</th>
          <th>Supervisor</th><th>Praça</th><th>Carregamento</th>
          <th>Destino</th><th>Peso(kg)</th><th>Valor</th>
          <th>Placa</th><th>Status</th><th></th>
        </tr>
      </thead>
      <tbody id="tbody">{rows_html}</tbody>
    </table>
  </div>
  <div class="tc-foot">
    <span id="cnt">{len(trans)} registro(s)</span>
    <a href="/exportar" style="color:var(--acc);font-size:0.75rem;text-decoration:none;font-weight:700">⬇️ Exportar Excel</a>
  </div>
</div>"""

    scripts = f"""
const DS  = {json.dumps(ds)};
const NV  = {json.dumps([round(por_data[d]['v'],2) for d in ds])};
const NN  = {json.dumps([por_data[d]['n'] for d in ds])};
const NP  = {json.dumps([round(por_data[d]['p'],2) for d in ds])};
const TCC = {json.dumps([[x[0],round(x[1],2)] for x in top_cli])};
const SL  = {json.dumps(list(sups.keys()))};
const SV  = {json.dumps([round(v,2) for v in sups.values()])};
const DL  = {json.dumps([x[0] for x in top_dest])};
const DV  = {json.dumps([x[1] for x in top_dest])};

const PAL = ['#ff6b2b','#3b82f6','#22c55e','#a855f7','#eab308','#ef4444','#06b6d4','#f97316','#8b5cf6','#10b981'];
Chart.defaults.color = '#6b7585';
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.font.size = 11;

function mkGrid(col='#2a2f3a') {{
  return {{ x:{{grid:{{color:col}}, border:{{color:col}}}}, y:{{grid:{{color:col}}, border:{{color:col}}, beginAtZero:true}} }};
}}

if (DS.length) {{
  new Chart(document.getElementById('cV'), {{
    type:'line',
    data:{{ labels:DS, datasets:[{{ label:'Valor', data:NV,
      borderColor:'#ff6b2b', backgroundColor:'rgba(255,107,43,0.1)',
      borderWidth:2.5, pointBackgroundColor:'#ff6b2b', pointRadius:4,
      tension:0.35, fill:true }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{display:false}}, tooltip:{{callbacks:{{label:c=>fmt(c.raw)}}}} }},
      scales: mkGrid() }}
  }});
  new Chart(document.getElementById('cN'), {{
    type:'bar',
    data:{{ labels:DS, datasets:[{{ label:'Notas', data:NN,
      backgroundColor:'rgba(59,130,246,0.7)', borderRadius:4, borderSkipped:false }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{display:false}} }},
      scales: mkGrid() }}
  }});
  new Chart(document.getElementById('cP'), {{
    type:'line',
    data:{{ labels:DS, datasets:[{{ label:'Peso', data:NP,
      borderColor:'#22c55e', backgroundColor:'rgba(34,197,94,0.1)',
      borderWidth:2, pointBackgroundColor:'#22c55e', pointRadius:3,
      tension:0.35, fill:true }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{display:false}}, tooltip:{{callbacks:{{label:c=>fmtPeso(c.raw)}}}} }},
      scales: mkGrid() }}
  }});
}}

if (TCC.length) {{
  new Chart(document.getElementById('cC'), {{
    type:'bar',
    data:{{ labels:TCC.map(x=>x[0]), datasets:[{{ label:'Valor', data:TCC.map(x=>x[1]),
      backgroundColor:PAL.slice(0,TCC.length), borderRadius:4, borderSkipped:false }}] }},
    options:{{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{display:false}}, tooltip:{{callbacks:{{label:c=>fmt(c.raw)}}}} }},
      scales: mkGrid() }}
  }});
}}

if (SL.length) {{
  new Chart(document.getElementById('cS'), {{
    type:'bar',
    data:{{ labels:SL, datasets:[{{ label:'Valor', data:SV,
      backgroundColor:PAL.slice(0,SL.length), borderRadius:4, borderSkipped:false }}] }},
    options:{{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{display:false}}, tooltip:{{callbacks:{{label:c=>fmt(c.raw)}}}} }},
      scales: mkGrid() }}
  }});
}}

if (DL.length) {{
  new Chart(document.getElementById('cD'), {{
    type:'doughnut',
    data:{{ labels:DL, datasets:[{{ data:DV, backgroundColor:PAL, borderWidth:0, hoverOffset:4 }}] }},
    options:{{ responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{position:'right', labels:{{boxWidth:11, padding:12}}}} }} }}
  }});
}}

function filtrar() {{
  const q  = document.getElementById('busca').value.toLowerCase();
  const fd = document.getElementById('fdData').value;
  const fs = document.getElementById('fdStatus').value;
  let n = 0;
  document.querySelectorAll('#tbody tr[data-id]').forEach(r => {{
    const ok = (!fd || r.dataset.dt === fd)
            && (!fs || r.dataset.status === fs)
            && (!q  || r.textContent.toLowerCase().includes(q));
    r.style.display = ok ? '' : 'none';
    if (ok) n++;
  }});
  document.getElementById('cnt').textContent = n + ' registro(s)';
}}

async function excluir(id) {{
  if (!confirm('Remover esta transferência?')) return;
  const r = await fetch('/api/excluir/' + id, {{method:'DELETE'}});
  if ((await r.json()).ok) location.reload();
  else toast('❌ Erro ao excluir', 'te');
}}
"""
    return Response(page("Dashboard", body, scripts, "dash"), mimetype="text/html")

# ── LISTA FATURAMENTO ──────────────────────────────────────────────────────────
@app.route("/lista-fat")
def lista_fat():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM transferencias ORDER BY dt_transferencia DESC, id DESC").fetchall()
    trans = [dict(r) for r in rows]

    def br(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    rows_html = ""
    if not trans:
        rows_html = '<tr><td colspan="13"><div class="empty"><div class="empty-icon">📋</div><div class="empty-txt">Nenhuma transferência ainda.</div></div></td></tr>'
    for t in trans:
        st = t.get("status") or "pendente"
        row_cls = "row-done" if st == "roteirizado" else "row-pend"
        st_badge = (f'<span class="badge badge-grn">✅ Roteirizado</span>' if st == "roteirizado"
                    else f'<span class="badge badge-red">⏳ Pendente</span>')
        placa_txt = (f'<span class="mono" style="color:var(--yel);font-weight:700">{t["placa"]}</span>'
                     if t.get("placa") else '<span style="color:var(--mut)">—</span>')
        obs_txt = t.get("obs") or ""
        rows_html += f"""<tr class="{row_cls}" data-id="{t['id']}" data-dt="{t['dt_transferencia']}" data-status="{st}">
<td><span class="badge badge-acc mono">{t['dt_transferencia']}</span></td>
<td class="mono" style="font-weight:700">{t['numnota']}</td>
<td class="mono">{t.get('numped','') or '—'}</td>
<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{t['nomecliente'] or '—'}</td>
<td><span class="badge badge-blu">{t['nomesup'] or '—'}</span></td>
<td><span class="badge badge-mut">{t.get('praca') or '—'}</span></td>
<td>{t['numcarregamento'] or '—'}</td>
<td>{t['destino'] or '—'}</td>
<td class="mono">{(t['pesobrutotot'] or 0):.3f}</td>
<td class="mono" style="font-weight:700">{br(t['vltotal'] or 0)}</td>
<td>{placa_txt}</td>
<td>{st_badge}</td>
<td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt2)" title="{obs_txt}">{obs_txt or '—'}</td>
<td><button class="btn btn-red btn-sm" onclick="excluir({t['id']})">🗑</button></td>
</tr>"""

    datas_html = "".join(
        f'<option value="{d}">{d}</option>'
        for d in sorted(set(t["dt_transferencia"] for t in trans), reverse=True)
    )

    body = f"""
<div class="ph">
  <div class="ph-left">
    <div class="ph-tag fat">🧾 Faturamento</div>
    <h1>Histórico de Transferências</h1>
    <div class="ph-sub">Todas as notas registradas — {len(trans)} registro(s)</div>
  </div>
  <div class="ph-acts">
    <a href="/exportar" class="btn btn-ghost">⬇️ Exportar Excel</a>
    <a href="/nova" class="btn btn-acc">➕ Nova Transferência</a>
  </div>
</div>

<div class="tc">
  <div class="tc-head">
    <span class="tc-tit">📋 Todas as Transferências</span>
    <div class="tc-filters">
      <input class="si" type="text" id="busca" placeholder="🔍 Buscar..." style="width:175px" oninput="filtrar()"/>
      <select class="si" id="fdData" onchange="filtrar()">
        <option value="">Todas as datas</option>{datas_html}
      </select>
      <select class="si" id="fdStatus" onchange="filtrar()">
        <option value="">Todos os status</option>
        <option value="pendente">⏳ Pendentes</option>
        <option value="roteirizado">✅ Roteirizadas</option>
      </select>
    </div>
  </div>
  <div class="tc-wrap">
    <table>
      <thead>
        <tr>
          <th>Data</th><th>Nota</th><th>Pedido</th><th>Cliente</th>
          <th>Supervisor</th><th>Praça</th><th>Carregamento</th>
          <th>Destino</th><th>Peso(kg)</th><th>Valor</th>
          <th>Placa</th><th>Status</th><th>Obs</th><th></th>
        </tr>
      </thead>
      <tbody id="tbody">{rows_html}</tbody>
    </table>
  </div>
  <div class="tc-foot">
    <span id="cnt">{len(trans)} registro(s)</span>
  </div>
</div>"""

    scripts = """
function filtrar() {
  const q  = document.getElementById('busca').value.toLowerCase();
  const fd = document.getElementById('fdData').value;
  const fs = document.getElementById('fdStatus').value;
  let n = 0;
  document.querySelectorAll('#tbody tr[data-id]').forEach(r => {
    const ok = (!fd || r.dataset.dt === fd)
            && (!fs || r.dataset.status === fs)
            && (!q  || r.textContent.toLowerCase().includes(q));
    r.style.display = ok ? '' : 'none';
    if (ok) n++;
  });
  document.getElementById('cnt').textContent = n + ' registro(s)';
}
async function excluir(id) {
  if (!confirm('Remover esta transferência?')) return;
  const r = await fetch('/api/excluir/' + id, {method:'DELETE'});
  if ((await r.json()).ok) location.reload();
  else toast('❌ Erro ao excluir', 'te');
}
"""
    return Response(page("Histórico", body, scripts, "fat"), mimetype="text/html")

# ── NOVA TRANSFERÊNCIA ─────────────────────────────────────────────────────────
@app.route("/nova")
def nova():
    hoje = date.today().isoformat()
    body = f"""
<div class="ph">
  <div class="ph-left">
    <div class="ph-tag fat">🧾 Faturamento</div>
    <h1>Nova Transferência</h1>
    <div class="ph-sub">Registre a transferência de nota para a Roteirização</div>
  </div>
  <a href="/dashboard" class="btn btn-ghost">← Dashboard</a>
</div>

<div class="two-col">
  <!-- FORMULÁRIO -->
  <div class="form-card">
    <div class="form-sec">📝 Registro de Transferência</div>

    <div class="form-g">
      <label>📅 Data da Transferência *</label>
      <input class="fi" type="date" id="dt" value="{hoje}"/>
    </div>

    <div class="form-g">
      <label>🔍 Número da Nota (NUMNOTA) *</label>
      <div style="display:flex;gap:.5rem">
        <input class="fi mono" type="text" id="nota" placeholder="Ex: 398234" style="flex:1"
          onkeydown="if(event.key==='Enter')buscar()"/>
        <button class="btn btn-acc" onclick="buscar()" id="btnB" style="flex-shrink:0">Buscar</button>
      </div>
      <div id="alerta" style="margin-top:0.5rem"></div>
    </div>

    <div id="dados" style="display:none">
      <div class="road-box">
        <div class="road-box-tit">✅ Dados encontrados na base ROAD</div>
        <div class="form-row">
          <div class="form-g"><label>Pedido</label><input class="fi mono" id="fPed" readonly/></div>
          <div class="form-g"><label>Nota Fiscal</label><input class="fi mono" id="fNota" readonly/></div>
        </div>
        <div class="form-g"><label>Cliente</label><input class="fi" id="fCli" readonly/></div>
        <div class="form-row">
          <div class="form-g"><label>Supervisor</label><input class="fi" id="fSup" readonly/></div>
          <div class="form-g"><label>Praça</label><input class="fi" id="fPraca" readonly/></div>
        </div>
        <div class="form-row">
          <div class="form-g"><label>Carregamento</label><input class="fi mono" id="fCar" readonly/></div>
          <div class="form-g"><label>Destino</label><input class="fi" id="fDest" readonly/></div>
        </div>
        <div class="form-row">
          <div class="form-g"><label>Peso Bruto (kg)</label><input class="fi mono" id="fPeso" readonly/></div>
          <div class="form-g"><label>Valor Total</label><input class="fi mono" id="fVal" readonly/></div>
        </div>
      </div>

      <div class="form-g">
        <label>💬 Observação (opcional)</label>
        <textarea class="fi" id="fObs" rows="2" placeholder="Alguma observação adicional..."></textarea>
      </div>

      <button class="btn btn-acc" style="width:100%;padding:.75rem;font-size:0.95rem;justify-content:center"
        onclick="salvar()" id="btnS">
        🚛 Confirmar Transferência
      </button>
    </div>
  </div>

  <!-- LATERAL -->
  <div>
    <!-- Hoje -->
    <div class="side-card" style="margin-bottom:1rem;border-color:rgba(255,107,43,0.2)">
      <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:var(--txt2);margin-bottom:1rem">
        📅 Transferidas Hoje ({hoje})
      </div>
      <div id="listaHoje"><div style="color:var(--mut);text-align:center;padding:1.5rem;font-size:.85rem">Carregando...</div></div>
      <div style="display:flex;justify-content:space-between;padding-top:.85rem;margin-top:.5rem;border-top:1px solid var(--bdr);font-size:.8rem;color:var(--txt2)">
        <span>Notas: <strong id="tHoje" style="color:var(--txt)">0</strong></span>
        <span>Valor: <strong id="vHoje" style="color:var(--acc)">R$ 0,00</strong></span>
      </div>
    </div>

    <!-- Instruções -->
    <div class="side-card">
      <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.09em;color:var(--txt2);margin-bottom:1rem">💡 Como usar</div>
      <ol style="font-size:.83rem;color:var(--txt2);padding-left:1.2rem;line-height:2.2">
        <li>Selecione a <strong style="color:var(--txt)">data</strong> da transferência</li>
        <li>Digite o <strong style="color:var(--txt)">número da nota</strong> e pressione <kbd style="background:var(--sur2);border:1px solid var(--bdr);border-radius:4px;padding:0 4px;font-size:.75rem">Enter</kbd></li>
        <li>Dados preenchidos <strong style="color:var(--acc)">automaticamente</strong> do ROAD</li>
        <li>Adicione observação se necessário</li>
        <li>Clique em <strong style="color:var(--txt)">Confirmar Transferência</strong></li>
      </ol>
      <div style="margin-top:1rem;padding:.75rem;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:9px;font-size:.82rem;color:var(--grn2)">
        🗺️ Após registrar, a nota ficará <strong>pendente</strong> até a Roteirização informar a placa.
      </div>
    </div>
  </div>
</div>"""

    scripts = f"""
const HOJE = '{hoje}';
let cur = null;

async function buscar() {{
  const nota = document.getElementById('nota').value.trim();
  if (!nota) {{ al('Informe o número da nota.', 'e'); return; }}
  const btn = document.getElementById('btnB');
  btn.innerHTML = '<span class="spin"></span> Buscando...';
  btn.disabled = true;
  try {{
    const r = await fetch('/api/buscar?nota=' + encodeURIComponent(nota));
    const d = await r.json();
    btn.textContent = 'Buscar'; btn.disabled = false;
    if (d.erro) {{
      al('❌ ' + d.erro, 'e');
      document.getElementById('dados').style.display = 'none';
      cur = null; return;
    }}
    cur = d;
    document.getElementById('fPed').value   = d.numped || '—';
    document.getElementById('fNota').value  = d.numnota;
    document.getElementById('fCli').value   = d.nomecliente;
    document.getElementById('fSup').value   = d.nomesup;
    document.getElementById('fPraca').value = d.praca || '—';
    document.getElementById('fCar').value   = d.numcarregamento;
    document.getElementById('fPeso').value  = Number(d.pesobrutotot).toFixed(3).replace('.', ',') + ' kg';
    document.getElementById('fVal').value   = fmt(d.vltotal);
    document.getElementById('fDest').value  = d.destino;
    document.getElementById('dados').style.display = 'block';
    al('', '');
  }} catch(e) {{
    btn.textContent = 'Buscar'; btn.disabled = false;
    al('Erro de conexão com o servidor.', 'e');
  }}
}}

async function salvar() {{
  if (!cur) return;
  const dt = document.getElementById('dt').value;
  if (!dt) {{ al('Selecione a data.', 'e'); return; }}
  const btn = document.getElementById('btnS');
  btn.innerHTML = '<span class="spin"></span> Salvando...';
  btn.disabled = true;
  try {{
    const r = await fetch('/api/salvar', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        dt_transferencia: dt,
        numped: cur.numped,
        numnota: cur.numnota,
        nomecliente: cur.nomecliente,
        nomesup: cur.nomesup,
        praca: cur.praca,
        pesobrutotot: cur.pesobrutotot,
        numcarregamento: cur.numcarregamento,
        vltotal: cur.vltotal,
        destino: cur.destino,
        obs: document.getElementById('fObs').value,
      }})
    }});
    const d = await r.json();
    btn.textContent = '🚛 Confirmar Transferência'; btn.disabled = false;
    if (d.ok) {{
      toast('✅ Transferência registrada! Nota pendente.', 'ts');
      document.getElementById('nota').value = '';
      document.getElementById('fObs').value = '';
      document.getElementById('dados').style.display = 'none';
      cur = null;
      carregarHoje();
    }} else {{
      al('Erro: ' + (d.erro || 'Tente novamente.'), 'e');
    }}
  }} catch(e) {{
    btn.textContent = '🚛 Confirmar Transferência'; btn.disabled = false;
    al('Erro de conexão.', 'e');
  }}
}}

function al(msg, tipo) {{
  const el = document.getElementById('alerta');
  el.innerHTML = msg ? `<div class="alert alert-${{tipo === 'e' ? 'e' : 's'}}">${{msg}}</div>` : '';
}}

async function carregarHoje() {{
  try {{
    const r = await fetch('/api/lista');
    const lista = await r.json();
    const hj = lista.filter(t => t.dt_transferencia === HOJE);
    const c = document.getElementById('listaHoje');
    if (!hj.length) {{
      c.innerHTML = '<div style="color:var(--mut);text-align:center;padding:1.5rem;font-size:.85rem">Nenhuma transferência hoje.</div>';
      document.getElementById('tHoje').textContent = '0';
      document.getElementById('vHoje').textContent = 'R$ 0,00';
      return;
    }}
    let tv = 0;
    c.innerHTML = hj.map(t => {{
      tv += t.vltotal || 0;
      const st = t.status || 'pendente';
      const stEl = st === 'roteirizado'
        ? `<span style="font-size:.68rem;color:var(--grn)">✅ ${{t.placa}}</span>`
        : `<span style="font-size:.68rem;color:var(--red)">⏳ Pendente</span>`;
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--bdr);font-size:.82rem">
        <div>
          <span class="mono" style="font-weight:700">${{t.numnota}}</span>
          <span style="color:var(--txt2);margin-left:.5rem">${{(t.nomecliente||'').slice(0,22)}}</span>
        </div>
        <div style="text-align:right">
          <div style="color:var(--acc);font-weight:700;font-size:.78rem">${{fmt(t.vltotal)}}</div>
          ${{stEl}}
        </div>
      </div>`;
    }}).join('');
    document.getElementById('tHoje').textContent = hj.length;
    document.getElementById('vHoje').textContent = fmt(tv);
  }} catch(e) {{}}
}}
carregarHoje();
"""
    return Response(page("Nova Transferência", body, scripts, "fat"), mimetype="text/html")

# ── ROTEIRIZAÇÃO ───────────────────────────────────────────────────────────────
@app.route("/roteirizacao")
def roteirizacao():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM transferencias ORDER BY dt_transferencia DESC, id DESC").fetchall()
    trans = [dict(r) for r in rows]

    pendentes = [t for t in trans if (t.get("status") or "pendente") == "pendente"]
    roteiriz  = [t for t in trans if (t.get("status") or "pendente") == "roteirizado"]

    def br(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    def make_row_pend(t):
        return f"""<tr class="row-pend" data-id="{t['id']}" data-nota="{t['numnota']}"
             data-cli="{(t['nomecliente'] or '').replace('"','')}" data-dest="{t['destino'] or ''}">
<td><span class="badge badge-acc mono">{t['dt_transferencia']}</span></td>
<td class="mono" style="font-weight:700">{t['numnota']}</td>
<td class="mono">{t.get('numped','') or '—'}</td>
<td>{t['nomecliente'] or '—'}</td>
<td><span class="badge badge-blu">{t['nomesup'] or '—'}</span></td>
<td><span class="badge badge-mut">{t.get('praca') or '—'}</span></td>
<td>{t['destino'] or '—'}</td>
<td class="mono">{(t['pesobrutotot'] or 0):.3f}</td>
<td class="mono" style="font-weight:700">{br(t['vltotal'] or 0)}</td>
<td>
  <button class="btn btn-grn btn-sm" onclick="abrirModal({t['id']},'{t['numnota']}','{(t['nomecliente'] or '').replace(chr(39),chr(92)+chr(39))}','{(t['destino'] or '').replace(chr(39),chr(92)+chr(39))}','{t.get('praca') or ''}')">
    🚗 Informar Placa
  </button>
</td>
</tr>"""

    def make_row_rot(t):
        return f"""<tr class="row-done" data-id="{t['id']}" data-nota="{t['numnota']}">
<td><span class="badge badge-acc mono">{t['dt_transferencia']}</span></td>
<td class="mono" style="font-weight:700">{t['numnota']}</td>
<td class="mono">{t.get('numped','') or '—'}</td>
<td>{t['nomecliente'] or '—'}</td>
<td><span class="badge badge-blu">{t['nomesup'] or '—'}</span></td>
<td><span class="badge badge-mut">{t.get('praca') or '—'}</span></td>
<td>{t['destino'] or '—'}</td>
<td class="mono">{(t['pesobrutotot'] or 0):.3f}</td>
<td class="mono" style="font-weight:700">{br(t['vltotal'] or 0)}</td>
<td><span class="mono" style="color:var(--yel);font-weight:800;font-size:.9rem">🚗 {t.get('placa','')}</span></td>
<td>
  <button class="btn btn-ghost btn-sm" onclick="abrirModal({t['id']},'{t['numnota']}','{(t['nomecliente'] or '').replace(chr(39),chr(92)+chr(39))}','{(t['destino'] or '').replace(chr(39),chr(92)+chr(39))}','{t.get('praca') or ''}','{t.get('placa','')}')" title="Editar placa">✏️</button>
  <button class="btn btn-red btn-sm" onclick="removerPlaca({t['id']})" title="Devolver para pendente">↩️</button>
</td>
</tr>"""

    pend_rows = "".join(make_row_pend(t) for t in pendentes) if pendentes else \
        '<tr><td colspan="10"><div class="empty"><div class="empty-icon">✅</div><div class="empty-txt">Nenhuma nota pendente!</div></div></td></tr>'

    rot_rows = "".join(make_row_rot(t) for t in roteiriz) if roteiriz else \
        '<tr><td colspan="11"><div class="empty"><div class="empty-icon">📋</div><div class="empty-txt">Nenhuma nota roteirizada ainda.</div></div></td></tr>'

    datas_pend = sorted(set(t["dt_transferencia"] for t in pendentes), reverse=True)
    datas_pend_html = "".join(f'<option value="{d}">{d}</option>' for d in datas_pend)

    peso_pend = sum(t["pesobrutotot"] or 0 for t in pendentes)
    val_pend  = sum(t["vltotal"] or 0 for t in pendentes)
    peso_rot  = sum(t["pesobrutotot"] or 0 for t in roteiriz)
    val_rot   = sum(t["vltotal"] or 0 for t in roteiriz)

    body = f"""
<div class="ph">
  <div class="ph-left">
    <div class="ph-tag rot">🗺️ Roteirização</div>
    <h1>Roteirizar Notas</h1>
    <div class="ph-sub">Informe a placa do veículo para cada nota transferida</div>
  </div>
  <a href="/dashboard" class="btn btn-ghost">← Dashboard</a>
</div>

<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:1.5rem">
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--red),#f87171)"></div>
    <div class="kpi-lbl">⏳ Pendentes</div>
    <div class="kpi-val" style="color:var(--red)">{len(pendentes)}</div>
    <div class="kpi-sub">{br(val_pend)} · {peso_pend:,.1f} kg</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar" style="background:linear-gradient(90deg,var(--grn),var(--grn2))"></div>
    <div class="kpi-lbl">✅ Roteirizadas</div>
    <div class="kpi-val" style="color:var(--grn)">{len(roteiriz)}</div>
    <div class="kpi-sub">{br(val_rot)} · {peso_rot:,.1f} kg</div>
  </div>
</div>

<!-- PENDENTES -->
<div class="tc" style="margin-bottom:1.5rem;border-color:rgba(239,68,68,0.25)">
  <div class="tc-head" style="border-bottom-color:rgba(239,68,68,0.2)">
    <span class="tc-tit" style="color:#f87171">⏳ Notas Pendentes de Roteirização</span>
    <div class="tc-filters">
      <input class="si" type="text" id="buscaPend" placeholder="🔍 Buscar..." style="width:175px" oninput="filtrarPend()"/>
      <select class="si" id="fdDataPend" onchange="filtrarPend()">
        <option value="">Todas as datas</option>{datas_pend_html}
      </select>
    </div>
  </div>
  <div class="tc-wrap">
    <table>
      <thead>
        <tr><th>Data</th><th>Nota</th><th>Pedido</th><th>Cliente</th>
        <th>Supervisor</th><th>Praça</th><th>Destino</th>
        <th>Peso(kg)</th><th>Valor</th><th>Ação</th></tr>
      </thead>
      <tbody id="tbodyPend">{pend_rows}</tbody>
    </table>
  </div>
  <div class="tc-foot"><span id="cntPend">{len(pendentes)} pendente(s)</span></div>
</div>

<!-- ROTEIRIZADAS -->
<div class="tc" style="border-color:rgba(34,197,94,0.25)">
  <div class="tc-head" style="border-bottom-color:rgba(34,197,94,0.2)">
    <span class="tc-tit" style="color:var(--grn2)">✅ Notas Roteirizadas</span>
    <div class="tc-filters">
      <input class="si" type="text" id="buscaRot" placeholder="🔍 Buscar..." style="width:175px" oninput="filtrarRot()"/>
    </div>
  </div>
  <div class="tc-wrap">
    <table>
      <thead>
        <tr><th>Data</th><th>Nota</th><th>Pedido</th><th>Cliente</th>
        <th>Supervisor</th><th>Praça</th><th>Destino</th>
        <th>Peso(kg)</th><th>Valor</th><th>Placa</th><th>Ações</th></tr>
      </thead>
      <tbody id="tbodyRot">{rot_rows}</tbody>
    </table>
  </div>
  <div class="tc-foot"><span id="cntRot">{len(roteiriz)} roteirizada(s)</span></div>
</div>

<!-- MODAL PLACA -->
<div class="modal-bg" id="modalBg" onclick="if(event.target===this)fecharModal()">
  <div class="modal">
    <div class="modal-tit">🚗 Informar Placa do Veículo</div>
    <div class="modal-info" id="modalInfo"></div>
    <div class="form-g">
      <label>Placa *</label>
      <input class="fi mono" type="text" id="inputPlaca"
        placeholder="Ex: ABC-1234 ou ABC1D23"
        style="text-transform:uppercase;font-size:1.15rem;font-weight:800;letter-spacing:.1em;text-align:center"
        oninput="this.value=this.value.toUpperCase()"
        onkeydown="if(event.key==='Enter')confirmarPlaca()"/>
      <div id="modalAlerta" style="margin-top:0.5rem"></div>
    </div>
    <div style="display:flex;gap:.7rem;margin-top:1.5rem">
      <button class="btn btn-ghost" style="flex:1" onclick="fecharModal()">Cancelar</button>
      <button class="btn btn-grn" style="flex:2;justify-content:center;padding:.7rem" onclick="confirmarPlaca()" id="btnConf">
        ✅ Confirmar Placa
      </button>
    </div>
  </div>
</div>"""

    scripts = """
let modalId = null;

function abrirModal(id, nota, cli, dest, praca, placaAtual='') {
  modalId = id;
  document.getElementById('modalInfo').innerHTML = `
    <div class="info-item"><span class="info-lbl">Nota Fiscal</span><span class="info-val mono">${nota}</span></div>
    <div class="info-item"><span class="info-lbl">Cliente</span><span class="info-val">${cli}</span></div>
    <div class="info-item"><span class="info-lbl">Praça</span><span class="info-val">${praca||'—'}</span></div>
    <div class="info-item" style="border-bottom:none"><span class="info-lbl">Destino</span><span class="info-val">${dest||'—'}</span></div>
  `;
  document.getElementById('inputPlaca').value = placaAtual;
  document.getElementById('modalAlerta').innerHTML = '';
  document.getElementById('modalBg').classList.add('open');
  setTimeout(() => document.getElementById('inputPlaca').focus(), 150);
}

function fecharModal() {
  document.getElementById('modalBg').classList.remove('open');
  modalId = null;
}

async function confirmarPlaca() {
  const placa = document.getElementById('inputPlaca').value.trim();
  if (!placa) {
    document.getElementById('modalAlerta').innerHTML = '<div class="alert alert-e">Informe a placa.</div>';
    return;
  }
  const btn = document.getElementById('btnConf');
  btn.innerHTML = '<span class="spin"></span> Salvando...';
  btn.disabled = true;
  try {
    const r = await fetch('/api/roteirizar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: modalId, placa})
    });
    const d = await r.json();
    btn.textContent = '✅ Confirmar Placa'; btn.disabled = false;
    if (d.ok) {
      fecharModal();
      toast('🚗 Placa ' + placa + ' registrada com sucesso!', 'ts');
      setTimeout(() => location.reload(), 1200);
    } else {
      document.getElementById('modalAlerta').innerHTML = '<div class="alert alert-e">Erro ao salvar. Tente novamente.</div>';
    }
  } catch(e) {
    btn.textContent = '✅ Confirmar Placa'; btn.disabled = false;
    document.getElementById('modalAlerta').innerHTML = '<div class="alert alert-e">Erro de conexão.</div>';
  }
}

async function removerPlaca(id) {
  if (!confirm('Remover a placa desta nota? Ela voltará para pendentes.')) return;
  const r = await fetch('/api/remover-placa/' + id, {method:'POST'});
  if ((await r.json()).ok) {
    toast('↩️ Nota devolvida para pendentes.', 'ti');
    setTimeout(() => location.reload(), 1000);
  } else toast('❌ Erro', 'te');
}

function filtrarPend() {
  const q  = document.getElementById('buscaPend').value.toLowerCase();
  const fd = document.getElementById('fdDataPend').value;
  let n = 0;
  document.querySelectorAll('#tbodyPend tr[data-id]').forEach(r => {
    const ok = (!fd || r.querySelector('td:first-child').textContent.includes(fd))
            && (!q  || r.textContent.toLowerCase().includes(q));
    r.style.display = ok ? '' : 'none';
    if (ok) n++;
  });
  document.getElementById('cntPend').textContent = n + ' pendente(s)';
}

function filtrarRot() {
  const q = document.getElementById('buscaRot').value.toLowerCase();
  let n = 0;
  document.querySelectorAll('#tbodyRot tr[data-id]').forEach(r => {
    const ok = !q || r.textContent.toLowerCase().includes(q);
    r.style.display = ok ? '' : 'none';
    if (ok) n++;
  });
  document.getElementById('cntRot').textContent = n + ' roteirizada(s)';
}
"""
    return Response(page("Roteirização", body, scripts, "rot"), mimetype="text/html")

# ── APIs ───────────────────────────────────────────────────────────────────────
@app.route("/api/buscar")
def api_buscar():
    nota = request.args.get("nota", "").strip()
    if not nota:
        return jsonify({"erro": "Informe o número da nota."})
    d = buscar_nota(nota)
    if d is None:
        return jsonify({"erro": f"Nota '{nota}' não encontrada na base ROAD."})
    return jsonify(d)

@app.route("/api/salvar", methods=["POST"])
def api_salvar():
    d = request.json
    if not d.get("numnota") or not d.get("dt_transferencia"):
        return jsonify({"erro": "Campos obrigatórios ausentes."}), 400
    # Verifica duplicata no mesmo dia
    with get_db() as conn:
        dup = conn.execute(
            "SELECT id FROM transferencias WHERE numnota=? AND dt_transferencia=?",
            (d["numnota"], d["dt_transferencia"])
        ).fetchone()
        if dup:
            return jsonify({"erro": f"Nota {d['numnota']} já registrada nesta data."})
        conn.execute("""INSERT INTO transferencias
          (dt_transferencia,numped,numnota,nomecliente,nomesup,praca,pesobrutotot,
           numcarregamento,vltotal,destino,obs,status)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,'pendente')""",
          (d["dt_transferencia"], d.get("numped",""), d["numnota"],
           d.get("nomecliente",""), d.get("nomesup",""), d.get("praca",""),
           d.get("pesobrutotot",0), d.get("numcarregamento",""),
           d.get("vltotal",0), d.get("destino",""), d.get("obs","")))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/roteirizar", methods=["POST"])
def api_roteirizar():
    d = request.json
    tid   = d.get("id")
    placa = (d.get("placa") or "").strip().upper()
    if not tid or not placa:
        return jsonify({"erro": "Dados incompletos."}), 400
    hoje = date.today().isoformat()
    with get_db() as conn:
        conn.execute("""UPDATE transferencias
          SET placa=?, dt_roteirizacao=?, status='roteirizado' WHERE id=?""",
          (placa, hoje, tid))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/remover-placa/<int:tid>", methods=["POST"])
def api_remover_placa(tid):
    with get_db() as conn:
        conn.execute("""UPDATE transferencias
          SET placa=NULL, dt_roteirizacao=NULL, status='pendente' WHERE id=?""", (tid,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/excluir/<int:tid>", methods=["DELETE"])
def api_excluir(tid):
    with get_db() as conn:
        conn.execute("DELETE FROM transferencias WHERE id=?", (tid,))
        conn.commit()
    return jsonify({"ok": True})

@app.route("/api/lista")
def api_lista():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transferencias ORDER BY dt_transferencia DESC, id DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/exportar")
def exportar():
    import io
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transferencias ORDER BY dt_transferencia DESC"
        ).fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Transferencias")
    output.seek(0)
    return send_file(
        output,
        download_name=f"transferencias_{date.today().isoformat()}.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── INICIALIZAÇÃO ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = "seu-ip-local"

    print("\n" + "="*60)
    print("  🚛  SISTEMA DE TRANSFERÊNCIAS — TRANSF")
    print("="*60)
    print(f"  Local  :  http://localhost:5000")
    print(f"  Rede   :  http://{ip}:5000   ← compartilhe este link")
    print(f"  Banco  :  {DB_PATH}")
    print(f"  ROAD   :  {ROAD_PATH}")
    print("="*60)
    print("  Para que outros acessem: use o endereço de Rede acima")
    print("  ou configure um proxy reverso (nginx/ngrok).")
    print("="*60 + "\n")

    try:
        from waitress import serve
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "waitress", "--quiet"])
        from waitress import serve

    serve(app, host="0.0.0.0", port=5000, threads=8)
