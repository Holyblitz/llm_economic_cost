#!/usr/bin/env python3
import argparse, os, sys, time, csv
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

def fetch_openai_pricing(user_agent: str):
    url = "https://openai.com/pricing"
    headers = {"User-Agent": user_agent}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # NOTE: Les sélecteurs peuvent changer. On capture le maximum d'infos en fallback.
    rows = []
    for card in soup.find_all(["section","div"]):
        text = " ".join(card.get_text(" ", strip=True).split())
        if not text:
            continue
        # Heuristique simple : cherche des lignes avec pattern "$x / 1M"
        if "/ 1M" in text or "per 1M" in text or "per‑1M" in text or "1M tokens" in text:
            rows.append({"model":"unknown","price_per_million_input":"","price_per_million_output":"","currency":"USD","source_url":url,"raw":text})
    return rows

def main():
    load_dotenv()
    ua = os.getenv("HTTP_USER_AGENT", "llm-econ-research-bot/0.1")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Chemin CSV de sortie")
    args = ap.parse_args()

    rows = fetch_openai_pricing(ua)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model","price_per_million_input","price_per_million_output","currency","source_url","raw"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {args.out}")

if __name__ == "__main__":
    main()
