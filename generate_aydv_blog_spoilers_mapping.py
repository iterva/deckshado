"""
Generate Cloudinary fetch URLs for AYDV blog spoiler cards.

This avoids API uploads when Cloudinary credentials are unavailable, while still
serving assets through Cloudinary (including crops for multi-card images).

Inputs:
  - cartas-blog3/extracted/manifest.csv

Output:
  - aydv_blog_spoilers_mapping.json (slug_key -> cloudinary_fetch_url)

Usage:
  c:/Users/terva/Documents/deckshadow/.venv-1/Scripts/python.exe generate_aydv_blog_spoilers_mapping.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "cartas-blog3" / "extracted" / "manifest.csv"
OUTPUT_PATH = ROOT / "aydv_blog_spoilers_mapping.json"

CLOUDINARY_FETCH_BASE = "https://res.cloudinary.com/drw7y27sm/image/fetch"

SOURCE_URLS: Dict[str, str] = {
    "d5_46c77f68-7677-4320-94f1-0b0c696f2940.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/d5_46c77f68-7677-4320-94f1-0b0c696f2940.png?v=1780090769",
    "Demonios_del_abismo_17.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Demonios_del_abismo_17.png?v=1780090769",
    "Lahmu_Inmortal_0.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Lahmu_Inmortal_0.png?v=1780090770",
    "Nefandos_194.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Nefandos_194.png?v=1780090769",
    "Satanas_0.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Satanas_0.png?v=1780090769",
    "azi_1.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/azi_1.png?v=1780088600",
    "azi_2.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/azi_2.png?v=1780088600",
    "Escamas_de_Azi_229.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Escamas_de_Azi_229.png?v=1780088426",
    "Gran_Dragon_3.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Gran_Dragon_3.png?v=1780088426",
    "Leviathan_4.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Leviathan_4.png?v=1780088426",
    "Wyrm_de_la_Plaga_8.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Wyrm_de_la_Plaga_8.png?v=1780088426",
    "d1_6ed5cab9-f3c8-450b-8008-8318f873bc24.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/d1_6ed5cab9-f3c8-450b-8008-8318f873bc24.png?v=1780089251",
    "d2_7e83f45a-56dd-4d82-985d-de86053e6433.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/d2_7e83f45a-56dd-4d82-985d-de86053e6433.png?v=1780089251",
    "d3_5d5e5345-b3c4-458f-a668-2a207be87e92.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/d3_5d5e5345-b3c4-458f-a668-2a207be87e92.png?v=1780089251",
    "d4_0ef04ab6-91f8-47f9-8a79-bb4cdefd6ce9.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/d4_0ef04ab6-91f8-47f9-8a79-bb4cdefd6ce9.png?v=1780089251",
    "Lucifer_9.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Lucifer_9.png?v=1780088997",
    "Morgana_09.png": "https://cdn.shopify.com/s/files/1/0103/3601/0303/files/Morgana_09.png?v=1780088997",
}

# Source image horizontal split layout (left-to-right widths).
SPLIT_LAYOUTS: Dict[str, Tuple[int, ...]] = {
    "d5_46c77f68-7677-4320-94f1-0b0c696f2940.png": (386, 386),
    "d1_6ed5cab9-f3c8-450b-8008-8318f873bc24.png": (390, 391),
    "d2_7e83f45a-56dd-4d82-985d-de86053e6433.png": (381, 382),
    "d3_5d5e5345-b3c4-458f-a668-2a207be87e92.png": (387, 388),
    "d4_0ef04ab6-91f8-47f9-8a79-bb4cdefd6ce9.png": (383, 384),
    "azi_2.png": (386, 386),
    "azi_1.png": (256, 256, 258),
}


def key_from_card(card: str) -> str:
    return card.strip().lower().replace(" ", "_")


def build_fetch_url(source_url: str, crop: Tuple[int, int, int, int] | None = None) -> str:
    encoded = quote(source_url, safe="")
    if crop is None:
        return f"{CLOUDINARY_FETCH_BASE}/{encoded}"
    x, y, w, h = crop
    transform = f"c_crop,x_{x},y_{y},w_{w},h_{h}"
    return f"{CLOUDINARY_FETCH_BASE}/{transform}/{encoded}"


def crop_for_mode(source: str, mode: str, width: int, height: int) -> Tuple[int, int, int, int] | None:
    if mode == "single-copy":
        return None

    layout = SPLIT_LAYOUTS.get(source)
    if not layout:
        raise ValueError(f"Missing split layout for source: {source}")

    if mode in ("split-left", "split-1"):
        return (0, 0, width, height)

    if mode in ("split-right", "split-2"):
        x = layout[0]
        return (x, 0, width, height)

    if mode == "split-3":
        x = layout[0] + layout[1]
        return (x, 0, width, height)

    raise ValueError(f"Unsupported split mode: {mode}")


def verify_url(url: str) -> bool:
    try:
        response = requests.get(url, timeout=30, stream=True)
        return response.status_code == 200 and "image" in (response.headers.get("content-type") or "").lower()
    except Exception:
        return False


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")

    mapping: Dict[str, str] = {}
    rows = []

    with MANIFEST_PATH.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded manifest rows: {len(rows)}")

    for row in rows:
        card = row["card"]
        source = row["source"]
        mode = row["mode"]
        width = int(row["width"])
        height = int(row["height"])

        source_url = SOURCE_URLS.get(source)
        if not source_url:
            raise ValueError(f"Missing source URL for {source}")

        crop = crop_for_mode(source, mode, width, height)
        fetch_url = build_fetch_url(source_url, crop)
        mapping[key_from_card(card)] = fetch_url

    ok = 0
    failed = 0
    for key, url in sorted(mapping.items()):
        if verify_url(url):
            ok += 1
        else:
            failed += 1
            print(f"VERIFY_FAIL {key}: {url}")

    if failed:
        raise SystemExit(f"Verification failed for {failed} URLs")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"Verified URLs: {ok}")
    print(f"Mapping saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
