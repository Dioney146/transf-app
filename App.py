# ═══════════════════════════════════════════════════════════════════════════════
# HISTÓRICO  —  versão sem cabeçalho exposto e sem legendas de gráfico visíveis
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋  Histórico":

    # ── Gráficos: Vendedor (colunas+linha) + Veículo (barras horiz) ──────────
    _gc1, _gc2 = st.columns([3, 2])

    with _gc1:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-head">'
            '<span class="chart-title" style="color:#ef4444">Notas Fiscais por Vendedor · Qtd + Valor</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="chart-body">', unsafe_allow_html=True)

        _rows_vend2 = _top_vend.to_dict("records") if not _top_vend.empty else []
        if not df_all.empty and "nomevend" in df_all.columns:
            _vend_qtd2 = df_all.groupby("nomevend")["numnota"].count().reset_index()
            _vend_qtd2.columns = ["vendedor", "qtd"]
            _vend_val2 = df_all.groupby("nomevend")["vltotal"].sum().reset_index()
            _vend_val2.columns = ["vendedor", "valor"]
            _tv2 = _vend_qtd2.merge(_vend_val2, on="vendedor", how="left").fillna(0)
            _tv2 = _tv2.sort_values("valor", ascending=False).head(7)
            _rows_vend2 = _tv2.to_dict("records")

        def _fmt_brl(v):
            s = f"{int(round(v)):,}".replace(",", ".")
            return f"R {s}"

        st.markdown(
            _svg_col_line(
                _rows_vend2,
                label_key="vendedor", val_key="valor", qtd_key="qtd",
                bar_color_1="#ef4444", bar_color_2="#b91c1c",
                line_color="#fbbf24",
                fmt_val=_fmt_brl,
            ),
            unsafe_allow_html=True,
        )
        # legenda inline (pequena, dentro do card — não visível fora)
        st.markdown(
            '<div style="display:flex;align-items:center;gap:6px;margin-top:6px;padding:0 .25rem">'
            '<svg width="22" height="10" style="flex-shrink:0"><line x1="0" y1="5" x2="14" y2="5" stroke="#fbbf24" stroke-width="2"/>'
            '<circle cx="18" cy="5" r="3.5" fill="#fbbf24"/></svg>'
            '<span style="font-size:.68rem;color:#7d95b5">Linha = quantidade de NFs</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)

    with _gc2:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.markdown(
            '<div class="chart-head">'
            '<span class="chart-title" style="color:#34d399">Notas Fiscais por Veículo · Qtd</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="chart-body">', unsafe_allow_html=True)

        _rows_veic2 = []
        if not df_all.empty and "placa_road" in df_all.columns:
            _df_veic2 = df_all[df_all["placa_road"].notna() & (df_all["placa_road"].astype(str).str.strip() != "")]
            if not _df_veic2.empty:
                _top_veic2 = _df_veic2.groupby("placa_road")["numnota"].count().sort_values(ascending=False).head(7).reset_index()
                _top_veic2.columns = ["placa", "qtd"]
                _rows_veic2 = _top_veic2.to_dict("records")
        st.markdown(
            _svg_bar_horiz(
                _rows_veic2,
                label_key="placa", val_key="qtd",
                bar_color_1="#34d399", bar_color_2="#10b981",
                fmt_val=lambda v: f"{int(v)} NFs",
            ),
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)

    # ── Filtros: busca + status + supervisor + excel ──────────────────────────
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

    # ── Filtro por data de saída ──────────────────────────────────────────────
    st.markdown(
        '<div style="margin-top:10px;margin-bottom:2px;display:flex;align-items:center;gap:8px">'
        '<span style="font-size:.68rem;font-weight:600;color:#7d95b5;text-transform:uppercase;letter-spacing:.08em">&#128197; Filtrar por Data de Sa&#237;da</span>'
        '<div style="flex:1;height:1px;background:rgba(255,255,255,0.07)"></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    hf5, hf6, _hf_spacer = st.columns([1.3, 1.3, 4])
    with hf5:
        dt_saida_de = st.date_input(
            "Dt. Saída — De",
            value=None, key="h_dt_saida_de", format="DD/MM/YYYY", label_visibility="visible",
        )
    with hf6:
        dt_saida_ate = st.date_input(
            "Dt. Saída — Até",
            value=None, key="h_dt_saida_ate", format="DD/MM/YYYY", label_visibility="visible",
        )

    # ── Filtro por nova placa ─────────────────────────────────────────────────
    hf7, _hf_spacer2 = st.columns([1.3, 5.3])
    with hf7:
        _placas_opts = (
            ["Todos"] + sorted(df_all["placa_veiculo"].dropna().unique().tolist())
            if not df_all.empty and "placa_veiculo" in df_all.columns
            else ["Todos"]
        )
        filtro_nova_placa = st.selectbox("Nova Placa", _placas_opts, key="h_nova_placa", label_visibility="visible")

    # ── Aplicar filtros no dataframe ──────────────────────────────────────────
    df_h = df_all.copy() if not df_all.empty else pd.DataFrame(columns=TCOLS)
    if not df_h.empty:
        df_h = df_h[df_h["dt_transferencia"] == data_str]
        if fst != "Todos":
            df_h = df_h[df_h["status"] == fst]
        if fsup != "Todos":
            df_h = df_h[df_h["nomesup"] == fsup]
        if filtro_nova_placa != "Todos" and "placa_veiculo" in df_h.columns:
            df_h = df_h[df_h["placa_veiculo"] == filtro_nova_placa]
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

    _hist_front = ["placa_road", "placa_veiculo", "observacao"]
    _hist_rest  = [c for c in STD_COLS + ["dt_saida", "status", "observacao"] if c not in _hist_front]
    HIST_COLS = [c for c in _hist_front + _hist_rest if c in df_h.columns]
    HIST_CONFIG = {
        **STD_CONFIG,
        "placa_veiculo": st.column_config.TextColumn("Nova Placa",  width=110),
        "dt_saida":      st.column_config.TextColumn("Dt. Saída",   width=100),
        "status":        st.column_config.TextColumn("Status",      width=110),
        "observacao":    st.column_config.TextColumn("Observação",  width=220),
    }

    # ── Card da tabela ────────────────────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-head">
      <span class="card-title">Registros</span>
      <span class="card-count">{len(df_h)} resultados</span>
    </div>
    """, unsafe_allow_html=True)

    if df_h.empty:
        st.markdown(
            '<div style="padding:1.5rem"><div class="al-i">Nenhum registro encontrado para os filtros selecionados.</div></div>',
            unsafe_allow_html=True,
        )
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
