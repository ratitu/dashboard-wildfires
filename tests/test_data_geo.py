from datetime import datetime

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from data import (
    calcular_agregacoes,
    comparar_municipios,
    df_para_tabela,
    filtrar_rmc,
    preparar_gdf,
    separar_janelas,
)


def gdf_rmc_fake():
    poligono = Polygon([
        (-48.0, -23.2),
        (-46.0, -23.2),
        (-46.0, -22.6),
        (-48.0, -22.6),
        (-48.0, -23.2),
    ])
    return gpd.GeoDataFrame(
        {"NM_MUN": ["Teste"]},
        geometry=[poligono],
        crs="EPSG:4674",
    )


def df_focos_fake():
    return pd.DataFrame({
        "lat": [-22.9, -23.5],
        "lon": [-47.05, -47.0],
        "data_hora_gmt": ["2026-07-15 12:00:00", "2026-07-15 12:30:00"],
        "municipio": ["Teste", "Fora"],
    })


def test_filtrar_rmc_mantem_apenas_pontos_dentro():
    rmc = gdf_rmc_fake()
    resultado = filtrar_rmc(df_focos_fake(), rmc)
    assert len(resultado) == 1
    assert resultado["municipio"].iloc[0] == "Teste"
    assert "NM_MUN" in resultado.columns


def test_preparar_gdf():
    rmc = gdf_rmc_fake()
    gdf = preparar_gdf(filtrar_rmc(df_focos_fake(), rmc))
    assert isinstance(gdf.index, pd.DatetimeIndex)
    assert "Número de Focos" in gdf.columns
    assert gdf["Número de Focos"].sum() == 1
    assert gdf["Municipio"].iloc[0] == "Teste"


def test_separar_janelas():
    idx = pd.to_datetime([
        "2026-07-01 10:00",
        "2026-07-10 10:00",
        "2026-07-20 10:00",
        "2026-07-25 10:00",
    ])
    gdf = pd.DataFrame({
        "Municipio": ["A", "B", "C", "D"],
        "Número de Focos": [1, 1, 1, 1],
        "Latitude": [-22.9] * 4,
        "Longitude": [-47.05] * 4,
    }, index=idx)
    hoje = datetime(2026, 7, 30, 12, 0, 0)
    atual, anterior = separar_janelas(gdf, 15, hoje)
    assert atual.index.tolist() == [
        pd.Timestamp("2026-07-20 10:00:00"),
        pd.Timestamp("2026-07-25 10:00:00"),
    ]
    assert anterior.index.tolist() == [
        pd.Timestamp("2026-07-01 10:00:00"),
        pd.Timestamp("2026-07-10 10:00:00"),
    ]


def test_calcular_agregacoes():
    idx = pd.to_datetime(["2026-07-20 10:00", "2026-07-21 11:00"])
    df = pd.DataFrame({
        "Municipio": ["A", "B"],
        "bioma": ["X", "Y"],
        "satelite": ["S1", "S2"],
        "Número de Focos": [1, 1],
    }, index=idx)
    agg_mun, agg_dia, agg_bio, agg_sat = calcular_agregacoes(df)
    assert dict(agg_mun) == {"A": 1, "B": 1}
    assert len(agg_dia) == 2
    assert dict(agg_bio) == {"X": 1, "Y": 1}
    assert dict(agg_sat) == {"S1": 1, "S2": 1}


def test_calcular_agregacoes_sem_colunas_opcionais():
    idx = pd.to_datetime(["2026-07-20 10:00"])
    df = pd.DataFrame({
        "Municipio": ["A"],
        "Número de Focos": [1],
    }, index=idx)
    agg_mun, agg_dia, agg_bio, agg_sat = calcular_agregacoes(df)
    assert dict(agg_mun) == {"A": 1}
    assert agg_bio is None
    assert agg_sat is None


def test_df_para_tabela():
    idx = pd.to_datetime(["2026-07-20 10:00"])
    df = pd.DataFrame({
        "Municipio": ["A"],
        "satelite": ["S1"],
        "bioma": ["X"],
        "risco_fogo": [30.0],
        "frp": [12.5],
        "Latitude": [-22.9],
        "Longitude": [-47.05],
    }, index=idx)
    tabela = df_para_tabela(df)
    assert list(tabela.columns) == [
        "Data", "Município", "Satélite", "Bioma", "Risco de Fogo", "FRP", "Latitude", "Longitude",
    ]
    assert tabela.iloc[0]["Município"] == "A"
    assert tabela.iloc[0]["Data"] == "20/07/2026 10:00"


def test_comparar_municipios():
    idx = pd.to_datetime(["2026-07-20 10:00", "2026-07-21 10:00"])
    atual = pd.DataFrame({
        "Municipio": ["A", "B"],
        "Número de Focos": [3, 1],
    }, index=idx)
    anterior = pd.DataFrame({
        "Municipio": ["A", "C"],
        "Número de Focos": [1, 5],
    }, index=idx)
    comp = comparar_municipios(atual, anterior)
    assert comp.loc["A", "Variação"] == 2
    assert comp.loc["B", "Variação"] == 1
    assert comp.loc["C", "Variação"] == -5
    assert comp.index[0] == "A"
