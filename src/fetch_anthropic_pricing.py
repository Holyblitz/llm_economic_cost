#!/usr/bin/env python3
import argparse, os, sys, time, csv
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

def fetch_anthropic_pricing(user_agent: str):
    url = "https://www.anthropic.com/api#pricing"
    headers = {"User-Agent": user_agent}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    text = " ".join(soup.get_text(" ", strip=True).split())
    # Heuristique: capture la section "Pricing"
    # TODO: affiner avec des sélecteurs spécifiques si la page a des tables identifiables
    if "pricing" in text.lower():
        rows.append({"model":"unknown","price_per_million_input":"","price_per_million_output":"","currency":"USD","source_url":url,"raw":text[:1200]})
    return rows

def main():
    load_dotenv()
    ua = os.getenv("HTTP_USER_AGENT", "llm-econ-research-bot/0.1")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Chemin CSV de sortie")
    args = ap.parse_args()

    rows = fetch_anthropic_pricing(ua)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model","price_per_million_input","price_per_million_output","currency","source_url","raw"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {args.out}")

if __name__ == "__main__":
    main()
