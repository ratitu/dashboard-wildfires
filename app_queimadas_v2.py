import streamlit as st
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap, Fullscreen, MarkerCluster
from datetime import datetime, timedelta
import urllib.request
import io

st.set_page_config(
    page_title="Monitoramento de Queimadas na Região Metropolitana de Campinas",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "dias" not in st.session_state:
    st.session_state.dias = 15

URL_BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil"

def _fetch_csv(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as f:
            raw = f.read()
        if len(raw) < 50:
            return None
        return pd.read_csv(io.BytesIO(raw), encoding='utf-8')
    except Exception:
        return None

@st.cache_data(ttl=3600)
def load_data(dias):
    rmc = gpd.read_file("dataset/RMC_Municipios_2024.shp")

    hoje = datetime.now()
    urls = [
        f"{URL_BASE}/focos_diario_br_{(hoje - timedelta(days=i)).strftime('%Y%m%d')}.csv"
        for i in range(dias)
    ]

    registros = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_csv, u): u for u in urls}
        for fut in as_completed(futures):
            df = fut.result()
            if df is not None:
                df.columns = [c.strip().lower() for c in df.columns]
                registros.append(df)

    if not registros:
        return None, None, None, rmc

    df = pd.concat(registros, ignore_index=True)

    for col in ['lat', 'lon']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['lat', 'lon'])

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['lon'], df['lat']),
        crs="EPSG:4326"
    )
    gdf = gdf.to_crs(rmc.crs)
    gdf = gdf.sjoin(rmc, how='inner', predicate='within')

    if gdf.empty:
        return None, None, None, rmc

    gdf['Data'] = pd.to_datetime(gdf['data_hora_gmt'], errors='coerce')
    gdf = gdf.dropna(subset=['Data'])
    gdf.set_index('Data', inplace=True)
    gdf['Número de Focos'] = 1
    gdf['Latitude'] = gdf['lat']
    gdf['Longitude'] = gdf['lon']
    gdf['Municipio'] = gdf['NM_MUN']

    df_q = gdf

    list_municipios = sorted(df_q['Municipio'].unique())
    data_inicio = df_q.index.min().strftime('%d/%m/%Y')
    data_fim = df_q.index.max().strftime('%d/%m/%Y')

    return df_q, list_municipios, (data_inicio, data_fim), rmc

df_queimadas, list_municipios, periodo, rmc = load_data(st.session_state.dias)

if df_queimadas is not None:
    agg_municipio = df_queimadas.groupby("Municipio")["Número de Focos"].sum()
    agg_diario = df_queimadas.resample("D")["Número de Focos"].sum()
    if "bioma" in df_queimadas.columns and df_queimadas["bioma"].notna().any():
        agg_bioma = df_queimadas.groupby("bioma")["Número de Focos"].sum()
    else:
        agg_bioma = None
    if "satelite" in df_queimadas.columns:
        agg_satelite = df_queimadas.groupby("satelite")["Número de Focos"].sum()
    else:
        agg_satelite = None
