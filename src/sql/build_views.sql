-- Vue: coût / 1M tokens calculé dynamiquement (utilise les colonnes intrants)
CREATE OR REPLACE VIEW v_cost_per_1m_dynamic AS
WITH per_type AS (
  SELECT
    le.*,
    (1000000.0 / (NULLIF(le.throughput_tok_s_mini,0) * 3600.0))     AS gpu_hours_1m_mini,
    (1000000.0 / (NULLIF(le.throughput_tok_s_flagship,0) * 3600.0)) AS gpu_hours_1m_flagship
  FROM llm_economics le
),
costs AS (
  SELECT
    p.*,
    ((p.gpu_power_w_mini/1000.0)     * p.pue * p.gpu_hours_1m_mini     * p.electricity_price_usd_kwh) AS elec_cost_1m_mini,
    ((p.gpu_power_w_flagship/1000.0) * p.pue * p.gpu_hours_1m_flagship * p.electricity_price_usd_kwh) AS elec_cost_1m_flagship
  FROM per_type p
)
SELECT
  c.date, c.company,
  (c.gpu_hours_1m_mini * c.gpu_price_hour_mini + c.elec_cost_1m_mini)         AS total_1m_mini,
  (c.gpu_hours_1m_flagship * c.gpu_price_hour_flagship + c.elec_cost_1m_flagship) AS total_1m_flagship,
  ( (c.gpu_hours_1m_mini * c.gpu_price_hour_mini + c.elec_cost_1m_mini) * (c.mix_mini_pct/100.0)
   + (c.gpu_hours_1m_flagship * c.gpu_price_hour_flagship + c.elec_cost_1m_flagship) * (c.mix_flagship_pct/100.0) ) 
   AS blended_cost_per_1m
FROM costs c
ORDER BY c.date, c.company;

-- Vue: break-even standard (1M tokens / abo / mois, marge 70%)
CREATE OR REPLACE VIEW v_break_even_standard_dynamic AS
WITH params AS (SELECT 1000000.0::NUMERIC AS tokens_per_user, 0.70::NUMERIC AS target_margin),
joined AS (
  SELECT le.date, le.company, v.blended_cost_per_1m
  FROM llm_economics le
  JOIN v_cost_per_1m_dynamic v USING (date, company)
)
SELECT
  j.date,
  j.company,
  j.blended_cost_per_1m,
  (j.blended_cost_per_1m * (SELECT tokens_per_user FROM params) / 1000000.0) AS cost_per_user_month,
  (j.blended_cost_per_1m * (SELECT tokens_per_user FROM params) / 1000000.0) / (1 - (SELECT target_margin FROM params)) AS break_even_price_usd
FROM joined j
ORDER BY j.date, j.company;
