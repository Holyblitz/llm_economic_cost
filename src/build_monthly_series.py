#!/usr/bin/env python3
import argparse, os
import pandas as pd
import numpy as np

def month_range(start_yyyy_mm: str, end_yyyy_mm: str):
    start = start_yyyy_mm + "-01"
    end   = end_yyyy_mm   + "-01"
    return pd.date_range(start=start, end=end, freq="MS")

def load_csv(path):
    return pd.read_csv(path) if (path and os.path.exists(path)) else pd.DataFrame()

def normalize_month_str(s):
    s = str(s)
    if len(s) == 7:   # 'YYYY-MM'
        return s + "-01"
    if len(s) == 10:  # 'YYYY-MM-DD'
        return s
    if len(s) == 6:   # 'YYYYMM'
        return f"{s[:4]}-{s[4:6]}-01"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY-MM (ex: 2023-08)")
    ap.add_argument("--end",   required=True, help="YYYY-MM (ex: 2026-09)")
    ap.add_argument("--out",   required=True, help="CSV de sortie")
    ap.add_argument("--eia_prices", default="data/eia_electricity_us_commercial.csv")
    ap.add_argument("--gpu_overrides", default="data/gpu_hour_overrides.csv")
    args = ap.parse_args()

    # 1) Grille mensuelle OpenAI/Anthropic
    dates = month_range(args.start, args.end)
    companies = ["OpenAI", "Anthropic"]
    base_rows = []
    for d in dates:
        d_iso = d.date().isoformat()
        for company in companies:
            base_rows.append({
                "date": d_iso,
                "company": company,
                "run_rate_revenue_usd": None,
                "tokens_volume_est_m": None,
                "mix_mini_pct": 85.0,
                "mix_flagship_pct": 15.0,
                "gpu_type_mini": "L4",
                "gpu_type_flagship": "H100",
                # Valeurs par défaut (seront remplacées si overrides présents)
                "gpu_price_hour_mini": 0.80,
                "gpu_price_hour_flagship": 3.00,
                "gpu_power_w_mini": 72.0,
                "gpu_power_w_flagship": 700.0,
                "throughput_tok_s_mini": 120.0,
                "throughput_tok_s_flagship": 280.0,
                "pue": 1.09,
                "electricity_price_usd_kwh": None,
                "price_per_million_tokens_usd": None,
                "cost_per_million_tokens_usd": None,
                "gross_margin_pct": None
            })
    df = pd.DataFrame(base_rows)

    # 2) Électricité EIA (join exact + ffill)
    df_eia = load_csv(args.eia_prices)
    if not df_eia.empty and {"date","price_usd_per_kwh"}.issubset(df_eia.columns):
        eia = df_eia.copy()
        eia["date"] = eia["date"].apply(normalize_month_str)
        eia = eia.dropna(subset=["date"])
        eia = eia.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        grid = pd.date_range(df["date"].min(), df["date"].max(), freq="MS").strftime("%Y-%m-%d")
        eia = eia.set_index("date").reindex(grid)
        eia["price_usd_per_kwh"] = eia["price_usd_per_kwh"].ffill().bfill()
        eia = eia.reset_index().rename(columns={"index":"date"})
        df = df.merge(eia[["date","price_usd_per_kwh"]], on="date", how="left")
        df["electricity_price_usd_kwh"] = df["price_usd_per_kwh"]
        df = df.drop(columns=["price_usd_per_kwh"])
    else:
        df["electricity_price_usd_kwh"] = 0.132  # fallback

    # 3) Overrides $/GPU-h (H100/L4) — simple & robuste
    ovr = load_csv(args.gpu_overrides)
    if not ovr.empty and {"date","H100","L4"}.issubset(ovr.columns):
        o = ovr.copy()
        o["date"] = o["date"].apply(normalize_month_str)
        o = o.dropna(subset=["date"])
        o = o.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        grid = pd.DataFrame({"date": pd.date_range(df["date"].min(), df["date"].max(), freq="MS").strftime("%Y-%m-%d")})
        o = grid.merge(o[["date","H100","L4"]], on="date", how="left").sort_values("date").ffill()
        df = df.merge(o, on="date", how="left")
        if "H100" in df.columns:
            df["gpu_price_hour_flagship"] = df["H100"].fillna(df["gpu_price_hour_flagship"])
        if "L4" in df.columns:
            df["gpu_price_hour_mini"] = df["L4"].fillna(df["gpu_price_hour_mini"])
        for col in ["H100","L4"]:
            if col in df.columns:
                df = df.drop(columns=[col])

    # 3.5) Sanity: forcer les types numériques (avant calculs)
    num_cols = [
        "gpu_price_hour_mini", "gpu_price_hour_flagship",
        "gpu_power_w_mini", "gpu_power_w_flagship",
        "throughput_tok_s_mini", "throughput_tok_s_flagship",
        "pue", "electricity_price_usd_kwh",
        "mix_mini_pct", "mix_flagship_pct"
    ]
    def _to_num(s):
        if isinstance(s, str):
            s = s.strip().replace("€","").replace("$","").replace(" ", "").replace(",", ".")
        return pd.to_numeric(s, errors="coerce")
    for c in num_cols:
        if c in df.columns:
            df[c] = df[c].apply(_to_num)
    # Valeurs par défaut en cas de trous
    df["gpu_price_hour_mini"].fillna(0.80, inplace=True)
    df["gpu_price_hour_flagship"].fillna(3.00, inplace=True)
    df["gpu_power_w_mini"].fillna(72.0, inplace=True)
    df["gpu_power_w_flagship"].fillna(700.0, inplace=True)
    df["throughput_tok_s_mini"].fillna(120.0, inplace=True)
    df["throughput_tok_s_flagship"].fillna(280.0, inplace=True)
    df["pue"].fillna(1.09, inplace=True)
    df["electricity_price_usd_kwh"].fillna(0.132, inplace=True)
    df["mix_mini_pct"].fillna(85.0, inplace=True)
    df["mix_flagship_pct"].fillna(15.0, inplace=True)

    # 4) (Optionnel) paliers réalistes — décommente si tu veux plus de dynamique
    # df.loc[df["date"] >= "2025-01-01", "mix_mini_pct"] = 80.0
    # df.loc[df["date"] >= "2025-01-01", "mix_flagship_pct"] = 20.0
    # df.loc[df["date"] >= "2025-04-01", "throughput_tok_s_mini"] = 150.0
    # df.loc[df["date"] >= "2025-04-01", "throughput_tok_s_flagship"] = 320.0
    # df.loc[df["date"] >= "2025-06-01", "pue"] = 1.06

    # 5) Calculs coût / 1M tokens (ordre correct)
    df["gpu_hours_1m_mini"] = 1_000_000.0 / (df["throughput_tok_s_mini"]     * 3600.0)
    df["gpu_hours_1m_flag"] = 1_000_000.0 / (df["throughput_tok_s_flagship"] * 3600.0)

    df["elec_cost_1m_mini"] = (df["gpu_power_w_mini"]/1000.0)     * df["pue"] * df["gpu_hours_1m_mini"] * df["electricity_price_usd_kwh"]
    df["elec_cost_1m_flag"] = (df["gpu_power_w_flagship"]/1000.0) * df["pue"] * df["gpu_hours_1m_flag"] * df["electricity_price_usd_kwh"]

    df["gpu_cost_1m_mini"] = df["gpu_hours_1m_mini"] * df["gpu_price_hour_mini"]
    df["gpu_cost_1m_flag"] = df["gpu_hours_1m_flag"] * df["gpu_price_hour_flagship"]

    df["total_1m_mini"] = df["elec_cost_1m_mini"] + df["gpu_cost_1m_mini"]
    df["total_1m_flag"] = df["elec_cost_1m_flag"] + df["gpu_cost_1m_flag"]

    df["cost_per_million_tokens_usd"] = (
        df["total_1m_mini"] * (df["mix_mini_pct"]/100.0) +
        df["total_1m_flag"] * (df["mix_flagship_pct"]/100.0)
    )

        # 5.5) Abonnements break-even selon profils d’usage (marge cible)
    TARGET_MARGIN = 0.70  # 70%
    # Profils d’usage (tokens/mois/utilisateur) — ajuste comme tu veux
    TIER_LITE     = 200_000
    TIER_STANDARD = 1_000_000
    TIER_PRO      = 5_000_000

    def price_for(tokens):
        return df["cost_per_million_tokens_usd"] * (tokens / 1_000_000.0) / (1.0 - TARGET_MARGIN)

    df["break_even_lite_usd"]     = price_for(TIER_LITE)
    df["break_even_standard_usd"] = price_for(TIER_STANDARD)
    df["break_even_pro_usd"]      = price_for(TIER_PRO)


    # 6) Sortie
    df["price_per_million_tokens_usd"] = None

    print("EIA uniques dans la sortie:",
          df["electricity_price_usd_kwh"].nunique(),
          "| min/max:",
          float(df["electricity_price_usd_kwh"].min()),
          float(df["electricity_price_usd_kwh"].max()))
    print("GPU $/h échantillon:",
          df[["date","company","gpu_price_hour_mini","gpu_price_hour_flagship"]].head(4).to_string(index=False))

    cols = [
        "date","company","run_rate_revenue_usd","tokens_volume_est_m",
        "mix_mini_pct","mix_flagship_pct",
        "gpu_type_mini","gpu_type_flagship",
        "gpu_price_hour_mini","gpu_price_hour_flagship",
        "gpu_power_w_mini","gpu_power_w_flagship",
        "throughput_tok_s_mini","throughput_tok_s_flagship",
        "pue","electricity_price_usd_kwh",
        "price_per_million_tokens_usd","cost_per_million_tokens_usd","gross_margin_pct",
        "break_even_lite_usd","break_even_standard_usd","break_even_pro_usd"
    ]
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    df[cols].to_csv(args.out, index=False)
    print(f"Wrote monthly series to {args.out} with {len(df)} rows")

if __name__ == "__main__":
    main()


