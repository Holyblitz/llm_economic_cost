-- Schéma brut et table finale

CREATE TABLE IF NOT EXISTS raw_openai_pricing (
  fetched_at TIMESTAMP DEFAULT NOW(),
  model TEXT,
  price_per_million_input NUMERIC,
  price_per_million_output NUMERIC,
  currency TEXT,
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS raw_anthropic_pricing (
  fetched_at TIMESTAMP DEFAULT NOW(),
  model TEXT,
  price_per_million_input NUMERIC,
  price_per_million_output NUMERIC,
  currency TEXT,
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS raw_vast_gpu_market (
  fetched_at TIMESTAMP DEFAULT NOW(),
  gpu_model TEXT,
  hourly_price_usd NUMERIC,
  location TEXT,
  provider_id TEXT,
  spot BOOLEAN,
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS raw_lambda_gpu_pricing (
  fetched_at TIMESTAMP DEFAULT NOW(),
  gpu_model TEXT,
  hourly_price_usd NUMERIC,
  instance_type TEXT,
  notes TEXT,
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS raw_eia_electricity (
  fetched_at TIMESTAMP DEFAULT NOW(),
  date DATE,
  price_usd_per_kwh NUMERIC,
  sector TEXT,
  region TEXT,
  source_series_id TEXT,
  source_url TEXT
);

-- Table finale (alignée avec ton schéma existant)
CREATE TABLE IF NOT EXISTS llm_economics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    company VARCHAR(50) NOT NULL,
    run_rate_revenue_usd NUMERIC,
    tokens_volume_est_m NUMERIC,
    mix_mini_pct NUMERIC,
    mix_flagship_pct NUMERIC,
    gpu_type_mini VARCHAR(20),
    gpu_type_flagship VARCHAR(20),
    gpu_price_hour_mini NUMERIC,
    gpu_price_hour_flagship NUMERIC,
    gpu_power_w_mini NUMERIC,
    gpu_power_w_flagship NUMERIC,
    throughput_tok_s_mini NUMERIC,
    throughput_tok_s_flagship NUMERIC,
    pue NUMERIC,
    electricity_price_usd_kwh NUMERIC,
    cost_per_million_tokens_usd NUMERIC,
    price_per_million_tokens_usd NUMERIC,
    gross_margin_pct NUMERIC
);
