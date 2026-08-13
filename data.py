import io
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import geopandas as gpd
import pandas as pd
import streamlit as st

URL_BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil"

CATEGORIAS_RISCO = ["Baixo", "Médio", "Alto", "Crítico", "Sem dado"]


def _fetch_csv(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as f:
            raw = f.read()
        if len(raw) < 50:
            return None
        return pd.read_csv(io.BytesIO(raw), encoding="utf-8")
    except Exception:
        return None


def _servidor_online():
    try:
        with urllib.request.urlopen(URL_BASE, timeout=15) as f:
            f.read(1024)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def filtrar_rmc(df, rmc):
    for col in ["lat", "lon"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    )
    gdf = gdf.to_crs(rmc.crs)
    return gdf.sjoin(rmc, how="inner", predicate="within")


def preparar_gdf(gdf):
    gdf["Data"] = pd.to_datetime(gdf["data_hora_gmt"], errors="coerce")
    gdf = gdf.dropna(subset=["Data"])
    gdf.set_index("Data", inplace=True)
    gdf["Número de Focos"] = 1
    gdf["Latitude"] = gdf["lat"]
    gdf["Longitude"] = gdf["lon"]
    gdf["Municipio"] = gdf["NM_MUN"]
    return gdf


def separar_janelas(gdf, dias, hoje=None):
    hoje = hoje or datetime.now()
    data_corte = hoje - timedelta(days=dias)
    df_atual = gdf[gdf.index > data_corte]
    df_anterior = gdf[gdf.index <= data_corte]
    if df_atual.empty:
        df_atual = None
    if df_anterior.empty:
        df_anterior = None
    return df_atual, df_anterior


@st.cache_data(ttl=3600)
def load_data(dias):
    rmc = gpd.read_file("dataset/RMC_Municipios_2024.shp")

    hoje = datetime.now()
    urls = [
        f"{URL_BASE}/focos_diario_br_{(hoje - timedelta(days=i)).strftime('%Y%m%d')}.csv"
        for i in range(2 * dias)
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
        return None, None, None, None, rmc, _servidor_online()

    df = pd.concat(registros, ignore_index=True)
    gdf = filtrar_rmc(df, rmc)

    if gdf.empty:
        return None, None, None, None, rmc, True

    gdf = preparar_gdf(gdf)
    df_atual, df_anterior = separar_janelas(gdf, dias, hoje)

    if df_atual is None:
        return None, None, None, None, rmc, True

    list_municipios = sorted(df_atual["Municipio"].unique())
    data_inicio = df_atual.index.min().strftime("%d/%m/%Y")
    data_fim = df_atual.index.max().strftime("%d/%m/%Y")

    return df_atual, df_anterior, list_municipios, (data_inicio, data_fim), rmc, True


def calcular_agregacoes(df):
    if df is None:
        return None, None, None, None
    agg_municipio = df.groupby("Municipio")["Número de Focos"].sum()
    agg_diario = df.resample("D")["Número de Focos"].sum()
    agg_bioma = df.groupby("bioma")["Número de Focos"].sum() if "bioma" in df.columns else None
    agg_satelite = df.groupby("satelite")["Número de Focos"].sum() if "satelite" in df.columns else None
    return agg_municipio, agg_diario, agg_bioma, agg_satelite


def categoria_risco(v):
    if pd.isna(v) or v == -999:
        return "Sem dado"
    if v <= 25:
        return "Baixo"
    if v <= 50:
        return "Médio"
    if v <= 75:
        return "Alto"
    return "Crítico"


def df_para_tabela(df):
    df_pontos = pd.DataFrame({
        "Data": df.index.strftime("%d/%m/%Y %H:%M").values,
        "Município": df["Municipio"].values,
    })
    for nome, col in [("Satélite", "satelite"), ("Bioma", "bioma"),
                      ("Risco de Fogo", "risco_fogo"), ("FRP", "frp")]:
        if col in df.columns:
            df_pontos[nome] = df[col].values
    df_pontos["Latitude"] = df["Latitude"].values
    df_pontos["Longitude"] = df["Longitude"].values
    return df_pontos


def df_resumo_municipios(df):
    return df.groupby("Municipio").agg({
        "Número de Focos": "sum",
        "satelite": lambda x: x.nunique() if x.notna().any() else 0,
    }).rename(columns={"satelite": "Satélites"}).reset_index().sort_values(
        "Número de Focos", ascending=False
    )


def comparar_municipios(df_atual, df_anterior):
    atual = df_atual.groupby("Municipio")["Número de Focos"].sum()
    anterior = df_anterior.groupby("Municipio")["Número de Focos"].sum()
    comparacao = pd.DataFrame({"Atual": atual, "Anterior": anterior}).fillna(0)
    comparacao["Variação"] = comparacao["Atual"] - comparacao["Anterior"]
    return comparacao.sort_values("Variação", ascending=False)
