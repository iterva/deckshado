"""
Proxy para obtener precios de TCGPlayer para cartas de Riftbound.

Usa scraping ligero de la API de búsqueda de TCGPlayer.
Cachea en memoria con un TTL de 30 minutos.
"""
import time
import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache en memoria: { card_name_lower: (timestamp, data_dict) }
_price_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 30 * 60  # 30 minutos


TCG_SEARCH_URL = "https://mp-search-api.tcgplayer.com/v1/search/request"
TCG_PRODUCT_LINE = "riftbound-league-of-legends-trading-card-game"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _search_tcgplayer(card_name: str) -> Optional[dict]:
    """Busca un producto en TCGPlayer y devuelve el primer resultado que haga match."""
    body = {
        "algorithm": "",
        "from": 0,
        "size": 10,
        "filters": {
            "term": {
                "productLineName": [TCG_PRODUCT_LINE],
            },
            "range": {},
            "match": {},
        },
        "listingSearch": {
            "filters": {
                "term": {"sellerStatus": "Live", "channelId": 0},
                "range": {"quantity": {"gte": 1}},
                "exclude": {"channelExclusion": 0},
            },
        },
        "context": {"cart": {}, "shippingCountry": "US"},
        "settings": {"useFuzzySearch": True, "didYouMean": {}},
        "sort": {},
    }

    try:
        resp = requests.post(
            TCG_SEARCH_URL,
            params={"q": card_name, "isList": "false"},
            json=body,
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("TCGPlayer search returned %d for '%s'", resp.status_code, card_name)
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        aggregations = results[0] if results else {}
        product_results = aggregations.get("results", [])
        if not product_results:
            return None

        # Buscar match exacto primero, luego parcial
        name_lower = card_name.lower().strip()
        best = None
        for item in product_results:
            product_name = (item.get("productName") or "").lower()
            if product_name == name_lower:
                best = item
                break
            if name_lower in product_name and best is None:
                best = item

        if best is None and product_results:
            best = product_results[0]

        if best is None:
            return None

        return {
            "product_name": best.get("productName", ""),
            "market_price": best.get("marketPrice"),
            "low_price": best.get("lowestPrice"),
            "mid_price": best.get("medianPrice"),
            "high_price": None,
            "product_url": f"https://www.tcgplayer.com/product/{int(best['productId'])}" if best.get("productId") else None,
            "image_url": best.get("imageUrl", ""),
        }

    except requests.RequestException as e:
        logger.error("TCGPlayer request error for '%s': %s", card_name, e)
        return None
    except (ValueError, KeyError) as e:
        logger.error("TCGPlayer parse error for '%s': %s", card_name, e)
        return None


def get_tcg_price(card_name: str) -> Optional[dict]:
    """Obtiene precio de TCGPlayer con caché."""
    key = card_name.lower().strip()
    now = time.time()

    if key in _price_cache:
        ts, data = _price_cache[key]
        if now - ts < CACHE_TTL:
            return data

    data = _search_tcgplayer(card_name)
    if data is not None:
        _price_cache[key] = (now, data)
    else:
        # Cache negativo corto (5 min) para no reintentar constantemente
        _price_cache[key] = (now - CACHE_TTL + 300, {})

    return data


def get_tcg_prices_batch(card_names: list[str]) -> list[dict]:
    """Obtiene precios para múltiples cartas (máx 20)."""
    results = []
    for name in card_names[:20]:
        price = get_tcg_price(name)
        if price:
            results.append({"card_name": name, **price})
        else:
            results.append({"card_name": name, "market_price": None})
        # Pequeño delay para no saturar
        time.sleep(0.15)
    return results
