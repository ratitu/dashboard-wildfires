# AGENTS.md

## Stack
- Python 3 + Streamlit (dashboard with pages via `streamlit_option_menu`)
- Dependencies pinned in `requirements.txt`
- Conda environment expected (`.vscode/settings.json`)

## Codebase
- Entrypoint: `app_queimadas_v2.py` (pages/UI only)
- Logic split into modules:
  - `data.py` — INPE download, `load_data`, spatial filter, aggregations, risk categories, table/comparison helpers
  - `mapa.py` — `plot_mapa`, `layer_temporal` (folium TimestampedGeoJson playback)
  - `graficos.py` — plotly chart builders
- Pages (nav): Início, Últimos N dias, Análises, Municípios e Satélites, Município, Mapa
- Language: Portuguese (PT-BR) — code, comments, UI text, variable names
- Tests in `tests/` (pytest); no lint/typecheck config, no CI pipeline
- No monorepo tooling or build steps

## Data
- **Real-time** wildfire data from INPE (daily CSV):
  `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_YYYYMMDD.csv`
- Fetches the last **2×N** days (parallel downloads) so the "Análises" page can compare the current window with the preceding one; daily files are only retained ~30 days by INPE, so comparison works best with N=15
- INPE data is UTF-8 encoded, auto-downloaded at startup and cached for 1 hour (`@st.cache_data ttl=3600`)
- `-999` is INPE's "no data" sentinel (not NaN) in `risco_fogo` / `numero_dias_sem_chuva` — handled in `categoria_risco`
- Wildfire records are spatially filtered to the RMC polygon (spatial join of lat/lon points with shapefile)
- RMC boundary: `dataset/RMC_Municipios_2024.shp` (+ companion .dbf, .prj, .shx, .cpg) — EPSG:4674
- **Requires internet at runtime** (no longer uses local Excel file)
- Legacy static file `dataset/QUEIMADAS_2019_2024_TOTAL.xlsx` is no longer used

## Commands
- Install: `pip install -r requirements.txt`
- Install dev deps: `pip install -r requirements-dev.txt`
- Run: `streamlit run app_queimadas_v2.py` → http://localhost:8501
- Test: `python -m pytest tests/`

## Deployment
- Streamlit Cloud: `app-queimadas.streamlit.app`
- Deploys from GitHub `main` branch automatically
