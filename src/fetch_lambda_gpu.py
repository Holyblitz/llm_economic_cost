#!/usr/bin/env python3
import argparse, os, csv, re, asyncio
from datetime import datetime
from bs4 import BeautifulSoup

# Playwright
from playwright.async_api import async_playwright

URL = "https://lambdalabs.com/service/gpu-cloud#pricing"

# On veut au minimum H100 et L4
TARGETS = ["H100", "L4"]

PRICE_RE = re.compile(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*(?:hour|hr)", re.I)

async def render_and_get_html(url: str, timeout_ms: int = 30000) -> str:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        # Va à la page et attend que le réseau soit calme (utile pour hydratation JS)
        await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        html = await page.content()
        await browser.close()
        return html

def extract_prices_from_html(html: str):
    """
    Heuristique robuste:
    - Scan tout le texte rendu
    - Pour chaque mention de modèle (H100/L4), cherche un prix "$X.xx / hour" dans le voisinage
    - Conserve le plus petit prix trouvé par modèle (au cas où plusieurs occurrences)
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    rows = []
    for model in TARGETS:
        # Cherche l'index du modèle dans le texte rendu
        for m in re.finditer(model, text, flags=re.I):
            start = max(0, m.start() - 200)
            end = min(len(text), m.end() + 200)
            window = text[start:end]
            price_m = PRICE_RE.search(window)
            if price_m:
                price = float(price_m.group(1))
                rows.append({"gpu_model": model, "hourly_price_usd": price})

    # dédoublonnage: garde le plus petit prix observé par modèle
    best = {}
    for r in rows:
        k = r["gpu_model"].upper()
        if k not in best or r["hourly_price_usd"] < best[k]["hourly_price_usd"]:
            best[k] = r
    out = []
    fetched_at = datetime.utcnow().strftime("%Y-%m-01")
    for k, v in best.items():
        out.append({
            "fetched_at": fetched_at,
            "gpu_model": k,
            "hourly_price_usd": v["hourly_price_usd"],
            "source_url": URL
        })
    return out

async def main_async(out_path: str):
    html = await render_and_get_html(URL)
    rows = extract_prices_from_html(html)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fetched_at","gpu_model","hourly_price_usd","source_url"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    if rows:
        print("Sample:", rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    asyncio.run(main_async(args.out))

if __name__ == "__main__":
    main()
