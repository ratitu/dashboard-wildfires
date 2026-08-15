import base64

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu

from data import (
    calcular_agregacoes,
    comparar_municipios,
    df_para_tabela,
    df_resumo_municipios,
    load_data,
)
from graficos import (
    fig_biomas,
    fig_comparacao,
    fig_diario,
    fig_horario,
    fig_risco,
    fig_satelites,
    fig_top_municipios,
)
from mapa import plot_mapa

st.set_page_config(
    page_title="Monitoramento de Queimadas na Região Metropolitana de Campinas",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "dias" not in st.session_state:
    st.session_state.dias = 15

df_queimadas, df_anterior, list_municipios, periodo, rmc, servidor_online = load_data(st.session_state.dias)

if not servidor_online:
    st.error(
        "O servidor de dados do INPE (**dataserver-coids.inpe.br**) está fora do ar e não é possível "
        "fazer o download dos dados de focos de queimadas. Tente novamente mais tarde.",
        icon="🚫",
    )

agg_municipio, agg_diario, agg_bioma, agg_satelite = calcular_agregacoes(df_queimadas)
bioma_tem_dados = agg_bioma is not None and not agg_bioma.empty

rmc_geojson = rmc.__geo_interface__

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background-color: #5f705e;
        padding: 15px;
        border-radius: 15px;
        border: 2px solid transparent;
        border-image: linear-gradient(45deg, #34322f, #76716b) 1;
        color: white;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover {
        transform: scale(1.03);
        box-shadow: 0px 6px 18px rgba(0,0,0,0.6);
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-size: 28px;
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #DDDDDD;
        font-size: 16px;
    }
    div[data-testid="stMetricDelta"] {
        color: #00FF00 !important;
        font-weight: bold;
    }
    div[data-testid="stMetricDelta"] svg {
        display: none !important;
    }
    @media (max-width: 700px) {
        div[data-testid="stMetric"] {
            padding: 10px;
        }
        div[data-testid="stMetricValue"] {
            font-size: 20px;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 12px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

horizontal_bar = "<hr style='margin-top: 0; margin-bottom: 0; height: 1px; border: 1px solid #FF9100DA;'><br>"

range_label = f"Últimos {st.session_state.dias} dias"

OPCOES = ["Início", range_label, "Análises", "Municípios e Satélites", "Município", "Mapa"]
ICONES = ["house", "bar-chart", "graph-up", "geo-alt", "search", "map"]


def _ir_para_mapa(municipio):
    st.session_state["municipio_map_selector"] = [municipio]
    st.session_state["pagina_alvo"] = OPCOES.index("Mapa")


def _aviso_sem_dados(msg_online):
    if not servidor_online:
        return
    st.warning(msg_online)


with st.sidebar:
    _logo_b64 = base64.b64encode(open("logo-no-background.png", "rb").read()).decode()
    st.markdown(
        f'<a href="https://www.instagram.com/passeionamata/" target="_blank">'
        f'<img src="data:image/png;base64,{_logo_b64}" style="width:50%;">'
        f'</a>',
        unsafe_allow_html=True,
    )
    st.selectbox("Período:", [15, 30], index=0, key="dias")
    pagina_alvo = st.session_state.pop("pagina_alvo", None)
    selected = option_menu(
        menu_title="Navegação",
        options=OPCOES,
        icons=ICONES,
        menu_icon="cast",
        default_index=0,
        manual_select=pagina_alvo,
    )

if selected == "Início":
    st.subheader("🔥 Monitoramento de Queimadas na Região Metropolitana de Campinas")

    st.markdown(
        f"""
        <div style="font-size:15px;">

        <p>
        Este aplicativo apresenta um <b>painel de monitoramento em tempo quase real</b> dos focos de
        queimadas detectados na <b>Região Metropolitana de Campinas (RMC)</b>.
        Ele consome automaticamente os dados do <b>INPE</b> (Instituto Nacional de Pesquisas Espaciais) —
        via satélites de referência do Programa Queimadas — abrangendo os <b>últimos {st.session_state.dias} dias</b>,
        disponíveis em
        <a href="https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/" target="_blank">https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/</a>.
        </p>

        <p>
        Cada foco registra data, hora, município, bioma, satélite de origem e o índice <b>FRP</b>
        (Fire Radiative Power), que estima a intensidade da queima. Com essas informações o painel permite:
        </p>

        <ul>
        <li><b>{range_label}</b>: evolução diária dos focos, resumo por município e tabela de focos por FRP.</li>
        <li><b>Análises</b>: distribuição horária, risco de fogo e comparação com o período anterior.</li>
        <li><b>Municípios e Satélites</b>: distribuição dos focos por município, satélite de origem e bioma.</li>
        <li><b>Município</b>: detalhamento de um município específico, com gráficos e tabela de focos.</li>
        <li><b>Mapa</b>: mapa interativo com mapa de calor, marcadores e animação temporal dia a dia.</li>
        </ul>

        <p>
        Os dados são filtrados espacialmente para o limite da RMC (IBGE 2024) e atualizados a cada passagem
        dos satélites, com cache de 1 hora.
        </p>

        <hr>
        <p style="font-size:13px; color:#999;">
        © <b>@passeionamata</b> · Este aplicativo está licenciado sob a
        <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank">CC BY-NC-SA 4.0</a>.
        O código-fonte está disponível em
        <a href="https://github.com/ratitu/dashboard-wildfires" target="_blank">github.com/ratitu/dashboard-wildfires</a>.
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    if df_queimadas is None:
        _aviso_sem_dados(f"Nenhum foco de queimada detectado na RMC nos últimos {st.session_state.dias} dias.")
    else:
        st.markdown(
            f'<p style="font-size:15px;">Panorama dos últimos {st.session_state.dias} dias:</p>',
            unsafe_allow_html=True
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            label="Município",
            value=agg_municipio.idxmax(),
            delta=f"{agg_municipio.max()} focos",
            border=True
        )

        if bioma_tem_dados:
            col2.metric(
                label="Bioma",
                value=agg_bioma.idxmax(),
                delta=f"{agg_bioma.max()} focos",
                border=True
            )
        else:
            col2.metric("Bioma", "N/D", border=True)

        col3.metric(
            label="Dia",
            value=agg_diario.idxmax().strftime("%d/%m/%Y"),
            delta=f"{agg_diario.max()} focos",
            border=True
        )

        col4.metric(
            label="Total",
            value=f"{df_queimadas['Número de Focos'].sum()} focos",
            delta=periodo[0] if periodo else "",
            border=True
        )

        st.markdown("---")

if selected == range_label:
    st.subheader("Evolução Diária dos Focos de Queimadas")

    if df_queimadas is None:
        st.warning("Nenhum dado disponível para o período.")
    else:
        st.plotly_chart(fig_diario(agg_diario), width='stretch')

        st.markdown("**Resumo por município**")
        st.dataframe(df_resumo_municipios(df_queimadas), use_container_width=True, hide_index=True)

        if "frp" in df_queimadas.columns:
            st.markdown(horizontal_bar, True)
            st.subheader("Focos por FRP (Crescente)")

            df_frp = pd.DataFrame({
                "Município": df_queimadas["Municipio"].values,
                "Data": df_queimadas.index.strftime("%d/%m/%Y %H:%M").values,
                "Satélite": df_queimadas["satelite"].values,
                "Bioma": df_queimadas["bioma"].values,
                "FRP": pd.to_numeric(df_queimadas["frp"], errors="coerce").values,
                "Latitude": df_queimadas["Latitude"].values,
                "Longitude": df_queimadas["Longitude"].values,
            })
            df_frp = df_frp.dropna(subset=["FRP"]).sort_values("FRP", ascending=True).reset_index(drop=True)

            event = st.dataframe(
                df_frp,
                on_select="rerun",
                selection_mode="single-row",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Latitude": None,
                    "Longitude": None,
                }
            )

            if event.selection and event.selection.rows:
                sel_row = event.selection.rows[0]
                lat = df_frp.iloc[sel_row]["Latitude"]
                lon = df_frp.iloc[sel_row]["Longitude"]
                mun = df_frp.iloc[sel_row]["Município"]
                frp_val = df_frp.iloc[sel_row]["FRP"]
                data_val = df_frp.iloc[sel_row]["Data"]

                mapa_frp = folium.Map(location=[lat, lon], zoom_start=12)
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(
                        f"<b>{mun}</b><br>Data: {data_val}<br>FRP: {frp_val}",
                        max_width=250
                    ),
                    icon=folium.Icon(color="red", icon="fire", icon_color="white")
                ).add_to(mapa_frp)
                st_folium(mapa_frp, use_container_width=True, height=400)
            else:
                st.caption("Clique em uma linha da tabela para ver o ponto no mapa.")

        st.markdown(horizontal_bar, True)

if selected == "Análises":
    st.subheader("Análises dos Focos de Queimadas")

    if df_queimadas is None:
        _aviso_sem_dados("Nenhum dado disponível para o período.")
    else:
        st.markdown("#### Distribuição por hora do dia")
        st.plotly_chart(fig_horario(df_queimadas), width='stretch')
        st.caption("Horários em GMT (UTC); os satélites polares sobrevoam a região no início da tarde.")
        st.markdown(horizontal_bar, True)

        fig_risco_atual = fig_risco(df_queimadas)
        if fig_risco_atual is not None:
            st.markdown("#### Risco de Fogo")
            st.plotly_chart(fig_risco_atual, width='stretch')
            st.markdown(horizontal_bar, True)

        st.markdown("#### Comparação com o período anterior")
        if df_anterior is not None and not df_anterior.empty:
            total_atual = int(df_queimadas["Número de Focos"].sum())
            total_anterior = int(df_anterior["Número de Focos"].sum())
            variacao = total_atual - total_anterior
            variacao_pct = (variacao / total_anterior * 100) if total_anterior else None

            c1, c2, c3 = st.columns(3)
            c1.metric("Período atual", f"{total_atual} focos", border=True)
            c2.metric("Período anterior", f"{total_anterior} focos", border=True)
            c3.metric(
                "Variação",
                f"{variacao:+,d} focos",
                delta=f"{variacao_pct:+.0f}%" if variacao_pct is not None else "—",
                delta_color="inverse",
                border=True
            )
            st.caption(
                f"Atual: {periodo[0]} a {periodo[1]} | "
                f"Anterior: {df_anterior.index.min().strftime('%d/%m/%Y')} a "
                f"{df_anterior.index.max().strftime('%d/%m/%Y')}"
            )

            serie_atual = df_queimadas.resample("D")["Número de Focos"].sum()
            serie_anterior = df_anterior.resample("D")["Número de Focos"].sum()
            st.plotly_chart(
                fig_comparacao(serie_atual, serie_anterior, "Período atual", "Período anterior"),
                width='stretch'
            )

            comp = comparar_municipios(df_queimadas, df_anterior)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Maiores altas por município**")
                st.dataframe(
                    comp.head(5)[["Anterior", "Atual", "Variação"]],
                    use_container_width=True,
                    hide_index=True
                )
            with col_b:
                st.markdown("**Maiores quedas por município**")
                st.dataframe(
                    comp.tail(5).iloc[::-1][["Anterior", "Atual", "Variação"]],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning(
                "Não há dados do período anterior disponíveis. "
                "O servidor do INPE mantém os arquivos diários por aproximadamente 30 dias; "
                "a comparação é mais confiável com períodos de 15 dias."
            )

        st.markdown(horizontal_bar, True)

if selected == "Municípios e Satélites":
    st.subheader("Distribuição dos Focos por Município e Satélite")

    if df_queimadas is None:
        _aviso_sem_dados("Nenhum dado disponível para o período.")
    else:
        col_sel, _, _ = st.columns([1.2, 2, 1])
        with col_sel:
            num_municipios = st.selectbox(
                "Número de municípios a exibir:",
                options=[5, 10, 15, 20],
                index=1,
                key="num_municipios_selector"
            )

        if periodo:
            titulo_periodo = f"({periodo[0]} a {periodo[1]})"
        else:
            titulo_periodo = ""

        st.plotly_chart(
            fig_top_municipios(agg_municipio, num_municipios, titulo_periodo),
            width='stretch'
        )

        if agg_satelite is not None:
            st.plotly_chart(fig_satelites(agg_satelite), width='stretch')

        if agg_bioma is not None:
            st.plotly_chart(fig_biomas(agg_bioma), width='stretch')

        st.markdown(horizontal_bar, True)

if selected == "Município":
    st.subheader("Detalhamento por Município")

    if df_queimadas is None or not list_municipios:
        _aviso_sem_dados("Nenhum dado disponível para o período.")
    else:
        col_sel, _, _ = st.columns([1.2, 2, 1])
        with col_sel:
            municipio = st.selectbox("Município:", list_municipios, key="municipio_detalhe_selector")

        df_mun = df_queimadas[df_queimadas["Municipio"] == municipio]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de focos", f"{int(df_mun['Número de Focos'].sum())}", border=True)
        c2.metric("Dias com focos", f"{df_mun.resample('D')['Número de Focos'].sum().size}", border=True)
        c3.metric(
            "Satélites",
            f"{df_mun['satelite'].nunique()}" if "satelite" in df_mun.columns else "N/D",
            border=True
        )
        c4.metric(
            "Biomas",
            f"{df_mun['bioma'].nunique()}" if "bioma" in df_mun.columns else "N/D",
            border=True
        )

        agg_diario_mun = df_mun.resample("D")["Número de Focos"].sum()
        st.plotly_chart(fig_diario(agg_diario_mun, titulo=f"Focos por Dia em {municipio}"), width='stretch')

        col_sat, col_bio = st.columns(2)
        with col_sat:
            if "satelite" in df_mun.columns:
                agg_sat_mun = df_mun.groupby("satelite")["Número de Focos"].sum()
                st.plotly_chart(fig_satelites(agg_sat_mun, titulo="Por Satélite", altura=350), width='stretch')
        with col_bio:
            if "bioma" in df_mun.columns:
                agg_bio_mun = df_mun.groupby("bioma")["Número de Focos"].sum()
                st.plotly_chart(fig_biomas(agg_bio_mun, titulo="Por Bioma", altura=350), width='stretch')

        fig_risco_mun = fig_risco(df_mun)
        if fig_risco_mun is not None:
            st.plotly_chart(fig_risco_mun, width='stretch')

        df_pontos_mun = df_para_tabela(df_mun)
        st.markdown(f"**Focos detectados em {municipio}**")
        event_mun = st.dataframe(
            df_pontos_mun,
            on_select="rerun",
            selection_mode="single-row",
            use_container_width=True,
            hide_index=True,
            key="tabela_focos_municipio",
            column_config={
                "Latitude": None,
                "Longitude": None,
                "FRP": st.column_config.NumberColumn("FRP", format="%.1f"),
            },
        )

        if event_mun.selection and event_mun.selection.rows:
            sel_mun = df_pontos_mun.iloc[event_mun.selection.rows[0]]
            lat = sel_mun["Latitude"]
            lon = sel_mun["Longitude"]
            mapa_mun = folium.Map(location=[lat, lon], zoom_start=12)
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(
                    f"<b>{sel_mun['Município']}</b><br>Data: {sel_mun['Data']}",
                    max_width=250
                ),
                icon=folium.Icon(color="red", icon="fire", icon_color="white")
            ).add_to(mapa_mun)
            st_folium(mapa_mun, use_container_width=True, height=400)
        else:
            st.caption("Clique em uma linha da tabela para ver o ponto no mapa.")

        if st.button(
            "Ver no mapa",
            on_click=_ir_para_mapa,
            args=(municipio,),
            use_container_width=True
        ):
            pass

        st.markdown(horizontal_bar, True)

if selected == "Mapa":
    st.subheader("Mapa de Calor dos Focos de Queimadas na RMC")

    col_sel_mapa, _, _ = st.columns([1, 2, 1])
    with col_sel_mapa:
        if df_queimadas is not None and list_municipios:
            municipios_sel = st.multiselect(
                "Filtrar por município:",
                options=list_municipios,
                default=[],
                key="municipio_map_selector"
            )
        else:
            municipios_sel = []
            st.multiselect(
                "Filtrar por município:",
                options=["Sem dados"],
                default=[],
                key="municipio_map_selector_empty",
                disabled=True
            )
        usar_temporal = st.checkbox("Animação temporal (dia a dia)", key="animacao_temporal")
        focos_individuais = st.checkbox(
            "Exibir focos individualmente (pontos vermelhos)",
            key="focos_individuais",
            value=False,
        )

    if periodo:
        st.markdown(f"**Período:** {periodo[0]} a {periodo[1]}")

    destaque = None
    df_pontos = None
    df_filtrado = None
    if df_queimadas is not None:
        df_filtrado = df_queimadas
        if municipios_sel:
            df_filtrado = df_queimadas[df_queimadas['Municipio'].isin(municipios_sel)]

        if st.session_state.get("filtro_mapa_anterior") != municipios_sel:
            st.session_state.pop("tabela_focos_mapa", None)
        st.session_state["filtro_mapa_anterior"] = municipios_sel

        if not df_filtrado.empty:
            df_pontos = df_para_tabela(df_filtrado)

            estado = st.session_state.get("tabela_focos_mapa")
            if estado:
                linhas = estado.get("selection", {}).get("rows", [])
                if linhas and linhas[0] < len(df_pontos):
                    linha = linhas[0]
                    destaque = (df_pontos.iloc[linha]["Latitude"], df_pontos.iloc[linha]["Longitude"])

    mapa = plot_mapa(df_filtrado, rmc_geojson, destaque=destaque, animacao=usar_temporal, pontos_individuais=focos_individuais)
    st_folium(mapa, use_container_width=True, height=500)

    if df_pontos is not None:
        st.subheader("Focos Detectados")

        event = st.dataframe(
            df_pontos,
            key="tabela_focos_mapa",
            on_select="rerun",
            selection_mode="single-row",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Latitude": None,
                "Longitude": None,
                "FRP": st.column_config.NumberColumn("FRP", format="%.1f"),
            },
        )

        if event.selection and event.selection.rows:
            sel = df_pontos.iloc[event.selection.rows[0]]
            st.caption(
                f"Foco selecionado: **{sel['Município']}** — {sel['Data']} "
                f"({sel['Latitude']:.4f}, {sel['Longitude']:.4f})"
            )
        else:
            st.caption("Clique em uma linha da tabela para destacar o foco no mapa.")
    else:
        st.warning("Nenhum foco detectado para a região selecionada.")
    st.markdown(horizontal_bar, True)

st.markdown("---")
st.markdown(
    '<p style="text-align:center; font-size:13px; color:#999;">'
    '© @passeionamata · Licenciado sob <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank">CC BY-NC-SA 4.0</a> · '
    'Código-fonte disponível em <a href="https://github.com/ratitu/dashboard-wildfires" target="_blank">GitHub</a>'
    '</p>',
    unsafe_allow_html=True
)

