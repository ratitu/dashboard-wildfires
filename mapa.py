import folium
from folium.plugins import Fullscreen, HeatMap, MarkerCluster, TimestampedGeoJson


def _popup_html(idx, row):
    return (
        f"<b>Município:</b> {row['Municipio']}<br>"
        f"<b>Data:</b> {idx.strftime('%d/%m/%Y %H:%M')}<br>"
        f"<b>Satélite:</b> {row.get('satelite', 'N/D')}<br>"
        f"<b>Bioma:</b> {row.get('bioma', 'N/D')}<br>"
        f"<b>Risco de Fogo:</b> {row.get('risco_fogo', 'N/D')}<br>"
        f"<b>FRP:</b> {row.get('frp', 'N/D')}"
    )


def layer_temporal(df):
    features = []
    for idx, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["Longitude"], row["Latitude"]],
            },
            "properties": {
                "time": idx.strftime("%Y-%m-%dT%H:%M:%S"),
                "popup": _popup_html(idx, row),
                "icon": "circle",
                "iconstyle": {
                    "fillColor": "#e63946",
                    "fillOpacity": 0.8,
                    "stroke": "false",
                    "radius": 6,
                },
            },
        })
    return TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period="PT1H",
        duration="PT0S",
        transition_time=300,
        loop=False,
        auto_play=False,
        add_last_point=True,
    )


def plot_mapa(df_filtrado, rmc_geojson, destaque=None, animacao=False):
    if destaque:
        mapa = folium.Map(location=[destaque[0], destaque[1]], zoom_start=13)
    else:
        mapa = folium.Map(location=[-22.9, -47.05], zoom_start=10)

    folium.GeoJson(
        rmc_geojson, name="Limites RMC",
        style_function=lambda x: {"color": "black", "weight": 2, "fillOpacity": 0}
    ).add_to(mapa)

    if df_filtrado is not None and not df_filtrado.empty:
        heat_data = df_filtrado[["Latitude", "Longitude"]].values.tolist()
        HeatMap(heat_data, radius=10, name="Mapa de Calor", blur=10).add_to(mapa)

        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Esri Satellite",
            overlay=False,
            control=True,
        ).add_to(mapa)

        marker_cluster = MarkerCluster(name="Focos de Queimadas")
        for idx, row in df_filtrado.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(_popup_html(idx, row), max_width=300),
                icon=folium.Icon(color="red", icon="fire", icon_color="white"),
            ).add_to(marker_cluster)
        marker_cluster.add_to(mapa)

        if animacao:
            layer_temporal(df_filtrado).add_to(mapa)

        folium.LayerControl(position="topright").add_to(mapa)

    if destaque:
        folium.Marker(
            location=[destaque[0], destaque[1]],
            popup=folium.Popup("Foco selecionado na tabela", max_width=200),
            icon=folium.Icon(color="blue", icon="star", icon_color="white"),
        ).add_to(mapa)

    Fullscreen().add_to(mapa)
    return mapa
