# llm_economic_cost

# LLM Economics Time-Series ETL

Pipeline pour collecter **des données réelles** (scraping + API) et construire une série temporelle mensuelle (OpenAI, Anthropic) sur les **coûts d'inférence** et le **prix d'abonnement break-even**.

## Structure

```
llm_timeseries_etl/
├─ src/
│  ├─ fetch_openai_pricing.py
│  ├─ fetch_anthropic_pricing.py
│  ├─ fetch_vast_api.py
│  ├─ fetch_lambda_gpu.py
│  ├─ fetch_eia.py
│  ├─ build_monthly_series.py
│  └─ sql/
│     ├─ create_raw_tables.sql
│     └─ build_views.sql
├─ requirements.txt
├─ .env.example
└─ README.md
```

## Prérequis

- Python 3.10+
- PostgreSQL (optionnel si tu veux charger directement la série)
- Variables d'environnement (voir `.env.example`)

## Installation rapide

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Édite .env pour ajouter ta clé EIA (obligatoire) et, si dispo, ta clé Vast.ai
```

## Usage (local CSVs d'abord)

```bash
# 1) Récupérer les prix API (OpenAI/Anthropic)
python src/fetch_openai_pricing.py --out data/openai_pricing.csv
python src/fetch_anthropic_pricing.py --out data/anthropic_pricing.csv

# 2) Récupérer prix GPU (Vast + Lambda)
python src/fetch_vast_api.py --out data/vast_gpu_market.csv
python src/fetch_lambda_gpu.py --out data/lambda_gpu_pricing.csv

# 3) Récupérer prix électricité (EIA, mensuel)
python src/fetch_eia.py --series 'EBA.CM.PRICE.US.M' --out data/eia_electricity_us_commercial.csv

# 4) Construire la série mensuelle complète (coûts, break-even)
python src/build_monthly_series.py --start 2023-08 --end 2026-09 --out data/llm_economics_monthly.csv
```

## Chargement dans PostgreSQL

```sql
-- Crée les tables "raw_*" et "facts"
\i src/sql/create_raw_tables.sql

-- (Optionnel) Crée des vues de calcul (coût / 1M tokens dynamique, break-even)
\i src/sql/build_views.sql

-- Charger depuis CSV (exemple)
\COPY raw_openai_pricing FROM 'data/openai_pricing.csv' CSV HEADER;
\COPY raw_anthropic_pricing FROM 'data/anthropic_pricing.csv' CSV HEADER;
\COPY raw_vast_gpu_market FROM 'data/vast_gpu_market.csv' CSV HEADER;
\COPY raw_lambda_gpu_pricing FROM 'data/lambda_gpu_pricing.csv' CSV HEADER;
\COPY raw_eia_electricity FROM 'data/eia_electricity_us_commercial.csv' CSV HEADER;

-- Charger la table finale si tu passes par CSV
\COPY llm_economics(...) FROM 'data/llm_economics_monthly.csv' CSV HEADER;
```

## Notes

- Les **revenus mensuels** (run-rate) resteront semi-manuels (points presse + interpolation). Ajoute un `data/revenues_press.csv` avec colonnes: `date,company,run_rate_revenue_usd,source_url`.
- Les sélecteurs CSS peuvent évoluer : code **défensif** + logs.
- Le calcul **break-even** se fait *dynamiquement* à partir des intrants (pas d'écriture de coût figé).
