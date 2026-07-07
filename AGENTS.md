# AGENTS.md

## Stack
- Python 3 + Streamlit (single-page dashboard)
- Dependencies pinned in `requirements.txt`
- Conda environment expected (`.vscode/settings.json`)

## Codebase
- Single entrypoint: `app_queimadas_v2.py` (all UI + logic in one file)
- Language: Portuguese (PT-BR) — code, comments, UI text, variable names
- No tests, no lint/typecheck config, no CI pipeline
- No monorepo tooling or build steps

## Data
- **Real-time** wildfire data from INPE (daily CSV, last 15 days):
  `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_YYYYMMDD.csv`
- INPE data is UTF-8 encoded, auto-downloaded at startup and cached for 1 hour (`@st.cache_data ttl=3600`)
- Wildfire records are spatially filtered to the RMC polygon (spatial join of lat/lon points with shapefile)
- RMC boundary: `dataset/RMC_Municipios_2024.shp` (+ companion .dbf, .prj, .shx, .cpg) — EPSG:4674
- **Requires internet at runtime** (no longer uses local Excel file)
- Legacy static file `dataset/QUEIMADAS_2019_2024_TOTAL.xlsx` is no longer used

## Commands
- Install: `pip install -r requirements.txt`
- Run: `streamlit run app_queimadas_v2.py` → http://localhost:8501

## Deployment
- Streamlit Cloud: `app-queimadas.streamlit.app`
- Deploys from GitHub `main` branch automatically
