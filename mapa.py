import folium
from folium.plugins import Fullscreen, HeatMap, MarkerCluster, TimestampedGeoJson
from folium.template import Template

LEAFLET_JS_171 = "https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.js"
LEAFLET_CSS_171 = "https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/leaflet.css"

GUARD_JS = """(function () {
    var realUpdate = function () {
        if (this._map && this._map._animatingZoom) { return; }
        L.GridLayer.prototype._update.call(this);
        if (this._map) { this.fire("update"); }
    };
    var wrapped = function () {
        if (this._tdGuard) { return; }
        this._tdGuard = true;
        try {
            if (this._visible || !this._loaded) { this._originalUpdate.call(this); }
        } finally { this._tdGuard = false; }
    };
    L.TileLayer.include({ _originalUpdate: realUpdate, _update: wrapped });
})();"""


class _MapTemporal(folium.Map):
    """folium.Map com guarda anti-recursão para a animação temporal.

    O streamlit-folium dispara onRender duas vezes em rajada; as cargas
    concorrentes de leaflet-timedimension envolvem L.TileLayer.prototype._update
    duas vezes, e o shim acaba chamando a si mesmo (RangeError). Este template
    reinstala _update/_originalUpdate com guarda de reentrada antes de criar o
    mapa. Mantido em sincronia com o template de folium.Map (folium 0.19.4).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guard_js = GUARD_JS

    _template = Template(
        """
        {% macro header(this, kwargs) %}
            <meta name="viewport" content="width=device-width,
                initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
            <style>
                #{{ this.get_name() }} {
                    position: {{this.position}};
                    width: {{this.width[0]}}{{this.width[1]}};
                    height: {{this.height[0]}}{{this.height[1]}};
                    left: {{this.left[0]}}{{this.left[1]}};
                    top: {{this.top[0]}}{{this.top[1]}};
                }
                .leaflet-container { font-size: {{this.font_size}}; }
            </style>
        {% endmacro %}

        {% macro html(this, kwargs) %}
            <div class="folium-map" id={{ this.get_name()|tojson }} ></div>
        {% endmacro %}

        {% macro script(this, kwargs) %}
            {{ this.guard_js }}
            var {{ this.get_name() }} = L.map(
                {{ this.get_name()|tojson }},
                {
                    center: {{ this.location|tojson }},
                    crs: L.CRS.{{ this.crs }},
                    ...{{this.options|tojavascript}}

                }
            );

            {%- if this.control_scale %}
            L.control.scale().addTo({{ this.get_name() }});
            {%- endif %}

            {%- if this.zoom_control_position %}
            L.control.zoom( { position: {{ this.zoom_control|tojson }} } ).addTo({{ this.get_name() }});
            {%- endif %}

            {% if this.objects_to_stay_in_front %}
            function objects_in_front() {
                {%- for obj in this.objects_to_stay_in_front %}
                    {{ obj.get_name() }}.bringToFront();
                {%- endfor %}
            };
            {{ this.get_name() }}.on("overlayadd", objects_in_front);
            $(document).ready(objects_in_front);
            {%- endif %}

        {% endmacro %}
        """
    )


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
    tgj = TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period="PT24H",
        duration="PT0S",
        transition_time=300,
        loop=False,
        auto_play=True,
        add_last_point=True,
    )
    tgj.default_js = [
        (
            "jqueryui1.13.3",
            "https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.3/jquery-ui.min.js",
        ),
        (
            "iso8601",
            "https://cdn.jsdelivr.net/npm/iso8601-js-period@0.2.1/iso8601.min.js",
        ),
        (
            "leaflet.timedimension",
            "https://cdn.jsdelivr.net/npm/leaflet-timedimension@1.1.1/dist/leaflet.timedimension.min.js",
        ),
        (
            "moment",
            "https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.30.1/moment.min.js",
        ),
    ]
    tgj.default_css = [
        (
            "leaflet.timedimension_css",
            "https://cdn.jsdelivr.net/npm/leaflet-timedimension@1.1.1/dist/leaflet.timedimension.control.css",
        ),
    ]
    return tgj


def plot_mapa(df_filtrado, rmc_geojson, destaque=None, animacao=False):
    if destaque:
        location, zoom = [destaque[0], destaque[1]], 13
    else:
        location, zoom = [-22.9, -47.05], 10

    if animacao:
        mapa = _MapTemporal(location=location, zoom_start=zoom)
    else:
        mapa = folium.Map(location=location, zoom_start=zoom)

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
            mapa.default_js = [
                (n, LEAFLET_JS_171 if n == "leaflet" else u) for n, u in mapa.default_js
            ]
            mapa.default_css = [
                (n, LEAFLET_CSS_171 if n == "leaflet_css" else u)
                for n, u in mapa.default_css
            ]
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
