"""
Proxy para obtener precios de TCGMatch para cartas de Riftbound.

Usa el endpoint JSON publico de TCGMatch y cachea respuestas en memoria.
"""
import logging
import re
import time
import unicodedata
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# Cache en memoria: { card_name_lower: (timestamp, data_dict) }
_price_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 15 * 60  # 15 minutos

TCGMATCH_SEARCH_URL = "https://api.tcgmatch.cl/catalog/search"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://tcgmatch.cl",
    "Referer": "https://tcgmatch.cl/",
}


def _normalize_name(value: str) -> str:
    """Normaliza nombre para comparar resultados de manera tolerante."""
    text = (value or "").strip().lower()
    text = text.replace("—", "-").replace("–", "-")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _candidate_queries(card_name: str) -> list[str]:
    """Genera variantes de consulta para mejorar el match."""
    base = (card_name or "").strip()
    if not base:
        return []

    base = base.replace("—", "-").replace("–", "-")
    base = re.sub(r"\s+", " ", base).strip()
    candidates = [base]

    no_paren = re.sub(r"\s*\([^)]*\)", "", base).strip()
    if no_paren and no_paren != base:
        candidates.append(no_paren)

    if "//" in no_paren:
        left = no_paren.split("//", 1)[0].strip()
        if left:
            candidates.append(left)

    if " - " in no_paren:
        _, right = no_paren.split(" - ", 1)
        right = right.strip()
        if right:
            candidates.append(right)

    seen = set()
    ordered: list[str] = []
    for item in candidates:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            ordered.append(item)
    return ordered


def _pick_best_product(products: list[dict], query: str) -> Optional[dict]:
    """Elige el mejor producto por similitud de nombre."""
    if not products:
        return None

    q = _normalize_name(query)
    if not q:
        return products[0]

    best = None
    best_score = -1

    for item in products:
        name = _normalize_name(item.get("name") or "")
        if not name:
            continue

        score = 0
        if name == q:
            score = 100
        elif name.startswith(q):
            score = 80
        elif q in name:
            score = 70
        elif any(part and part in name for part in q.split(" ")):
            score = 40

        if item.get("marketPrice") is not None:
            score += 8
        if item.get("lowestPrice") is not None:
            score += 4

        if score > best_score:
            best_score = score
            best = item

    return best or products[0]


def _search_tcgmatch(card_name: str) -> Optional[dict]:
    """Busca producto en TCGMatch y devuelve precio normalizado."""
    try:
        resp = requests.get(
            TCGMATCH_SEARCH_URL,
            params={"q": card_name},
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("TCGMatch search returned %d for '%s'", resp.status_code, card_name)
            return None

        payload = resp.json() if resp.content else {}
        products = payload.get("products") if isinstance(payload, dict) else []
        if not isinstance(products, list) or not products:
            return None

        best = _pick_best_product(products, card_name)
        if not best:
            return None

        product_id = best.get("id")
        return {
            "product_name": best.get("name") or card_name,
            "market_price": best.get("marketPrice"),
            "low_price": best.get("lowestPrice"),
            "currency": "CLP",
            "listings_count": best.get("listingsCount"),
            "product_url": f"https://tcgmatch.cl/producto/catalogo/{product_id}" if product_id else None,
            "image_url": best.get("image"),
        }

    except requests.RequestException as e:
        logger.error("TCGMatch request error for '%s': %s", card_name, e)
        return None
    except ValueError as e:
        logger.error("TCGMatch parse error for '%s': %s", card_name, e)
        return None


def get_tcgmatch_price(card_name: str) -> Optional[dict]:
    """Obtiene precio de TCGMatch con cache en memoria."""
    key = (card_name or "").lower().strip()
    if not key:
        return None

    now = time.time()
    if key in _price_cache:
        ts, data = _price_cache[key]
        if now - ts < CACHE_TTL:
            return data

    data = None
    for query in _candidate_queries(card_name):
        data = _search_tcgmatch(query)
        if data and (data.get("market_price") is not None or data.get("low_price") is not None):
            break

    if data is not None:
        data["card_name"] = card_name
        _price_cache[key] = (now, data)
    else:
        # Cache negativo corto (5 min)
        _price_cache[key] = (now - CACHE_TTL + 300, {})

    return data
