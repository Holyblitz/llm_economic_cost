#!/usr/bin/env python3
import argparse, os, csv, requests
from datetime import datetime

CANDIDATES = [
    # Officiel public browse (le plus courant)
    "https://vast.ai/api/v0/bundles/public",
    # Variantes vues dans certains environnements / proxys
    "https://vast.ai/api/v0/bundles",                 # parfois ?public=true
    "https://vast.ai/api/v0/market/bundles",          # alias marché
]

QUERY = 'gpu_name in ["H100","H200","A100","L4"]'

def try_fetch(url: str):
    params = {
        "q": QUERY,
        "limit": 200,
        "order": "score",
        "desc": "true",
    }
    headers = {
        "User-Agent": os.getenv("HTTP_USER_AGENT", "llm-econ-research-bot/0.1"),
        "Accept": "application/json",
    }
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    js = r.json()
    # les réponses Vast peuvent mettre la liste sous "offers" ou "data"
    offers = js.get("offers") or js.get("data") or []
    return offers

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    last_err = None
    offers = []
    chosen = None
    for url in CANDIDATES:
        try:
            offers = try_fetch(url)
            chosen = url
            break
        except Exception as e:
            last_err = e
            continue

    if chosen is None:
        raise SystemExit(
            "Impossible d'atteindre Vast.ai API via les endpoints testés.\n"
            f"Dernière erreur: {last_err}\n"
            "Astuce: teste dans ton shell:\n"
            "  curl -s 'https://vast.ai/api/v0/bundles/public?limit=3' | head\n"
        )

    fetched_at = datetime.utcnow().strftime("%Y-%m-01")
    rows = []
    for it in offers:
        rows.append({
            "fetched_at": fetched_at,
            "gpu_model": it.get("gpu_name"),
            "hourly_price_usd": it.get("dph"),
            "location": it.get("geolocation") or it.get("country"),
            "provider_id": it.get("id"),
            "spot": bool(it.get("is_spot")) if "is_spot" in it else None,
            "source_url": chosen,
        })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "fetched_at","gpu_model","hourly_price_usd","location","provider_id","spot","source_url"
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Endpoint OK: {chosen}")
    print(f"Wrote {len(rows)} rows to {args.out}")

if __name__ == "__main__":
    main()


