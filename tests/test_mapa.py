"""Testes de composição do mapa (flag `pontos_individuais`).

Cobre os dois modos de `plot_mapa`:
(a) OFF (default): HeatMap + MarkerCluster + Esri Satellite + LayerControl.
(b) ON: FeatureGroup "Focos Individuais" com CircleMarkers, sem HeatMap/MarkerCluster.

A fixture é construída inline (sem importar `app_queimadas_v2.py` nem `data.py`,
que disparariam download do INPE / dependências pesadas).
"""

import folium
import pandas as pd

from mapa import plot_mapa


def fixture_df():
    """DataFrame com DatetimeIndex e colunas usadas por `plot_mapa`."""
    idx = pd.date_range("2026-08-01 10:00", periods=4, freq="h")
    return pd.DataFrame({
        "Latitude": [-22.9, -23.0, -22.8, -23.1],
        "Longitude": [-47.05, -47.1, -47.0, -47.15],
        "Municipio": ["A", "B", "C", "D"],
        "satelite": ["S1", "S2", "S3", "S4"],
        "bioma": ["X", "Y", "X", "Y"],
        "risco_fogo": [10.0, 30.0, 60.0, 90.0],
        "frp": [5.0, 12.5, 20.0, 8.0],
    }, index=idx)


RMC_GEOJSON = {"type": "FeatureCollection", "features": []}


def coletar_camadas(mapa):
    """Lista de (classe, layer_name) de todos os children do mapa."""
    return [
        (type(child).__name__, getattr(child, "layer_name", None))
        for child in mapa._children.values()
    ]


def feature_group_focos(mapa):
    """FeatureGroup com layer_name == 'Focos Individuais' (ou None)."""
    for child in mapa._children.values():
        if isinstance(child, folium.FeatureGroup) and child.layer_name == "Focos Individuais":
            return child
    return None


def test_off_composicao_completa():
    """Flag OFF (default): composição atual completa, sem 'Focos Individuais'."""
    mapa = plot_mapa(fixture_df(), RMC_GEOJSON)
    camadas = coletar_camadas(mapa)

    # HeatMap com nome de exibição correto
    assert any(
        cls == "HeatMap" and nome == "Mapa de Calor" for cls, nome in camadas
    )

    # MarkerCluster com 4 Markers
    clusters = [
        child for child in mapa._children.values()
        if isinstance(child, folium.plugins.MarkerCluster)
    ]
    assert len(clusters) == 1
    mc = clusters[0]
    assert mc.layer_name == "Focos de Queimadas"
    marcadores = [
        v for v in mc._children.values() if isinstance(v, folium.Marker)
    ]
    assert len(marcadores) == 4

    # Camadas fixas da composição OFF
    assert any(
        cls == "TileLayer" and nome == "Esri Satellite" for cls, nome in camadas
    )
    assert any(cls == "LayerControl" for cls, nome in camadas)
    assert any(
        cls == "GeoJson" and nome == "Limites RMC" for cls, nome in camadas
    )
    assert any(cls == "Fullscreen" for cls, nome in camadas)

    # Modo ON não deve vazar para o modo OFF
    assert not any(nome == "Focos Individuais" for cls, nome in camadas)


def test_on_focos_individuais():
    """Flag ON: FeatureGroup com 4 CircleMarkers, sem HeatMap/MarkerCluster."""
    mapa = plot_mapa(fixture_df(), RMC_GEOJSON, pontos_individuais=True)
    camadas = coletar_camadas(mapa)

    # FeatureGroup "Focos Individuais" presente
    fg = feature_group_focos(mapa)
    assert fg is not None

    # 4 CircleMarkers com as opções esperadas
    circulos = [
        v for v in fg._children.values() if isinstance(v, folium.CircleMarker)
    ]
    assert len(circulos) == 4
    for cm in circulos:
        assert cm.options["radius"] == 4
        assert cm.options["color"] == "#e63946"
        assert cm.options["fill"] is True
        assert cm.options["fillColor"] == "#e63946"
        assert cm.options["fillOpacity"] == 0.8
        # Popup fica em _children sob chave gerada (popup_<uuid>)
        assert any(isinstance(v, folium.Popup) for v in cm._children.values())

    # Modo ON substitui HeatMap/MarkerCluster
    assert not any(cls == "HeatMap" for cls, nome in camadas)
    assert not any(cls == "MarkerCluster" for cls, nome in camadas)