else:
    agg_municipio = agg_diario = agg_bioma = agg_satelite = None

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
    </style>
    """,
    unsafe_allow_html=True
)

def plot_mapa(municipios_selecionados=None):
    if df_queimadas is not None:
        df_filtrado = df_queimadas
        if municipios_selecionados:
            df_filtrado = df_queimadas[df_queimadas['Municipio'].isin(municipios_selecionados)]
    else:
        df_filtrado = None

    mapa = folium.Map(location=[-22.9, -47.05], zoom_start=10)

    folium.GeoJson(
        rmc_geojson, name="Limites RMC",
        style_function=lambda x: {'color': 'black', 'weight': 2, 'fillOpacity': 0}
    ).add_to(mapa)

    if df_filtrado is not None and not df_filtrado.empty:
        heat_data = df_filtrado[['Latitude', 'Longitude']].values.tolist()
        HeatMap(heat_data, radius=10, name="Mapa de Calor", blur=10).add_to(mapa)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Esri Satellite',
            overlay=False,
            control=True
        ).add_to(mapa)

        marker_cluster = MarkerCluster(name="Focos de Queimadas")
        for idx, row in df_filtrado.iterrows():
            popup_text = (
                f"<b>Município:</b> {row['Municipio']}<br>"
                f"<b>Data:</b> {idx.strftime('%d/%m/%Y %H:%M')}<br>"
                f"<b>Satélite:</b> {row.get('satelite', 'N/D')}<br>"
                f"<b>Bioma:</b> {row.get('bioma', 'N/D')}<br>"
                f"<b>Risco de Fogo:</b> {row.get('risco_fogo', 'N/D')}<br>"
                f"<b>FRP:</b> {row.get('frp', 'N/D')}"
            )
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                icon=folium.Icon(color="red", icon="fire", icon_color="white")
            ).add_to(marker_cluster)
        marker_cluster.add_to(mapa)
        folium.LayerControl(position="topright").add_to(mapa)

    Fullscreen().add_to(mapa)
    return mapa

horizontal_bar = "<hr style='margin-top: 0; margin-bottom: 0; height: 1px; border: 1px solid #FF9100DA;'><br>"

range_label = f"Últimos {st.session_state.dias} dias"

with st.sidebar:
    st.selectbox("Período:", [15, 30], index=0, key="dias")
    selected = option_menu(
        menu_title="Navegação",
        options=["Início", range_label, "Municípios e Satélites", "Mapa"],
        icons=["house", "bar-chart", "geo-alt", "map"],
        menu_icon="cast",
        default_index=0,
    )

if selected == "Início":
    st.subheader("🔥 Monitoramento de Queimadas na Região Metropolitana de Campinas")

    st.markdown(
        f"""
        <p style="font-size:15px;">
        Este aplicativo apresenta dados em tempo quase real dos focos de queimadas na
        <b>Região Metropolitana de Campinas (RMC)</b>.
        Os dados são obtidos automaticamente do <b>INPE</b> (Instituto Nacional de Pesquisas Espaciais)
        e abrangem os <b>últimos {st.session_state.dias} dias</b>.
        </p>
        <ul style="font-size:15px;">
        <li><b>{range_label}</b>: evolução diária dos focos de queimadas.</li>
        <li><b>Municípios e Satélites</b>: distribuição por município e satélite de origem.</li>
        <li><b>Mapa</b>: mapa interativo com mapa de calor e marcadores dos focos.</li>
        </ul>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    if df_queimadas is None:
        st.warning(f"Nenhum foco de queimada detectado na RMC nos últimos {st.session_state.dias} dias.")
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

        if agg_bioma is not None:
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
        df_diario = agg_diario.reset_index()
        df_diario["Data"] = df_diario["Data"].dt.strftime("%d/%m")

        fig_diario = px.bar(
            df_diario,
            x="Data",
            y="Número de Focos",
            title="Focos de Queimadas por Dia",
            color_discrete_sequence=["red"]
        )
        fig_diario.add_trace(go.Scatter(
            x=df_diario["Data"],
            y=df_diario["Número de Focos"].rolling(3, min_periods=1).mean(),
            mode="lines+markers",
            name="Média móvel (3 dias)",
            line=dict(color="yellow", width=2)
        ))
        fig_diario.update_layout(
            xaxis_title="Data",
            yaxis_title="Número de Focos",
            hoverlabel=dict(font_size=12, font_color="white"),
            hovermode="x unified"
        )
        st.plotly_chart(fig_diario, width='stretch')

        df_resumo = df_queimadas.groupby("Municipio").agg({
            "Número de Focos": "sum",
            "satelite": lambda x: x.nunique() if x.notna().any() else 0,
        }).rename(columns={"satelite": "Satélites"}).reset_index().sort_values("Número de Focos", ascending=False)
        st.dataframe(df_resumo, use_container_width=True, hide_index=True)

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
                st_folium(mapa_frp, width=800, height=400)
            else:
                st.caption("Clique em uma linha da tabela para ver o ponto no mapa.")

        st.markdown(horizontal_bar, True)

if selected == "Municípios e Satélites":
    st.subheader("Distribuição dos Focos por Município e Satélite")

    if df_queimadas is None:
        st.warning("Nenhum dado disponível para o período.")
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

        df_top_mun = (
            agg_municipio.reset_index()
            .sort_values("Número de Focos", ascending=True)
            .tail(num_municipios)
        )
        fig_mun = px.bar(
            df_top_mun,
            x="Número de Focos",
            y="Municipio",
            orientation="h",
            title=f"Top {num_municipios} Municípios {titulo_periodo}",
            color_discrete_sequence=["red"],
            height=600
        )
        fig_mun.update_layout(
            yaxis={"categoryorder": "total ascending"},
            hoverlabel=dict(font_size=12, font_color="white")
        )
        st.plotly_chart(fig_mun, width='stretch')

        if agg_satelite is not None:
            df_sat = (
                agg_satelite.reset_index()
                .sort_values("Número de Focos", ascending=True)
            )
            fig_sat = px.bar(
                df_sat,
                x="Número de Focos",
                y="satelite",
                orientation="h",
                title="Focos Detectados por Satélite",
                color_discrete_sequence=["orange"],
                height=400
            )
            fig_sat.update_layout(hoverlabel=dict(font_size=12, font_color="white"))
            st.plotly_chart(fig_sat, width='stretch')

        if agg_bioma is not None:
            df_bio = (
                agg_bioma.reset_index()
                .sort_values("Número de Focos", ascending=True)
            )
            fig_bio = px.bar(
                df_bio,
                x="Número de Focos",
                y="bioma",
                orientation="h",
                title="Focos por Bioma",
                color_discrete_sequence=["darkred"],
                height=300
            )
            fig_bio.update_layout(hoverlabel=dict(font_size=12, font_color="white"))
            st.plotly_chart(fig_bio, width='stretch')

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

    if periodo:
        st.markdown(f"**Período:** {periodo[0]} a {periodo[1]}")

    mapa = plot_mapa(municipios_sel if municipios_sel else None)
    st_folium(mapa, width=800, height=500)
    st.markdown(horizontal_bar, True)
