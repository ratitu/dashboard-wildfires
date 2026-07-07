<div align="center">
  <h1 style="text-align: center; font-size: 2em;">
    🔥 Monitoramento de Focos de Queimadas na Região Metropolitana de Campinas 🚒
  </h1>
</div>

<p align="center">
  Dashboard em tempo real com dados do <b>INPE</b> (Instituto Nacional de Pesquisas Espaciais) dos focos de queimadas
  na <b>Região Metropolitana de Campinas (RMC)</b> — último 15 dias.
</p>

<div align="center">
  <a href="https://app-queimadas.streamlit.app/" target="_blank">
    <strong>🔥 Visite o App</strong>
  </a>
</div>

<br>

<div align="center">
  <a href="https://app-queimadas.streamlit.app/">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Streamlit Badge"/>
  </a>
</div>

<hr>

## 💻 Utilização

1. Clone o repositório:

```
git clone https://github.com/ratitu/dashboard-wildfires.git
```

2. Instale as dependências:

```
pip install -r requirements.txt
```

3. Rode o app:

```
streamlit run app_queimadas_v2.py
```

4. Acesse o app em seu navegador em: http://localhost:8501

> **Nota:** Requer conexão com a internet para baixar os dados mais recentes do INPE.

## 📡 Fonte dos dados

- **Focos de queimadas**: [INPE — Programa Queimadas](https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/)
  (CSV diário, últimos 15 dias, atualizado a cada passagem de satélite)
- **Limite municipal**: RMC — IBGE 2024 (EPSG:4674)
