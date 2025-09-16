#!/usr/bin/env python3
import argparse, os, csv, requests

BASE_URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"

def fetch_us_commercial_price_monthly(api_key: str, start: str, end: str):
    """
    Prix commercial US mensuel = sum(revenue)/sum(sales) agrégé sur tous les états.
    start/end: 'YYYY-MM'
    Retour: liste {date (YYYY-MM-01), price_usd_per_kwh}
    """
    params = {
        "api_key": api_key,
        "frequency": "monthly",
        "data[0]": "revenue",
        "data[1]": "sales",
        "facets[sectorid][]": "COM",      # Commercial
        # Ne **pas** fixer stateid → on récupère tous les états et on agrège
        "start": start,
        "end": end,
        "length": 5000,                   # large pour couvrir états x mois
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    # *** v2: les données sont sous 'response' -> 'data' ***
    data = js.get("response", {}).get("data", [])

    by_period = {}
    for rec in data:
        period = rec.get("period")   # 'YYYY-MM'
        rev = rec.get("revenue")
        sales = rec.get("sales")
        if not period or rev is None or sales is None:
            continue
        try:
            rev = float(rev)         # million dollars
            sales = float(sales)     # million kWh
        except ValueError:
            continue
        agg = by_period.setdefault(period, {"rev": 0.0, "sales": 0.0})
        agg["rev"] += rev
        agg["sales"] += sales

    rows = []
    for period in sorted(by_period.keys()):
        agg = by_period[period]
        if agg["sales"] > 0:
            price = agg["rev"] / agg["sales"]  # USD/kWh (les "millions" s'annulent)
            rows.append({
                "date": f"{period}-01",
                "price_usd_per_kwh": price,
                "sector": "commercial",
                "region": "US_weighted",
                "source_series_id": "retail-sales sum(revenue)/sum(sales) COM monthly",
                "source_url": BASE_URL,
            })
    return rows

def main():
    ap = argparse.ArgumentParser(description="EIA v2 → prix élec. commercial US mensuel (agrégé États).")
    ap.add_argument("--start", required=True, help="YYYY-MM, ex: 2023-08")
    ap.add_argument("--end",   required=True, help="YYYY-MM, ex: 2026-09")
    ap.add_argument("--out",   required=True, help="CSV de sortie")
    args = ap.parse_args()

    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        raise SystemExit("EIA_API_KEY manquant (export EIA_API_KEY=...)")

    rows = fetch_us_commercial_price_monthly(api_key, args.start, args.end)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "date","price_usd_per_kwh","sector","region","source_series_id","source_url"
        ])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.out}")
    if rows:
        print("Sample first:", rows[:2])
        print("Sample last :", rows[-2:])

if __name__ == "__main__":
    main()




